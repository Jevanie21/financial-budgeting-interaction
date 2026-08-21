import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import Flask, render_template_string, request

from .budgeting import create_budget_plan
from .change_detection import detect_changes
from .session_manager import render_plan_text
from .storage import Storage

PROFILE_FIELDS = (
    "income",
    "pay_schedule",
    "groceries_budget",
    "pocket_money",
    "car_payment_amount",
    "car_payment_due_day",
    "car_payment_deadline_day",
    "grace_period_days",
)

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Money Buddy</title>
  <style>
    body { font-family: Arial, sans-serif; background: linear-gradient(120deg, #f0f9ff, #f5f3ff); margin: 0; padding: 24px; }
    .card { max-width: 980px; margin: 0 auto; background: white; border-radius: 16px; padding: 20px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
    h1 { margin-top: 0; color: #334155; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    label { font-size: 13px; color: #334155; display: block; }
    input, textarea, select { width: 100%; padding: 10px; border-radius: 8px; border: 1px solid #cbd5e1; margin-top: 6px; }
    button { margin-top: 16px; background: #6366f1; color: white; border: 0; border-radius: 10px; padding: 10px 14px; cursor: pointer; }
    pre { white-space: pre-wrap; background: #0f172a; color: #d1fae5; border-radius: 8px; padding: 14px; }
    .hint { font-size: 12px; color: #64748b; }
  </style>
</head>
<body>
  <div class="card">
    <h1>💸 Money Buddy (Local-First)</h1>
    <p class="hint">Everything stays local on your device (SQLite + local logs).</p>
    <form method="post">
      <div class="grid">
        <label>Income per pay period<input name="income" value="{{ profile.get('income', '') }}" required></label>
        <label>Pay schedule<select name="pay_schedule">{% for item in ['weekly','biweekly','semimonthly','monthly'] %}<option value="{{item}}" {% if profile.get('pay_schedule') == item %}selected{% endif %}>{{item}}</option>{% endfor %}</select></label>
        <label>Groceries budget<input name="groceries_budget" value="{{ profile.get('groceries_budget', '') }}" required></label>
        <label>Pocket money / discretionary<input name="pocket_money" value="{{ profile.get('pocket_money', '') }}" required></label>
        <label>Car payment amount<input name="car_payment_amount" value="{{ profile.get('car_payment_amount', '') }}" required></label>
        <label>Car payment due day<input name="car_payment_due_day" value="{{ profile.get('car_payment_due_day', '') }}" required></label>
        <label>Car payment deadline day<input name="car_payment_deadline_day" value="{{ profile.get('car_payment_deadline_day', '') }}"></label>
        <label>Grace period days<input name="grace_period_days" value="{{ profile.get('grace_period_days', 0) }}" required></label>
      </div>
      <label>Recurring bills JSON list
        <textarea rows="6" name="bills_json">{{ bills_json }}</textarea>
      </label>
      <label>Savings goals JSON list
        <textarea rows="6" name="goals_json">{{ goals_json }}</textarea>
      </label>
      <button type="submit">Generate My Plan</button>
    </form>
    {% if summary %}
      <h2>Plan Summary</h2>
      <pre>{{ summary }}</pre>
    {% endif %}
  </div>
</body>
</html>
"""


def _normalize_bills(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "amount": float(item["amount"]),
            "due_day": int(item["due_day"]),
            "deadline_day": int(item["deadline_day"]) if item.get("deadline_day") not in (None, "") else None,
        }
        for item in raw
    ]


def _normalize_goals(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "target_amount": float(item["target_amount"]),
            "target_date": item["target_date"],
        }
        for item in raw
    ]


def create_app(storage: Storage) -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        profile = storage.get_profile() or {}
        previous_bills = storage.get_recurring_bills()
        previous_goals = storage.get_savings_goals()

        summary = ""
        bills_json = json.dumps(
            [
                {
                    "name": b["name"],
                    "amount": b["amount"],
                    "due_day": b["due_day"],
                    "deadline_day": b.get("deadline_day"),
                }
                for b in previous_bills
            ],
            indent=2,
        )
        goals_json = json.dumps(
            [
                {
                    "name": g["name"],
                    "target_amount": g["target_amount"],
                    "target_date": g["target_date"],
                }
                for g in previous_goals
            ],
            indent=2,
        )

        if request.method == "POST":
            previous_profile = {key: profile.get(key) for key in PROFILE_FIELDS}
            profile = {
                "income": float(request.form["income"]),
                "pay_schedule": request.form["pay_schedule"],
                "groceries_budget": float(request.form["groceries_budget"]),
                "pocket_money": float(request.form["pocket_money"]),
                "car_payment_amount": float(request.form["car_payment_amount"]),
                "car_payment_due_day": int(request.form["car_payment_due_day"]),
                "car_payment_deadline_day": int(request.form["car_payment_deadline_day"])
                if request.form.get("car_payment_deadline_day")
                else None,
                "grace_period_days": int(request.form["grace_period_days"]),
            }

            bills = _normalize_bills(json.loads(request.form.get("bills_json", "[]") or "[]"))
            goals = _normalize_goals(json.loads(request.form.get("goals_json", "[]") or "[]"))

            storage.save_profile(profile)
            storage.replace_recurring_bills(bills)
            storage.replace_savings_goals(goals)

            plan = create_budget_plan(profile, bills, goals)
            changes = {
                "profile": detect_changes(previous_profile, profile),
                "bills_changed": [
                    {
                        "name": b["name"],
                        "amount": float(b["amount"]),
                        "due_day": int(b["due_day"]),
                        "deadline_day": b.get("deadline_day"),
                    }
                    for b in previous_bills
                ]
                != bills,
                "goals_changed": [
                    {
                        "name": g["name"],
                        "target_amount": float(g["target_amount"]),
                        "target_date": g["target_date"],
                    }
                    for g in previous_goals
                ]
                != goals,
            }
            summary = render_plan_text(plan, changes)
            storage.save_session(
                period_label=datetime.now().strftime("%Y-%m"),
                detected_changes=changes,
                budget_plan=plan,
                summary_text=summary,
                interaction_log=[
                    {
                        "role": "assistant",
                        "message": "Web UI budgeting plan generated",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            )

            bills_json = json.dumps(bills, indent=2)
            goals_json = json.dumps(goals, indent=2)

        return render_template_string(
            HTML,
            profile=profile,
            summary=summary,
            bills_json=bills_json,
            goals_json=goals_json,
        )

    return app
