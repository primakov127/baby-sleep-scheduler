"""Pattern-based sleep prediction model."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from .data import get_historical_days, parse_time, format_time

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_FILE = MODEL_DIR / "model.json"


def get_default_model() -> dict[str, Any]:
    """Return default model with typical baby patterns."""
    return {
        "wake_windows": [150, 165, 180],
        "nap_durations": [75, 90, 45],
        "typical_naps_count": 3,
        "night_sleep_window": 120,
        "night_sleep_duration": 660,  # 11 hours default
        "trained_on": None,
        "days_count": 0
    }


def load_model() -> dict[str, Any]:
    """Load trained model from JSON file."""
    if not MODEL_FILE.exists():
        return get_default_model()

    with open(MODEL_FILE, "r") as f:
        return json.load(f)


def save_model(model: dict[str, Any]) -> None:
    """Save model to JSON file."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_FILE, "w") as f:
        json.dump(model, f, indent=2)


def time_diff_minutes(start: str, end: str) -> int:
    """Calculate minutes between two time strings."""
    t1 = datetime.strptime(start, "%H:%M")
    t2 = datetime.strptime(end, "%H:%M")
    diff = (t2 - t1).total_seconds() / 60
    return int(diff)


def train(data: dict[str, Any]) -> dict[str, Any]:
    """Train model on historical data."""
    days = get_historical_days(data)

    if not days:
        model = get_default_model()
        model["trained_on"] = date.today().isoformat()
        save_model(model)
        return model

    wake_windows_by_nap: dict[int, list[int]] = {}
    nap_durations_by_nap: dict[int, list[int]] = {}
    night_windows: list[int] = []
    night_durations: list[int] = []
    nap_counts: list[int] = []

    # Sort days by date for consecutive day analysis
    sorted_days = sorted(days, key=lambda d: d["date"])

    for day in sorted_days:
        naps = day["naps"]
        if not naps:
            continue

        nap_counts.append(len(naps))
        prev_wake = day["morning_wake"]

        for i, nap in enumerate(naps):
            wake_window = time_diff_minutes(prev_wake, nap["start"])
            if i not in wake_windows_by_nap:
                wake_windows_by_nap[i] = []
            wake_windows_by_nap[i].append(wake_window)

            duration = time_diff_minutes(nap["start"], nap["end"])
            if i not in nap_durations_by_nap:
                nap_durations_by_nap[i] = []
            nap_durations_by_nap[i].append(duration)

            prev_wake = nap["end"]

        if day.get("night_sleep"):
            last_nap_end = naps[-1]["end"]
            night_window = time_diff_minutes(last_nap_end, day["night_sleep"])
            night_windows.append(night_window)

    # Calculate night sleep duration from consecutive days
    days_by_date = {d["date"]: d for d in sorted_days}
    for day in sorted_days:
        if not day.get("night_sleep"):
            continue

        # Find next day
        current_date = date.fromisoformat(day["date"])
        next_date = (current_date + timedelta(days=1)).isoformat()

        if next_date in days_by_date:
            next_day = days_by_date[next_date]
            if next_day.get("morning_wake"):
                # Calculate duration from night_sleep to next morning_wake
                # Night sleep is in the evening, wake is next morning
                night_time = datetime.strptime(day["night_sleep"], "%H:%M")
                wake_time = datetime.strptime(next_day["morning_wake"], "%H:%M")

                # Add 24 hours to wake time since it's the next day
                duration = (24 * 60 - night_time.hour * 60 - night_time.minute) + \
                           (wake_time.hour * 60 + wake_time.minute)
                night_durations.append(duration)

    typical_naps = int(np.median(nap_counts)) if nap_counts else 3
    wake_windows = []
    nap_durations = []

    for i in range(typical_naps):
        if i in wake_windows_by_nap and wake_windows_by_nap[i]:
            wake_windows.append(int(np.mean(wake_windows_by_nap[i])))
        else:
            wake_windows.append(150 + i * 15)

        if i in nap_durations_by_nap and nap_durations_by_nap[i]:
            nap_durations.append(int(np.mean(nap_durations_by_nap[i])))
        else:
            nap_durations.append(75 if i == 0 else 90 if i == 1 else 45)

    night_sleep_window = int(np.mean(night_windows)) if night_windows else 120
    night_sleep_duration = int(np.mean(night_durations)) if night_durations else 660

    model = {
        "wake_windows": wake_windows,
        "nap_durations": nap_durations,
        "typical_naps_count": typical_naps,
        "night_sleep_window": night_sleep_window,
        "night_sleep_duration": night_sleep_duration,
        "trained_on": date.today().isoformat(),
        "days_count": len(days)
    }

    save_model(model)
    return model


