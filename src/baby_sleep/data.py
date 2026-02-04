"""Data loading and saving for baby sleep records."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_FILE = DATA_DIR / "sleep_data.json"


def get_default_data() -> dict[str, Any]:
    """Return default data structure."""
    return {
        "baby_info": {
            "name": "Baby",
            "birth_date": None
        },
        "days": []
    }


def load_data() -> dict[str, Any]:
    """Load sleep data from JSON file."""
    if not DATA_FILE.exists():
        return get_default_data()

    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data: dict[str, Any]) -> None:
    """Save sleep data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def validate_time(time_str: str) -> bool:
    """Validate time string in HH:MM format."""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def validate_date(date_str: str) -> bool:
    """Validate date string in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_time(time_str: str) -> datetime:
    """Parse time string to datetime object (today's date)."""
    return datetime.strptime(time_str, "%H:%M").replace(
        year=date.today().year,
        month=date.today().month,
        day=date.today().day
    )


def format_time(dt: datetime) -> str:
    """Format datetime to HH:MM string."""
    return dt.strftime("%H:%M")


def get_day(data: dict[str, Any], date_str: str) -> dict[str, Any] | None:
    """Get day record by date string."""
    for day in data["days"]:
        if day["date"] == date_str:
            return day
    return None


def get_today(data: dict[str, Any]) -> dict[str, Any]:
    """Get or create today's record."""
    today_str = date.today().isoformat()
    day = get_day(data, today_str)

    if day is None:
        day = {
            "date": today_str,
            "morning_wake": None,
            "naps": [],
            "night_sleep": None,
            "feeds": [],
            "predictions": None,
            "calendar_event_ids": {}
        }
        data["days"].append(day)

    # Ensure calendar_event_ids exists for older records
    if "calendar_event_ids" not in day:
        day["calendar_event_ids"] = {}

    return day


def add_day(
    data: dict[str, Any],
    date_str: str,
    morning_wake: str,
    naps: list[dict[str, str]],
    night_sleep: str,
    feeds: list[str] | None = None
) -> dict[str, Any]:
    """Add or update a day record."""
    existing = get_day(data, date_str)

    day = {
        "date": date_str,
        "morning_wake": morning_wake,
        "naps": naps,
        "night_sleep": night_sleep,
        "feeds": feeds or [],
        "calendar_event_ids": existing.get("calendar_event_ids", {}) if existing else {}
    }

    if existing:
        data["days"].remove(existing)

    data["days"].append(day)
    data["days"].sort(key=lambda d: d["date"])

    return day


def get_yesterday(data: dict[str, Any]) -> dict[str, Any] | None:
    """Get yesterday's record if it exists."""
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()
    day = get_day(data, yesterday_str)

    # Ensure calendar_event_ids exists for older records
    if day and "calendar_event_ids" not in day:
        day["calendar_event_ids"] = {}

    return day


def get_historical_days(data: dict[str, Any], exclude_today: bool = True) -> list[dict[str, Any]]:
    """Get completed historical days for training."""
    today_str = date.today().isoformat()
    days = []

    for day in data["days"]:
        if exclude_today and day["date"] == today_str:
            continue
        if day.get("morning_wake") and day.get("naps") and day.get("night_sleep"):
            days.append(day)

    return days
