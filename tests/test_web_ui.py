import tempfile
import unittest
from pathlib import Path

from budget_agent.storage import Storage
from budget_agent.web_ui import create_app


class WebUiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(str(Path(self.tmp.name) / "agent.db"))
        self.app = create_app(self.storage).test_client()

    def tearDown(self):
        self.storage.close()
        self.tmp.cleanup()

    def test_rejects_invalid_json_input(self):
        response = self.app.post(
            "/",
            data={
                "income": "2000",
                "pay_schedule": "biweekly",
                "groceries_budget": "300",
                "pocket_money": "150",
                "car_payment_amount": "250",
                "car_payment_due_day": "15",
                "car_payment_deadline_day": "",
                "grace_period_days": "3",
                "bills_json": "{not-valid",
                "goals_json": "[]",
            },
        )
        text = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Please fix input values", text)
        self.assertEqual(len(self.storage.get_recurring_bills()), 0)

    def test_rejects_invalid_schedule(self):
        response = self.app.post(
            "/",
            data={
                "income": "2000",
                "pay_schedule": "daily",
                "groceries_budget": "300",
                "pocket_money": "150",
                "car_payment_amount": "250",
                "car_payment_due_day": "15",
                "car_payment_deadline_day": "",
                "grace_period_days": "3",
                "bills_json": "[]",
                "goals_json": "[]",
            },
        )
        text = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Pay schedule must be one of", text)

    def test_generates_plan_for_valid_input(self):
        response = self.app.post(
            "/",
            data={
                "income": "2000",
                "pay_schedule": "biweekly",
                "groceries_budget": "300",
                "pocket_money": "150",
                "car_payment_amount": "250",
                "car_payment_due_day": "15",
                "car_payment_deadline_day": "",
                "grace_period_days": "3",
                "bills_json": "[]",
                "goals_json": "[]",
            },
        )
        text = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Plan Summary", text)
        self.assertIn("Safe to spend this period", text)


if __name__ == "__main__":
    unittest.main()
