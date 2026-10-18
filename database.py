"""SQLite data layer: users, products, orders. Money is stored as integer centavos."""
import hashlib
import hmac
import secrets
import sqlite3
import uuid
from pathlib import Path

from PIL import Image, ImageOps

from utils import DATA_DIR, now_str, validate_password, validate_username

DB_PATH = DATA_DIR / "brewpos.db"
IMAGE_DIR = DATA_DIR / "images"
_ITERATIONS = 200_000
_conn = None


class StockError(Exception):
    """Raised at checkout when an item no longer has enough stock."""


# ------------------------------------------------------------ connection
def init_db() -> None:
    global _conn
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    _conn = sqlite3.connect(DB_PATH)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA foreign_keys = ON")
    _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'cashier')),
            secret_question TEXT NOT NULL,
            secret_answer_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            category TEXT NOT NULL,
            price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
            stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
            image TEXT
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            payment TEXT NOT NULL CHECK (payment IN ('Cash', 'Gcash')),
            total_cents INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
            name TEXT NOT NULL,
            price_cents INTEGER NOT NULL,
            qty INTEGER NOT NULL CHECK (qty > 0)
        );
        """
    )
    _conn.commit()
    _seed_products()


def close_db() -> None:
    if _conn is not None:
        _conn.close()


def _seed_products() -> None:
    """Sample menu from the design, only when the table is empty."""
    if _conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]:
        return
    sample = [
        ("Espresso", "Coffee", 9000, 32), ("Cappuccino", "Coffee", 12000, 20),
        ("Cafe Latte", "Coffee", 12000, 18), ("Chamomile Tea", "Tea", 9000, 15),
        ("Croissant", "Pastry", 8500, 10), ("Blueberry Muffin", "Pastry", 9500, 0),
        ("Sourdough Loaf", "Bread", 15000, 8),
    ]
    with _conn:
        _conn.executemany(
            "INSERT INTO products (name, category, price_cents, stock) VALUES (?, ?, ?, ?)", sample
        )


# --------------------------------------------------------------- hashing
def _hash(secret: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def _verify(secret: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), bytes.fromhex(salt_hex), _ITERATIONS)
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _normalise_answer(answer: str) -> str:
    return " ".join(answer.lower().split())


_DUMMY_HASH = None


# ----------------------------------------------------------------- users
def create_user(username: str, password: str, question: str, answer: str) -> dict:
    """The very first account becomes the admin; every later one is a cashier."""
    username = validate_username(username)
    validate_password(password)
    if not _normalise_answer(answer):
        raise ValueError("Please enter an answer to your secret question.")
    role = "cashier" if _conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] else "admin"
    try:
        with _conn:
            cur = _conn.execute(
                "INSERT INTO users (username, password_hash, role, secret_question, secret_answer_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, _hash(password), role, question, _hash(_normalise_answer(answer))),
            )
    except sqlite3.IntegrityError:
        raise ValueError("That username is already taken.")
    return {"id": cur.lastrowid, "username": username, "role": role}


def authenticate(username: str, password: str):
    global _DUMMY_HASH
    row = _conn.execute(
        "SELECT id, username, role, password_hash FROM users WHERE username = ?", (username.strip(),)
    ).fetchone()
    if row is None:  # same work either way so timing doesn't reveal valid usernames
        _DUMMY_HASH = _DUMMY_HASH or _hash("dummy")
        _verify(password, _DUMMY_HASH)
        return None
    if not _verify(password, row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"], "role": row["role"]}


def verify_secret(username: str, question: str, answer: str):
    """Return the user id if username + question + answer all match, else None."""
    row = _conn.execute(
        "SELECT id, secret_question, secret_answer_hash FROM users WHERE username = ?",
        (username.strip(),),
    ).fetchone()
    ok = row is not None and row["secret_question"] == question
    stored = row["secret_answer_hash"] if row is not None else _hash("dummy")
    ok = _verify(_normalise_answer(answer), stored) and ok
    return row["id"] if ok else None


def set_password(user_id: int, new_password: str) -> None:
    validate_password(new_password)
    with _conn:
        _conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (_hash(new_password), user_id))


# -------------------------------------------------------------- products
def list_products(search: str = "", category: str = "All") -> list:
    sql, args = "SELECT * FROM products WHERE 1=1", []
    if search.strip():
        sql += " AND name LIKE ? ESCAPE '\\'"
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        args.append(f"%{escaped}%")
    if category != "All":
        sql += " AND category = ?"
        args.append(category)
    return _conn.execute(sql + " ORDER BY id", args).fetchall()     # menu order = order added


def get_product(product_id: int):
    return _conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()


def add_product(name: str, category: str, price_cents: int, stock: int, image=None) -> int:
    try:
        with _conn:
            cur = _conn.execute(
                "INSERT INTO products (name, category, price_cents, stock, image) VALUES (?, ?, ?, ?, ?)",
                (name.strip(), category, price_cents, stock, image),
            )
    except sqlite3.IntegrityError:
        raise ValueError("A product with that name already exists.")
    return cur.lastrowid


def update_product(product_id: int, name: str, category: str, price_cents: int, stock: int, image) -> None:
    try:
        with _conn:
            _conn.execute(
                "UPDATE products SET name=?, category=?, price_cents=?, stock=?, image=? WHERE id=?",
                (name.strip(), category, price_cents, stock, image, product_id),
            )
    except sqlite3.IntegrityError:
        raise ValueError("A product with that name already exists.")


def restock(product_id: int, qty: int) -> None:
    with _conn:
        _conn.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (qty, product_id))


def delete_product(product_id: int) -> None:
    row = get_product(product_id)
    with _conn:
        _conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    if row is not None:
        delete_image(row["image"])


# ---------------------------------------------------------------- images
def save_product_image(source_path: str) -> str:
    """Validate, shrink and copy a chosen photo into data/images; returns the stored file name."""
    try:
        with Image.open(source_path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((600, 600))
            name = f"{uuid.uuid4().hex}.png"
            img.save(IMAGE_DIR / name, "PNG")
    except Exception:
        raise ValueError("That file isn't a readable image (try a PNG or JPG).")
    return name


def delete_image(name) -> None:
    if name:
        try:
            (IMAGE_DIR / Path(name).name).unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------- orders
def create_order(user_id: int, payment: str, lines: list) -> int:
    """lines = [(product_id, qty), ...]. All-or-nothing: stock is checked and deducted atomically."""
    if not lines:
        raise ValueError("The cart is empty.")
    try:
        with _conn:
            total, priced = 0, []
            for product_id, qty in lines:
                product = get_product(product_id)
                if product is None:
                    raise StockError("An item in your cart is no longer on the menu.")
                cur = _conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (qty, product_id, qty),
                )
                if cur.rowcount == 0:
                    raise StockError(f"Only {product['stock']} left of {product['name']}.")
                total += product["price_cents"] * qty
                priced.append((product_id, product["name"], product["price_cents"], qty))
            order_id = _conn.execute(
                "INSERT INTO orders (created_at, user_id, payment, total_cents) VALUES (?, ?, ?, ?)",
                (now_str(), user_id, payment, total),
            ).lastrowid
            _conn.executemany(
                "INSERT INTO order_items (order_id, product_id, name, price_cents, qty) "
                "VALUES (?, ?, ?, ?, ?)",
                [(order_id, *item) for item in priced],
            )
    except StockError:
        raise
    return order_id


def _order_filter(start, user_id):
    where, args = "1=1", []
    if start:
        where += " AND o.created_at >= ?"
        args.append(start)
    if user_id is not None:
        where += " AND o.user_id = ?"
        args.append(user_id)
    return where, args


def list_orders(start=None, user_id=None) -> list:
    where, args = _order_filter(start, user_id)
    return _conn.execute(
        f"""SELECT o.id, o.created_at, o.payment, o.total_cents,
                   COALESCE(u.username, '(deleted)') AS cashier,
                   (SELECT group_concat(qty || '× ' || name, ', ')
                      FROM order_items WHERE order_id = o.id) AS items
            FROM orders o LEFT JOIN users u ON u.id = o.user_id
            WHERE {where} ORDER BY o.id DESC""",
        args,
    ).fetchall()


def order_items(order_id: int) -> list:
    return _conn.execute(
        "SELECT name, price_cents, qty FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
    ).fetchall()


def sales_stats(start=None, user_id=None) -> dict:
    where, args = _order_filter(start, user_id)
    total, count = _conn.execute(
        f"SELECT COALESCE(SUM(o.total_cents), 0), COUNT(*) FROM orders o WHERE {where}", args
    ).fetchone()
    best = _conn.execute(
        f"""SELECT oi.name, SUM(oi.qty) AS sold FROM order_items oi
            JOIN orders o ON o.id = oi.order_id WHERE {where}
            GROUP BY oi.name ORDER BY sold DESC, oi.name LIMIT 1""",
        args,
    ).fetchone()
    return {"total_cents": total, "orders": count,
            "best_name": best["name"] if best else None, "best_sold": best["sold"] if best else 0}
