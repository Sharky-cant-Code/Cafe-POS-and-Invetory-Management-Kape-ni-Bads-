"""BrewPOS - Kapehan ni Bads: cafe point of sale + inventory (CustomTkinter + SQLite).

Run:  python main.py
"""
from tkinter import messagebox

import customtkinter as ctk

import database as db
from admin_screens import InventoryScreen, SalesScreen
from auth_screens import ForgotScreen, LoginScreen, ResetScreen, SignupScreen
from pos_screens import DashboardScreen, GcashScreen, OrderScreen, POSScreen
from theme import PAGE_BG
from widgets import init_styles


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title("BrewPOS - Kapehan ni Bads")
        self.configure(fg_color=PAGE_BG)
        width, height = 1280, 780
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1100, 680)
        db.init_db()
        init_styles(self)
        self.protocol("WM_DELETE_WINDOW", self._quit)

        self.user = None          # {'id', 'username', 'role'} once logged in
        self.cart = {}            # product_id -> quantity
        self.cart_focus = None    # product shown in the POS side panel
        self._screen = None
        self.show_login()

    # ------------------------------------------------------------ navigation
    def _show(self, screen_class, *args, **kwargs):
        new = screen_class(self, self, *args, **kwargs)
        new.pack(fill="both", expand=True)
        if self._screen is not None:
            self._screen.destroy()
        self._screen = new
        return new

    @property
    def is_admin(self) -> bool:
        return bool(self.user) and self.user["role"] == "admin"

    def _needs_login(self) -> bool:
        if self.user is None:
            self.show_login()
            return True
        return False

    def show_login(self, prefill=None):
        screen = self._show(LoginScreen)
        if prefill:
            screen.prefill(prefill)

    def show_signup(self):
        self._show(SignupScreen)

    def show_forgot(self):
        self._show(ForgotScreen)

    def show_reset(self, user_id, initial_password=""):
        self._show(ResetScreen, user_id, initial_password)

    def login(self, user):
        self.user, self.cart, self.cart_focus = user, {}, None
        self.show_pos()

    def logout(self):
        if self.cart and not messagebox.askyesno("Log out", "Your cart has items that haven't been paid for.\nLog out anyway?"):
            return
        self.user, self.cart, self.cart_focus = None, {}, None
        self.show_login()

    def show_dashboard(self):
        if not self._needs_login():
            self._show(DashboardScreen)

    def show_pos(self):
        if not self._needs_login():
            self._show(POSScreen)

    def show_order(self):
        if not self._needs_login():
            self._show(OrderScreen)

    def show_gcash(self):
        if self._needs_login():
            return
        if not self.cart_lines():
            self.show_order()
            return
        self._show(GcashScreen)

    def show_sales(self):
        if self._needs_login():
            return
        if not self.is_admin:
            messagebox.showinfo("Admins only", "Only an admin account can open Sales History & Reports.")
            return
        self._show(SalesScreen)

    def show_inventory(self):
        if self._needs_login():
            return
        if not self.is_admin:
            messagebox.showinfo("Admins only", "Only an admin account can manage the inventory.")
            return
        self._show(InventoryScreen)

    # ------------------------------------------------------------------ cart
    def cart_add(self, product_id: int, qty: int = 1) -> bool:
        product = db.get_product(product_id)
        if product is None:
            return False
        wanted = self.cart.get(product_id, 0) + qty
        if wanted > product["stock"]:
            messagebox.showwarning("Not enough stock", f"Only {product['stock']} left of {product['name']}.")
            return False
        if wanted <= 0:
            self.cart.pop(product_id, None)
        else:
            self.cart[product_id] = wanted
        self.cart_focus = product_id
        return True

    def cart_remove(self, product_id: int):
        self.cart.pop(product_id, None)

    def cart_lines(self):
        """Cart as [{'product': row, 'qty': n, 'amount': cents}], dropping items deleted since."""
        lines = []
        for product_id, qty in list(self.cart.items()):
            product = db.get_product(product_id)
            if product is None:
                del self.cart[product_id]
                continue
            lines.append({"product": product, "qty": qty, "amount": product["price_cents"] * qty})
        return lines

    def cart_total(self) -> int:
        return sum(line["amount"] for line in self.cart_lines())

    # ------------------------------------------------------------------ exit
    def _quit(self):
        db.close_db()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
