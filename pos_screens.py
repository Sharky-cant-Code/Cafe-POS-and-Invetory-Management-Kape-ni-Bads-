"""Cashier-side screens: menu (POS), Your order, Gcash payment, and the dashboard hub."""
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

import database as db
from theme import (AMBER, FIELD_BG, GCASH_NUMBER, GREY_TEXT, ORANGE, PAGE_BG, TILE_BG, F)
from utils import CATEGORIES, pretty_time, peso, range_start
from widgets import (ASSETS, AppHeader, ChipBar, DataTable, StatCard, product_image, solid_button,
                     link_button)

CHECKOUT_COLOR = "#d9822b"


def finish_order(app, payment: str) -> bool:
    """Save the cart as an order (stock is deducted atomically). Returns True on success."""
    lines = app.cart_lines()
    total = sum(line["amount"] for line in lines)
    try:
        order_id = db.create_order(app.user["id"], payment, [(l["product"]["id"], l["qty"]) for l in lines])
    except (db.StockError, ValueError) as error:
        messagebox.showerror("Can't complete the order", f"{error}\nPlease adjust the cart and try again.")
        return False
    app.cart, app.cart_focus = {}, None
    messagebox.showinfo("Order complete", f"Order #{order_id} saved.\nTotal: {peso(total)}  ({payment})")
    return True


