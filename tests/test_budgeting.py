import unittest

from budget_agent.budgeting import create_budget_plan


class BudgetingTests(unittest.TestCase):
    def test_allocates_categories_deterministically(self):
        profile = {
            "income": 2500,
            "pay_schedule": "biweekly",
            "groceries_budget": 300,
            "pocket_money": 200,
            "car_payment_amount": 250,
            "car_payment_due_day": 15,
            "car_payment_deadline_day": 20,
            "grace_period_days": 3,
        }
        bills = [{"name": "Rent", "amount": 900, "due_day": 1, "deadline_day": 5}]
        goals = [{"name": "Emergency", "target_amount": 1200, "target_date": "2030-01-01"}]

        plan = create_budget_plan(profile, bills, goals)

        self.assertEqual(plan["total_bills"], 1150.0)
        self.assertGreater(plan["savings"], 0)
        self.assertAlmostEqual(
            plan["buffer"],
            plan["income"] - plan["total_bills"] - plan["groceries"] - plan["discretionary"] - plan["savings"],
        )

    def test_flags_tight_budget(self):
        profile = {
            "income": 500,
            "pay_schedule": "monthly",
            "groceries_budget": 250,
            "pocket_money": 200,
            "car_payment_amount": 300,
            "car_payment_due_day": 10,
            "car_payment_deadline_day": 13,
            "grace_period_days": 0,
        }

        plan = create_budget_plan(profile, [], [])

        self.assertEqual(plan["discretionary"], 0)
        self.assertTrue(plan["adjustments"])


if __name__ == "__main__":
    unittest.main()
