import unittest

from capex3.infrastructure.workbook_assumptions import load_workbook_model_spec_record
from capex3.presentation.http_contracts import (
    SOLVER_VARIABLES,
    calculate_payload,
)
from capex3.core.teaching.calculation_result_traces import (
    build_calculation_result_traces,
)
from capex3.core.teaching.solver_question_display import (
    threshold_questions_to_contract,
    threshold_solver_tolerance,
)


class CalculationResultTracesTest(unittest.TestCase):
    def test_build_calculation_result_traces_exposes_all_six_trace_ids(self) -> None:
        payload = calculate_payload({})
        traces = payload["result"]["traces"]

        self.assertEqual(
            set(traces.keys()),
            {
                "cashFlow",
                "repairDrivers",
                "repairFund",
                "tenYear",
                "whatWorks",
                "cashFlowStability",
            },
        )
        self.assertEqual(traces["cashFlow"]["id"], "cashFlow")
        self.assertEqual(traces["repairDrivers"]["id"], "repairDrivers")
        self.assertEqual(traces["repairFund"]["id"], "repairFund")
        self.assertEqual(traces["tenYear"]["id"], "tenYear")
        self.assertEqual(traces["whatWorks"]["id"], "whatWorks")
        self.assertEqual(traces["cashFlowStability"]["id"], "cashFlowStability")

    def test_repair_fund_trace_carries_app_regression_flags(self) -> None:
        trace = calculate_payload({})["result"]["traces"]["repairFund"]

        self.assertIs(trace["workbookCanonical"], False)
        self.assertIs(trace["appRegressionOnly"], True)
        self.assertEqual(
            trace["decisionId"],
            "repair_reserve_path_trace_workbook_vs_teaching",
        )
        self.assertNotIn("teachingOnly", trace)

    def test_what_works_question_count_matches_threshold_catalog(self) -> None:
        payload = calculate_payload({})
        what_works = payload["result"]["traces"]["whatWorks"]
        catalog = threshold_questions_to_contract()

        self.assertEqual(len(what_works["questions"]), len(catalog))

    def test_threshold_solver_tolerance_is_money_or_ratio_by_metric(self) -> None:
        self.assertEqual(threshold_solver_tolerance(metric="monthlyCashFlow"), 1.0)
        self.assertEqual(threshold_solver_tolerance(metric="firstEmergencyGap"), 1.0)
        self.assertEqual(threshold_solver_tolerance(metric="cashOnCashReturn"), 0.01)

    def test_cash_flow_trace_row_count_stable_on_defaults(self) -> None:
        payload = calculate_payload({})
        cash_flow = payload["result"]["traces"]["cashFlow"]

        self.assertEqual(len(cash_flow["rows"]), 8)

    def test_direct_builder_matches_calculate_payload_traces(self) -> None:
        payload = calculate_payload({})
        contract = dict(payload["result"])
        contract.pop("traces", None)

        direct = build_calculation_result_traces(
            contract,
            solver_variables=SOLVER_VARIABLES,
            model_spec=load_workbook_model_spec_record(),
        )

        self.assertEqual(direct, payload["result"]["traces"])
