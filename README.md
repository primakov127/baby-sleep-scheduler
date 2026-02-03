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

## Requirements

- Python 3.10+
- click
- rich
- numpy