# ------------------------------------------------------------------ menu
class POSScreen(ctk.CTkFrame):
    CARD_W, CARD_H = 190, 262

    def __init__(self, master, app):
        super().__init__(master, fg_color=PAGE_BG, corner_radius=0)
        self.app, self.category, self._cols = app, "All", 0
        AppHeader(self, app, nav=True).pack(fill="x")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(22, 24))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 22))
        search_row = ctk.CTkFrame(left, fg_color="transparent")
        search_row.pack(fill="x")
        self.search = ctk.CTkEntry(search_row, height=46, corner_radius=0, border_width=1,
                                   border_color="black", fg_color="white", text_color="black", font=F(15))
        self.search.pack(side="left", fill="x", expand=True)
        self.search.bind("<KeyRelease>", lambda _e: self.render())
        solid_button(search_row, "SEARCH", self.render, fg=AMBER, width=130, height=50,
                     font=F(17)).pack(side="left", padx=(12, 0))
        ctk.CTkLabel(left, text="Search products:", font=F(14), text_color="black",
                     anchor="w").pack(anchor="w", pady=(6, 10))
        ChipBar(left, ["All"] + CATEGORIES, self._set_category, "All", on_fg=CHECKOUT_COLOR,
                on_text="black", off_fg=FIELD_BG, width=82).pack(anchor="w", pady=(0, 12))
        self.grid_area = ctk.CTkScrollableFrame(left, fg_color="white", border_color="black",
                                                border_width=1, corner_radius=0)
        self.grid_area.pack(fill="both", expand=True)
        self.grid_area.bind("<Configure>", self._on_resize)

        panel = ctk.CTkFrame(body, fg_color="white", border_color="black", border_width=1,
                             corner_radius=0, width=440)
        panel.grid(row=0, column=1, sticky="ns")
        panel.pack_propagate(False)
        self.big_image = ctk.CTkLabel(panel, text="", image=product_image(None, (392, 290)))
        self.big_image.pack(padx=24, pady=(26, 14))
        self.name_label = ctk.CTkLabel(panel, text="Select an item", font=F(21, True), text_color="black",
                                       anchor="w", wraplength=380, justify="left")
        self.name_label.pack(anchor="w", padx=36)
        self.total_label = ctk.CTkLabel(panel, text="", font=F(17, True), text_color="black", anchor="w")
        self.total_label.pack(anchor="w", padx=36, pady=(6, 0))
        self.count_label = ctk.CTkLabel(panel, text="", font=F(13), text_color=GREY_TEXT, anchor="w")
        self.count_label.pack(anchor="w", padx=36, pady=(2, 0))
        solid_button(panel, "Checkout", self.checkout, fg=CHECKOUT_COLOR, height=50,
                     font=F(22)).pack(side="bottom", fill="x", padx=4, pady=4)
        self._update_panel()

    # -- product grid
    def _set_category(self, category):
        self.category = category
        self.render()

    def _on_resize(self, event):
        cols = max(1, (event.width - 24) // (self.CARD_W + 20))
        if cols != self._cols:
            self._cols = cols
            self.render()

    def render(self):
        for child in self.grid_area.winfo_children():
            child.destroy()
        products = db.list_products(self.search.get(), self.category)
        if not products:
            ctk.CTkLabel(self.grid_area, text="No products found.", font=F(15),
                         text_color=GREY_TEXT).grid(row=0, column=0, padx=20, pady=20)
        cols = self._cols or 3
        for index, product in enumerate(products):
            self._card(product).grid(row=index // cols, column=index % cols, padx=10, pady=10)

    def _card(self, product):
        sold_out = product["stock"] <= 0
        card = ctk.CTkFrame(self.grid_area, width=self.CARD_W, height=self.CARD_H, fg_color=TILE_BG,
                            border_color="#444444", border_width=1, corner_radius=0)
        card.pack_propagate(False)
        picture = ctk.CTkLabel(card, text="", image=product_image(product["image"], (172, 112)))
        picture.pack(padx=8, pady=(10, 6))
        name = ctk.CTkLabel(card, text=product["name"], font=F(15, True), text_color="black", wraplength=172)
        name.pack()
        ctk.CTkLabel(card, text=peso(product["price_cents"]), font=F(13), text_color=GREY_TEXT).pack(pady=(2, 0))
        solid_button(card, "Out of stock" if sold_out else "Add to cart",
                     lambda pid=product["id"]: self._add(pid), fg=AMBER, width=112, height=30,
                     font=F(12), state="disabled" if sold_out else "normal").pack(side="bottom", pady=(0, 8))
        for widget in (picture, name):
            widget.bind("<Button-1>", lambda _e, pid=product["id"]: self._select(pid))
        return card

    # -- side panel
    def _add(self, product_id):
        if self.app.cart_add(product_id):
            self._update_panel()

    def _select(self, product_id):
        self.app.cart_focus = product_id
        self._update_panel()

    def _update_panel(self):
        product = db.get_product(self.app.cart_focus) if self.app.cart_focus else None
        if product is None:
            self.big_image.configure(image=product_image(None, (392, 290)))
            self.name_label.configure(text="Select an item")
        else:
            in_cart = self.app.cart.get(product["id"], 0)
            self.big_image.configure(image=product_image(product["image"], (392, 290)))
            self.name_label.configure(text=product["name"] + (f"  × {in_cart}" if in_cart else ""))
        self.total_label.configure(text=f"Total: {peso(self.app.cart_total())}")
        count = sum(self.app.cart.values())
        self.count_label.configure(text=f"{count} item{'s' if count != 1 else ''} in cart" if count else "Cart is empty")

    def checkout(self):
        if not self.app.cart_lines():
            messagebox.showinfo("Cart is empty", "Add something from the menu first.")
            return
        self.app.show_order()


# ------------------------------------------------------------- your order
class OrderScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=PAGE_BG, corner_radius=0)
        self.app = app
        AppHeader(self, app, nav=True).pack(fill="x")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(18, 24))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        ctk.CTkLabel(body, text="Your order", font=F(30, True), text_color="black",
                     anchor="w").grid(row=0, column=0, columnspan=2, sticky="w")
        ctk.CTkLabel(body, text="Today's orders on the left. Review the cart, pick a payment method and check out on the right.",
                     font=F(13), text_color="black", anchor="w").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 14))

        # row 2 holds both columns; the stat cards sit above the table
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=2, column=0, sticky="nsew", padx=(0, 22))
        cards = ctk.CTkFrame(left, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 16))
        for column in range(3):
            cards.columnconfigure(column, weight=1, uniform="stat")
        self.top_card = StatCard(cards, "Top product today")
        self.orders_card = StatCard(cards, "Total orders")
        self.amount_card = StatCard(cards, "Amount")
        for column, card in enumerate((self.top_card, self.orders_card, self.amount_card)):
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 8, 0 if column == 2 else 8))
        self.table = DataTable(left, [
            ("order", "Order#", 84, "center", False), ("when", "Date and time", 190, "center", True),
            ("items", "Items", 250, "w", True), ("payment", "Payment", 90, "center", False),
            ("total", "Total", 110, "e", False)])
        self.table.pack(fill="both", expand=True)

        panel = ctk.CTkFrame(body, fg_color="white", border_color="black", border_width=1,
                             corner_radius=0, width=420)
        panel.grid(row=2, column=1, sticky="ns")
        panel.pack_propagate(False)
        ctk.CTkLabel(panel, text="Your order", font=F(22, True), text_color="black",
                     anchor="w").pack(anchor="w", padx=22, pady=(14, 0))
        ctk.CTkLabel(panel, text="Item  -  Quantity  -  Amount", font=F(11), text_color=GREY_TEXT,
                     anchor="w").pack(anchor="w", padx=24)
        solid_button(panel, "Checkout", self.checkout, fg=CHECKOUT_COLOR, height=50,
                     font=F(22)).pack(side="bottom", fill="x", padx=2, pady=2)
        self.pay = ctk.StringVar(value="Cash")
        pay_row = ctk.CTkFrame(panel, fg_color="transparent")
        pay_row.pack(side="bottom", fill="x", padx=24, pady=(0, 14))
        for text in ("Cash", "Gcash"):
            ctk.CTkRadioButton(pay_row, text=text, value=text, variable=self.pay, font=F(14),
                               text_color="black", fg_color="#6b6b6b", hover_color="#8a8a8a",
                               border_color="#bdbdbd", border_width_unchecked=3, border_width_checked=6,
                               radiobutton_width=22, radiobutton_height=22).pack(side="left", padx=(0, 36))
        ctk.CTkLabel(panel, text="Payment method", font=F(14), text_color="black",
                     anchor="w").pack(side="bottom", anchor="w", padx=24, pady=(0, 8))
        self.total_label = ctk.CTkLabel(panel, text="", font=F(18, True), text_color="black", anchor="w")
        self.total_label.pack(side="bottom", anchor="w", padx=24, pady=(6, 14))
        self.lines_area = ctk.CTkScrollableFrame(panel, fg_color="white", corner_radius=0)
        self.lines_area.pack(fill="both", expand=True, padx=(10, 6), pady=(6, 0))
        self.lines_area.columnconfigure(0, weight=1)
        self.refresh()

    def refresh(self):
        self._render_cart()
        start, uid = range_start("Today"), self.app.user["id"]
        stats = db.sales_stats(start, uid)
        self.top_card.set(f"{stats['best_name']} ({stats['best_sold']})" if stats["best_name"] else "-")
        self.orders_card.set(str(stats["orders"]))
        self.amount_card.set(peso(stats["total_cents"]))
        self.table.fill([
            {"iid": str(o["id"]), "values": (f"#{o['id']}", pretty_time(o["created_at"]), o["items"] or "",
                                              o["payment"], peso(o["total_cents"]))}
            for o in db.list_orders(start, uid)])

    def _render_cart(self):
        for child in self.lines_area.winfo_children():
            child.destroy()
        lines = self.app.cart_lines()
        if not lines:
            ctk.CTkLabel(self.lines_area, text="Your cart is empty.\nUse “Back to menu” to add items.",
                         font=F(13), text_color=GREY_TEXT, justify="left").grid(row=0, column=0, sticky="w", padx=12, pady=16)
        for row, line in enumerate(lines):
            product, pid = line["product"], line["product"]["id"]
            item = ctk.CTkFrame(self.lines_area, fg_color="transparent")
            item.grid(row=row, column=0, sticky="ew", pady=5)
            item.columnconfigure(0, weight=1)
            info = ctk.CTkFrame(item, fg_color="transparent")
            info.grid(row=0, column=0, sticky="w", padx=(6, 0))
            ctk.CTkLabel(info, text=product["name"], font=F(14, True), text_color="black",
                         anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=f"{peso(product['price_cents'])} each", font=F(11), text_color=GREY_TEXT,
                         anchor="w").pack(anchor="w")
            stepper = ctk.CTkFrame(item, fg_color="transparent")
            stepper.grid(row=0, column=1, padx=8)
            solid_button(stepper, "−", lambda p=pid: self._change(p, -1), fg=FIELD_BG, text_color="black",
                         width=28, height=28, font=F(15, True), corner_radius=4).pack(side="left")
            ctk.CTkLabel(stepper, text=str(line["qty"]), font=F(14, True), text_color="black",
                         width=30).pack(side="left")
            solid_button(stepper, "+", lambda p=pid: self._change(p, 1), fg=FIELD_BG, text_color="black",
                         width=28, height=28, font=F(15, True), corner_radius=4).pack(side="left")
            ctk.CTkLabel(item, text=peso(line["amount"]), font=F(13, True), text_color="black",
                         width=92, anchor="e").grid(row=0, column=2)
            link_button(item, "✕", lambda p=pid: self._remove(p), color="#a33", size=14).grid(row=0, column=3, padx=(4, 2))
        self.total_label.configure(text=f"Total: {peso(self.app.cart_total())}")

    def _change(self, product_id, delta):
        self.app.cart_add(product_id, delta)
        self._render_cart()

    def _remove(self, product_id):
        self.app.cart_remove(product_id)
        self._render_cart()

    def checkout(self):
        if not self.app.cart_lines():
            messagebox.showinfo("Cart is empty", "Add something from the menu first.")
        elif self.pay.get() == "Gcash":
            self.app.show_gcash()
        elif finish_order(self.app, "Cash"):
            self.refresh()
        else:
            self._render_cart()


