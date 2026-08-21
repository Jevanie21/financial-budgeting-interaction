import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class Storage:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        self.conn.executescript(schema_path.read_text(encoding="utf-8"))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def get_profile(self) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM user_profile WHERE id = 1").fetchone()
        return dict(row) if row else None

    def save_profile(self, profile: Dict[str, Any]) -> None:
        profile = {**profile, "id": 1, "updated_at": datetime.now(timezone.utc).isoformat()}
        self.conn.execute(
            """
            INSERT INTO user_profile (
                id, income, pay_schedule, groceries_budget, pocket_money,
                car_payment_amount, car_payment_due_day, car_payment_deadline_day,
                grace_period_days, updated_at
            ) VALUES (
                :id, :income, :pay_schedule, :groceries_budget, :pocket_money,
                :car_payment_amount, :car_payment_due_day, :car_payment_deadline_day,
                :grace_period_days, :updated_at
            )
            ON CONFLICT(id) DO UPDATE SET
                income=excluded.income,
                pay_schedule=excluded.pay_schedule,
                groceries_budget=excluded.groceries_budget,
                pocket_money=excluded.pocket_money,
                car_payment_amount=excluded.car_payment_amount,
                car_payment_due_day=excluded.car_payment_due_day,
                car_payment_deadline_day=excluded.car_payment_deadline_day,
                grace_period_days=excluded.grace_period_days,
                updated_at=excluded.updated_at
            """,
            profile,
        )
        self.conn.commit()

    def get_recurring_bills(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM recurring_bills WHERE active = 1 ORDER BY due_day, name"
        ).fetchall()
        return [dict(row) for row in rows]

    def replace_recurring_bills(self, bills: List[Dict[str, Any]]) -> None:
        self.conn.execute("DELETE FROM recurring_bills")
        self.conn.executemany(
            """
            INSERT INTO recurring_bills(name, amount, due_day, deadline_day, active)
            VALUES (:name, :amount, :due_day, :deadline_day, 1)
            """,
            bills,
        )
        self.conn.commit()

    def get_savings_goals(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM savings_goals WHERE active = 1 ORDER BY target_date, name"
        ).fetchall()
        return [dict(row) for row in rows]

    def replace_savings_goals(self, goals: List[Dict[str, Any]]) -> None:
        self.conn.execute("DELETE FROM savings_goals")
        self.conn.executemany(
            """
            INSERT INTO savings_goals(name, target_amount, target_date, active)
            VALUES (:name, :target_amount, :target_date, 1)
            """,
            goals,
        )
        self.conn.commit()

    def get_last_session_state(self) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT id, created_at, period_label, detected_changes_json, budget_plan_json FROM sessions ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["detected_changes"] = json.loads(data.pop("detected_changes_json"))
        data["budget_plan"] = json.loads(data.pop("budget_plan_json"))
        return data

    def save_session(
        self,
        period_label: str,
        detected_changes: Dict[str, Any],
        budget_plan: Dict[str, Any],
        summary_text: str,
        interaction_log: List[Dict[str, str]],
    ) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO sessions(created_at, period_label, detected_changes_json, budget_plan_json, summary_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                created_at,
                period_label,
                json.dumps(detected_changes),
                json.dumps(budget_plan),
                summary_text,
            ),
        )
        session_id = cursor.lastrowid

        self.conn.executemany(
            """
            INSERT INTO interaction_logs(session_id, timestamp, role, message)
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    session_id,
                    item.get("timestamp", created_at),
                    item["role"],
                    item["message"],
                )
                for item in interaction_log
            ],
        )

        self.conn.execute(
            """
            INSERT INTO budget_snapshots(
                session_id, income, total_bills, groceries, discretionary, savings, buffer, safe_to_spend, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                budget_plan["income"],
                budget_plan["total_bills"],
                budget_plan["groceries"],
                budget_plan["discretionary"],
                budget_plan["savings"],
                budget_plan["buffer"],
                budget_plan["safe_to_spend"],
                json.dumps(budget_plan),
            ),
        )
        self.conn.commit()
        return int(session_id)
