import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .budgeting import create_budget_plan
from .change_detection import detect_changes
from .llm import explain_with_ollama
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


def _normalized_profile(profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not profile:
        return {}
    return {key: profile.get(key) for key in PROFILE_FIELDS}


class SessionManager:
    def __init__(self, storage: Storage):
        self.storage = storage

    @staticmethod
    def _prompt_text(prompt: str, default: Optional[str] = None) -> str:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()
        return value if value else (default or "")

    @staticmethod
    def _prompt_float(prompt: str, default: Optional[float] = None) -> float:
        while True:
            raw = SessionManager._prompt_text(prompt, str(default) if default is not None else None)
            try:
                return float(raw)
            except ValueError:
                print("Please enter a valid number.")

    @staticmethod
    def _prompt_int(prompt: str, default: Optional[int] = None) -> int:
        while True:
            raw = SessionManager._prompt_text(prompt, str(default) if default is not None else None)
            try:
                return int(raw)
            except ValueError:
                print("Please enter a valid whole number.")

    @staticmethod
    def _prompt_optional_int(prompt: str, default: Optional[int] = None) -> Optional[int]:
        suffix = f" [{default}]" if default is not None else ""
        while True:
            raw = input(f"{prompt}{suffix}: ").strip()
            if raw == "":
                return default
            try:
                return int(raw)
            except ValueError:
                print("Please enter a valid whole number.")

    def collect_profile(self, previous: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "income": self._prompt_float("Income this pay period", previous.get("income") if previous else None),
            "pay_schedule": self._prompt_text(
                "Pay schedule (weekly/biweekly/semimonthly/monthly)",
                previous.get("pay_schedule") if previous else "biweekly",
            ),
            "groceries_budget": self._prompt_float(
                "Groceries budget", previous.get("groceries_budget") if previous else None
            ),
            "pocket_money": self._prompt_float(
                "Pocket money / discretionary target",
                previous.get("pocket_money") if previous else None,
            ),
            "car_payment_amount": self._prompt_float(
                "Car payment amount", previous.get("car_payment_amount") if previous else None
            ),
            "car_payment_due_day": self._prompt_int(
                "Car payment due day (1-31)", previous.get("car_payment_due_day") if previous else None
            ),
            "car_payment_deadline_day": self._prompt_optional_int(
                "Car payment late-fee deadline day (1-31)",
                previous.get("car_payment_deadline_day") if previous else None,
            ),
            "grace_period_days": self._prompt_int(
                "Grace period in days", previous.get("grace_period_days") if previous else 0
            ),
        }

    def collect_bills(self, previous_bills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        print("\nRecurring bills (excluding car payment).")
        if previous_bills:
            keep = self._prompt_text("Keep previous recurring bills? (y/n)", "y").lower()
            if keep.startswith("y"):
                return [
                    {
                        "name": b["name"],
                        "amount": float(b["amount"]),
                        "due_day": int(b["due_day"]),
                        "deadline_day": b.get("deadline_day"),
                    }
                    for b in previous_bills
                ]

        bills = []
        while True:
            name = self._prompt_text("Bill name (blank to finish)")
            if not name:
                break
            amount = self._prompt_float("Amount")
            due_day = self._prompt_int("Due day (1-31)")
            deadline_input = self._prompt_text("Late-fee deadline day (optional)")
            bills.append(
                {
                    "name": name,
                    "amount": amount,
                    "due_day": due_day,
                    "deadline_day": int(deadline_input) if deadline_input else None,
                }
            )
        return bills

    def collect_goals(self, previous_goals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        print("\nSavings goals.")
        if previous_goals:
            keep = self._prompt_text("Keep previous savings goals? (y/n)", "y").lower()
            if keep.startswith("y"):
                return [
                    {
                        "name": g["name"],
                        "target_amount": float(g["target_amount"]),
                        "target_date": g["target_date"],
                    }
                    for g in previous_goals
                ]

        goals = []
        while True:
            name = self._prompt_text("Goal name (blank to finish)")
            if not name:
                break
            target_amount = self._prompt_float("Target amount")
            target_date = self._prompt_text("Target date (YYYY-MM-DD)")
            goals.append(
                {"name": name, "target_amount": target_amount, "target_date": target_date}
            )
        return goals

    def run_cli_session(self, use_ollama: bool = False) -> Dict[str, Any]:
        previous_profile = _normalized_profile(self.storage.get_profile())
        previous_bills = self.storage.get_recurring_bills()
        previous_goals = self.storage.get_savings_goals()
        last_session = self.storage.get_last_session_state()

        if previous_profile:
            print("Welcome back. I loaded your local memory and will ask only what changed.")
        else:
            print("First-time setup. Let's build your baseline financial profile.")

        profile = self.collect_profile(previous_profile)
        bills = self.collect_bills(previous_bills)
        goals = self.collect_goals(previous_goals)

        self.storage.save_profile(profile)
        self.storage.replace_recurring_bills(bills)
        self.storage.replace_savings_goals(goals)

        plan = create_budget_plan(profile, bills, goals)

        current_state = {
            "profile": profile,
            "bills": bills,
            "goals": goals,
        }
        previous_state = {
            "profile": previous_profile,
            "bills": [
                {
                    "name": b["name"],
                    "amount": float(b["amount"]),
                    "due_day": int(b["due_day"]),
                    "deadline_day": b.get("deadline_day"),
                }
                for b in previous_bills
            ],
            "goals": [
                {
                    "name": g["name"],
                    "target_amount": float(g["target_amount"]),
                    "target_date": g["target_date"],
                }
                for g in previous_goals
            ],
        }

        changes = {
            "profile": detect_changes(previous_state["profile"], current_state["profile"]),
            "bills_changed": previous_state["bills"] != current_state["bills"],
            "goals_changed": previous_state["goals"] != current_state["goals"],
            "compared_to_last_session": bool(last_session),
        }

        period_label = datetime.now().strftime("%Y-%m")
        summary = render_plan_text(plan, changes)
        if use_ollama:
            extra = explain_with_ollama(
                f"Explain this budget plan in plain language:\n{json.dumps(plan)}"
            )
            if extra:
                summary += "\n\nLocal LLM note:\n" + extra.strip()

        interaction_log = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "role": "assistant",
                "message": "Generated budgeting session with local memory comparison.",
            }
        ]

        self.storage.save_session(period_label, changes, plan, summary, interaction_log)
        print("\n" + summary)
        return {"plan": plan, "changes": changes, "summary": summary}


def render_plan_text(plan: Dict[str, Any], changes: Dict[str, Any]) -> str:
    lines = [
        "=== Budget Plan ===",
        f"Income: ${plan['income']:.2f}",
        f"Bills reserve: ${plan['total_bills']:.2f}",
        f"Groceries: ${plan['groceries']:.2f}",
        f"Discretionary: ${plan['discretionary']:.2f}",
        f"Savings this period: ${plan['savings']:.2f}",
        f"Buffer: ${plan['buffer']:.2f}",
        f"Safe to spend this period: ${plan['safe_to_spend']:.2f}",
    ]

    if plan["goal_breakdown"]:
        lines.append("\nSavings goals per period:")
        for goal in plan["goal_breakdown"]:
            lines.append(
                f"- {goal['name']}: ${goal['recommended_per_period']:.2f} each period until {goal['target_date']}"
            )

    if plan["adjustments"]:
        lines.append("\nAdjustments needed:")
        lines.extend(f"- {item}" for item in plan["adjustments"])

    lines.append("\nDetected updates vs last memory snapshot:")
    lines.append(f"- Profile fields changed: {len(changes.get('profile', {}))}")
    lines.append(f"- Recurring bills changed: {changes.get('bills_changed')}")
    lines.append(f"- Savings goals changed: {changes.get('goals_changed')}")

    return "\n".join(lines)
