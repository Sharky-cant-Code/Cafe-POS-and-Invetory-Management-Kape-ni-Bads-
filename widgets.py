"""Reusable widgets that give every screen the same look as the Figma design."""
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk
from PIL import Image, ImageOps, ImageTk

import database as db
from theme import (AMBER, AMBER_DARK, FIELD_BG, GREY_TEXT, HEADER_BG, HINT_TEXT, ORANGE, PAGE_BG,
                   SELECT_BG, SHOP_NAME, SHOP_TAGLINE, F, font_family)
from utils import SECRET_QUESTIONS

ASSETS = Path(__file__).resolve().parent / "assets"
_icons, _photos = {}, {}


# ----------------------------------------------------------------- images
def load_icon(name: str, size: tuple) -> ctk.CTkImage:
    key = (name, size)
    if key not in _icons:
        img = Image.open(ASSETS / f"{name}.png").convert("RGBA")
        _icons[key] = ctk.CTkImage(light_image=img, dark_image=img, size=size)
    return _icons[key]


def _fit_photo(filename, pixel_size: tuple) -> Image.Image:
    """Product photo cropped to pixel_size, or a flat beige placeholder."""
    if filename:
        try:
            with Image.open(db.IMAGE_DIR / Path(filename).name) as img:
                return ImageOps.fit(img.convert("RGB"), pixel_size, Image.LANCZOS)
        except OSError:
            pass
    return Image.new("RGB", pixel_size, PAGE_BG)


def product_image(filename, size: tuple) -> ctk.CTkImage:
    key = (filename, size)
    if key not in _photos:
        pil = _fit_photo(filename, (size[0] * 2, size[1] * 2))   # 2x so it stays sharp on HiDPI
        _photos[key] = ctk.CTkImage(light_image=pil, dark_image=pil, size=size)
    return _photos[key]


def product_thumb(filename, pixel_size: tuple) -> ImageTk.PhotoImage:
    """For ttk.Treeview rows (caller must keep a reference)."""
    return ImageTk.PhotoImage(_fit_photo(filename, pixel_size))


# ---------------------------------------------------------------- buttons
def _darken(color: str, factor: float = 0.88) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


def solid_button(master, text, command, fg=AMBER, text_color="white", width=120, height=40,
                 font=None, corner_radius=0, **kw):
    return ctk.CTkButton(master, text=text, command=command, fg_color=fg, hover_color=_darken(fg),
                         text_color=text_color, text_color_disabled="#d8d8d8", width=width,
                         height=height, corner_radius=corner_radius, font=font or F(14, True), **kw)


def outline_button(master, text, command, width=110, height=40, font=None, **kw):
    return ctk.CTkButton(master, text=text, command=command, fg_color="#fcfcfc", hover_color="#f1e4d4",
                         text_color="black", border_color=ORANGE, border_width=1, corner_radius=0,
                         width=width, height=height, font=font or F(13), **kw)


def link_button(master, text, command, color="black", size=12, bold=True):
    return ctk.CTkButton(master, text=text, command=command, fg_color="transparent",
                         hover_color=master.cget("fg_color") if master.cget("fg_color") != "transparent" else PAGE_BG,
                         text_color=color, font=F(size, bold), width=10, height=20, corner_radius=4)


# ----------------------------------------------------------------- header
class AppHeader(ctk.CTkFrame):
    """Dark-brown bar. nav=False: centered brand (auth screens). nav=True: brand left + menu buttons."""

    def __init__(self, master, app, nav: bool = False):
        super().__init__(master, fg_color=HEADER_BG, corner_radius=0, height=100)
        self.pack_propagate(False)
        brand = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(brand, text="", image=load_icon("logo", (66, 66))).pack(side="left", padx=(0, 16))
        text = ctk.CTkFrame(brand, fg_color="transparent")
        text.pack(side="left")
        ctk.CTkLabel(text, text=SHOP_NAME, font=F(22), text_color="white").pack()
        ctk.CTkLabel(text, text=SHOP_TAGLINE, font=F(15), text_color="white").pack()
        if not nav:
            brand.place(relx=0.5, rely=0.5, anchor="center")
            return
        brand.pack(side="left", padx=(30, 0))
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(side="right", padx=30)
        ctk.CTkButton(buttons, text="  Dashboard", image=load_icon("icon_dashboard", (22, 26)),
                      compound="left", command=app.show_dashboard, fg_color="white", hover_color="#f1e4d4",
                      text_color="black", border_color=ORANGE, border_width=1, corner_radius=2,
                      width=150, height=48, font=F(13, True)).pack(side="left", padx=8)
        ctk.CTkButton(buttons, text="Back to menu", command=app.show_pos, fg_color="white",
                      hover_color="#f1e4d4", text_color="black", border_color=ORANGE, border_width=1,
                      corner_radius=2, width=120, height=48, font=F(13, True)).pack(side="left", padx=8)
        solid_button(buttons, "Log out", app.logout, fg=AMBER_DARK, text_color="#ff0000", width=130,
                     height=48, font=F(14), corner_radius=2).pack(side="left", padx=(8, 0))


