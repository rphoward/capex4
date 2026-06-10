import unittest
from copy import deepcopy

from capex3.core.solver_question_catalog import list_selected_solver_questions
from capex3.presentation.http_contracts import workbench_payload
from capex3.core.teaching.solver_question_display import (
    SOLVER_QUESTION_DISPLAY,
    threshold_questions_to_contract,
)

EXPECTED_QUESTION_IDS = (
    "breakEvenRent",
    "maxPurchasePriceCashFlowZero",
    "requiredDownPaymentCashFlowZero",
    "maxRehabBudgetCashOnCash8Pct",
    "reserveIncreaseFirstShortfall",
)

BREAK_EVEN_RENT_GOLDEN = {
    "id": "breakEvenRent",
    "title": "Break-even rent",
    "prompt": "What rent would make monthly cash flow hit zero?",
    "solver": {"variable": "rent", "metric": "monthlyCashFlow", "targetValue": 0},
    "solvedValueKind": "moneyCents",
    "solvedMetricKind": "moneyCents",
    "workbench": True,
}

RESERVE_INCREASE_GOLDEN = {
    "id": "reserveIncreaseFirstShortfall",
    "title": "Reserve bump for first shortfall",
    "prompt": (
        "What monthly reserve increase clears the first unfunded emergency repair?"
    ),
    "solver": {
        "variable": "monthlyReserveIncrease",
        "metric": "firstEmergencyGap",
        "targetValue": 0,
        "solverKind": "reserveFirstShortfall",
    },
    "solvedValueKind": "moneyCents",
    "solvedMetricKind": "money",
    "workbench": False,
    "offerReady": True,
}


class SolverQuestionCatalogTests(unittest.TestCase):
    def test_core_catalog_has_five_questions(self) -> None:
        questions = list_selected_solver_questions()
        self.assertEqual(len(questions), 5)
        self.assertEqual(tuple(question.id for question in questions), EXPECTED_QUESTION_IDS)

    def test_reserve_increase_first_shortfall_core_flags(self) -> None:
        question = next(
            question
            for question in list_selected_solver_questions()
            if question.id == "reserveIncreaseFirstShortfall"
        )
        self.assertEqual(question.solver.solver_kind, "reserveFirstShortfall")
        self.assertTrue(question.offer_ready)
        self.assertFalse(question.workbench)

    def test_teaching_merge_includes_display_copy_for_all_five(self) -> None:
        merged = threshold_questions_to_contract()
        self.assertEqual(len(merged), 5)
        for question in merged:
            question_id = str(question["id"])
            self.assertIn(question_id, SOLVER_QUESTION_DISPLAY)
            self.assertEqual(question["title"], SOLVER_QUESTION_DISPLAY[question_id]["title"])
            self.assertEqual(question["prompt"], SOLVER_QUESTION_DISPLAY[question_id]["prompt"])

    def test_teaching_merge_reserve_increase_matches_baseline(self) -> None:
        merged = next(
            question
            for question in threshold_questions_to_contract()
            if question["id"] == "reserveIncreaseFirstShortfall"
        )
        self.assertEqual(merged, RESERVE_INCREASE_GOLDEN)

    def test_teaching_merge_break_even_rent_golden_snapshot(self) -> None:
        merged = next(
            question
            for question in threshold_questions_to_contract()
            if question["id"] == "breakEvenRent"
        )
        self.assertEqual(merged, BREAK_EVEN_RENT_GOLDEN)

    def test_workbench_payload_threshold_question_ids_unchanged(self) -> None:
        payload = workbench_payload()["workbench"]
        threshold_ids = [question["id"] for question in payload["thresholdQuestions"]]
        workbench_ids = [
            question["id"] for question in payload["workbenchThresholdQuestions"]
        ]
        self.assertEqual(threshold_ids, list(EXPECTED_QUESTION_IDS))
        self.assertEqual(workbench_ids, list(EXPECTED_QUESTION_IDS))
        self.assertEqual(
            deepcopy(payload["thresholdQuestions"]),
            threshold_questions_to_contract(),
        )


if __name__ == "__main__":
    unittest.main()
