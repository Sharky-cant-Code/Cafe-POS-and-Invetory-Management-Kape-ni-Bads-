"""
database.py
Handles all SQLite database setup and operations for the
Cafe Point of Sale & Inventory Management System.

Every other module (auth, POS screen, inventory screen, reports)
talks to the database ONLY through the functions in this file.
Keeping all SQL in one place makes the rest of the app easier
to read and debug.
"""

import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cafe_pos.db")


def get_connection():
    """Open a new connection to the database.

    We open a fresh connection per call instead of sharing one
    global connection, because Tkinter callbacks can fire from
    different points in the program and SQLite connections are
    not always safe to reuse across contexts.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row      # lets us access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    """Simple salted SHA-256 hash. Good enough for a local school
    project — do NOT use this scheme for a real production app."""
    salt = "cafe_pos_salt"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------
# SCHEMA + SEED DATA
# ---------------------------------------------------------------

def init_db():
    """Create all tables if they don't exist yet, and seed some
    starter data (default admin account, categories, products)
    the first time the app is ever run."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'cashier')),
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category_id INTEGER,
        price REAL NOT NULL DEFAULT 0,
        cost REAL NOT NULL DEFAULT 0,
        stock_qty INTEGER NOT NULL DEFAULT 0,
        reorder_level INTEGER NOT NULL DEFAULT 5,
        unit TEXT NOT NULL DEFAULT 'pc',
        active INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        cashier_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        subtotal REAL NOT NULL,
        discount REAL NOT NULL DEFAULT 0,
        tax REAL NOT NULL DEFAULT 0,
        total REAL NOT NULL,
        payment_method TEXT NOT NULL DEFAULT 'Cash',
        amount_paid REAL NOT NULL,
        change_due REAL NOT NULL,
        FOREIGN KEY (cashier_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS inventory_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        change_qty INTEGER NOT NULL,
        reason TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        user_id INTEGER,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)
    conn.commit()

    # ---- seed default admin account (only if no users yet) ----
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, role, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("admin", hash_password("admin123"), "Administrator", "admin",
             datetime.now().isoformat(timespec="seconds")),
        )
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, role, active, created_at) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("cashier", hash_password("cashier123"), "Sample Cashier", "cashier",
             datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()

    # ---- seed sample categories + products (only if none yet) ----
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        categories = ["Coffee", "Non-Coffee", "Pastries", "Snacks"]
        cur.executemany("INSERT INTO categories (name) VALUES (?)",
                         [(c,) for c in categories])
        conn.commit()

        cat_ids = {row["name"]: row["id"] for row in
                   cur.execute("SELECT id, name FROM categories").fetchall()}

        sample_products = [
            ("Espresso", cat_ids["Coffee"], 90.0, 30.0, 50, 10, "cup"),
            ("Americano", cat_ids["Coffee"], 100.0, 32.0, 50, 10, "cup"),
            ("Cafe Latte", cat_ids["Coffee"], 120.0, 40.0, 50, 10, "cup"),
            ("Cappuccino", cat_ids["Coffee"], 120.0, 40.0, 50, 10, "cup"),
            ("Hot Chocolate", cat_ids["Non-Coffee"], 110.0, 38.0, 40, 8, "cup"),
            ("Iced Tea", cat_ids["Non-Coffee"], 80.0, 25.0, 40, 8, "cup"),
            ("Croissant", cat_ids["Pastries"], 85.0, 35.0, 25, 5, "pc"),
            ("Blueberry Muffin", cat_ids["Pastries"], 95.0, 38.0, 25, 5, "pc"),
            ("Chips", cat_ids["Snacks"], 45.0, 20.0, 30, 6, "pack"),
            ("Sandwich", cat_ids["Snacks"], 130.0, 55.0, 20, 5, "pc"),
        ]
        cur.executemany(
            "INSERT INTO products (name, category_id, price, cost, stock_qty, reorder_level, unit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            sample_products,
        )
        conn.commit()

    conn.close()


# ---------------------------------------------------------------
# USERS / AUTH
# ---------------------------------------------------------------

def verify_login(username: str, password: str):
    """Returns the user row (as a dict) if credentials are valid
    and the account is active, otherwise None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? AND active = 1", (username,)
    ).fetchone()
    conn.close()
    if row and row["password_hash"] == hash_password(password):
        return dict(row)
    return None


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT id, username, full_name, role, active FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_user(username, password, full_name, role):
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role, active, created_at) "
        "VALUES (?, ?, ?, ?, 1, ?)",
        (username, hash_password(password), full_name, role,
         datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def set_user_active(user_id, active: bool):
    conn = get_connection()
    conn.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))
    conn.commit()
    conn.close()


def change_password(user_id, new_password):
    conn = get_connection()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                 (hash_password(new_password), user_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------
# CATEGORIES
# ---------------------------------------------------------------

def get_categories():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name):
    conn = get_connection()
    conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------
# PRODUCTS / INVENTORY
# ---------------------------------------------------------------

def get_products(active_only=True, category_id=None, search=None):
    query = """
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []
    if active_only:
        query += " AND p.active = 1"
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)
    if search:
        query += " AND p.name LIKE ?"
        params.append(f"%{search}%")
    query += " ORDER BY p.name"

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(product_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_product(name, category_id, price, cost, stock_qty, reorder_level, unit):
    conn = get_connection()
    conn.execute(
        "INSERT INTO products (name, category_id, price, cost, stock_qty, reorder_level, unit) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, category_id, price, cost, stock_qty, reorder_level, unit),
    )
    conn.commit()
    conn.close()


def update_product(product_id, name, category_id, price, cost, reorder_level, unit):
    conn = get_connection()
    conn.execute(
        "UPDATE products SET name=?, category_id=?, price=?, cost=?, reorder_level=?, unit=? "
        "WHERE id=?",
        (name, category_id, price, cost, reorder_level, unit, product_id),
    )
    conn.commit()
    conn.close()


def delete_product(product_id):
    """Soft delete — keeps historical order data intact."""
    conn = get_connection()
    conn.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


def adjust_stock(product_id, change_qty, reason, user_id):
    """Positive change_qty = restock, negative = sale/adjustment."""
    conn = get_connection()
    conn.execute("UPDATE products SET stock_qty = stock_qty + ? WHERE id = ?",
                 (change_qty, product_id))
    conn.execute(
        "INSERT INTO inventory_log (product_id, change_qty, reason, timestamp, user_id) "
        "VALUES (?, ?, ?, ?, ?)",
        (product_id, change_qty, reason, datetime.now().isoformat(timespec="seconds"), user_id),
    )
    conn.commit()
    conn.close()


def get_low_stock_products():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM products WHERE active = 1 AND stock_qty <= reorder_level ORDER BY stock_qty"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------
# ORDERS (POS TRANSACTIONS)
# ---------------------------------------------------------------

def generate_order_number():
    return "ORD-" + datetime.now().strftime("%Y%m%d-%H%M%S")


def create_order(cashier_id, cart_items, subtotal, discount, tax, total,
                  payment_method, amount_paid, change_due):
    """cart_items: list of dicts with product_id, name, qty, unit_price, subtotal.

    Inserts the order + its line items, deducts stock for every item,
    and logs each deduction — all in one function so the POS screen
    doesn't need to know about the individual steps.
    """
    conn = get_connection()
    cur = conn.cursor()
    order_number = generate_order_number()
    ts = datetime.now().isoformat(timespec="seconds")

    cur.execute(
        "INSERT INTO orders (order_number, cashier_id, timestamp, subtotal, discount, tax, "
        "total, payment_method, amount_paid, change_due) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (order_number, cashier_id, ts, subtotal, discount, tax, total,
         payment_method, amount_paid, change_due),
    )
    order_id = cur.lastrowid

    for item in cart_items:
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, quantity, "
            "unit_price, subtotal) VALUES (?,?,?,?,?,?)",
            (order_id, item["product_id"], item["name"], item["qty"],
             item["unit_price"], item["subtotal"]),
        )
        cur.execute("UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?",
                     (item["qty"], item["product_id"]))
        cur.execute(
            "INSERT INTO inventory_log (product_id, change_qty, reason, timestamp, user_id) "
            "VALUES (?, ?, 'sale', ?, ?)",
            (item["product_id"], -item["qty"], ts, cashier_id),
        )

    conn.commit()
    conn.close()
    return order_id, order_number, ts


