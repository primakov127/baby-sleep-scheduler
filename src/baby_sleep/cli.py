"""CLI commands for baby sleep scheduler."""

import click
from datetime import date

from . import data, model, display


@click.group()
@click.version_option()
def cli():
    """Baby Sleep Scheduler - Predict and track baby sleep patterns."""
    pass


@cli.command()
def train():
    """Train the model on historical sleep data."""
    sleep_data = data.load_data()
    historical = data.get_historical_days(sleep_data)

    if not historical:
        display.warning("No historical data found. Using default patterns.")

    trained_model = model.train(sleep_data)
    display.success(f"Model trained on {trained_model['days_count']} days of data.")
    display.show_model_info(trained_model)


@cli.command()
@click.argument("wake_time")
def predict(wake_time: str):
    """Predict today's sleep schedule from morning wake time.

    WAKE_TIME should be in HH:MM format (e.g., 07:15)
    """
    if not data.validate_time(wake_time):
        display.error("Invalid time format. Use HH:MM (e.g., 07:15)")
        return

    trained_model = model.load_model()
    if not trained_model.get("trained_on"):
        display.warning("No trained model found. Using default patterns.")
        display.info("Run 'baby-sleep train' after adding historical data for better predictions.")

    schedule = model.predict(wake_time, trained_model)

    sleep_data = data.load_data()
    today = data.get_today(sleep_data)
    today["morning_wake"] = wake_time
    today["predictions"] = schedule
    data.save_data(sleep_data)

    display.show_schedule(schedule)


@cli.command()
@click.argument("target")
@click.argument("start")
@click.argument("end", required=False)
def correct(target: str, start: str, end: str | None):
    """Correct actual nap or night sleep time.

    TARGET is either a nap number (1, 2, 3) or 'night'
    START is the actual start time (HH:MM)
    END is the optional actual end time (HH:MM) - only for naps

    Examples:
      baby-sleep correct 1 09:30 10:45    # Correct nap 1
      baby-sleep correct night 19:30      # Correct night sleep
    """
    if not data.validate_time(start):
        display.error("Invalid time format. Use HH:MM (e.g., 09:30)")
        return

    sleep_data = data.load_data()
    today = data.get_today(sleep_data)

    if not today.get("morning_wake"):
        display.error("No prediction for today. Run 'baby-sleep predict <wake_time>' first.")
        return

    # Handle night sleep correction
    if target.lower() == "night":
        today["night_sleep"] = start
        if today.get("predictions"):
            today["predictions"]["night_sleep"] = start
            today["predictions"]["night_predicted"] = False
        data.save_data(sleep_data)
        display.success(f"Night sleep updated: {start}")
        if today.get("predictions"):
            display.show_schedule(today["predictions"], "Updated Schedule")
        return

    # Handle nap correction
    try:
        nap_number = int(target)
    except ValueError:
        display.error("TARGET must be a nap number (1, 2, 3) or 'night'")
        return

    if end and not data.validate_time(end):
        display.error("Invalid end time format. Use HH:MM (e.g., 10:45)")
        return

    trained_model = model.load_model()
    if nap_number < 1 or nap_number > trained_model["typical_naps_count"]:
        display.error(f"Invalid nap number. Expected 1-{trained_model['typical_naps_count']}")
        return

    corrections = []
    for i, nap in enumerate(today.get("naps", []), 1):
        if not nap.get("predicted", True):
            corrections.append({
                "nap_number": i,
                "start": nap["start"],
                "end": nap.get("end")
            })

    new_correction = {"nap_number": nap_number, "start": start}
    if end:
        new_correction["end"] = end

    existing = next((c for c in corrections if c["nap_number"] == nap_number), None)
    if existing:
        corrections.remove(existing)
    corrections.append(new_correction)

    schedule = model.recalculate(today["morning_wake"], corrections, trained_model)

    # Preserve night sleep correction if it was already set
    if today.get("predictions") and not today["predictions"].get("night_predicted", True):
        schedule["night_sleep"] = today["predictions"]["night_sleep"]
        schedule["night_predicted"] = False

    today["predictions"] = schedule
    today["naps"] = schedule["naps"]
    data.save_data(sleep_data)

    if end:
        display.success(f"Nap {nap_number} updated: {start}-{end}")
    else:
        display.success(f"Nap {nap_number} started: {start}")

    display.show_schedule(schedule, "Updated Schedule")


@cli.command()
@click.argument("date_str", metavar="DATE")
def add(date_str: str):
    """Add historical day data interactively.

    DATE should be in YYYY-MM-DD format (e.g., 2025-01-15)
    """
    if not data.validate_date(date_str):
        display.error("Invalid date format. Use YYYY-MM-DD (e.g., 2025-01-15)")
        return

    display.info(f"Adding sleep data for {date_str}")

    morning_wake = click.prompt("Morning wake time (HH:MM)", type=str)
    if not data.validate_time(morning_wake):
        display.error("Invalid time format")
        return

    naps = []
    nap_num = 1
    while True:
        add_nap = click.confirm(f"Add nap {nap_num}?", default=nap_num <= 3)
        if not add_nap:
            break

        nap_start = click.prompt(f"  Nap {nap_num} start (HH:MM)", type=str)
        if not data.validate_time(nap_start):
            display.error("Invalid time format")
            return

        nap_end = click.prompt(f"  Nap {nap_num} end (HH:MM)", type=str)
        if not data.validate_time(nap_end):
            display.error("Invalid time format")
            return

        naps.append({"start": nap_start, "end": nap_end, "predicted": False})
        nap_num += 1

    night_sleep = click.prompt("Night sleep time (HH:MM)", type=str)
    if not data.validate_time(night_sleep):
        display.error("Invalid time format")
        return

    sleep_data = data.load_data()
    data.add_day(sleep_data, date_str, morning_wake, naps, night_sleep)
    data.save_data(sleep_data)

    display.success(f"Added sleep data for {date_str}")


@cli.command()
def show():
    """Show today's current predictions and corrections."""
    sleep_data = data.load_data()
    today = data.get_today(sleep_data)

    if not today.get("morning_wake"):
        display.warning("No prediction for today.")
        display.info("Run 'baby-sleep predict <wake_time>' to get started.")
        return

    if today.get("predictions"):
        display.show_schedule(today["predictions"], f"Schedule for {today['date']}")
    else:
        display.warning("No predictions available.")


@cli.command()
@click.argument("days", default=7, type=int)
def history(days: int):
    """Show recent sleep history.

    DAYS is the number of days to show (default: 7)
    """
    sleep_data = data.load_data()
    historical = data.get_historical_days(sleep_data, exclude_today=False)

    if not historical:
        display.warning("No historical data found.")
        display.info("Use 'baby-sleep add <date>' to add historical data.")
        return

    display.show_history(historical, limit=days)


if __name__ == "__main__":
    cli()
