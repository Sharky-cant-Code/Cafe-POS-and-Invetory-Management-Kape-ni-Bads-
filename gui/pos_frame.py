"""
gui/pos_frame.py
The Point-of-Sale screen: browse products, build a cart, and
check out. Checking out deducts stock and records the order in
the database, then shows a printable receipt.
"""

import customtkinter as ctk
from tkinter import messagebox
import database as db
from gui.receipt import show_receipt_window

TAX_RATE = 0.0  # set e.g. 0.12 if you want VAT added on top of prices


class POSFrame(ctk.CTkFrame):
    def __init__(self, master, user):
        super().__init__(master, fg_color="transparent")
        self.user = user
        self.cart = {}            # product_id -> {name, unit_price, qty, stock_qty}
        self.selected_category = None

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # ---------------- LEFT SIDE: products ----------------
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=(0, 10))
        top_bar.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(top_bar, placeholder_text="Search products...")
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_products())

        self.category_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.category_bar.grid(row=1, column=0, sticky="new", padx=(0, 10))
        # actual product grid lives below the category buttons, in a scroll frame
        self.products_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.products_scroll.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(10, 0))
        self.grid_rowconfigure(2, weight=1)

        # ---------------- RIGHT SIDE: cart ----------------
        cart_panel = ctk.CTkFrame(self, corner_radius=12)
        cart_panel.grid(row=0, column=1, rowspan=3, sticky="nsew")
        cart_panel.grid_rowconfigure(1, weight=1)
        cart_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(cart_panel, text="Current Order",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        self.cart_scroll = ctk.CTkScrollableFrame(cart_panel, fg_color="transparent")
        self.cart_scroll.grid(row=1, column=0, sticky="nsew", padx=10)

        totals_frame = ctk.CTkFrame(cart_panel, fg_color="transparent")
        totals_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(10, 5))
        totals_frame.grid_columnconfigure(1, weight=1)

        self.subtotal_label = ctk.CTkLabel(totals_frame, text="Subtotal: P0.00")
        self.subtotal_label.grid(row=0, column=0, sticky="w")
        self.tax_label = ctk.CTkLabel(totals_frame, text="Tax: P0.00")
        self.tax_label.grid(row=1, column=0, sticky="w")
        self.total_label = ctk.CTkLabel(totals_frame, text="TOTAL: P0.00",
                                         font=ctk.CTkFont(size=18, weight="bold"))
        self.total_label.grid(row=2, column=0, sticky="w", pady=(5, 0))

        payment_frame = ctk.CTkFrame(cart_panel, fg_color="transparent")
        payment_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=5)
        payment_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(payment_frame, text="Payment method:").grid(row=0, column=0, sticky="w")
        self.payment_method = ctk.CTkOptionMenu(payment_frame, values=["Cash", "GCash", "Card"])
        self.payment_method.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(payment_frame, text="Amount received:").grid(row=1, column=0, sticky="w",
                                                                    pady=(8, 0))
        self.payment_entry = ctk.CTkEntry(payment_frame, placeholder_text="0.00")
        self.payment_entry.grid(row=1, column=1, sticky="e", pady=(8, 0))
        self.payment_entry.bind("<KeyRelease>", lambda e: self.update_change())

        self.change_label = ctk.CTkLabel(payment_frame, text="Change: P0.00",
                                          font=ctk.CTkFont(weight="bold"))
        self.change_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

        action_frame = ctk.CTkFrame(cart_panel, fg_color="transparent")
        action_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(5, 15))
        action_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(action_frame, text="Clear Cart", fg_color="gray40",
                      hover_color="gray30", command=self.clear_cart).grid(
            row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(action_frame, text="Charge", command=self.checkout).grid(
            row=0, column=1, sticky="ew", padx=(5, 0))

        self.build_category_bar()
        self.refresh_products()
        self.refresh_cart()

    # ---------------------------------------------------------
    # PRODUCT BROWSING
    # ---------------------------------------------------------

    def build_category_bar(self):
        for w in self.category_bar.winfo_children():
            w.destroy()
        categories = db.get_categories()
        ctk.CTkButton(self.category_bar, text="All", width=80,
                      command=lambda: self.set_category(None)).pack(side="left", padx=(0, 5),
                                                                      pady=5)
        for cat in categories:
            ctk.CTkButton(self.category_bar, text=cat["name"], width=100,
                          command=lambda c=cat["id"]: self.set_category(c)).pack(
                side="left", padx=5, pady=5)

    def set_category(self, category_id):
        self.selected_category = category_id
        self.refresh_products()

    def refresh_products(self):
        for w in self.products_scroll.winfo_children():
            w.destroy()

        search = self.search_entry.get().strip() or None
        products = db.get_products(active_only=True, category_id=self.selected_category,
                                    search=search)

        cols = 3
        for i in range(cols):
            self.products_scroll.grid_columnconfigure(i, weight=1)

        for idx, p in enumerate(products):
            r, c = divmod(idx, cols)
            low_stock = p["stock_qty"] <= p["reorder_level"]
            out_of_stock = p["stock_qty"] <= 0

            card = ctk.CTkFrame(self.products_scroll, corner_radius=10,
                                 fg_color=("gray85", "gray20"))
            card.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            ctk.CTkLabel(card, text=p["name"], font=ctk.CTkFont(size=14, weight="bold"),
                         wraplength=140).pack(padx=10, pady=(10, 2))
            ctk.CTkLabel(card, text=f"P{p['price']:.2f}").pack()
            stock_color = "#e74c3c" if out_of_stock else ("#e67e22" if low_stock else "gray60")
            ctk.CTkLabel(card, text=f"Stock: {p['stock_qty']}", text_color=stock_color,
                         font=ctk.CTkFont(size=11)).pack(pady=(0, 5))

            btn = ctk.CTkButton(card, text="Add to Order" if not out_of_stock else "Out of Stock",
                                 state="normal" if not out_of_stock else "disabled",
                                 command=lambda pr=p: self.add_to_cart(pr))
            btn.pack(padx=10, pady=(0, 10), fill="x")

    # ---------------------------------------------------------
    # CART
    # ---------------------------------------------------------

    def add_to_cart(self, product):
        pid = product["id"]
        if pid in self.cart:
            if self.cart[pid]["qty"] + 1 > product["stock_qty"]:
                messagebox.showwarning("Insufficient stock",
                                        f"Only {product['stock_qty']} left of {product['name']}.")
                return
            self.cart[pid]["qty"] += 1
        else:
            self.cart[pid] = {
                "name": product["name"],
                "unit_price": product["price"],
                "qty": 1,
                "stock_qty": product["stock_qty"],
            }
        self.refresh_cart()

    def change_qty(self, product_id, delta):
        item = self.cart.get(product_id)
        if not item:
            return
        new_qty = item["qty"] + delta
        if new_qty <= 0:
            del self.cart[product_id]
        elif new_qty > item["stock_qty"]:
            messagebox.showwarning("Insufficient stock",
                                    f"Only {item['stock_qty']} left of {item['name']}.")
            return
        else:
            item["qty"] = new_qty
        self.refresh_cart()

    def clear_cart(self):
        self.cart = {}
        self.payment_entry.delete(0, "end")
        self.refresh_cart()

    def refresh_cart(self):
        for w in self.cart_scroll.winfo_children():
            w.destroy()

        for pid, item in self.cart.items():
            row = ctk.CTkFrame(self.cart_scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(row, text=item["name"], anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkLabel(row, text=f"P{item['unit_price'] * item['qty']:.2f}",
                         width=70, anchor="e").grid(row=0, column=1, padx=(5, 0))

            qty_frame = ctk.CTkFrame(row, fg_color="transparent")
            qty_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))
            ctk.CTkButton(qty_frame, text="-", width=28,
                          command=lambda p=pid: self.change_qty(p, -1)).pack(side="left")
            ctk.CTkLabel(qty_frame, text=str(item["qty"]), width=30).pack(side="left")
            ctk.CTkButton(qty_frame, text="+", width=28,
                          command=lambda p=pid: self.change_qty(p, 1)).pack(side="left")
            ctk.CTkButton(qty_frame, text="Remove", width=70, fg_color="#c0392b",
                          hover_color="#96281b",
                          command=lambda p=pid: self.change_qty(p, -item["qty"])).pack(
                side="left", padx=(8, 0))

        self.update_totals()

    def get_totals(self):
        subtotal = sum(item["unit_price"] * item["qty"] for item in self.cart.values())
        tax = subtotal * TAX_RATE
        total = subtotal + tax
        return subtotal, tax, total

    def update_totals(self):
        subtotal, tax, total = self.get_totals()
        self.subtotal_label.configure(text=f"Subtotal: P{subtotal:.2f}")
        self.tax_label.configure(text=f"Tax: P{tax:.2f}")
        self.total_label.configure(text=f"TOTAL: P{total:.2f}")
        self.update_change()

    def update_change(self):
        _, _, total = self.get_totals()
        try:
            paid = float(self.payment_entry.get() or 0)
        except ValueError:
            paid = 0
        change = paid - total
        self.change_label.configure(
            text=f"Change: P{max(change, 0):.2f}",
            text_color="#e74c3c" if change < 0 else ("gray60" if change == 0 else "#27ae60"),
        )

    # ---------------------------------------------------------
    # CHECKOUT
    # ---------------------------------------------------------

    def checkout(self):
        if not self.cart:
            messagebox.showinfo("Empty order", "Add at least one item before charging.")
            return

        subtotal, tax, total = self.get_totals()
        try:
            paid = float(self.payment_entry.get() or 0)
        except ValueError:
            messagebox.showerror("Invalid amount", "Enter a valid payment amount.")
            return

        if paid < total:
            messagebox.showerror("Insufficient payment",
                                  f"Amount received (P{paid:.2f}) is less than the total "
                                  f"(P{total:.2f}).")
            return

        change_due = paid - total
        cart_items = [
            {"product_id": pid, "name": item["name"], "qty": item["qty"],
             "unit_price": item["unit_price"], "subtotal": item["unit_price"] * item["qty"]}
            for pid, item in self.cart.items()
        ]

        order_id, order_number, ts = db.create_order(
            cashier_id=self.user["id"],
            cart_items=cart_items,
            subtotal=subtotal, discount=0, tax=tax, total=total,
            payment_method=self.payment_method.get(),
            amount_paid=paid, change_due=change_due,
        )

        items_for_receipt = [
            {"product_name": it["name"], "quantity": it["qty"], "subtotal": it["subtotal"]}
            for it in cart_items
        ]
        show_receipt_window(self, order_number, ts, self.user["full_name"], items_for_receipt,
                             subtotal, 0, tax, total, self.payment_method.get(), paid, change_due)

        self.clear_cart()
        self.refresh_products()
