"""Display copy for solver questions; numeric targets live in capex3.core."""

from typing import Mapping

from capex3.core.solver_question_catalog import list_selected_solver_questions

# App-side threshold/manual solver previews — not fixture-parity bisection precision.
MONEY_VALUE_KINDS = frozenset({"money", "moneyCents"})
THRESHOLD_SOLVER_MONEY_TOLERANCE = 1.0
THRESHOLD_SOLVER_RATIO_TOLERANCE = 0.01

SOLVER_METRIC_VALUE_KINDS: Mapping[str, str] = {
    "monthlyCashFlow": "moneyCents",
    "cashOnCashReturn": "percent",
    "year10Roi": "percent",
    "year10AnnualizedRoi": "percent",
    "firstEmergencyGap": "money",
}


def threshold_solver_tolerance(
    *,
    metric: str | None = None,
    value_kind: str | None = None,
) -> float:
    resolved_kind = value_kind or SOLVER_METRIC_VALUE_KINDS.get(str(metric or ""), "")
    if resolved_kind in MONEY_VALUE_KINDS:
        return THRESHOLD_SOLVER_MONEY_TOLERANCE
    return THRESHOLD_SOLVER_RATIO_TOLERANCE

SOLVER_QUESTION_DISPLAY: Mapping[str, dict[str, str]] = {
    "breakEvenRent": {
        "title": "Break-even rent",
        "prompt": "What rent would make monthly cash flow hit zero?",
    },
    "maxPurchasePriceCashFlowZero": {
        "title": "Max purchase price",
        "prompt": (
            "What purchase price would make monthly cash flow hit zero with the "
            "default down payment percent?"
        ),
    },
    "requiredDownPaymentCashFlowZero": {
        "title": "Needed down payment",
        "prompt": (
            "What down payment would make monthly cash flow hit zero at the current "
            "purchase price?"
        ),
    },
    "maxRehabBudgetCashOnCash8Pct": {
        "title": "Rehab room",
        "prompt": (
            "What rehab budget still leaves the deal at an 8% cash-on-cash return?"
        ),
    },
    "reserveIncreaseFirstShortfall": {
        "title": "Reserve bump for first shortfall",
        "prompt": (
            "What monthly reserve increase clears the first unfunded emergency repair?"
        ),
    },
}


def threshold_questions_to_contract() -> list[dict[str, object]]:
    questions: list[dict[str, object]] = []
    for question in list_selected_solver_questions():
        display = SOLVER_QUESTION_DISPLAY[question.id]
        merged: dict[str, object] = {
            "id": question.id,
            "title": display["title"],
            "prompt": display["prompt"],
            "solver": question.solver.to_contract_dict(),
            "solvedValueKind": question.solved_value_kind,
            "solvedMetricKind": question.solved_metric_kind,
            "workbench": question.workbench,
        }
        if question.offer_ready:
            merged["offerReady"] = True
        questions.append(merged)
    return questions
