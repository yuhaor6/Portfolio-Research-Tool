"""client/cashflows.py — Income, expenses, loan amortization, and savings projection."""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CLIENT_PROFILE, SIMULATION_CONFIG


def generate_savings_schedule(profile: dict | None = None) -> pd.DataFrame:
    """
    Generate a year-by-year savings schedule for the client.

    Accounts for:
    - Salary growth
    - Federal + state income tax (flat effective rate)
    - Fixed living expenses (inflation-adjusted by 2.5% / year)
    - Student loan minimum payments and accelerated payoff
    - Emergency fund build-up in Year 1-2

    Returns
    -------
    pd.DataFrame with columns:
        year, gross_salary, net_salary, expenses, loan_payment,
        emergency_contribution, investable_savings, cumulative_loan_balance
    """
    if profile is None:
        profile = CLIENT_PROFILE

    horizon = profile["investment_horizon_years"]
    salary = profile["starting_salary"]
    growth = profile["salary_growth_rate"]
    tax = profile["tax_rate"]
    base_expenses = profile["annual_expenses"]
    loan_bal = profile["loan_balance"]
    loan_rate = profile["loan_rate"]
    min_payment = profile.get("loan_min_payment", 500) * 12  # annualize
    # Support either explicit dollar target or months-of-expenses
    if "emergency_fund_target" in profile:
        emerg_target = profile["emergency_fund_target"]
    else:
        months = profile.get("emergency_fund_months", 6)
        emerg_target = (base_expenses / 12) * months
    expense_inflation = 0.025

    records = []
    emerg_saved = 0.0

    for yr in range(1, horizon + 1):
        gross = salary * (1 + growth) ** (yr - 1)
        net = gross * (1 - tax)
        expenses = base_expenses * (1 + expense_inflation) ** (yr - 1)

        # Emergency fund: build to target over first 2 years
        if emerg_saved < emerg_target:
            emerg_contrib = min(emerg_target - emerg_saved, net * 0.10)
            emerg_saved += emerg_contrib
        else:
            emerg_contrib = 0.0

        # Loan payment: pay minimum or more if we have surplus
        annual_interest = loan_bal * loan_rate
        if loan_bal > 0:
            actual_loan_pmt = min(loan_bal + annual_interest, min_payment)
            principal_paid = actual_loan_pmt - annual_interest
            loan_bal = max(0.0, loan_bal - principal_paid)
        else:
            actual_loan_pmt = 0.0

        investable = max(0.0, net - expenses - emerg_contrib - actual_loan_pmt)

        records.append({
            "year": yr,
            "gross_salary": round(gross, 0),
            "net_salary": round(net, 0),
            "expenses": round(expenses, 0),
            "loan_payment": round(actual_loan_pmt, 0),
            "emergency_contribution": round(emerg_contrib, 0),
            "investable_savings": round(investable, 0),
            "cumulative_loan_balance": round(loan_bal, 0),
        })

    return pd.DataFrame(records)


def monthly_contributions(schedule: pd.DataFrame) -> np.ndarray:
    """
    Convert annual savings schedule to a monthly contributions array.
    Length = horizon_years * 12.
    """
    monthly = []
    for _, row in schedule.iterrows():
        monthly.extend([row["investable_savings"] / 12.0] * 12)
    return np.array(monthly)


if __name__ == "__main__":
    schedule = generate_savings_schedule()
    pd.set_option("display.float_format", "${:,.0f}".format)
    print("\n=== Client Savings Schedule ===")
    print(schedule.to_string(index=False))
    print(f"\nTotal investable over {CLIENT_PROFILE['investment_horizon_years']} years: "
          f"${schedule['investable_savings'].sum():,.0f}")
    print(f"Initial investment: ${CLIENT_PROFILE['initial_investment']:,.0f}")
    print(f"Goal: ${CLIENT_PROFILE['goal_amount']:,.0f}")
