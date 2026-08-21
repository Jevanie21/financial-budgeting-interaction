# Financial Budgeting Interaction (Local-First)

A fully local AI-style money-management agent that remembers your financial profile between sessions, compares updates, and generates deterministic budget plans.

## Features

- **Local-first by default**: no cloud required.
- **Persistent memory** using SQLite:
  - user profile
  - recurring bills
  - savings goals
  - session history
  - budget snapshots
  - interaction logs
  - detected changes between sessions
- **Deterministic budgeting engine** for reliable category allocation:
  - bills / reserves
  - groceries
  - pocket money / discretionary spending
  - savings contribution by target date
  - emergency buffer
- **Session continuity**:
  - first run collects baseline values
  - later runs load memory and ask for updates/confirmation
- **Optional local LLM integration** (Ollama) for friendly explanations.
- **Easy local UI** with a relaxed, lightweight web interface.

## Project Structure

- `/budget_agent/storage.py` - SQLite persistence + schema initialization
- `/budget_agent/budgeting.py` - deterministic budgeting logic
- `/budget_agent/change_detection.py` - memory diff detection
- `/budget_agent/session_manager.py` - onboarding/update flow + logging
- `/budget_agent/web_ui.py` - simple local web interface
- `/main.py` - app entry point (CLI or web)
- `/budget_agent/schema.sql` - DB schema

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### CLI mode (default)

```bash
python main.py --mode cli --db data/budget_agent.db
```

Optional local LLM explanation (requires Ollama running locally):

```bash
python main.py --mode cli --use-ollama
```

### Web UI mode

```bash
python main.py --mode web --db data/budget_agent.db --host 127.0.0.1 --port 5050
```

Open `http://127.0.0.1:5050`.

## Recurring Bills / Goals JSON format (Web UI)

Recurring bills example:

```json
[
  {"name": "Rent", "amount": 1200, "due_day": 1, "deadline_day": 5},
  {"name": "Phone", "amount": 65, "due_day": 10, "deadline_day": 12}
]
```

Savings goals example:

```json
[
  {"name": "Emergency Fund", "target_amount": 5000, "target_date": "2027-12-31"},
  {"name": "Vacation", "target_amount": 1800, "target_date": "2027-06-01"}
]
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Notes

- All data remains on your device inside the SQLite DB file you choose via `--db`.
- A sample defaults file is provided at `config.sample.json`.
