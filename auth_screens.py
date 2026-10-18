"""Login, Create Account, Forgot Password and Create-new-password screens."""
from tkinter import messagebox

import customtkinter as ctk

import database as db
from theme import CARD_BG, GREY_TEXT, HINT_TEXT, ORANGE, PAGE_BG, F
from utils import load_settings, save_settings, validate_password
from widgets import AppHeader, IconEntry, QuestionBox, field_label, link_button, solid_button

ERROR_RED = "#c0392b"


class AuthScreen(ctk.CTkFrame):
    """Beige page, centered brand header and a rounded light-grey card."""

    def __init__(self, master, app, title: str, back_link: bool = True):
        super().__init__(master, fg_color=PAGE_BG, corner_radius=0)
        self.app = app
        AppHeader(self, app).pack(fill="x")
        card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=28)
        card.place(relx=0.5, rely=0.56, anchor="center")
        self.form = ctk.CTkFrame(card, fg_color="transparent")
        self.form.pack(padx=80, pady=(40, 40))
        ctk.CTkLabel(self.form, text=title, font=F(32, True), text_color="black",
                     justify="center", wraplength=306).pack(pady=(0, 14))
        self._back_link = back_link

    # -- building blocks
    def add_field(self, label, widget):
        field_label(self.form, label).pack(anchor="w", padx=6, pady=(10, 3))
        widget.pack()
        return widget

    def add_message(self):
        self.message = ctk.CTkLabel(self.form, text="", font=F(12), text_color=ERROR_RED,
                                    wraplength=306, justify="left", anchor="w")
        self.message.pack(anchor="w", padx=6, pady=(6, 0))

    def show_error(self, text: str):
        self.message.configure(text=text)

    def add_button(self, text, command):
        button = solid_button(self.form, text, command, fg=ORANGE, text_color="black", width=306,
                              height=48, font=F(17, True), corner_radius=10)
        button.pack(pady=(8, 0))
        if self._back_link:
            link_button(self.form, "← Back to login", self.app.show_login, color=GREY_TEXT,
                        size=12).pack(pady=(14, 0))
        return button


class LoginScreen(AuthScreen):
    def __init__(self, master, app):
        super().__init__(master, app, "Login", back_link=False)
        self.username = self.add_field("Username", IconEntry(self.form, "Enter your Username", icon="icon_user"))
        self.password = self.add_field("Password", IconEntry(self.form, "Enter your Password",
                                                             icon="icon_lock", password=True, toggle=True))
        row = ctk.CTkFrame(self.form, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        self.remember = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row, text="Remember me", variable=self.remember, font=F(11, True),
                        checkbox_width=18, checkbox_height=18, border_width=2, corner_radius=2,
                        fg_color=ORANGE, hover_color=ORANGE, border_color="black",
                        text_color="black").pack(side="left", padx=(6, 0))
        link_button(row, "Forgot Password ?", app.show_forgot, size=11).pack(side="right")
        self.add_message()
        self.login_button = self.add_button("Login", self.submit)
        footer = ctk.CTkFrame(self.form, fg_color="transparent")
        footer.pack(pady=(16, 0))
        ctk.CTkLabel(footer, text="Don't have an account ?", font=F(12, True),
                     text_color="#8a8a8a").pack(side="left")
        link_button(footer, "Sign up", app.show_signup, size=12).pack(side="left", padx=(4, 0))

        for field in (self.username, self.password):
            field.on_enter(self.submit)
        remembered = load_settings().get("remembered_username")
        if remembered:
            self.username.set(remembered)
            self.remember.set(True)
            self.after(100, self.password.focus)
        else:
            self.after(100, self.username.focus)

    def prefill(self, username: str):
        self.username.set(username)
        self.after(100, self.password.focus)

    def submit(self):
        username, password = self.username.get().strip(), self.password.get()
        if not username or not password:
            self.show_error("Please enter your username and password.")
            return
        user = db.authenticate(username, password)
        if user is None:
            self.show_error("Invalid username or password.")
            self.login_button.configure(state="disabled")      # brief pause slows down guessing
            self.after(1200, lambda: self.login_button.winfo_exists() and self.login_button.configure(state="normal"))
            return
        settings = load_settings()
        if self.remember.get():
            settings["remembered_username"] = user["username"]
        else:
            settings.pop("remembered_username", None)
        save_settings(settings)
        self.app.login(user)


