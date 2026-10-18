"""Small helpers: money, validation, dates, settings, CSV safety."""
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"

LOW_STOCK_LIMIT = 10          # stock at or below this (but > 0) shows "Low Stock"
CATEGORIES = ["Coffee", "Pastry", "Tea", "Bread"]
SECRET_QUESTIONS = [
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "In what city were you born?",
    "What was the name of your first school?",
    "What is your favorite food?",
]


# ---------------------------------------------------------------- money
def peso(cents: int) -> str:
    """12050 -> 'PHP 120.50' (prices are stored as whole centavos)."""
    cents = int(cents)
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}PHP {cents // 100:,}.{cents % 100:02d}"


def parse_price(text: str) -> int:
    """'120' or '120.5' -> centavos. Raises ValueError on bad input."""
    text = text.strip().replace(",", "")
    if text.upper().startswith("PHP"):
        text = text[3:].strip()
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError("Price must be a number, e.g. 120 or 120.50.")
    if not value.is_finite() or value < 0 or value > Decimal("1000000"):
        raise ValueError("Price must be between 0 and 1,000,000.")
    if value != value.quantize(Decimal("0.01")):
        raise ValueError("Price can have at most 2 decimal places.")
    return int(value * 100)


def parse_whole_number(text: str, label: str, minimum: int = 0) -> int:
    try:
        value = int(text.strip())
    except ValueError:
        raise ValueError(f"{label} must be a whole number.")
    if value < minimum or value > 1_000_000:
        raise ValueError(f"{label} must be at least {minimum}.")
    return value


# ----------------------------------------------------------- validation
def validate_username(username: str) -> str:
    username = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.]{3,20}", username):
        raise ValueError("Username must be 3-20 characters: letters, numbers, _ or .")
    return username


def validate_password(password: str) -> str:
    if (len(password) < 8
            or not re.search(r"[A-Za-z]", password)
            or not re.search(r"\d", password)
            or not re.search(r"[^A-Za-z0-9]", password)):
        raise ValueError("Password needs at least 8 characters with letters, numbers, and symbols.")
    return password


# ---------------------------------------------------------------- dates
DB_TIME = "%Y-%m-%d %H:%M:%S"


def now_str() -> str:
    return datetime.now().strftime(DB_TIME)


def pretty_time(db_value: str) -> str:
    try:
        return datetime.strptime(db_value, DB_TIME).strftime("%b %d, %Y  %I:%M %p")
    except (TypeError, ValueError):
        return str(db_value)


def range_start(label: str):
    """Start of 'Today' / 'This Week' (Mon) / 'This Month' as a DB timestamp; None = all time."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if label == "Today":
        start = today
    elif label == "This Week":
        start = today - timedelta(days=today.weekday())
    elif label == "This Month":
        start = today.replace(day=1)
    else:
        return None
    return start.strftime(DB_TIME)


# ------------------------------------------------------------------ csv
def csv_safe(value) -> str:
    """Stop spreadsheet apps from running a cell that starts like a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


# ------------------------------------------------------------- settings
def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass  # remembering the username is a convenience, never fatal
