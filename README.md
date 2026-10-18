# BrewPOS – Kapehan ni Bads

A desktop point-of-sale and inventory app for a small café, built in Python from the "Login-front" Figma design.

- **GUI:** CustomTkinter (plus `ttk.Treeview` for the tables)
- **Database:** SQLite (a single file, created automatically)
- **Tested with:** Python 3.12. Any recent Python 3 with Tk should work.

---

## 1. Running it

```bash
pip install -r requirements.txt
python main.py
```

- **Windows / macOS:** Tk comes with the python.org installer.
- **Linux:** you may need `sudo apt install python3-tk` first.

On first launch the app creates a `data/` folder next to the code and fills the menu with a few sample products.

**The first account you sign up becomes the admin.** Every account after that is a cashier.

---

## 2. Project layout

| File | What it does |
|---|---|
| `main.py` | Entry point. The `App` window, screen navigation, role checks, and the shopping cart. |
| `auth_screens.py` | Login, Create Account, Forgot Password, Create new password. |
| `pos_screens.py` | Menu (POS), Your order (cart + checkout), Gcash payment, Dashboard. |
| `admin_screens.py` | Sales History & Reports, Inventory, and the Add/Edit and Restock dialogs. |
| `database.py` | Every SQL query, password hashing, and the checkout transaction. |
| `widgets.py` | Reusable pieces: header bar, icon text fields, filter chips, stat cards, styled table. |
| `theme.py` | Colors, fonts, shop name, Gcash number. **Edit this to restyle.** |
| `utils.py` | Money formatting, input validation, date ranges, settings file, CSV safety. |
| `assets/` | Logo, icons and the Gcash QR image, cropped from the Figma export. |
| `data/` | Created at runtime: `brewpos.db`, `images/` (product photos), `settings.json`. |

The screens only talk to the database through `database.py`. Nothing else contains SQL.

---

## 3. How the app flows

```
Login ──► Menu (POS) ◄──► Your order ──► (Gcash QR) ──► order saved
  │          │                 │
  │          └── Dashboard ◄───┘
  │                 ├── Sales History & Reports   (admin only)
  │                 └── Inventory                 (admin only)
  ├── Sign up ──► Create Account
  └── Forgot Password ──► Create new password
```

The header's **Dashboard**, **Back to menu** and **Log out** buttons are on every screen after login.

### Accounts and login
- **Username:** 3–20 characters (letters, numbers, `_` or `.`), and not case-sensitive.
- **Password:** at least 8 characters with letters, numbers **and** symbols.
- Passwords and secret answers are **never stored as plain text**. They are hashed with PBKDF2-SHA256 and a random salt.
- A wrong login shows a generic message and pauses the button for about a second. It never says which part was wrong.
- **Remember me** saves only your username (in `data/settings.json`), never the password.
- **Forgot Password:** you choose your secret question, type the answer and (optionally) a new password. If all three match, the app opens the "Create new password" screen, where you confirm the new password.

### Taking an order (Menu → Your order)
1. On the **Menu**, search or filter by category, then click **Add to cart**. Clicking a product shows it in the right-hand panel.
2. **Checkout** opens **Your order**. Change quantities with − / +, or remove an item with ✕.
3. Pick **Cash** or **Gcash**, then click **Checkout**.
   - **Cash:** the order is saved right away.
   - **Gcash:** a QR screen appears. Click **Payment received** once the customer has paid, and the order is saved.
4. Saving an order **deducts stock** and records the order and its items.

Checkout is all-or-nothing. If any item no longer has enough stock, nothing is saved and you are told which item is short. You also can't add more of an item than is in stock.

The left side of **Your order** shows *your own* orders for today, with the top product, order count and amount.

### Inventory (admin)
- **+ Add Product**, **Edit** (or double-click a row), **Restock** (adds units), and **Delete**.
- Status is **Out of Stock** at 0, **Low Stock** at 10 or fewer, and **In Stock** above that. Out-of-stock rows are highlighted orange.
- Photos are checked, shrunk to at most 600 px and saved into `data/images/`.
- Deleting a product doesn't affect past sales. Each order keeps its own copy of the item names and prices.

### Sales History & Reports (admin)
- Filters: **Today**, **This Week** (Monday to now), **This Month**, **All Time**.
- The cards show total sales, order count and the best-seller. Click an order to see its breakdown.
- **Export CSV** saves the orders in the current filter. It opens correctly in Excel, and text that starts like a spreadsheet formula (`=`, `+`, `-`, `@`) is neutralised.
- **+ Add Sales** jumps to the Menu so you can ring up a sale.

---

## 4. Data model

Money is stored as **whole centavos** (`PHP 120.50` → `12050`) to avoid floating-point rounding errors.

| Table | Purpose |
|---|---|
| `users` | username, password hash, role (`admin` / `cashier`), secret question, answer hash |
| `products` | name, category, `price_cents`, stock, photo file name |
| `orders` | timestamp, cashier, payment (`Cash` / `Gcash`), `total_cents` |
| `order_items` | the items of each order (name and price copied at sale time, plus quantity) |

---

## 5. Customising

| To change… | Edit |
|---|---|
| Gcash number | `GCASH_NUMBER` in `theme.py` |
| Gcash QR code | replace `assets/gcash_qr.png` |
| Shop name / tagline | `SHOP_NAME`, `SHOP_TAGLINE` in `theme.py` |
| Colors | the palette at the top of `theme.py` |
| Product categories | `CATEGORIES` in `utils.py` (the menu filter chips and the product form use it) |
| Secret questions | `SECRET_QUESTIONS` in `utils.py` |
| "Low Stock" threshold | `LOW_STOCK_LIMIT` in `utils.py` |
| Password rules | `validate_password` in `utils.py` |
| Window size | `width, height` in `App.__init__` (`main.py`) |

To **start fresh**, close the app and delete the `data/` folder. That removes all accounts, products, orders and photos.

---

## 6. Notes and limits

- **Dashboard** has no frame in the Figma file, so it is a simple page with a tile for each section, and only admins see the Sales and Inventory tiles.
- The Gcash QR and number in the project are placeholders from the design.
- Resetting a password with a secret question is only as strong as the answer, so tell staff to pick answers others can't guess.
- This is a single-computer app. The database is one local file, so it doesn't sync between devices.
- **Not included:** receipt printing, refunds or voids, editing past orders, and cash-change calculation.
