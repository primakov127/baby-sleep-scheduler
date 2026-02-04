"""Google Calendar integration for baby sleep scheduler."""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth scopes for Calendar API
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Config directory for credentials
CONFIG_DIR = Path.home() / ".baby-sleep"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"

# Google Calendar event colors (colorId)
# 5 = Yellow (Banana), 9 = Blue (Blueberry)
COLOR_NAP = "5"
COLOR_NIGHT = "9"


def get_config_dir() -> Path:
    """Get or create the config directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def credentials_exist() -> bool:
    """Check if credentials.json exists."""
    return CREDENTIALS_FILE.exists()


def get_credentials() -> Credentials | None:
    """Get valid OAuth credentials, refreshing or initiating flow as needed."""
    creds = None

    # Load existing token if available
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # If no valid credentials, refresh or start OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                return None

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        get_config_dir()
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def get_calendar_service():
    """Build and return Google Calendar API service."""
    creds = get_credentials()
    if not creds:
        return None
    return build("calendar", "v3", credentials=creds)


def setup_credentials_interactive() -> bool:
    """Guide user through credential setup. Returns True if setup successful."""
    from . import display

    display.info("Google Calendar Setup")
    display.info("=" * 40)
    print()
    print("To sync sleep events to Google Calendar, you need to create")
    print("OAuth credentials in Google Cloud Console.")
    print()
    print("Steps:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a new project (or select existing)")
    print("3. Enable the Google Calendar API:")
    print("   - Go to 'APIs & Services' > 'Library'")
    print("   - Search for 'Google Calendar API'")
    print("   - Click 'Enable'")
    print("4. Create OAuth credentials:")
    print("   - Go to 'APIs & Services' > 'Credentials'")
    print("   - Click 'Create Credentials' > 'OAuth client ID'")
    print("   - Choose 'Desktop app' as application type")
    print("   - Download the JSON file")
    print(f"5. Save the file as: {CREDENTIALS_FILE}")
    print()

    if credentials_exist():
        display.success(f"Credentials found at {CREDENTIALS_FILE}")
        print()
        print("Run 'baby-sleep sync' to authenticate and sync events.")
        return True
    else:
        display.warning(f"Credentials not found at {CREDENTIALS_FILE}")
        print()
        print("After downloading credentials.json, save it to the path above")
        print("and run 'baby-sleep sync' to authenticate.")
        return False


def create_event(
    service,
    calendar_id: str,
    title: str,
    start_datetime: datetime,
    end_datetime: datetime,
    color_id: str,
    description: str = "",
    timezone: str | None = None
) -> str | None:
    """Create a calendar event. Returns event ID."""
    if timezone is None:
        timezone = _get_local_timezone()

    event = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": timezone,
        },
        "colorId": color_id,
    }

    try:
        result = service.events().insert(calendarId=calendar_id, body=event).execute()
        return result.get("id")
    except HttpError:
        return None


def update_event(
    service,
    calendar_id: str,
    event_id: str,
    title: str,
    start_datetime: datetime,
    end_datetime: datetime,
    color_id: str,
    description: str = "",
    timezone: str | None = None
) -> bool:
    """Update an existing calendar event. Returns True on success."""
    if timezone is None:
        timezone = _get_local_timezone()

    event = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_datetime.isoformat(),
            "timeZone": timezone,
        },
        "end": {
            "dateTime": end_datetime.isoformat(),
            "timeZone": timezone,
        },
        "colorId": color_id,
    }

    try:
        service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status == 404:
            return False
        raise


def delete_event(service, calendar_id: str, event_id: str) -> bool:
    """Delete a calendar event. Returns True on success."""
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except HttpError:
        return False


def _get_local_timezone() -> str:
    """Get local timezone string (IANA format like 'America/New_York')."""
    import os
    import subprocess

    # Try TZ environment variable first
    tz = os.environ.get("TZ")
    if tz and not tz.startswith(":"):
        return tz
    if tz and tz.startswith(":"):
        return tz[1:]

    # macOS: read /etc/localtime symlink
    try:
        result = subprocess.run(
            ["readlink", "/etc/localtime"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            if "zoneinfo/" in path:
                return path.split("zoneinfo/")[-1]
    except Exception:
        pass

    # Linux: read /etc/timezone
    try:
        with open("/etc/timezone", "r") as f:
            return f.read().strip()
    except Exception:
        pass

    return "UTC"


def _parse_time_for_date(time_str: str, target_date: date) -> datetime:
    """Parse HH:MM time string to datetime for a specific date."""
    time_obj = datetime.strptime(time_str, "%H:%M")
    return datetime(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=time_obj.hour,
        minute=time_obj.minute
    )


def sync_day_to_calendar(
    service,
    calendar_id: str,
    day_data: dict[str, Any],
    model: dict[str, Any],
    existing_event_ids: dict[str, str] | None = None
) -> dict[str, str]:
    """
    Sync a day's sleep events to Google Calendar.

    Args:
        service: Google Calendar API service
        calendar_id: Target calendar ID (use 'primary' for default)
        day_data: Day record with naps, night_sleep, predictions
        model: Trained model with night_sleep_duration
        existing_event_ids: Dict mapping event keys to Google event IDs

    Returns:
        Dict mapping event keys (nap_1, nap_2, nap_3, night) to Google event IDs
    """
    if existing_event_ids is None:
        existing_event_ids = {}

    event_ids = {}
    target_date = date.fromisoformat(day_data["date"])

    # Get schedule data (use predictions if available, else use raw data)
    schedule = day_data.get("predictions") or {}
    naps = schedule.get("naps") or day_data.get("naps", [])

    # Sync naps
    for i, nap in enumerate(naps, 1):
        event_key = f"nap_{i}"
        nap_start = _parse_time_for_date(nap["start"], target_date)
        nap_end = _parse_time_for_date(nap["end"], target_date)

        is_predicted = nap.get("predicted", True)
        status = "Predicted" if is_predicted else "Actual"
        duration_mins = nap.get("duration_minutes", 0)
        description = f"Duration: {duration_mins} minutes\nStatus: {status}"

        title = f"Baby Nap {i}"

        existing_id = existing_event_ids.get(event_key)
        if existing_id:
            # Try to update existing event
            success = update_event(
                service, calendar_id, existing_id,
                title, nap_start, nap_end, COLOR_NAP, description
            )
            if success:
                event_ids[event_key] = existing_id
            else:
                # Event was deleted, create new one
                new_id = create_event(
                    service, calendar_id,
                    title, nap_start, nap_end, COLOR_NAP, description
                )
                if new_id:
                    event_ids[event_key] = new_id
        else:
            # Create new event
            new_id = create_event(
                service, calendar_id,
                title, nap_start, nap_end, COLOR_NAP, description
            )
            if new_id:
                event_ids[event_key] = new_id

    # Sync night sleep
    night_sleep_time = schedule.get("night_sleep") or day_data.get("night_sleep")
    if night_sleep_time:
        night_start = _parse_time_for_date(night_sleep_time, target_date)

        # Calculate wake time using model's night_sleep_duration
        night_duration = model.get("night_sleep_duration", 660)
        wake_time = night_start + timedelta(minutes=night_duration)

        is_predicted = schedule.get("night_predicted", True)
        status = "Predicted" if is_predicted else "Actual"
        description = f"Duration: {night_duration // 60}h {night_duration % 60}m\nStatus: {status}"
        description += f"\nPredicted wake: {wake_time.strftime('%H:%M')}"

        title = "Baby Night Sleep"
        event_key = "night"

        existing_id = existing_event_ids.get(event_key)
        if existing_id:
            success = update_event(
                service, calendar_id, existing_id,
                title, night_start, wake_time, COLOR_NIGHT, description
            )
            if success:
                event_ids[event_key] = existing_id
            else:
                new_id = create_event(
                    service, calendar_id,
                    title, night_start, wake_time, COLOR_NIGHT, description
                )
                if new_id:
                    event_ids[event_key] = new_id
        else:
            new_id = create_event(
                service, calendar_id,
                title, night_start, wake_time, COLOR_NIGHT, description
            )
            if new_id:
                event_ids[event_key] = new_id

    return event_ids


def list_calendars(service) -> list[dict[str, str]]:
    """List available calendars. Returns list of {id, name} dicts."""
    try:
        result = service.calendarList().list().execute()
        calendars = []
        for cal in result.get("items", []):
            calendars.append({
                "id": cal["id"],
                "name": cal.get("summary", cal["id"])
            })
        return calendars
    except HttpError:
        return []
