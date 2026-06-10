from dataclasses import dataclass
from typing import Sequence


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
