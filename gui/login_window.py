"""
gui/login_window.py
The login screen. Verifies the username/password against the
database and, on success, tells the main App to open the main
window for that user's role.
"""

import customtkinter as ctk
import database as db


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        """
        master:            the root App window
        on_login_success:  callback(user_dict) the App gives us to call
                            once a login is verified
        """
        super().__init__(master)
        self.on_login_success = on_login_success

        container = ctk.CTkFrame(self, corner_radius=16)
        container.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(container, text="☕ Cafe POS System",
                     font=ctk.CTkFont(size=26, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=40, pady=(30, 5))
        ctk.CTkLabel(container, text="Point of Sale & Inventory Management",
                     font=ctk.CTkFont(size=13), text_color="gray60").grid(
            row=1, column=0, columnspan=2, padx=40, pady=(0, 20))

        ctk.CTkLabel(container, text="Username").grid(row=2, column=0, columnspan=2,
                                                        sticky="w", padx=40)
        self.username_entry = ctk.CTkEntry(container, width=260, placeholder_text="Username")
        self.username_entry.grid(row=3, column=0, columnspan=2, padx=40, pady=(0, 10))

        ctk.CTkLabel(container, text="Password").grid(row=4, column=0, columnspan=2,
                                                        sticky="w", padx=40)
        self.password_entry = ctk.CTkEntry(container, width=260, show="*",
                                            placeholder_text="Password")
        self.password_entry.grid(row=5, column=0, columnspan=2, padx=40, pady=(0, 10))
        self.password_entry.bind("<Return>", lambda e: self.attempt_login())

        self.error_label = ctk.CTkLabel(container, text="", text_color="#e74c3c")
        self.error_label.grid(row=6, column=0, columnspan=2, padx=40)

        ctk.CTkButton(container, text="Log In", width=260,
                      command=self.attempt_login).grid(
            row=7, column=0, columnspan=2, padx=40, pady=(10, 15))

        ctk.CTkLabel(
            container,
            text="Default admin: admin / admin123\nDefault cashier: cashier / cashier123",
            font=ctk.CTkFont(size=11), text_color="gray50", justify="center"
        ).grid(row=8, column=0, columnspan=2, padx=40, pady=(0, 25))

        self.username_entry.focus()

    def attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            self.error_label.configure(text="Please enter both username and password.")
            return

        user = db.verify_login(username, password)
        if user is None:
            self.error_label.configure(text="Invalid username or password.")
            self.password_entry.delete(0, "end")
            return

        self.error_label.configure(text="")
        self.on_login_success(user)