class SignupScreen(AuthScreen):
    def __init__(self, master, app):
        super().__init__(master, app, "Create Account")
        self.username = self.add_field("Create your username", IconEntry(self.form, "Username", icon="icon_user"))
        self.password = self.add_field("Create your password", IconEntry(
            self.form, "Password", icon="icon_lock", password=True, toggle=True))
        self.question = self.add_field("Secret Question", QuestionBox(self.form))
        self.answer = self.add_field("Your Answer", IconEntry(self.form, "Your answer", password=True, toggle=True))
        self.add_message()
        self.add_button("Create", self.submit)
        self.after(100, self.username.focus)

    def submit(self):
        question = self.question.selected()
        if not self.username.get().strip() or not self.password.get() or not question:
            self.show_error("Please fill in every field and choose a secret question.")
            return
        try:
            user = db.create_user(self.username.get(), self.password.get(), question, self.answer.get())
        except ValueError as error:
            self.show_error(str(error))
            return
        note = ("This first account is the admin account." if user["role"] == "admin"
                else "You can now log in.")
        messagebox.showinfo("Account created", f"Welcome, {user['username']}! {note}")
        self.app.show_login(prefill=user["username"])


class ForgotScreen(AuthScreen):
    def __init__(self, master, app):
        super().__init__(master, app, "Forgot Password")
        self.username = self.add_field("Enter your username", IconEntry(self.form, "Enter your username", icon="icon_user"))
        self.question = self.add_field("Secret Question", QuestionBox(self.form))
        self.answer = self.add_field("Your Answer", IconEntry(self.form, "Your Answer"))
        self.new_password = self.add_field("Change Your Password", IconEntry(self.form, "New Password", password=True))
        self.add_message()
        self.add_button("Create new password", self.submit)
        self.after(100, self.username.focus)

    def submit(self):
        question = self.question.selected()
        if not self.username.get().strip() or not question or not self.answer.get().strip():
            self.show_error("Please enter your username, secret question, and answer.")
            return
        user_id = db.verify_secret(self.username.get(), question, self.answer.get())
        if user_id is None:
            self.show_error("Username, secret question, or answer is incorrect.")
            return
        new_password = self.new_password.get()
        if new_password:
            try:
                validate_password(new_password)
            except ValueError as error:
                self.show_error(str(error))
                return
        self.app.show_reset(user_id, new_password)       # identity confirmed -> final screen


class ResetScreen(AuthScreen):
    def __init__(self, master, app, user_id: int, initial_password: str = ""):
        super().__init__(master, app, "Create new password")
        self.user_id = user_id
        self.password = self.add_field("Create new Password", IconEntry(
            self.form, "Create new password", icon="icon_lock", password=True))
        self.show_password = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self.form, text="Show password", variable=self.show_password, command=self._toggle,
                        font=F(11), checkbox_width=18, checkbox_height=18, border_width=2, corner_radius=2,
                        fg_color=ORANGE, hover_color=ORANGE, border_color="black",
                        text_color="black").pack(anchor="w", padx=6, pady=(8, 0))
        ctk.CTkLabel(self.form, text="Use at least 8 characters with a mix of letters, numbers, and symbols.",
                     font=F(11), text_color=HINT_TEXT, wraplength=240, justify="left",
                     anchor="w").pack(anchor="w", padx=6, pady=(4, 0))
        self.confirm = self.add_field("Confirm your password", IconEntry(self.form, "Confirm your password", password=True))
        self.add_message()
        self.add_button("Create new password", self.submit)
        if initial_password:
            self.password.set(initial_password)
        self.after(100, self.password.focus if not initial_password else self.confirm.focus)

    def _toggle(self):
        hidden = not self.show_password.get()
        self.password.set_hidden(hidden)
        self.confirm.set_hidden(hidden)

    def submit(self):
        password = self.password.get()
        try:
            validate_password(password)
        except ValueError as error:
            self.show_error(str(error))
            return
        if password != self.confirm.get():
            self.show_error("The two passwords don't match.")
            return
        db.set_password(self.user_id, password)
        messagebox.showinfo("Password changed", "Your password has been updated. Please log in.")
        self.app.show_login()
