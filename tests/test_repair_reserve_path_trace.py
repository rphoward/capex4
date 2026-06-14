import math
import unittest

from capex3.core.repair_reserve_path_trace import (
    compute_repair_reserve_path_trace,
    repair_reserve_year_status,
)
from capex3.presentation.http_contracts import (
    calculate_payload,
    defaults_payload,
)


class RepairReservePathTraceTest(unittest.TestCase):
    def test_repair_fund_trace_view_model_is_app_owned_calculation_truth(self) -> None:
        trace = _trace({})

        self.assertIs(trace["workbookCanonical"], False)
        self.assertIs(trace["appRegressionOnly"], True)
        self.assertEqual(
            trace["decisionId"],
            "repair_reserve_path_trace_workbook_vs_teaching",
        )
        self.assertEqual(trace["canonicalReserveSource"], "proForma_and_dashboard")
        self.assertIn("proForma[].annualCapexContribution", trace["canonicalReserveFields"])
        self.assertIn("dashboard.targetCapExReserve", trace["canonicalReserveFields"])
        source_note = str(trace["sourceNote"]).lower()
        self.assertIn("app-owned", source_note)
        self.assertIn("workbook-parity", source_note)

    def test_no_repair_events_in_10_years_keeps_stable_rows_and_empty_markers(self) -> None:
        trace = _trace({"effectiveAgeYears": -10})

        self.assertEqual(list(range(11)), [row["year"] for row in trace["rows"]])
        self.assertEqual([], trace["events"])
        self.assertTrue(all(row["repairCost"] == 0 for row in trace["rows"]))
        self.assertTrue(
            all(row["noReserveSurpriseCost"] == 0 for row in trace["rows"])
        )
        balances = [row["endingBalance"] for row in trace["rows"]]
        self.assertEqual(balances, sorted(balances))

    def test_multiple_events_in_same_year_aggregate_costs_and_preserve_labels(self) -> None:
        trace = _trace({"effectiveAgeYears": 9})
        year_one = trace["rows"][1]

        self.assertGreaterEqual(len(year_one["events"]), 2)
        self.assertAlmostEqual(
            year_one["repairCost"],
            sum(event["amount"] for event in year_one["events"]),
        )
        self.assertGreaterEqual(
            len({event["label"] for event in year_one["events"]}),
            2,
        )

    def test_depleted_reserve_status_is_recorded_without_hiding_comparison(self) -> None:
        trace = _trace({"effectiveAgeYears": 40})

        self.assertGreater(trace["rows"][-1]["noReserveSurpriseCost"], 0)
        self.assertTrue(all("endingBalance" in row for row in trace["rows"]))
        self.assertNotIn(
            "shortfall",
            {row["status"] for row in trace["rows"]},
            "Year-0 accrual (Amendment B) should not spuriously shortfall aged defaults",
        )

        shortfall_trace = compute_repair_reserve_path_trace(
            {"reserveAccountApy": 0.0, "capexInflationRate": 0.0},
            {"totalMonthlyCapexReserve": 100.0, "targetCapExReserve": 1000.0},
            [
                {
                    "component": "Roofing: Arch. Asphalt (per sq)",
                    "remainingLife": 1.0,
                    "futureCost": 50_000.0,
                }
            ],
        )
        shortfall_statuses = {row["status"] for row in shortfall_trace["years"]}
        self.assertIn("shortfall", shortfall_statuses)
        self.assertEqual(
            repair_reserve_year_status([{"amount": 1.0}], 100.0, 0.5),
            "depleted",
        )

    def test_zero_repair_contribution_remains_finite_and_clear(self) -> None:
        component_overrides = {
            component["name"]: {"quantity": 0, "age": 0}
            for component in defaults_payload()["assumptions"]["components"]
        }
        trace = _trace({"componentOverrides": component_overrides})

        self.assertEqual(0, trace["monthlyContribution"])
        self.assertEqual(0, trace["targetReserve"])
        self.assertTrue(all(row["annualContribution"] == 0 for row in trace["rows"]))
        self.assertTrue(all(row["endingBalance"] == 0 for row in trace["rows"]))
        self.assertTrue(_all_trace_numbers_are_finite(trace))

    def test_high_inflation_keeps_future_events_finite_and_renderable(self) -> None:
        trace = _trace({"capexInflationRate": 0.35, "effectiveAgeYears": 0})

        self.assertEqual(11, len(trace["rows"]))
        self.assertTrue(trace["events"])
        self.assertTrue(_all_trace_numbers_are_finite(trace))
        self.assertTrue(all(event["label"] for event in trace["events"]))

    def test_year_zero_accrues_contribution_when_monthly_reserve_positive(self) -> None:
        trace = _trace({})
        year_zero = trace["rows"][0]

        self.assertGreater(trace["monthlyContribution"], 0)
        self.assertGreater(year_zero["annualContribution"], 0)
        self.assertGreater(year_zero["balanceBeforeRepairs"], 0)
        self.assertEqual(year_zero["repairCost"], 0)
        self.assertEqual(
            year_zero["endingBalance"],
            year_zero["balanceBeforeRepairs"],
        )

    def test_year_one_starting_balance_inherits_year_zero_ending(self) -> None:
        trace = _trace({})
        year_zero = trace["rows"][0]
        year_one = trace["rows"][1]

        self.assertAlmostEqual(
            year_one["startingBalance"],
            year_zero["endingBalance"],
        )


def _trace(inputs: dict[str, object]) -> dict[str, object]:
    payload = calculate_payload(inputs)
    return payload["result"]["traces"]["repairFund"]


def _all_trace_numbers_are_finite(value: object) -> bool:
    if isinstance(value, dict):
        return all(_all_trace_numbers_are_finite(item) for item in value.values())
    if isinstance(value, list):
        return all(_all_trace_numbers_are_finite(item) for item in value)
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    return True


if __name__ == "__main__":
    unittest.main()
