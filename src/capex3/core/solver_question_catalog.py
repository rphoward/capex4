from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class SolverQuestionTarget:
    variable: str
    metric: str
    target_value: int | float
    solver_kind: str | None = None

    def to_contract_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "variable": self.variable,
            "metric": self.metric,
            "targetValue": self.target_value,
        }
        if self.solver_kind is not None:
            payload["solverKind"] = self.solver_kind
        return payload


@dataclass(frozen=True)
class SelectedSolverQuestion:
    id: str
    solver: SolverQuestionTarget
    solved_value_kind: str
    solved_metric_kind: str
    workbench: bool
    offer_ready: bool = False

    def to_contract_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "solver": self.solver.to_contract_dict(),
            "solvedValueKind": self.solved_value_kind,
            "solvedMetricKind": self.solved_metric_kind,
            "workbench": self.workbench,
        }
        if self.offer_ready:
            payload["offerReady"] = True
        return payload


SELECTED_SOLVER_QUESTIONS: Sequence[SelectedSolverQuestion] = (
    SelectedSolverQuestion(
        id="breakEvenRent",
        solver=SolverQuestionTarget(
            variable="rent",
            metric="monthlyCashFlow",
            target_value=0,
        ),
        solved_value_kind="moneyCents",
        solved_metric_kind="moneyCents",
        workbench=True,
    ),
    SelectedSolverQuestion(
        id="maxPurchasePriceCashFlowZero",
        solver=SolverQuestionTarget(
            variable="purchasePriceWithDefaultDownPayment",
            metric="monthlyCashFlow",
            target_value=0,
        ),
        solved_value_kind="moneyCents",
        solved_metric_kind="moneyCents",
        workbench=True,
    ),
    SelectedSolverQuestion(
        id="requiredDownPaymentCashFlowZero",
        solver=SolverQuestionTarget(
            variable="downPayment",
            metric="monthlyCashFlow",
            target_value=0,
        ),
        solved_value_kind="moneyCents",
        solved_metric_kind="moneyCents",
        workbench=True,
    ),
    SelectedSolverQuestion(
        id="maxRehabBudgetCashOnCash8Pct",
        solver=SolverQuestionTarget(
            variable="rehabBudget",
            metric="cashOnCashReturn",
            target_value=0.08,
        ),
        solved_value_kind="moneyCents",
        solved_metric_kind="percent",
        workbench=True,
    ),
    SelectedSolverQuestion(
        id="reserveIncreaseFirstShortfall",
        solver=SolverQuestionTarget(
            variable="monthlyReserveIncrease",
            metric="firstEmergencyGap",
            target_value=0,
            solver_kind="reserveFirstShortfall",
        ),
        solved_value_kind="moneyCents",
        solved_metric_kind="money",
        workbench=False,
        offer_ready=True,
    ),
)


def list_selected_solver_questions() -> Sequence[SelectedSolverQuestion]:
    return SELECTED_SOLVER_QUESTIONS


def selected_solver_question_catalog_to_contract() -> list[dict[str, object]]:
    return [question.to_contract_dict() for question in SELECTED_SOLVER_QUESTIONS]


SOLVER_QUESTION_CATALOG = SELECTED_SOLVER_QUESTIONS

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

SOLVER_QUESTION_DISPLAY: Mapping[str, dict[str, str]] = {
    "breakEvenRent": {
        "title": "Break-even rent",
        "prompt": "What rent would make monthly cash flow hit zero?",
        "gapBaseline": "current rent",
    },
    "maxPurchasePriceCashFlowZero": {
        "title": "Max purchase price",
        "prompt": (
            "What purchase price would make monthly cash flow hit zero with the "
            "default down payment percent?"
        ),
        "gapBaseline": "current price",
    },
    "requiredDownPaymentCashFlowZero": {
        "title": "Needed down payment",
        "prompt": (
            "What down payment would make monthly cash flow hit zero at the current "
            "purchase price?"
        ),
        "gapBaseline": "current down payment",
    },
    "maxRehabBudgetCashOnCash8Pct": {
        "title": "Rehab room",
        "prompt": (
            "What rehab budget still leaves the deal at an 8% cash-on-cash return?"
        ),
        "gapBaseline": "current rehab estimate",
    },
    "reserveIncreaseFirstShortfall": {
        "title": "Reserve bump for first shortfall",
        "prompt": (
            "What monthly reserve increase clears the first unfunded emergency repair?"
        ),
        "gapBaseline": "current reserve",
    },
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


def threshold_questions_to_contract() -> list[dict[str, object]]:
    questions: list[dict[str, object]] = []
    for question in list_selected_solver_questions():
        display = SOLVER_QUESTION_DISPLAY[question.id]
        merged: dict[str, object] = {
            "id": question.id,
            "title": display["title"],
            "prompt": display["prompt"],
            "gapBaseline": display.get("gapBaseline", "current input"),
            "solver": question.solver.to_contract_dict(),
            "solvedValueKind": question.solved_value_kind,
            "solvedMetricKind": question.solved_metric_kind,
            "workbench": question.workbench,
        }
        if question.offer_ready:
            merged["offerReady"] = True
        questions.append(merged)
    return questions


_SOLVER_REQUEST_KEYS = frozenset(
    {
        "baseInput",
        "variable",
        "metric",
        "targetValue",
        "lowerBound",
        "upperBound",
        "tolerance",
        "maxIterations",
    }
)


def threshold_solver_request_dict(
    question: Mapping[str, object],
    *,
    base_input: Mapping[str, object],
) -> dict[str, object]:
    solver_config = dict(question.get("solver", {}))
    return {
        key: value
        for key, value in {
            **solver_config,
            "baseInput": dict(base_input),
            "tolerance": threshold_solver_tolerance(
                metric=str(solver_config.get("metric") or ""),
            ),
        }.items()
        if key in _SOLVER_REQUEST_KEYS
    }
