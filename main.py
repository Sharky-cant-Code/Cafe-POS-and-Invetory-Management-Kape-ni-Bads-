"""
main.py
Entry point for the Cafe Point of Sale & Inventory Management
System. Run this file to start the app:

    python main.py

On first run it creates cafe_pos.db automatically (with a
default admin and cashier account, plus sample menu items) so
you can log in and try it out immediately.
"""

import customtkinter as ctk
import database as db
from gui.login_window import LoginFrame
from gui.main_window import MainWindow

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Cafe Point of Sale & Inventory Management System")
        self.geometry("1150x700")
        self.minsize(950, 600)

        db.init_db()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.current_screen = None
        self.show_login()

    def show_login(self):
        self._swap_screen(LoginFrame(self, on_login_success=self.show_main_app))

    def show_main_app(self, user):
        self._swap_screen(MainWindow(self, user, on_logout=self.show_login))

    def _swap_screen(self, new_screen):
        if self.current_screen is not None:
            self.current_screen.destroy()
        self.current_screen = new_screen
        self.current_screen.grid(row=0, column=0, sticky="nsew")


if __name__ == "__main__":
    app = App()
    app.mainloop()