# ------------------------------------------------------------ form fields
class IconEntry(ctk.CTkFrame):
    """Rounded grey field with an orange border, optional left icon and optional show/hide eye."""

    def __init__(self, master, placeholder: str, icon=None, password=False, toggle=False,
                 width=306, height=42):
        super().__init__(master, width=width, height=height, fg_color=FIELD_BG, border_color=ORANGE,
                         border_width=1, corner_radius=10)
        self.grid_propagate(False)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._hidden = password
        if icon:
            size = {"icon_user": (18, 20), "icon_lock": (22, 21)}.get(icon, (20, 20))
            ctk.CTkLabel(self, text="", image=load_icon(icon, size), fg_color="transparent",
                         width=30).grid(row=0, column=0, padx=(10, 0))
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder, fg_color="transparent",
                                  border_width=0, text_color="#222222",
                                  placeholder_text_color=HINT_TEXT, font=F(13, True),
                                  height=height - 6, show="•" if password else "")
        self.entry.grid(row=0, column=1, sticky="ew", padx=(8 if icon else 12, 4))
        self.entry.bind("<FocusIn>", lambda _e: self._apply_show())   # runs after CTk drops its placeholder
        self._eye = None
        if toggle:
            self._eye = ctk.CTkButton(self, text="", image=load_icon("icon_eye", (20, 20)), width=30,
                                      height=28, fg_color="transparent", hover_color="#c9c9c9",
                                      corner_radius=6, command=lambda: self.set_hidden(not self._hidden))
            self._eye.grid(row=0, column=2, padx=(0, 8))

    def _apply_show(self):
        show = "•" if self._hidden else ""
        if getattr(self.entry, "_placeholder_text_active", False):
            self.entry._pre_placeholder_arguments = {"show": show}   # keep the placeholder readable
        else:
            self.entry.configure(show=show)

    def set_hidden(self, hidden: bool):
        self._hidden = hidden
        self._apply_show()
        if self._eye is not None:
            self._eye.configure(image=load_icon("icon_eye" if hidden else "icon_eye_off", (20, 20)))

    def get(self) -> str:
        return self.entry.get()

    def set(self, text: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, text)
        self._apply_show()      # CTk's placeholder handling can leave a password field unmasked

    def focus(self):
        self.entry.focus_set()

    def on_enter(self, callback):
        self.entry.bind("<Return>", lambda _e: callback())


class QuestionBox(ctk.CTkComboBox):
    """Read-only 'Select your Question' dropdown."""
    PLACEHOLDER = "Select your Question"

    def __init__(self, master, width=306, height=42):
        super().__init__(master, values=SECRET_QUESTIONS, state="readonly", width=width, height=height,
                         corner_radius=10, border_width=1, border_color=ORANGE, fg_color=FIELD_BG,
                         button_color=FIELD_BG, button_hover_color="#c4c4c4", dropdown_fg_color="white",
                         dropdown_text_color="black", dropdown_hover_color=SELECT_BG,
                         text_color=HINT_TEXT, font=F(13, True), dropdown_font=F(13),
                         command=lambda _v: self.configure(text_color="#222222"))
        self.set(self.PLACEHOLDER)

    def selected(self):
        value = self.get()
        return value if value in SECRET_QUESTIONS else None


def field_label(master, text, size=13):
    return ctk.CTkLabel(master, text=text, font=F(size), text_color="black", anchor="w")


# --------------------------------------------------------- page furniture
class ChipBar(ctk.CTkFrame):
    """Row of square filter buttons where one is highlighted (All / Coffee ..., Today / This Week ...)."""

    def __init__(self, master, options, command, selected, on_fg, on_text, off_fg, width=100):
        super().__init__(master, fg_color="transparent")
        self.selected, self._command = selected, command
        self._style = (on_fg, on_text, off_fg)
        self._buttons = {}
        for option in options:
            btn = ctk.CTkButton(self, text=option, width=width, height=40, corner_radius=0,
                                border_width=1, font=F(15), command=lambda o=option: self.select(o))
            btn.pack(side="left", padx=(0, 14))
            self._buttons[option] = btn
        self._paint()

    def _paint(self):
        on_fg, on_text, off_fg = self._style
        for option, btn in self._buttons.items():
            active = option == self.selected
            btn.configure(fg_color=on_fg if active else off_fg, hover_color=_darken(on_fg if active else off_fg, 0.94),
                          text_color=on_text if active else "black",
                          border_color=on_fg if active else ORANGE)

    def select(self, option):
        self.selected = option
        self._paint()
        self._command(option)


