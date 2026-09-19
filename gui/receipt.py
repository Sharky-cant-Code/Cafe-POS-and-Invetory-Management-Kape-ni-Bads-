"""
gui/receipt.py
Builds a plain-text receipt for an order and shows it in a popup
window where the cashier can save it to a file or send it to the
system's default printer.
"""

import os
import sys
import customtkinter as ctk

RECEIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "receipts")
CAFE_NAME = "The Corner Cafe"
RECEIPT_WIDTH = 40


def format_receipt_text(order_number, timestamp, cashier_name, items,
                         subtotal, discount, tax, total, payment_method,
                         amount_paid, change_due):
    """Builds a monospace, receipt-style block of text."""
    line = "-" * RECEIPT_WIDTH
    lines = []
    lines.append(CAFE_NAME.center(RECEIPT_WIDTH))
    lines.append("Cafe POS & Inventory System".center(RECEIPT_WIDTH))
    lines.append(line)
    lines.append(f"Order #: {order_number}")
    lines.append(f"Date:    {timestamp}")
    lines.append(f"Cashier: {cashier_name}")
    lines.append(line)
    lines.append(f"{'Item':<20}{'Qty':>4}{'Amount':>16}")
    lines.append(line)
    for it in items:
        name = it["product_name"][:20]
        qty = it["quantity"]
        amt = f"P{it['subtotal']:.2f}"
        lines.append(f"{name:<20}{qty:>4}{amt:>16}")
    lines.append(line)
    lines.append(f"{'Subtotal:':<24}{('P%.2f' % subtotal):>16}")
    if discount:
        lines.append(f"{'Discount:':<24}{('-P%.2f' % discount):>16}")
    if tax:
        lines.append(f"{'Tax:':<24}{('P%.2f' % tax):>16}")
    lines.append(f"{'TOTAL:':<24}{('P%.2f' % total):>16}")
    lines.append(line)
    lines.append(f"{'Payment (' + payment_method + '):':<24}{('P%.2f' % amount_paid):>16}")
    lines.append(f"{'Change:':<24}{('P%.2f' % change_due):>16}")
    lines.append(line)
    lines.append("Thank you and see you again!".center(RECEIPT_WIDTH))
    return "\n".join(lines)


def save_receipt_to_file(text, order_number):
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    path = os.path.join(RECEIPTS_DIR, f"{order_number}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def print_receipt(filepath):
    """Best-effort OS print. Actual printing depends on the OS having
    a default printer configured — this simply hands the file to the
    OS's print mechanism. If that's not available, the caller should
    fall back to telling the user the file was saved instead."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(filepath, "print")
            return True, "Sent to default printer."
        elif sys.platform == "darwin":
            os.system(f'lpr "{filepath}"')
            return True, "Sent to default printer."
        else:
            os.system(f'lpr "{filepath}"')
            return True, "Sent to default printer (requires a configured CUPS printer)."
    except Exception as e:
        return False, f"Could not print automatically: {e}"


def show_receipt_window(parent, order_number, timestamp, cashier_name, items,
                         subtotal, discount, tax, total, payment_method,
                         amount_paid, change_due):
    """Opens a popup with the receipt text, plus Save / Print / Close buttons."""
    text = format_receipt_text(order_number, timestamp, cashier_name, items,
                                subtotal, discount, tax, total, payment_method,
                                amount_paid, change_due)

    win = ctk.CTkToplevel(parent)
    win.title(f"Receipt - {order_number}")
    win.geometry("380x560")
    win.grab_set()  # modal: keep focus until closed

    box = ctk.CTkTextbox(win, font=("Courier New", 12), width=360, height=440)
    box.pack(padx=10, pady=10, fill="both", expand=True)
    box.insert("1.0", text)
    box.configure(state="disabled")

    status_label = ctk.CTkLabel(win, text="")
    status_label.pack(pady=(0, 4))

    btn_frame = ctk.CTkFrame(win, fg_color="transparent")
    btn_frame.pack(pady=(0, 10))

    def do_save():
        path = save_receipt_to_file(text, order_number)
        status_label.configure(text=f"Saved to {path}")

    def do_print():
        path = save_receipt_to_file(text, order_number)
        ok, msg = print_receipt(path)
        status_label.configure(text=msg)

    ctk.CTkButton(btn_frame, text="Save as .txt", command=do_save).grid(row=0, column=0, padx=5)
    ctk.CTkButton(btn_frame, text="Print", command=do_print).grid(row=0, column=1, padx=5)
    ctk.CTkButton(btn_frame, text="Close", command=win.destroy,
                  fg_color="gray40", hover_color="gray30").grid(row=0, column=2, padx=5)

    return win