# ------------------------------------------------------------------ gcash
class GcashScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=PAGE_BG, corner_radius=0)
        self.app = app
        AppHeader(self, app).pack(fill="x")
        card = ctk.CTkFrame(self, fg_color="#c8c8c8", corner_radius=28)
        card.place(relx=0.5, rely=0.55, anchor="center")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=70, pady=(34, 34))
        ctk.CTkLabel(inner, text="Gcash Payment\nScan Here", font=F(28, True), text_color="black",
                     justify="center").pack(pady=(0, 16))
        qr_box = ctk.CTkFrame(inner, fg_color="white", border_color=ORANGE, border_width=1, corner_radius=10)
        qr_box.pack()
        qr = Image.open(ASSETS / "gcash_qr.png").convert("RGB")
        width = 280
        qr_image = ctk.CTkImage(light_image=qr, dark_image=qr, size=(width, int(width * qr.height / qr.width)))
        ctk.CTkLabel(qr_box, text="", image=qr_image).pack(padx=8, pady=8)
        ctk.CTkLabel(inner, text=GCASH_NUMBER, font=F(15), text_color="black").pack(pady=(16, 0))
        ctk.CTkLabel(inner, text=f"Amount due: {peso(app.cart_total())}", font=F(17, True),
                     text_color="black").pack(pady=(8, 14))
        solid_button(inner, "Payment received", self.confirm, fg=ORANGE, text_color="black", width=280,
                     height=46, font=F(16, True), corner_radius=10).pack()
        link_button(inner, "Cancel", app.show_order, color=GREY_TEXT, size=13).pack(pady=(10, 0))

    def confirm(self):
        amount = peso(self.app.cart_total())
        if messagebox.askyesno("Confirm payment", f"Confirm that {amount} was received on Gcash?"):
            if finish_order(self.app, "Gcash"):
                self.app.show_order()


