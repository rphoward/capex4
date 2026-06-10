import unittest

from capex3.core.emergency_debt_ledger import (
    evaluate_deal_survival,
    evaluate_emergency_debt_ledger,
    evaluate_shock_adjusted_cash_flow,
)
from capex3.core.financial import pmt


class ShockSurvivalTest(unittest.TestCase):
    def test_no_refi_shock_equals_baseline(self) -> None:
        baseline = 1_250.0
        ledger = _evaluate(_synthetic_trace_years({}))
        shock = evaluate_shock_adjusted_cash_flow(baseline, ledger)

        self.assertEqual(shock["shockAdjustedCashFlow"], baseline)
        self.assertEqual(shock["worstShockMonth"], 1)
        self.assertTrue(
            evaluate_deal_survival(
                float(shock["shockAdjustedCashFlow"]),
                baseline,
                0.0,
            )
        )

    def test_year_two_refi_lowers_worst_month(self) -> None:
        baseline = 100.0
        gap = 20_000.0
        apr = 0.125
        term_years = 5
        trace_years = _synthetic_trace_years(
            {2: {"repairCost": gap, "balanceBeforeRepairs": 0.0}},
        )
        ledger = _evaluate(
            trace_years,
            emergency_loan_apr=apr,
            emergency_loan_term_years=term_years,
        )
        shock = evaluate_shock_adjusted_cash_flow(baseline, ledger)
        payment = pmt(apr / 12, term_years * 12, 0.0, -gap, 0)

        self.assertLess(float(shock["shockAdjustedCashFlow"]), baseline)
        self.assertAlmostEqual(
            float(shock["shockAdjustedCashFlow"]),
            baseline - payment,
        )
        self.assertFalse(
            evaluate_deal_survival(
                float(shock["shockAdjustedCashFlow"]),
                baseline,
                0.0,
            )
        )

    def test_year_one_make_ready_does_not_reduce_shock(self) -> None:
        baseline = 800.0
        trace_years = _synthetic_trace_years(
            {1: {"repairCost": 15_000.0, "balanceBeforeRepairs": 2_000.0}},
        )
        ledger = _evaluate(trace_years)
        shock = evaluate_shock_adjusted_cash_flow(baseline, ledger)

        self.assertEqual(shock["shockAdjustedCashFlow"], baseline)
        self.assertEqual(ledger["refinanceEvents"], [])
        self.assertTrue(ledger["makeReadyShortfallFlag"])

    def test_floor_fails_survival_when_b40_below_minimum(self) -> None:
        baseline = 100.0
        floor = 250.0
        ledger = _evaluate(_synthetic_trace_years({}))
        shock = evaluate_shock_adjusted_cash_flow(baseline, ledger)

        self.assertFalse(
            evaluate_deal_survival(
                float(shock["shockAdjustedCashFlow"]),
                baseline,
                floor,
            )
        )

    def test_shock_months_cover_full_horizon(self) -> None:
        ledger = _evaluate(_synthetic_trace_years({}))
        shock = evaluate_shock_adjusted_cash_flow(1_000.0, ledger)

        self.assertEqual(len(shock["shockAdjustedMonths"]), 120)
        self.assertEqual(shock["shockAdjustedMonths"][0]["month"], 1)
        self.assertEqual(shock["shockAdjustedMonths"][-1]["month"], 120)


def _evaluate(
    trace_years: list[dict[str, object]],
    *,
    emergency_loan_apr: float = 0.125,
    emergency_loan_term_years: float = 5,
) -> dict[str, object]:
    return evaluate_emergency_debt_ledger(
        trace_years,
        emergency_loan_apr=emergency_loan_apr,
        emergency_loan_term_years=emergency_loan_term_years,
    )


def _synthetic_trace_years(
    overrides: dict[int, dict[str, float]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in range(11):
        values = overrides.get(
            year,
            {"repairCost": 0.0, "balanceBeforeRepairs": 0.0},
        )
        rows.append(
            {
                "year": year,
                "repairCost": values["repairCost"],
                "balanceBeforeRepairs": values["balanceBeforeRepairs"],
                "endingBalance": values["balanceBeforeRepairs"]
                - values["repairCost"],
            }
        )
    return rows


if __name__ == "__main__":
    unittest.main()
