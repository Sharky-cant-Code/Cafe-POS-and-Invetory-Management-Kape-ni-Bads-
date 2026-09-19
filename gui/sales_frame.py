"""
gui/sales_frame.py
Sales history & reports. Admins see every order; cashiers see
only their own. Includes quick date filters, summary stats,
best-sellers, order detail lookup, and CSV export.
"""

import csv
import os
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from datetime import date, timedelta
import database as db


class SalesFrame(ctk.CTkFrame):
    def __init__(self, master, user):
        super().__init__(master, fg_color="transparent")
        self.user = user
        self.is_admin = user["role"] == "admin"
        self.date_from = None
        self.date_to = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # ---------------- filter bar ----------------
        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        for label, days in [("Today", 0), ("This Week", 7), ("This Month", 30), ("All Time", None)]:
            ctk.CTkButton(filter_bar, text=label, width=100,
                          command=lambda d=days: self.apply_quick_filter(d)).pack(side="left",
                                                                                    padx=(0, 6))
        ctk.CTkButton(filter_bar, text="Export CSV", command=self.export_csv).pack(side="right")

        # ---------------- summary cards ----------------
        summary_bar = ctk.CTkFrame(self, fg_color="transparent")
        summary_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.total_sales_card = self._make_card(summary_bar, "Total Sales", "P0.00")
        self.total_sales_card.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.total_orders_card = self._make_card(summary_bar, "Total Orders", "0")
        self.total_orders_card.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.best_seller_card = self._make_card(summary_bar, "Best Seller", "-")
        self.best_seller_card.pack(side="left", fill="x", expand=True)

        # ---------------- orders table ----------------
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2a2d2e", foreground="white",
                         fieldbackground="#2a2d2e", rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background="#1f6aa5", foreground="white",
                         relief="flat")

        columns = ("order_no", "datetime", "cashier", "total", "payment")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        headers = {"order_no": "Order #", "datetime": "Date/Time", "cashier": "Cashier",
                   "total": "Total", "payment": "Payment"}
        widths = {"order_no": 160, "datetime": 150, "cashier": 140, "total": 100, "payment": 100}
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center")
        self.tree.grid(row=3, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self.show_order_detail)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=3, column=1, sticky="ns")

        ctk.CTkLabel(self, text="Double-click an order to view its items.",
                     text_color="gray60", font=ctk.CTkFont(size=11)).grid(
            row=4, column=0, sticky="w", pady=(4, 0))

        self.apply_quick_filter(0)  # default: today

    def _make_card(self, parent, label, value):
        card = ctk.CTkFrame(parent, corner_radius=10)
        ctk.CTkLabel(card, text=label, text_color="gray60",
                     font=ctk.CTkFont(size=12)).pack(padx=15, pady=(10, 0), anchor="w")
        value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=20, weight="bold"))
        value_label.pack(padx=15, pady=(0, 10), anchor="w")
        card.value_label = value_label
        return card

    # ---------------------------------------------------------

    def apply_quick_filter(self, days):
        if days is None:
            self.date_from, self.date_to = None, None
        else:
            self.date_to = date.today().isoformat()
            self.date_from = (date.today() - timedelta(days=days)).isoformat()
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        cashier_filter = None if self.is_admin else self.user["id"]
        orders = db.get_orders(self.date_from, self.date_to, cashier_filter)
        for o in orders:
            self.tree.insert("", "end", iid=str(o["id"]), values=(
                o["order_number"], o["timestamp"], o["cashier_name"],
                f"P{o['total']:.2f}", o["payment_method"]
            ))

        summary = db.get_sales_summary(self.date_from, self.date_to)
        self.total_sales_card.value_label.configure(text=f"P{summary['total_sales']:.2f}")
        self.total_orders_card.value_label.configure(text=str(summary["order_count"]))

        best = db.get_best_sellers(self.date_from, self.date_to, limit=1)
        self.best_seller_card.value_label.configure(
            text=best[0]["product_name"] if best else "-")

    def show_order_detail(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        order_id = int(sel[0])
        items = db.get_order_items(order_id)

        win = ctk.CTkToplevel(self)
        win.title("Order Detail")
        win.geometry("350x400")
        win.grab_set()

        box = ctk.CTkTextbox(win, font=("Courier New", 12))
        box.pack(fill="both", expand=True, padx=10, pady=10)
        lines = [f"{'Item':<20}{'Qty':>4}{'Amount':>10}", "-" * 34]
        for it in items:
            lines.append(f"{it['product_name'][:20]:<20}{it['quantity']:>4}"
                          f"{('P%.2f' % it['subtotal']):>10}")
        box.insert("1.0", "\n".join(lines))
        box.configure(state="disabled")

    def export_csv(self):
        cashier_filter = None if self.is_admin else self.user["id"]
        orders = db.get_orders(self.date_from, self.date_to, cashier_filter)
        if not orders:
            messagebox.showinfo("Nothing to export", "No orders in the current filter.")
            return

        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv")],
                                             initialfile="sales_export.csv")
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Order #", "Date/Time", "Cashier", "Subtotal", "Discount",
                              "Tax", "Total", "Payment Method"])
            for o in orders:
                writer.writerow([o["order_number"], o["timestamp"], o["cashier_name"],
                                  o["subtotal"], o["discount"], o["tax"], o["total"],
                                  o["payment_method"]])

        messagebox.showinfo("Exported", f"Saved to {path}")