def predict(wake_time: str, model: dict[str, Any] | None = None) -> dict[str, Any]:
    """Predict full day schedule from morning wake time."""
    if model is None:
        model = load_model()

    schedule = {
        "wake_time": wake_time,
        "naps": [],
        "night_sleep": None,
        "night_predicted": True
    }

    current_time = parse_time(wake_time)

    for i in range(model["typical_naps_count"]):
        wake_window = model["wake_windows"][i] if i < len(model["wake_windows"]) else 180
        nap_duration = model["nap_durations"][i] if i < len(model["nap_durations"]) else 60

        nap_start = current_time + timedelta(minutes=wake_window)
        nap_end = nap_start + timedelta(minutes=nap_duration)

        schedule["naps"].append({
            "start": format_time(nap_start),
            "end": format_time(nap_end),
            "duration_minutes": nap_duration,
            "predicted": True
        })

        current_time = nap_end

    night_time = current_time + timedelta(minutes=model["night_sleep_window"])
    schedule["night_sleep"] = format_time(night_time)

    return schedule


def predict_wake_time(night_sleep: str, model: dict[str, Any] | None = None) -> str:
    """Predict morning wake time based on night sleep start and learned duration."""
    if model is None:
        model = load_model()

    night_time = parse_time(night_sleep)
    duration = model.get("night_sleep_duration", 660)
    wake_time = night_time + timedelta(minutes=duration)

    return format_time(wake_time)


def recalculate(
    wake_time: str,
    corrections: list[dict[str, Any]],
    model: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Recalculate predictions after corrections."""
    if model is None:
        model = load_model()

    schedule = {
        "wake_time": wake_time,
        "naps": [],
        "night_sleep": None,
        "night_predicted": True
    }

    corrections_by_index = {c["nap_number"] - 1: c for c in corrections}
    current_time = parse_time(wake_time)

    for i in range(model["typical_naps_count"]):
        if i in corrections_by_index:
            corr = corrections_by_index[i]
            nap_start = corr["start"]
            nap_end = corr.get("end")

            if nap_end:
                duration = time_diff_minutes(nap_start, nap_end)
                schedule["naps"].append({
                    "start": nap_start,
                    "end": nap_end,
                    "duration_minutes": duration,
                    "predicted": False
                })
                current_time = parse_time(nap_end)
            else:
                nap_duration = model["nap_durations"][i] if i < len(model["nap_durations"]) else 60
                nap_end_dt = parse_time(nap_start) + timedelta(minutes=nap_duration)
                schedule["naps"].append({
                    "start": nap_start,
                    "end": format_time(nap_end_dt),
                    "duration_minutes": nap_duration,
                    "predicted": True
                })
                current_time = nap_end_dt
        else:
            wake_window = model["wake_windows"][i] if i < len(model["wake_windows"]) else 180
            nap_duration = model["nap_durations"][i] if i < len(model["nap_durations"]) else 60

            nap_start = current_time + timedelta(minutes=wake_window)
            nap_end = nap_start + timedelta(minutes=nap_duration)

            schedule["naps"].append({
                "start": format_time(nap_start),
                "end": format_time(nap_end),
                "duration_minutes": nap_duration,
                "predicted": True
            })

            current_time = nap_end

    night_time = current_time + timedelta(minutes=model["night_sleep_window"])
    schedule["night_sleep"] = format_time(night_time)

    return schedule
