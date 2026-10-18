"""Admin screens: Sales History & Reports, Inventory (with the add/edit and restock dialogs)."""
import csv
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

import database as db
from theme import (AMBER, CARD_BG, DANGER, FIELD_BG, GREY_TEXT, HINT_TEXT, ORANGE, PAGE_BG, SELECT_BG,
                   F, mono)
from utils import (CATEGORIES, LOW_STOCK_LIMIT, csv_safe, parse_price, parse_whole_number, peso,
                   pretty_time, range_start)
from widgets import (AppHeader, ChipBar, DataTable, IconEntry, StatCard, outline_button,
                     product_image, product_thumb, solid_button)

RANGES = ["Today", "This Week", "This Month", "All Time"]


def _search_box(master, placeholder, width, command):
    box = ctk.CTkEntry(master, placeholder_text=placeholder, width=width, height=42, corner_radius=0,
                       border_width=1, border_color="black", fg_color="white", text_color="black",
                       placeholder_text_color=GREY_TEXT, font=F(13))
    box.bind("<KeyRelease>", lambda _e: command())
    return box


# ------------------------------------------------------------------ sales
class SalesScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=PAGE_BG, corner_radius=0)
        self.app, self.range, self._orders = app, "Today", []
        AppHeader(self, app, nav=True).pack(fill="x")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(18, 24))

        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x")
        titles = ctk.CTkFrame(top, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="Sales History & Reports", font=F(30, True), text_color="black",
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(titles, text="Filter by date range, review orders, export to CSV", font=F(13),
                     text_color="black", anchor="w").pack(anchor="w", pady=(2, 0))
        outline_button(top, "Export CSV", self.export, width=128, height=48).pack(side="right")
        outline_button(top, "+ Add Sales", app.show_pos, width=118, height=48).pack(side="right", padx=(0, 16))

        ChipBar(body, RANGES, self._set_range, "Today", on_fg=AMBER, on_text="white", off_fg="#fcfcfc",
                width=120).pack(anchor="w", pady=(16, 16))

        cards = ctk.CTkFrame(body, fg_color="transparent")
        cards.pack(fill="x", pady=(0, 16))
        for column in range(3):
            cards.columnconfigure(column, weight=1, uniform="stat")
        self.sales_card = StatCard(cards, "Total sales")
        self.orders_card = StatCard(cards, "Total orders")
        self.best_card = StatCard(cards, "Best-seller")
        for column, card in enumerate((self.sales_card, self.orders_card, self.best_card)):
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0 if column == 2 else 10))

        middle = ctk.CTkFrame(body, fg_color="transparent")
        middle.pack(fill="both", expand=True)
        middle.columnconfigure(0, weight=1)
        middle.rowconfigure(0, weight=1)
        self.table = DataTable(middle, [
            ("order", "Order#", 84, "center", False), ("when", "Date and time", 190, "center", True),
            ("items", "Items", 250, "w", True), ("payment", "Payment", 90, "center", False),
            ("total", "Total", 110, "e", False)], on_select=self._show_breakdown)
        self.table.grid(row=0, column=0, sticky="nsew", padx=(0, 22))

        panel = ctk.CTkFrame(middle, fg_color="white", border_color="black", border_width=1,
                             corner_radius=0, width=400)
        panel.grid(row=0, column=1, sticky="ns")
        panel.pack_propagate(False)
        ctk.CTkLabel(panel, text="Order Breakdown", font=F(21, True), text_color="black",
                     anchor="w").pack(anchor="w", padx=20, pady=(14, 0))
        self.breakdown_title = ctk.CTkLabel(panel, text="Select an order to see its items", font=F(11),
                                            text_color=GREY_TEXT, anchor="w", wraplength=360, justify="left")
        self.breakdown_title.pack(anchor="w", padx=22, pady=(0, 8))
        self.breakdown = ctk.CTkTextbox(panel, fg_color="white", text_color="black", font=mono(13),
                                        wrap="none", state="disabled", corner_radius=0)
        self.breakdown.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.refresh()

    def _set_range(self, label):
        self.range = label
        self.refresh()

    def refresh(self):
        start = range_start(self.range)
        self._orders = db.list_orders(start)
        stats = db.sales_stats(start)
        self.sales_card.set(peso(stats["total_cents"]))
        self.orders_card.set(str(stats["orders"]))
        self.best_card.set(f"{stats['best_name']} ({stats['best_sold']} sold)" if stats["best_name"] else "-")
        self.table.fill([
            {"iid": str(o["id"]), "values": (f"#{o['id']}", pretty_time(o["created_at"]), o["items"] or "",
                                              o["payment"], peso(o["total_cents"]))}
            for o in self._orders])
        self._write_breakdown("Select an order to see its items", "")

    def _write_breakdown(self, title, text):
        self.breakdown_title.configure(text=title)
        self.breakdown.configure(state="normal")
        self.breakdown.delete("1.0", "end")
        self.breakdown.insert("1.0", text)
        self.breakdown.configure(state="disabled")

    def _show_breakdown(self):
        iid = self.table.selected()
        order = next((o for o in self._orders if str(o["id"]) == iid), None)
        if order is None:
            return
        lines = []
        for item in db.order_items(order["id"]):
            label = f"{item['qty']} × {item['name']}"
            label = label if len(label) <= 21 else label[:20] + "…"
            lines.append(f"{label:<22}{peso(item['price_cents'] * item['qty']):>14}")
        lines += ["-" * 36, f"{'Total':<22}{peso(order['total_cents']):>14}", "", f"Cashier: {order['cashier']}"]
        self._write_breakdown(f"Order# {order['id']}  -  {pretty_time(order['created_at'])}  -  {order['payment']}",
                              "\n".join(lines))

    def export(self):
        if not self._orders:
            messagebox.showinfo("Nothing to export", "There are no orders in this date range.")
            return
        stamp = f"{self.range.lower().replace(' ', '_')}_{date.today():%Y-%m-%d}"
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile=f"sales_{stamp}.csv",
                                            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:     # BOM so Excel reads ₱/ñ right
                writer = csv.writer(handle)
                writer.writerow(["Order #", "Date and time", "Cashier", "Items", "Payment", "Total (PHP)"])
                for o in self._orders:
                    cents = o["total_cents"]
                    writer.writerow([o["id"], o["created_at"], csv_safe(o["cashier"]), csv_safe(o["items"]),
                                     o["payment"], f"{cents // 100}.{cents % 100:02d}"])
        except OSError as error:
            messagebox.showerror("Couldn't save the file", str(error))
            return
        messagebox.showinfo("Exported", f"Saved {len(self._orders)} orders to:\n{path}")


