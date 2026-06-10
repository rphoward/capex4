import unittest

from capex3.core.emergency_debt_ledger import (
    debt_service_for_month,
    evaluate_emergency_debt_ledger,
    evaluate_overlap_detected,
    repair_year_first_month,
    trace_years_from_trace,
)
from capex3.core.errors import RentalCapexError
from capex3.core.financial import pmt
from capex3.core.repair_reserve_path_trace import compute_repair_reserve_path_trace
from capex3.presentation.http_contracts import calculate_payload


class EmergencyDebtLedgerTest(unittest.TestCase):
    def test_year_zero_not_evaluated_for_gap(self) -> None:
        trace_years = _synthetic_trace_years(
            {
                0: {"repairCost": 99_999.0, "balanceBeforeRepairs": 0.0},
                1: {"repairCost": 0.0, "balanceBeforeRepairs": 5_000.0},
            }
        )
        ledger = _evaluate(trace_years)

        self.assertEqual(len(ledger["years"]), 10)
        self.assertEqual(ledger["refinanceEvents"], [])
        self.assertEqual(ledger["makeReadyAttribution"], 0.0)
        self.assertFalse(ledger["makeReadyShortfallFlag"])

    def test_funded_repair_year_has_zero_gap_and_no_refi(self) -> None:
        trace_years = _synthetic_trace_years(
            {
                2: {"repairCost": 10_000.0, "balanceBeforeRepairs": 12_000.0},
            }
        )
        ledger = _evaluate(trace_years)
        year_two = _ledger_year(ledger, 2)

        self.assertEqual(year_two["rawShortfall"], 0.0)
        self.assertEqual(year_two["emergencyGap"], 0.0)
        self.assertEqual(ledger["refinanceEvents"], [])
        self.assertEqual(ledger["outstandingPrincipal"], 0.0)

    def test_year_one_shortfall_routes_to_make_ready_not_emergency(self) -> None:
        trace_years = _synthetic_trace_years(
            {
                1: {"repairCost": 20_000.0, "balanceBeforeRepairs": 5_000.0},
            }
        )
        ledger = _evaluate(trace_years, immediate_rehab_make_ready=3_000.0)
        year_one = _ledger_year(ledger, 1)

        self.assertEqual(year_one["rawShortfall"], 15_000.0)
        self.assertEqual(year_one["emergencyGap"], 0.0)
        self.assertTrue(year_one["routedToMakeReady"])
        self.assertEqual(ledger["makeReadyAttribution"], 15_000.0)
        self.assertTrue(ledger["makeReadyShortfallFlag"])
        self.assertEqual(
            ledger["suggestedImmediateRehabMakeReady"],
            18_000.0,
        )
        self.assertEqual(ledger["refinanceEvents"], [])
        self.assertFalse(ledger["overlapDetected"])
        self.assertEqual(ledger["overlapRefinanceYears"], [])

    def test_year_two_shortfall_triggers_single_refi_and_payment_schedule(self) -> None:
        gap = 8_000.0
        apr = 0.125
        term_years = 5
        term_months = term_years * 12
        trace_years = _synthetic_trace_years(
            {2: {"repairCost": gap, "balanceBeforeRepairs": 0.0}},
        )
        ledger = _evaluate(
            trace_years,
            emergency_loan_apr=apr,
            emergency_loan_term_years=term_years,
        )

        year_two = _ledger_year(ledger, 2)
        self.assertEqual(year_two["emergencyGap"], gap)
        self.assertEqual(len(ledger["refinanceEvents"]), 1)

        refi = ledger["refinanceEvents"][0]
        self.assertEqual(refi["year"], 2)
        self.assertEqual(refi["outstandingPrincipal"], gap)
        self.assertFalse(refi["priorScheduleActive"])
        self.assertFalse(ledger["overlapDetected"])
        self.assertEqual(ledger["overlapRefinanceYears"], [])
        self.assertEqual(refi["paymentStartMonth"], repair_year_first_month(2))

        expected_payment = pmt(apr / 12, term_months, 0.0, -gap, 0)
        self.assertAlmostEqual(refi["monthlyPayment"], expected_payment)

        start = int(refi["paymentStartMonth"])
        self.assertGreater(debt_service_for_month(ledger, start), 0.0)
        self.assertAlmostEqual(
            debt_service_for_month(ledger, start),
            expected_payment,
        )
        self.assertEqual(debt_service_for_month(ledger, start - 1), 0.0)
        self.assertAlmostEqual(
            debt_service_for_month(ledger, start + term_months - 1),
            expected_payment,
        )
        self.assertEqual(debt_service_for_month(ledger, start + term_months), 0.0)

    def test_stacked_refi_consolidates_principal_and_supersedes_prior_schedule(
        self,
    ) -> None:
        gap_one = 5_000.0
        gap_two = 3_000.0
        apr = 0.125
        term_years = 5
        term_months = term_years * 12
        trace_years = _synthetic_trace_years(
            {
                2: {"repairCost": gap_one, "balanceBeforeRepairs": 0.0},
                4: {"repairCost": gap_two, "balanceBeforeRepairs": 0.0},
            }
        )
        ledger = _evaluate(
            trace_years,
            emergency_loan_apr=apr,
            emergency_loan_term_years=term_years,
        )

        self.assertEqual(len(ledger["refinanceEvents"]), 2)
        first_refi, second_refi = ledger["refinanceEvents"]
        self.assertEqual(first_refi["outstandingPrincipal"], gap_one)
        self.assertEqual(
            second_refi["outstandingPrincipal"],
            gap_one + gap_two,
        )
        self.assertTrue(second_refi["priorScheduleActive"])
        self.assertTrue(ledger["overlapDetected"])
        self.assertEqual(ledger["overlapRefinanceYears"], [4])
        self.assertTrue(evaluate_overlap_detected(ledger))

        consolidated_payment = pmt(
            apr / 12,
            term_months,
            0.0,
            -(gap_one + gap_two),
            0,
        )
        self.assertAlmostEqual(second_refi["monthlyPayment"], consolidated_payment)

        second_start = int(second_refi["paymentStartMonth"])
        first_start = int(first_refi["paymentStartMonth"])
        first_payment = float(first_refi["monthlyPayment"])

        self.assertAlmostEqual(
            debt_service_for_month(ledger, first_start),
            first_payment,
        )
        self.assertAlmostEqual(
            debt_service_for_month(ledger, second_start - 1),
            first_payment,
        )
        self.assertAlmostEqual(
            debt_service_for_month(ledger, second_start),
            consolidated_payment,
        )

    def test_integrates_with_core_repair_trace_year_one_make_ready(self) -> None:
        trace = compute_repair_reserve_path_trace(
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
        ledger = evaluate_emergency_debt_ledger(
            trace["years"],
            emergency_loan_apr=0.125,
            emergency_loan_term_years=5,
        )
        year_one = _ledger_year(ledger, 1)

        self.assertGreater(year_one["rawShortfall"], 0.0)
        self.assertEqual(year_one["emergencyGap"], 0.0)
        self.assertEqual(ledger["refinanceEvents"], [])
        self.assertTrue(ledger["makeReadyShortfallFlag"])
        self.assertFalse(ledger["overlapDetected"])

    def test_late_second_refi_without_prior_schedule_active_has_no_overlap(self) -> None:
        """Second gap after first refi term ends — priorScheduleActive false, no overlap."""
        term_years = 5
        trace_years = _synthetic_trace_years(
            {
                2: {"repairCost": 5_000.0, "balanceBeforeRepairs": 0.0},
                8: {"repairCost": 3_000.0, "balanceBeforeRepairs": 0.0},
            }
        )
        ledger = _evaluate(
            trace_years,
            emergency_loan_apr=0.125,
            emergency_loan_term_years=term_years,
        )

        self.assertEqual(len(ledger["refinanceEvents"]), 2)
        self.assertFalse(ledger["refinanceEvents"][1]["priorScheduleActive"])
        self.assertFalse(ledger["overlapDetected"])
        self.assertEqual(ledger["overlapRefinanceYears"], [])

    def test_trace_years_from_trace_accepts_rows_or_years(self) -> None:
        trace_years = _synthetic_trace_years({})
        payload = calculate_payload({})
        repair_fund = payload["result"]["traces"]["repairFund"]

        self.assertEqual(
            trace_years_from_trace({"years": trace_years}),
            trace_years,
        )
        self.assertEqual(len(trace_years_from_trace(repair_fund)), 11)

    def test_invalid_term_raises(self) -> None:
        with self.assertRaises(RentalCapexError):
            _evaluate(_synthetic_trace_years({}), emergency_loan_term_years=0)


def _evaluate(
    trace_years: list[dict[str, object]],
    *,
    emergency_loan_apr: float = 0.125,
    emergency_loan_term_years: float = 5,
    immediate_rehab_make_ready: float = 0.0,
) -> dict[str, object]:
    return evaluate_emergency_debt_ledger(
        trace_years,
        emergency_loan_apr=emergency_loan_apr,
        emergency_loan_term_years=emergency_loan_term_years,
        immediate_rehab_make_ready=immediate_rehab_make_ready,
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


def _ledger_year(ledger: dict[str, object], year: int) -> dict[str, object]:
    for row in ledger["years"]:
        if row["year"] == year:
            return row
    raise AssertionError(f"missing ledger year {year}")


if __name__ == "__main__":
    unittest.main()
