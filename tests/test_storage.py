import tempfile
import unittest
from pathlib import Path

from budget_agent.storage import Storage


class StorageTests(unittest.TestCase):
    def test_persists_profile_bills_goals_and_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "agent.db"
            storage = Storage(str(db_path))

            profile = {
                "income": 1800,
                "pay_schedule": "biweekly",
                "groceries_budget": 220,
                "pocket_money": 100,
                "car_payment_amount": 240,
                "car_payment_due_day": 21,
                "car_payment_deadline_day": 26,
                "grace_period_days": 4,
            }
            bills = [{"name": "Internet", "amount": 80, "due_day": 12, "deadline_day": 15}]
            goals = [{"name": "Vacation", "target_amount": 1000, "target_date": "2028-01-01"}]

            storage.save_profile(profile)
            storage.replace_recurring_bills(bills)
            storage.replace_savings_goals(goals)
            session_id = storage.save_session(
                period_label="2026-08",
                detected_changes={"profile": {"income": [1700, 1800]}},
                budget_plan={
                    "income": 1800,
                    "total_bills": 320,
                    "groceries": 220,
                    "discretionary": 100,
                    "savings": 120,
                    "buffer": 1040,
                    "safe_to_spend": 1140,
                },
                summary_text="ok",
                interaction_log=[{"role": "assistant", "message": "saved"}],
            )

            self.assertIsInstance(session_id, int)
            self.assertEqual(storage.get_profile()["income"], 1800)
            self.assertEqual(len(storage.get_recurring_bills()), 1)
            self.assertEqual(len(storage.get_savings_goals()), 1)
            self.assertIsNotNone(storage.get_last_session_state())
            storage.close()


if __name__ == "__main__":
    unittest.main()
