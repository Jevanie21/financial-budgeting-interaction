from datetime import date, datetime
from typing import Any, Dict, List


PAY_SCHEDULES = {
    "weekly": 52,
    "biweekly": 26,
    "semimonthly": 24,
    "monthly": 12,
}


def _periods_until(target_date: str, pay_schedule: str) -> int:
    end = datetime.strptime(target_date, "%Y-%m-%d").date()
    days = max((end - date.today()).days, 0)
    periods_per_year = PAY_SCHEDULES.get(pay_schedule, 12)
    periods = max(int((days / 365) * periods_per_year), 0)
    return max(periods, 1)


def create_budget_plan(
    profile: Dict[str, Any], bills: List[Dict[str, Any]], goals: List[Dict[str, Any]]
) -> Dict[str, Any]:
    income = float(profile["income"])
    groceries = float(profile["groceries_budget"])
    discretionary_target = float(profile["pocket_money"])

    all_bills = [*bills]
    all_bills.append(
        {
            "name": "Car Payment",
            "amount": float(profile["car_payment_amount"]),
            "due_day": int(profile["car_payment_due_day"]),
            "deadline_day": profile.get("car_payment_deadline_day"),
        }
    )
    total_bills = round(sum(float(b["amount"]) for b in all_bills), 2)

    goal_breakdown = []
    total_needed_savings = 0.0
    for goal in goals:
        per_period = round(
            float(goal["target_amount"]) / _periods_until(goal["target_date"], profile["pay_schedule"]),
            2,
        )
        total_needed_savings += per_period
        goal_breakdown.append(
            {
                "name": goal["name"],
                "target_amount": float(goal["target_amount"]),
                "target_date": goal["target_date"],
                "recommended_per_period": per_period,
            }
        )

    essentials = total_bills + groceries
    remaining_after_essentials = income - essentials

    discretionary = max(min(discretionary_target, remaining_after_essentials), 0)
    remaining_after_discretionary = remaining_after_essentials - discretionary
    savings = max(min(total_needed_savings, remaining_after_discretionary), 0)
    buffer = max(remaining_after_discretionary - savings, 0)
    safe_to_spend = round(discretionary + buffer, 2)

    adjustments = []
    if remaining_after_essentials < 0:
        adjustments.append(
            "Income does not fully cover bills + groceries; reduce groceries, move due dates, or raise income."
        )
    elif savings < total_needed_savings:
        adjustments.append(
            "Savings target is not fully funded this period; reduce pocket money or extend savings deadlines."
        )

    return {
        "income": round(income, 2),
        "total_bills": total_bills,
        "bills": all_bills,
        "groceries": round(groceries, 2),
        "discretionary": round(discretionary, 2),
        "desired_discretionary": round(discretionary_target, 2),
        "savings": round(savings, 2),
        "needed_savings": round(total_needed_savings, 2),
        "buffer": round(buffer, 2),
        "safe_to_spend": safe_to_spend,
        "goal_breakdown": goal_breakdown,
        "adjustments": adjustments,
    }
