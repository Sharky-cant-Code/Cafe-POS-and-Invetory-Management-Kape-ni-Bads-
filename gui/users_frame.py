"""
gui/users_frame.py
Admin-only screen for managing staff accounts: create new
cashier/admin logins, deactivate accounts, reset passwords.
"""

import customtkinter as ctk
from tkinter import ttk, messagebox
import database as db


class UsersFrame(ctk.CTkFrame):
    def __init__(self, master, user):
        super().__init__(master, fg_color="transparent")
        self.user = user  # the logged-in admin

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkButton(top_bar, text="+ Add Staff Account", command=self.open_add_dialog).pack(
            side="left")
        ctk.CTkButton(top_bar, text="Reset Password", command=self.open_reset_dialog).pack(
            side="left", padx=8)
        ctk.CTkButton(top_bar, text="Deactivate", fg_color="#c0392b", hover_color="#96281b",
                      command=lambda: self.set_active(False)).pack(side="left", padx=8)
        ctk.CTkButton(top_bar, text="Reactivate", command=lambda: self.set_active(True)).pack(
            side="left")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2a2d2e", foreground="white",
                         fieldbackground="#2a2d2e", rowheight=28, borderwidth=0)
        style.configure("Treeview.Heading", background="#1f6aa5", foreground="white",
                         relief="flat")

        columns = ("username", "full_name", "role", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        for col, label, width in [("username", "Username", 150), ("full_name", "Full Name", 200),
                                    ("role", "Role", 100), ("status", "Status", 100)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="center" if col != "full_name" else "w")
        self.tree.grid(row=1, column=0, sticky="nsew")

        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for u in db.get_all_users():
            self.tree.insert("", "end", iid=str(u["id"]), values=(
                u["username"], u["full_name"], u["role"].capitalize(),
                "Active" if u["active"] else "Inactive"
            ))

    def selected_user_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def open_add_dialog(self):
        AddUserDialog(self, on_save=self._save_new_user)

    def _save_new_user(self, username, password, full_name, role):
        try:
            db.add_user(username, password, full_name, role)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Could not add user", str(e))

    def open_reset_dialog(self):
        uid = self.selected_user_id()
        if not uid:
            messagebox.showinfo("No selection", "Select a staff account first.")
            return
        ResetPasswordDialog(self, on_save=lambda pw: self._reset_password(uid, pw))

    def _reset_password(self, user_id, new_password):
        db.change_password(user_id, new_password)
        messagebox.showinfo("Done", "Password updated.")

    def set_active(self, active):
        uid = self.selected_user_id()
        if not uid:
            messagebox.showinfo("No selection", "Select a staff account first.")
            return
        if uid == self.user["id"] and not active:
            messagebox.showwarning("Not allowed", "You can't deactivate your own account.")
            return
        db.set_user_active(uid, active)
        self.refresh()


class AddUserDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save):
        super().__init__(master)
        self.title("Add Staff Account")
        self.geometry("320x420")
        self.grab_set()
        self.on_save = on_save

        pad = {"padx": 20, "pady": (8, 0)}
        ctk.CTkLabel(self, text="Username").pack(anchor="w", **pad)
        self.username_entry = ctk.CTkEntry(self, width=260)
        self.username_entry.pack(**pad)

        ctk.CTkLabel(self, text="Full name").pack(anchor="w", **pad)
        self.fullname_entry = ctk.CTkEntry(self, width=260)
        self.fullname_entry.pack(**pad)

        ctk.CTkLabel(self, text="Password").pack(anchor="w", **pad)
        self.password_entry = ctk.CTkEntry(self, width=260, show="*")
        self.password_entry.pack(**pad)

        ctk.CTkLabel(self, text="Role").pack(anchor="w", **pad)
        self.role_menu = ctk.CTkOptionMenu(self, values=["cashier", "admin"])
        self.role_menu.pack(**pad)

        self.error_label = ctk.CTkLabel(self, text="", text_color="#e74c3c")
        self.error_label.pack(pady=(10, 0))

        ctk.CTkButton(self, text="Create Account", command=self.save).pack(pady=15)

    def save(self):
        username = self.username_entry.get().strip()
        full_name = self.fullname_entry.get().strip()
        password = self.password_entry.get()
        role = self.role_menu.get()

        if not username or not full_name or not password:
            self.error_label.configure(text="All fields are required.")
            return
        if len(password) < 4:
            self.error_label.configure(text="Password should be at least 4 characters.")
            return

        self.on_save(username, password, full_name, role)
        self.destroy()


class ResetPasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, on_save):
        super().__init__(master)
        self.title("Reset Password")
        self.geometry("300x160")
        self.grab_set()
        self.on_save = on_save

        ctk.CTkLabel(self, text="New password:").pack(pady=(20, 5))
        self.password_entry = ctk.CTkEntry(self, width=200, show="*")
        self.password_entry.pack()
        self.error_label = ctk.CTkLabel(self, text="", text_color="#e74c3c")
        self.error_label.pack()
        ctk.CTkButton(self, text="Update Password", command=self.save).pack(pady=15)

    def save(self):
        pw = self.password_entry.get()
        if len(pw) < 4:
            self.error_label.configure(text="Password should be at least 4 characters.")
            return
        self.on_save(pw)
        self.destroy()
