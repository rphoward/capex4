import unittest

from capex3.core.reserve_first_shortfall_solver import (
    find_first_emergency_gap_year,
    find_first_raw_shortfall_year,
)
from capex3.presentation.http_contracts import calculate_payload
from capex3.core.calculate_rental_capex import (
    RentalCapexCalculationRequest,
    calculate_rental_capex,
)
from capex3.infrastructure.workbook_assumptions import load_workbook_model_spec_record


class CalculatorResilienceContractTest(unittest.TestCase):
    def test_calculate_payload_exposes_resilience_fields(self) -> None:
        payload = calculate_payload({})
        result = payload["result"]

        self.assertIn("emergencyDebtLedger", result)
        self.assertIn("shockAdjustedCashFlow", result)
        self.assertIn("dealSurvives", result)
        self.assertIn("shockSurvival", result)
        self.assertEqual(
            result["emergencyDebtLedger"]["id"],
            "emergencyDebtLedger",
        )
        self.assertEqual(
            result["shockSurvival"]["shockAdjustedCashFlow"],
            result["shockAdjustedCashFlow"],
        )
        self.assertEqual(
            result["shockSurvival"]["dealSurvives"],
            result["dealSurvives"],
        )
        self.assertIn("overlapDetected", result)
        self.assertFalse(result["overlapDetected"])
        self.assertEqual(
            result["overlapDetected"],
            result["emergencyDebtLedger"]["overlapDetected"],
        )
        self.assertEqual(result["emergencyDebtLedger"]["overlapRefinanceYears"], [])

    def test_calculate_payload_exposes_gap_year_contract_fields(self) -> None:
        payload = calculate_payload({})
        result = payload["result"]
        ledger = result["emergencyDebtLedger"]

        self.assertIn("firstEmergencyGapYear", result)
        self.assertIn("firstRawShortfallYear", result)
        self.assertEqual(
            result["firstEmergencyGapYear"],
            find_first_emergency_gap_year(ledger),
        )
        self.assertEqual(
            result["firstRawShortfallYear"],
            find_first_raw_shortfall_year(ledger),
        )

    def test_calculate_payload_exposes_cash_flow_stability_trace(self) -> None:
        payload = calculate_payload({})
        result = payload["result"]
        traces = result["traces"]

        self.assertIn("cashFlowStability", traces)
        stability = traces["cashFlowStability"]
        self.assertEqual(stability["id"], "cashFlowStability")
        self.assertIn("twoPathComparison", stability)
        self.assertIn("debtLedgerTimeline", stability)
        self.assertIn("plannedReservePath", stability["twoPathComparison"])
        self.assertIn("debtShockPath", stability["twoPathComparison"])
        timeline = stability["debtLedgerTimeline"]
        self.assertIn("refinanceEvents", timeline)
        self.assertIn("paymentMonths", timeline)
        self.assertIn("overlapDetected", timeline)
        self.assertIn("overlapRefinanceYears", timeline)
        self.assertFalse(timeline["overlapDetected"])
        self.assertEqual(timeline["overlapRefinanceYears"], [])
        self.assertEqual(
            stability["contractSource"],
            "capex3.core.teaching",
        )
        self.assertIn("teaching", stability)
        self.assertEqual(
            stability["teaching"]["primaryFramingCopy"],
            stability["primaryFramingCopy"],
        )

    def test_overlap_does_not_gate_deal_survival(self) -> None:
        model_spec = load_workbook_model_spec_record()
        baseline = calculate_rental_capex(
            RentalCapexCalculationRequest.from_contract_dict({}),
            model_spec=model_spec,
        )
        self.assertFalse(baseline.emergency_debt_ledger["overlapDetected"])
        self.assertIsInstance(baseline.shock_survival["dealSurvives"], bool)

    def test_minimum_floor_round_trips_and_affects_survival(self) -> None:
        model_spec = load_workbook_model_spec_record()
        baseline_result = calculate_rental_capex(
            RentalCapexCalculationRequest.from_contract_dict({}),
            model_spec=model_spec,
        )
        true_monthly = float(baseline_result.dashboard["trueMonthlyCashFlow"])
        floor_above_b40 = max(0.0, true_monthly) + 100.0

        below_floor = calculate_rental_capex(
            RentalCapexCalculationRequest.from_contract_dict(
                {"minimumTrueMonthlyCashFlow": floor_above_b40}
            ),
            model_spec=model_spec,
        )

        self.assertFalse(below_floor.shock_survival["dealSurvives"])
        self.assertEqual(
            below_floor.input["minimumTrueMonthlyCashFlow"],
            floor_above_b40,
        )
        self.assertLess(true_monthly, floor_above_b40)


if __name__ == "__main__":
    unittest.main()
