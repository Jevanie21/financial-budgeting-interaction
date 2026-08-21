CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    income REAL NOT NULL,
    pay_schedule TEXT NOT NULL,
    groceries_budget REAL NOT NULL,
    pocket_money REAL NOT NULL,
    car_payment_amount REAL NOT NULL,
    car_payment_due_day INTEGER NOT NULL,
    car_payment_deadline_day INTEGER,
    grace_period_days INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recurring_bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    due_day INTEGER NOT NULL,
    deadline_day INTEGER,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS savings_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target_amount REAL NOT NULL,
    target_date TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    period_label TEXT NOT NULL,
    detected_changes_json TEXT NOT NULL,
    budget_plan_json TEXT NOT NULL,
    summary_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interaction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS budget_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    income REAL NOT NULL,
    total_bills REAL NOT NULL,
    groceries REAL NOT NULL,
    discretionary REAL NOT NULL,
    savings REAL NOT NULL,
    buffer REAL NOT NULL,
    safe_to_spend REAL NOT NULL,
    details_json TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);
