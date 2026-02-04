# Baby Sleep Scheduler

A Python terminal app that predicts baby sleep schedules using pattern-based ML trained on historical data.

## Features

- **Pattern Learning**: Learns wake windows and nap durations from your baby's historical sleep data
- **Daily Predictions**: Predicts full day schedule from morning wake time
- **Real-time Corrections**: Update predictions as actual naps happen
- **History Tracking**: View and analyze past sleep patterns

## Installation

```bash
# Clone the repository
git clone https://github.com/primakov127/baby-sleep-scheduler.git
cd baby-sleep-scheduler

# Create virtual environment and install
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

## Usage

### Daily Workflow

1. **Train the model** (run periodically to incorporate new data):
   ```bash
   baby-sleep train
   ```

2. **Predict today's schedule** when baby wakes:
   ```bash
   baby-sleep predict 07:15
   ```

3. **Correct predictions** as naps happen:
   ```bash
   baby-sleep correct 1 09:30 10:45
   ```

4. **View current schedule**:
   ```bash
   baby-sleep show
   ```

### Commands

| Command | Description |
|---------|-------------|
| `baby-sleep train` | Train model on historical data |
| `baby-sleep predict <wake_time>` | Predict full day schedule (e.g., `07:15`) |
| `baby-sleep correct <nap> <start> [end]` | Update actual nap time |
| `baby-sleep show` | Show today's schedule |
| `baby-sleep history [days]` | Show recent history (default: 7 days) |
| `baby-sleep add <date>` | Add historical data interactively |
| `baby-sleep sync` | Sync today's schedule to Google Calendar |
| `baby-sleep sync -c <name>` | Sync to a specific calendar by name |
| `baby-sleep sync --setup` | Show Google Calendar setup instructions |

### Example Output

```
$ baby-sleep predict 07:00

        Predicted Schedule for Today
┏━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Event ┃ Start ┃  End  ┃ Duration ┃  Status   ┃
┡━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
│ Wake  │ 07:00 │   -   │    -     │  Actual   │
│ Nap 1 │ 09:30 │ 10:45 │  1h 15m  │ Predicted │
│ Nap 2 │ 13:30 │ 15:00 │  1h 30m  │ Predicted │
│ Nap 3 │ 17:45 │ 18:15 │   30m    │ Predicted │
│ Night │ 20:36 │   -   │    -     │ Predicted │
└───────┴───────┴───────┴──────────┴───────────┘
```

## How It Works

The model learns patterns from historical data:

- **Wake Windows**: Average time awake before each nap
- **Nap Durations**: Average duration of each nap
- **Night Sleep Window**: Average time from last nap to bedtime

When you correct a nap with actual times, remaining predictions are recalculated based on the learned patterns.

## Data Storage

- `data/sleep_data.json` - Historical sleep records
- `models/model.json` - Trained model parameters

## Google Calendar Integration

Sync your baby's sleep schedule to Google Calendar for easy sharing and visibility.

### Setup

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project (or select existing)

2. **Enable Calendar API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

3. **Create OAuth Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" as application type
   - Download the JSON file

4. **Configure the App**:
   ```bash
   # View setup instructions
   baby-sleep sync --setup

   # Save credentials to the config directory
   mv ~/Downloads/client_secret_*.json ~/.baby-sleep/credentials.json

   # Run sync to authenticate (opens browser)
   baby-sleep sync
   ```

### Usage

```bash
# Sync today's schedule to primary calendar
baby-sleep sync

# Sync to a specific calendar by name
baby-sleep sync -c "Family Calendar"

# Sync to a calendar by ID (from Google Calendar settings)
baby-sleep sync -c "abc123@group.calendar.google.com"
```

To find your calendar name or ID, open Google Calendar → Settings → click on the calendar → scroll to "Integrate calendar" for the Calendar ID.

### What Gets Synced

- **Naps**: Yellow events showing nap start/end times
- **Night Sleep**: Blue event from bedtime to predicted wake time

Events are updated in place when you make corrections, so your calendar always reflects the current schedule.

### Daily Workflow with Calendar

```bash
baby-sleep predict 06:30    # Predict schedule
baby-sleep sync             # Push to calendar

baby-sleep correct 1 09:15 10:00  # Correct nap 1
baby-sleep sync                    # Update calendar

baby-sleep correct night 19:00    # Correct bedtime
baby-sleep sync                    # Update calendar
```

## Requirements

- Python 3.10+
- click
- rich
- numpy
- google-api-python-client
- google-auth-httplib2
- google-auth-oauthlib
