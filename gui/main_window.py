"""
gui/main_window.py
The main app shell shown after login: a sidebar with navigation
buttons (which ones appear depends on the user's role) and a
content area on the right that swaps between POS / Inventory /
Sales / Users screens.
"""

import customtkinter as ctk
from tkinter import messagebox
from gui.pos_frame import POSFrame
from gui.inventory_frame import InventoryFrame
from gui.sales_frame import SalesFrame
from gui.users_frame import UsersFrame


class MainWindow(ctk.CTkFrame):
    def __init__(self, master, user, on_logout):
        super().__init__(master, fg_color="transparent")
        self.user = user
        self.on_logout = on_logout
        self.current_frame = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---------------- sidebar ----------------
        sidebar = ctk.CTkFrame(self, width=190, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="☕ Cafe POS",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(25, 5))
        ctk.CTkLabel(sidebar, text=f"{user['full_name']}\n({user['role'].capitalize()})",
                     text_color="gray60", justify="center").pack(pady=(0, 20))

        nav_buttons = [("Point of Sale", lambda: self.show_frame(POSFrame))]
        nav_buttons.append(("Inventory", lambda: self.show_frame(InventoryFrame)))
        nav_buttons.append(("Sales & Reports", lambda: self.show_frame(SalesFrame)))
        if user["role"] == "admin":
            nav_buttons.append(("Manage Staff", lambda: self.show_frame(UsersFrame)))

        self.nav_button_widgets = []
        for label, command in nav_buttons:
            btn = ctk.CTkButton(sidebar, text=label, anchor="w", command=command,
                                 fg_color="transparent", hover_color="gray25")
            btn.pack(fill="x", padx=15, pady=4)
            self.nav_button_widgets.append(btn)

        ctk.CTkButton(sidebar, text="Log Out", fg_color="#c0392b", hover_color="#96281b",
                      command=self.logout).pack(side="bottom", fill="x", padx=15, pady=20)

        # ---------------- content area ----------------
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        self.show_frame(POSFrame)

    def show_frame(self, frame_class):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = frame_class(self.content_area, self.user)
        self.current_frame.grid(row=0, column=0, sticky="nsew")

    def logout(self):
        if messagebox.askyesno("Log out", "Are you sure you want to log out?"):
            self.on_logout()
