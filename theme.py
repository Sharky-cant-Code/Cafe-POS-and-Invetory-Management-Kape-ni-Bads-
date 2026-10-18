"""Colors (sampled from the Figma frames), fonts and shop details."""
import tkinter.font as tkfont

import customtkinter as ctk

SHOP_NAME = "Kapehan ni Bads"
SHOP_TAGLINE = "Coffee, Pastries, and Sweets"
GCASH_NUMBER = "0912 345 6789"          # shown under the QR code on the Gcash screen

HEADER_BG = "#401b01"      # dark-brown top bar, table headings
PAGE_BG = "#e3dccf"        # beige page background
CARD_BG = "#ededed"        # login / sign-up card
FIELD_BG = "#d9d9d9"       # text fields
TILE_BG = "#f1eee7"        # product cards, photo placeholders
ORANGE = "#ff7b1c"         # primary buttons + field borders on the auth screens
AMBER = "#da8b3c"          # POS / table action buttons
AMBER_DARK = "#ca7827"     # Log out button
DANGER = "#fc1615"         # Delete button, out-of-stock text
GREY_TEXT = "#6b6b6b"
HINT_TEXT = "#9a9a9a"
SELECT_BG = "#f3d6b0"

_FAMILY = None
_FONTS = {}


def font_family() -> str:
    """Inter (the design's font) if installed, otherwise a clean system fallback."""
    global _FAMILY
    if _FAMILY is None:
        installed = set(tkfont.families())
        for name in ("Inter", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"):
            if name in installed:
                _FAMILY = name
                break
        else:
            _FAMILY = "TkDefaultFont"
    return _FAMILY


def F(size: int = 14, bold: bool = False) -> ctk.CTkFont:
    """Cached CTkFont (call only after the root window exists)."""
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = ctk.CTkFont(family=font_family(), size=size, weight="bold" if bold else "normal")
    return _FONTS[key]


def mono(size: int = 12) -> ctk.CTkFont:
    """Fixed-width font (used for the order breakdown so amounts line up)."""
    key = ("mono", size)
    if key not in _FONTS:
        installed = set(tkfont.families())
        family = next((n for n in ("Consolas", "Menlo", "DejaVu Sans Mono", "Courier New") if n in installed),
                      "TkFixedFont")
        _FONTS[key] = ctk.CTkFont(family=family, size=size)
    return _FONTS[key]