def get_orders(date_from=None, date_to=None, cashier_id=None):
    query = """
        SELECT o.*, u.full_name AS cashier_name
        FROM orders o
        JOIN users u ON o.cashier_id = u.id
        WHERE 1=1
    """
    params = []
    if date_from:
        query += " AND date(o.timestamp) >= date(?)"
        params.append(date_from)
    if date_to:
        query += " AND date(o.timestamp) <= date(?)"
        params.append(date_to)
    if cashier_id:
        query += " AND o.cashier_id = ?"
        params.append(cashier_id)
    query += " ORDER BY o.timestamp DESC"

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_items(order_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_order_by_number(order_number):
    conn = get_connection()
    row = conn.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------

def get_sales_summary(date_from=None, date_to=None):
    query = "SELECT COUNT(*) AS order_count, COALESCE(SUM(total),0) AS total_sales FROM orders WHERE 1=1"
    params = []
    if date_from:
        query += " AND date(timestamp) >= date(?)"
        params.append(date_from)
    if date_to:
        query += " AND date(timestamp) <= date(?)"
        params.append(date_to)
    conn = get_connection()
    row = conn.execute(query, params).fetchone()
    conn.close()
    return dict(row)


def get_best_sellers(date_from=None, date_to=None, limit=5):
    query = """
        SELECT oi.product_name, SUM(oi.quantity) AS total_qty, SUM(oi.subtotal) AS total_revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE 1=1
    """
    params = []
    if date_from:
        query += " AND date(o.timestamp) >= date(?)"
        params.append(date_from)
    if date_to:
        query += " AND date(o.timestamp) <= date(?)"
        params.append(date_to)
    query += " GROUP BY oi.product_name ORDER BY total_qty DESC LIMIT ?"
    params.append(limit)

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