# -------------------------------------------------------------- inventory
def stock_status(stock: int) -> str:
    return "Out of Stock" if stock <= 0 else "Low Stock" if stock <= LOW_STOCK_LIMIT else "In Stock"


class InventoryScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=PAGE_BG, corner_radius=0)
        self.app = app
        self._scale = self.tk.call("tk", "scaling") / (96 / 72)
        AppHeader(self, app, nav=True).pack(fill="x")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=28, pady=(18, 24))

        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x", pady=(0, 14))
        titles = ctk.CTkFrame(top, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(titles, text="Inventory", font=F(30, True), text_color="black", anchor="w").pack(anchor="w")
        ctk.CTkLabel(titles, text="Manage your stock, photos, and stock levels", font=F(13),
                     text_color="black", anchor="w").pack(anchor="w", pady=(2, 0))
        solid_button(top, "Delete", self.delete, fg=DANGER, width=96, height=48, font=F(13, True)).pack(side="right")
        outline_button(top, "Restock", self.restock, width=96, height=48).pack(side="right", padx=(0, 12))
        outline_button(top, "Edit", self.edit, width=84, height=48).pack(side="right", padx=(0, 12))
        solid_button(top, "+ Add Product", self.add, fg=AMBER, width=130, height=48,
                     font=F(13, True)).pack(side="right", padx=(0, 12))
        self.search = _search_box(top, "Search products...", 250, self.refresh)
        self.search.pack(side="right", padx=(0, 24))

        self.table = DataTable(body, [
            ("product", "Product", 220, "center", True), ("category", "Category", 140, "center", True),
            ("price", "Price", 130, "center", True), ("stock", "Stock", 100, "center", True),
            ("status", "Status", 140, "center", True)], photo=True, on_double=self.edit)
        self.table.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        size = (int(64 * self._scale), int(44 * self._scale))
        rows = []
        for p in db.list_products(self.search.get()):
            rows.append({"iid": str(p["id"]), "image": product_thumb(p["image"], size),
                         "tags": ("out",) if p["stock"] <= 0 else (),
                         "values": (p["name"], p["category"], peso(p["price_cents"]), p["stock"],
                                    stock_status(p["stock"]))})
        self.table.fill(rows)

    def _selected_product(self):
        iid = self.table.selected()
        product = db.get_product(int(iid)) if iid else None
        if product is None:
            messagebox.showinfo("Select a product", "Click a product in the table first.")
        return product

    # -- actions
    def add(self):
        ProductDialog(self, None, self._save_new)

    def _save_new(self, v):
        image = db.save_product_image(v["photo_path"]) if v["photo_path"] else None
        try:
            db.add_product(v["name"], v["category"], v["price_cents"], v["stock"], image)
        except ValueError:
            db.delete_image(image)
            raise
        self.refresh()

    def edit(self):
        product = self._selected_product()
        if product:
            ProductDialog(self, product, lambda v: self._save_edit(product, v))

    def _save_edit(self, old, v):
        image, new_image = old["image"], None
        if v["photo_path"]:
            image = new_image = db.save_product_image(v["photo_path"])
        elif v["remove_photo"]:
            image = None
        try:
            db.update_product(old["id"], v["name"], v["category"], v["price_cents"], v["stock"], image)
        except ValueError:
            db.delete_image(new_image)
            raise
        if image != old["image"]:
            db.delete_image(old["image"])
        self.refresh()

    def restock(self):
        product = self._selected_product()
        if product:
            RestockDialog(self, product, lambda qty: (db.restock(product["id"], qty), self.refresh()))

    def delete(self):
        product = self._selected_product()
        if product and messagebox.askyesno(
                "Delete product", f"Delete “{product['name']}” from the menu?\nPast orders keep their sales record."):
            db.delete_product(product["id"])
            self.refresh()


# ---------------------------------------------------------------- dialogs
class _Dialog(ctk.CTkToplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.configure(fg_color=CARD_BG)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self._parent = parent.winfo_toplevel()
        self.message = None

    def finish_layout(self):
        self.update_idletasks()
        x = self._parent.winfo_rootx() + (self._parent.winfo_width() - self.winfo_reqwidth()) // 2
        y = self._parent.winfo_rooty() + (self._parent.winfo_height() - self.winfo_reqheight()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.after(150, self._grab)            # CTkToplevel must be visible before it can grab input

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except tk.TclError:
            pass

    def add_message(self):
        self.message = ctk.CTkLabel(self, text="", font=F(12), text_color="#c0392b", wraplength=320,
                                    justify="left", anchor="w")
        self.message.pack(anchor="w", padx=30, pady=(8, 0))

    def error(self, text):
        self.message.configure(text=text)


class ProductDialog(_Dialog):
    """Add / edit a product. on_save(values) may raise ValueError to keep the dialog open."""

    def __init__(self, parent, product, on_save):
        super().__init__(parent, "Edit product" if product else "Add product")
        self._on_save, self._photo_path, self._remove_photo = on_save, None, False
        self._has_photo = bool(product and product["image"])
        ctk.CTkLabel(self, text="Edit product" if product else "Add product", font=F(24, True),
                     text_color="black").pack(padx=30, pady=(24, 4), anchor="w")
        self.name = self._field("Product name", IconEntry(self, "e.g. Iced Americano", width=340))
        ctk.CTkLabel(self, text="Category", font=F(13), text_color="black").pack(anchor="w", padx=30, pady=(10, 3))
        self.category = ctk.CTkComboBox(self, values=CATEGORIES, state="readonly", width=340, height=42,
                                        corner_radius=10, border_width=1, border_color=ORANGE,
                                        fg_color=FIELD_BG, button_color=FIELD_BG, button_hover_color="#c4c4c4",
                                        dropdown_fg_color="white", dropdown_text_color="black",
                                        dropdown_hover_color=SELECT_BG, text_color="#222222",
                                        font=F(13, True), dropdown_font=F(13))
        self.category.pack(padx=30)
        self.price = self._field("Price (PHP)", IconEntry(self, "0.00", width=340))
        self.stock = self._field("Stock on hand", IconEntry(self, "0", width=340))

        ctk.CTkLabel(self, text="Photo", font=F(13), text_color="black").pack(anchor="w", padx=30, pady=(10, 3))
        photo_row = ctk.CTkFrame(self, fg_color="transparent")
        photo_row.pack(fill="x", padx=30)
        self.preview = ctk.CTkLabel(photo_row, text="No photo", width=96, height=70, fg_color=PAGE_BG,
                                    text_color=GREY_TEXT, font=F(11))
        self.preview.pack(side="left")
        outline_button(photo_row, "Choose photo…", self._choose_photo, width=130, height=36,
                       font=F(12)).pack(side="left", padx=12)
        self.remove_button = outline_button(photo_row, "Remove", self._clear_photo, width=80, height=36,
                                            font=F(12))
        self.add_message()
        solid_button(self, "Save", self._save, fg=ORANGE, text_color="black", width=340, height=46,
                     font=F(16, True), corner_radius=10).pack(padx=30, pady=(12, 8))
        ctk.CTkButton(self, text="Cancel", command=self.destroy, fg_color="transparent",
                      hover_color="#dcdcdc", text_color=GREY_TEXT, font=F(13), height=24,
                      width=60).pack(pady=(0, 18))

        if product:
            self.name.set(product["name"])
            self.category.set(product["category"])
            self.price.set(f"{product['price_cents'] // 100}.{product['price_cents'] % 100:02d}")
            self.stock.set(str(product["stock"]))
            if self._has_photo:
                self._set_preview(db.IMAGE_DIR / product["image"])
        else:
            self.category.set(CATEGORIES[0])
            self.stock.set("0")
        self.finish_layout()
        self.after(200, self.name.focus)

    def _field(self, label, widget):
        ctk.CTkLabel(self, text=label, font=F(13), text_color="black").pack(anchor="w", padx=30, pady=(10, 3))
        widget.pack(padx=30)
        return widget

    def _set_preview(self, path):
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                img.thumbnail((192, 140))
                thumb = ctk.CTkImage(light_image=img.copy(), dark_image=img.copy(),
                                     size=(img.width // 2, img.height // 2))
        except OSError:
            self.error("Couldn't read that image.")
            return False
        self.preview.configure(image=thumb, text="")
        self.remove_button.pack(side="left")
        return True

    def _choose_photo(self):
        path = filedialog.askopenfilename(parent=self, title="Choose a product photo",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
        if path and self._set_preview(path):
            self._photo_path, self._remove_photo = path, False
            self.error("")

    def _clear_photo(self):
        self._photo_path, self._remove_photo = None, True
        self.preview.configure(image=product_image(None, (96, 70)), text="No photo")
        self.remove_button.pack_forget()

    def _save(self):
        name = self.name.get().strip()
        if not name:
            self.error("Please enter a product name.")
            return
        try:
            values = {"name": name, "category": self.category.get(),
                      "price_cents": parse_price(self.price.get()),
                      "stock": parse_whole_number(self.stock.get(), "Stock"),
                      "photo_path": self._photo_path, "remove_photo": self._remove_photo}
            self._on_save(values)
        except ValueError as error:
            self.error(str(error))
            return
        self.destroy()


class RestockDialog(_Dialog):
    def __init__(self, parent, product, on_save):
        super().__init__(parent, "Restock")
        self._on_save = on_save
        ctk.CTkLabel(self, text="Restock", font=F(24, True), text_color="black").pack(padx=30, pady=(24, 2), anchor="w")
        ctk.CTkLabel(self, text=f"{product['name']}  (currently {product['stock']} in stock)", font=F(13),
                     text_color=GREY_TEXT, wraplength=320, justify="left").pack(padx=30, anchor="w")
        ctk.CTkLabel(self, text="Units to add", font=F(13), text_color="black").pack(anchor="w", padx=30, pady=(14, 3))
        self.qty = IconEntry(self, "e.g. 12", width=320)
        self.qty.pack(padx=30)
        self.qty.on_enter(self._save)
        self.add_message()
        solid_button(self, "Add stock", self._save, fg=ORANGE, text_color="black", width=320, height=46,
                     font=F(16, True), corner_radius=10).pack(padx=30, pady=(12, 8))
        ctk.CTkButton(self, text="Cancel", command=self.destroy, fg_color="transparent", hover_color="#dcdcdc",
                      text_color=GREY_TEXT, font=F(13), height=24, width=60).pack(pady=(0, 18))
        self.finish_layout()
        self.after(200, self.qty.focus)

    def _save(self):
        try:
            self._on_save(parse_whole_number(self.qty.get(), "Units", minimum=1))
        except ValueError as error:
            self.error(str(error))
            return
        self.destroy()
