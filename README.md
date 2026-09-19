# Cafe Point of Sale & Inventory Management System

A desktop app for running a small cafe: ring up sales, track stock,
and review reports. Built with Python, CustomTkinter for the GUI,
and SQLite for storage.

## Features

- **Login with roles** — separate Admin and Cashier accounts.
  Admins get full access; cashiers get POS + a read-only inventory view.
- **Point of Sale** — browse products by category, search, build a
  cart, and check out with cash/GCash/card. Stock is deducted
  automatically and a printable/savable receipt is generated.
- **Inventory management** (admin) — add, edit, and soft-delete
  products; restock with a logged quantity; low-stock and
  out-of-stock items are flagged automatically.
- **Sales history & reports** — quick date filters (today/week/
  month/all time), totals, best-seller, per-order item breakdown,
  and CSV export.
- **Staff management** (admin) — create cashier/admin accounts,
  reset passwords, deactivate accounts.

## Setup

1. Make sure you have **Python 3.9+** installed.
2. Install the one dependency (CustomTkinter; everything else —
   tkinter and sqlite3 — ships with Python):

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   python main.py
   ```

On first run, `cafe_pos.db` is created automatically with two
starter accounts and a sample menu, so you can log in immediately:

| Username | Password    | Role    |
|----------|-------------|---------|
| admin    | admin123    | Admin   |
| cashier  | cashier123  | Cashier |

**Change these passwords** (or at least the admin one) via
*Manage Staff → Reset Password* before using this for anything real.

## Project structure

```
cafe_pos_system/
├── main.py              # Entry point — run this
├── database.py          # SQLite schema + all data access functions
├── requirements.txt
├── gui/
│   ├── login_window.py  # Login screen
│   ├── main_window.py   # Sidebar + screen switcher
│   ├── pos_frame.py      # Point of Sale screen
│   ├── inventory_frame.py# Inventory management screen
│   ├── sales_frame.py    # Sales history & reports screen
│   ├── users_frame.py    # Staff account management (admin)
│   └── receipt.py        # Receipt text formatting + save/print
└── receipts/             # Saved receipt .txt files land here
```

## Notes on design choices

- **SQLite** was used since this is a single-computer desktop app —
  no server setup needed, and the whole database is one file
  (`cafe_pos.db`) you can back up by copying it.
- **Soft deletes** — removing a product just marks it inactive
  instead of deleting the row, so old orders that reference it
  still display correctly in sales history.
- **Receipt "printing"** actually saves a formatted `.txt` file and
  attempts to send it to your OS's default printer. Real thermal-
  printer integration would need printer-specific drivers, which is
  out of scope here — the text file is a practical stand-in.
- Passwords are stored as salted SHA-256 hashes — reasonable for a
  local school/practice project, but not a substitute for a real
  auth system in production software.

## Extending it further

Some natural next steps if you want to keep building this out:
- Add a "void/refund order" flow.
- Add barcode scanning (most USB scanners just type + Enter, so a
  bound `<Return>` on a hidden search field would work).
- Move to PostgreSQL/MySQL if this ever needs multiple computers
  sharing one database at once.
