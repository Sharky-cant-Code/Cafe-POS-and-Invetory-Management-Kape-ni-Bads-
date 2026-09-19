"""
gui/inventory_frame.py
Inventory management screen. Admins can add/edit/delete products
and restock; cashiers get a read-only view (handy for checking
stock while serving a customer).
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import database as db


class InventoryFrame(ctk.CTkFrame):
    def __init__(self, master, user):
        super().__init__(master, fg_color="transparent")
        self.user = user
        self.is_admin = user["role"] == "admin"
        self.selected_product_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ---------------- header / low-stock banner ----------------
        self.low_stock_banner = ctk.CTkLabel(self, text="", text_color="white",
                                              fg_color="#c0392b", corner_radius=6)
        self.low_stock_banner.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        top_bar.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(top_bar, placeholder_text="Search products...")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_table())

        cat_names = ["All"] + [c["name"] for c in db.get_categories()]
        self.category_filter = ctk.CTkOptionMenu(top_bar, values=cat_names,
                                                   command=lambda v: self.refresh_table())
        self.category_filter.grid(row=0, column=1, padx=10)

        if self.is_admin:
            ctk.CTkButton(top_bar, text="+ Add Product", command=self.open_add_dialog).grid(
                row=0, column=2, padx=(0, 5))
            ctk.CTkButton(top_bar, text="Restock", command=self.open_restock_dialog).grid(
                row=0, column=3, padx=(0, 5))
            ctk.CTkButton(top_bar, text="Edit", command=self.open_edit_dialog).grid(
                row=0, column=4, padx=(0, 5))
            ctk.CTkButton(top_bar, text="Delete", fg_color="#c0392b", hover_color="#96281b",
                          command=self.delete_selected).grid(row=0, column=5)

        # ---------------- table ----------------
        # customtkinter has no built-in table widget, so we use the
        # standard ttk.Treeview here (it's the normal approach even
        # inside CustomTkinter apps) and style it to roughly match.
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2a2d2e", foreground="white",
                         fieldbackground="#2a2d2e", rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background="#1f6aa5", foreground="white",
                         relief="flat")
        style.map("Treeview", background=[("selected", "#144870")])

        columns = ("name", "category", "price", "stock", "reorder", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        headers = {"name": "Product", "category": "Category", "price": "Price",
                   "stock": "Stock", "reorder": "Reorder Lvl", "status": "Status"}
        widths = {"name": 200, "category": 130, "price": 80, "stock": 70,
                  "reorder": 100, "status": 100}
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center" if col != "name" else "w")
        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky="ns")

        self.refresh_table()

    # ---------------------------------------------------------

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        search = self.search_entry.get().strip() or None
        cat_name = self.category_filter.get()
        category_id = None
        if cat_name != "All":
            match = next((c for c in db.get_categories() if c["name"] == cat_name), None)
            category_id = match["id"] if match else None

        products = db.get_products(active_only=True, category_id=category_id, search=search)
        low_stock_names = []
        for p in products:
            status = "OK"
            tag = ""
            if p["stock_qty"] <= 0:
                status = "OUT OF STOCK"
                tag = "out"
                low_stock_names.append(p["name"])
            elif p["stock_qty"] <= p["reorder_level"]:
                status = "LOW STOCK"
                tag = "low"
                low_stock_names.append(p["name"])

            self.tree.insert("", "end", iid=str(p["id"]), values=(
                p["name"], p["category_name"] or "-", f"P{p['price']:.2f}",
                p["stock_qty"], p["reorder_level"], status
            ), tags=(tag,))

        self.tree.tag_configure("low", foreground="#f39c12")
        self.tree.tag_configure("out", foreground="#e74c3c")

        if low_stock_names:
            self.low_stock_banner.configure(
                text=f"⚠ Low stock: {', '.join(low_stock_names[:8])}"
                     f"{'...' if len(low_stock_names) > 8 else ''}")
            self.low_stock_banner.grid()
        else:
            self.low_stock_banner.configure(text="")
            self.low_stock_banner.grid_remove()

    def on_select(self, event=None):
        sel = self.tree.selection()
        self.selected_product_id = int(sel[0]) if sel else None

    # ---------------------------------------------------------
    # ADD / EDIT / DELETE / RESTOCK (admin only)
    # ---------------------------------------------------------

    def open_add_dialog(self):
        ProductDialog(self, title="Add Product", on_save=self._save_new_product)

    def _save_new_product(self, values):
        db.add_product(**values)
        self.refresh_table()

    def open_edit_dialog(self):
        if not self.selected_product_id:
            messagebox.showinfo("No selection", "Select a product first.")
            return
        product = db.get_product(self.selected_product_id)
        ProductDialog(self, title="Edit Product", product=product,
                      on_save=lambda values: self._save_edit(product["id"], values))

    def _save_edit(self, product_id, values):
        db.update_product(product_id, values["name"], values["category_id"], values["price"],
                          values["cost"], values["reorder_level"], values["unit"])
        self.refresh_table()

    def delete_selected(self):
        if not self.selected_product_id:
            messagebox.showinfo("No selection", "Select a product first.")
            return
        if messagebox.askyesno("Confirm delete", "Remove this product from the menu? "
                                                   "Past orders will keep referencing it."):
            db.delete_product(self.selected_product_id)
            self.refresh_table()

    def open_restock_dialog(self):
        if not self.selected_product_id:
            messagebox.showinfo("No selection", "Select a product first.")
            return
        product = db.get_product(self.selected_product_id)
        RestockDialog(self, product, on_confirm=self._do_restock)

    def _do_restock(self, product_id, qty):
        db.adjust_stock(product_id, qty, "restock", self.user["id"])
        self.refresh_table()


class ProductDialog(ctk.CTkToplevel):
    """Popup form used for both Add and Edit."""

    def __init__(self, master, title, on_save, product=None):
        super().__init__(master)
        self.title(title)
        self.geometry("360x440")
        self.grab_set()
        self.on_save = on_save

        categories = db.get_categories()
        self.category_map = {c["name"]: c["id"] for c in categories}

        pad = {"padx": 20, "pady": (8, 0)}

        ctk.CTkLabel(self, text="Name").pack(anchor="w", **pad)
        self.name_entry = ctk.CTkEntry(self, width=300)
        self.name_entry.pack(**pad)

        ctk.CTkLabel(self, text="Category").pack(anchor="w", **pad)
        self.category_menu = ctk.CTkOptionMenu(self, values=list(self.category_map.keys()) or ["-"])
        self.category_menu.pack(**pad)

        ctk.CTkLabel(self, text="Price (P)").pack(anchor="w", **pad)
        self.price_entry = ctk.CTkEntry(self, width=300)
        self.price_entry.pack(**pad)

        ctk.CTkLabel(self, text="Cost (P)").pack(anchor="w", **pad)
        self.cost_entry = ctk.CTkEntry(self, width=300)
        self.cost_entry.pack(**pad)

        ctk.CTkLabel(self, text="Unit (e.g. cup, pc, pack)").pack(anchor="w", **pad)
        self.unit_entry = ctk.CTkEntry(self, width=300)
        self.unit_entry.pack(**pad)

        ctk.CTkLabel(self, text="Reorder level").pack(anchor="w", **pad)
        self.reorder_entry = ctk.CTkEntry(self, width=300)
        self.reorder_entry.pack(**pad)

        if product is None:
            ctk.CTkLabel(self, text="Starting stock qty").pack(anchor="w", **pad)
            self.stock_entry = ctk.CTkEntry(self, width=300)
            self.stock_entry.pack(**pad)
        else:
            self.stock_entry = None
            self.name_entry.insert(0, product["name"])
            self.price_entry.insert(0, str(product["price"]))
            self.cost_entry.insert(0, str(product["cost"]))
            self.unit_entry.insert(0, product["unit"])
            self.reorder_entry.insert(0, str(product["reorder_level"]))
            current_cat = next((c["name"] for c in categories
                                if c["id"] == product["category_id"]), None)
            if current_cat:
                self.category_menu.set(current_cat)

        self.error_label = ctk.CTkLabel(self, text="", text_color="#e74c3c")
        self.error_label.pack(pady=(10, 0))

        ctk.CTkButton(self, text="Save", command=self.save).pack(pady=15)

    def save(self):
        try:
            name = self.name_entry.get().strip()
            if not name:
                raise ValueError("Name is required.")
            price = float(self.price_entry.get())
            cost = float(self.cost_entry.get() or 0)
            reorder_level = int(self.reorder_entry.get() or 5)
            unit = self.unit_entry.get().strip() or "pc"
            category_id = self.category_map.get(self.category_menu.get())

            values = {"name": name, "category_id": category_id, "price": price,
                      "cost": cost, "reorder_level": reorder_level, "unit": unit}
            if self.stock_entry is not None:
                values["stock_qty"] = int(self.stock_entry.get() or 0)

            self.on_save(values)
            self.destroy()
        except ValueError as e:
            self.error_label.configure(text=str(e) if str(e) else "Please check your inputs.")


class RestockDialog(ctk.CTkToplevel):
    def __init__(self, master, product, on_confirm):
        super().__init__(master)
        self.title(f"Restock: {product['name']}")
        self.geometry("300x180")
        self.grab_set()
        self.product = product
        self.on_confirm = on_confirm

        ctk.CTkLabel(self, text=f"Current stock: {product['stock_qty']}").pack(pady=(20, 5))
        ctk.CTkLabel(self, text="Quantity to add:").pack()
        self.qty_entry = ctk.CTkEntry(self, width=150)
        self.qty_entry.pack(pady=5)
        self.error_label = ctk.CTkLabel(self, text="", text_color="#e74c3c")
        self.error_label.pack()
        ctk.CTkButton(self, text="Confirm Restock", command=self.confirm).pack(pady=10)

    def confirm(self):
        try:
            qty = int(self.qty_entry.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            self.error_label.configure(text="Enter a positive whole number.")
            return
        self.on_confirm(self.product["id"], qty)
        self.destroy()