# -------------------------------------------------------------- dashboard
class DashboardScreen(ctk.CTkFrame):
    """Hub for the header's Dashboard button (the Figma file has no frame for it)."""

    def __init__(self, master, app):
        super().__init__(master, fg_color=PAGE_BG, corner_radius=0)
        AppHeader(self, app, nav=True).pack(fill="x")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(18, 24))
        ctk.CTkLabel(body, text="Dashboard", font=F(30, True), text_color="black", anchor="w").pack(anchor="w")
        ctk.CTkLabel(body, text=f"Signed in as {app.user['username']} ({app.user['role']})", font=F(13),
                     text_color="black", anchor="w").pack(anchor="w", pady=(2, 20))
        tiles = [("Menu", "Take orders and build the cart", app.show_pos),
                 ("Your order", "Today's orders, cart and checkout", app.show_order)]
        if app.is_admin:
            tiles += [("Sales History & Reports", "Filter by date, review orders, export to CSV", app.show_sales),
                      ("Inventory", "Manage products, photos and stock levels", app.show_inventory)]
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(fill="x")
        for column in range(2):
            grid.columnconfigure(column, weight=1, uniform="tile")
        for index, (title, text, command) in enumerate(tiles):
            self._tile(grid, title, text, command).grid(row=index // 2, column=index % 2, sticky="ew",
                                                        padx=10, pady=10)

    @staticmethod
    def _tile(parent, title, text, command):
        tile = ctk.CTkFrame(parent, fg_color="white", border_color=ORANGE, border_width=2,
                            corner_radius=0, height=120, cursor="hand2")
        tile.pack_propagate(False)
        heading = ctk.CTkLabel(tile, text=title, font=F(22, True), text_color="black", anchor="w")
        heading.pack(anchor="w", padx=26, pady=(26, 2))
        sub = ctk.CTkLabel(tile, text=text, font=F(13), text_color=GREY_TEXT, anchor="w")
        sub.pack(anchor="w", padx=26)
        for widget in (tile, heading, sub):
            widget.bind("<Button-1>", lambda _e: command())
            widget.bind("<Enter>", lambda _e: tile.configure(fg_color="#f8ecdd"))
            widget.bind("<Leave>", lambda _e: tile.configure(fg_color="white"))
        return tile