class StatCard(ctk.CTkFrame):
    """White box with a small grey label and a big bold value."""

    def __init__(self, master, label: str, value: str = "", height=94):
        super().__init__(master, fg_color="white", border_color="black", border_width=1,
                         corner_radius=0, height=height)
        self.pack_propagate(False)
        ctk.CTkLabel(self, text=label, font=F(13), text_color=GREY_TEXT, anchor="w").pack(
            anchor="w", padx=20, pady=(14, 0))
        self._value = ctk.CTkLabel(self, text=value, font=F(22, True), text_color="black", anchor="w")
        self._value.pack(anchor="w", padx=24, pady=(4, 0))

    def set(self, value: str):
        self._value.configure(text=value)


# ------------------------------------------------------------------ table
ROW_HEIGHT, PHOTO_ROW_HEIGHT = 42, 58


def init_styles(root) -> None:
    """Style ttk.Treeview like the design's tables (dark-brown heading, white rows)."""
    style = ttk.Style(root)
    style.theme_use("clam")
    scale = root.tk.call("tk", "scaling") / (96 / 72)       # pixels-per-point vs a 96-dpi screen
    family = font_family()
    for name, height in (("Brew", ROW_HEIGHT), ("BrewPhoto", PHOTO_ROW_HEIGHT)):
        tree_style = f"{name}.Treeview"
        style.configure(tree_style, background="white", fieldbackground="white", foreground="black",
                        rowheight=int(height * scale), font=(family, 11), borderwidth=0,
                        bordercolor="white", lightcolor="white", darkcolor="white")
        style.map(tree_style, background=[("selected", SELECT_BG)], foreground=[("selected", "black")])
        style.configure(f"{tree_style}.Heading", background=HEADER_BG, foreground="white",
                        font=(family, 11, "bold"), relief="flat", borderwidth=0, padding=(6, 12))
        style.map(f"{tree_style}.Heading", background=[("active", HEADER_BG)])
    style.layout("Brew.Treeview", style.layout("Treeview"))
    style.layout("BrewPhoto.Treeview", style.layout("Treeview"))


class DataTable(ctk.CTkFrame):
    """Treeview + scrollbar. columns = [(key, heading, width, anchor, stretch), ...]."""

    def __init__(self, master, columns, photo=False, on_select=None, on_double=None):
        super().__init__(master, fg_color="white", border_color="black", border_width=1, corner_radius=0)
        self._images = []
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns], selectmode="browse",
                                 show="tree headings" if photo else "headings",
                                 style="BrewPhoto.Treeview" if photo else "Brew.Treeview")
        for key, heading, width, anchor, stretch in columns:
            self.tree.heading(key, text=heading, anchor="center")
            self.tree.column(key, width=width, minwidth=50, anchor=anchor, stretch=stretch)
        if photo:
            self.tree.heading("#0", text="Photo", anchor="center")
            self.tree.column("#0", width=100, minwidth=100, stretch=False, anchor="center")
        self.tree.tag_configure("out", background=AMBER, foreground="#ff0000")
        scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.tree.yview,
                                     fg_color="white", button_color="#8a8a8a", button_hover_color="#6a6a6a")
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 1), pady=1)
        self.tree.pack(side="left", fill="both", expand=True, padx=1, pady=1)
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda _e: on_select())
        if on_double:
            self.tree.bind("<Double-1>", lambda _e: on_double())

    def fill(self, rows):
        """rows = [{'iid': str, 'values': tuple, 'tags': tuple, 'image': PhotoImage|None}, ...]"""
        self.tree.delete(*self.tree.get_children())
        self._images = []
        for row in rows:
            kwargs = {}
            if row.get("image") is not None:
                self._images.append(row["image"])
                kwargs["image"] = row["image"]
            self.tree.insert("", "end", iid=row["iid"], values=row["values"],
                             tags=row.get("tags", ()), **kwargs)

    def selected(self):
        selection = self.tree.selection()
        return selection[0] if selection else None
