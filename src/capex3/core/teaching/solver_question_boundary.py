from dataclasses import dataclass
from typing import Mapping, Sequence

from .selected_scenario import (
    SUPPORTED_SOLVED_VALUE_APPLY_ACTION_ID,
    SUPPORTED_SOLVED_VALUE_APPLY_INPUT_FIELD,
    SUPPORTED_SOLVED_VALUE_APPLY_RESULT_STATUS,
    SUPPORTED_SOLVED_VALUE_APPLY_SOURCE,
    SUPPORTED_SOLVED_VALUE_APPLY_VARIABLE,
    SUPPORTED_SOLVER_RECEIPT_ACTION_ID,
    SUPPORTED_SOLVER_RECEIPT_METRIC,
    SUPPORTED_SOLVER_RECEIPT_QUESTION_ID,
    SUPPORTED_SOLVER_RECEIPT_SOURCE,
    SUPPORTED_SOLVER_RECEIPT_TARGET_VALUE,
    SUPPORTED_SOLVER_RECEIPT_TRACE_IDS,
    SUPPORTED_SOLVER_RECEIPT_VARIABLE,
)
from .solver_question_catalog import (
    SelectedSolverQuestion,
    list_selected_solver_questions,
)


class SolverQuestionRequestError(ValueError):
    pass


class SolverReceiptError(ValueError):
    pass


class SolvedValueApplyPlanError(ValueError):
    pass


@dataclass(frozen=True)
class SolverQuestionRequest:
    question_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.question_id, str) or not self.question_id:
            raise SolverQuestionRequestError(
                "Solver question request requires a question id."
            )


@dataclass(frozen=True)
class SolverQuestionResponse:
    question: SelectedSolverQuestion

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "question": self.question.to_contract_dict(),
            "status": "accepted",
        }


@dataclass(frozen=True)
class SolverReceiptContract:
    action_id: str
    question_id: str
    variable: str
    metric: str
    target_value: int | float
    result_source: str
    trace_ids: Sequence[str]

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "status": "accepted",
            "actionId": self.action_id,
            "questionId": self.question_id,
            "solverRequest": {
                "variable": self.variable,
                "metric": self.metric,
                "targetValue": self.target_value,
            },
            "resultSource": self.result_source,
            "resultStatus": "ok",
            "traceReferences": [{"id": trace_id} for trace_id in self.trace_ids],
        }


@dataclass(frozen=True)
class SolvedValueApplyPlanContract:
    action_id: str
    variable: str
    input_field: str
    result_source: str
    required_solver_result_status: str

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "status": "accepted",
            "actionId": self.action_id,
            "solverRequest": {
                "variable": self.variable,
            },
            "inputField": self.input_field,
            "resultSource": self.result_source,
            "requiredSolverResultStatus": self.required_solver_result_status,
        }


def selected_solver_question_request(question_id: str) -> SolverQuestionRequest:
    return SolverQuestionRequest(question_id=question_id)


def describe_solver_question_request(
    request: SolverQuestionRequest,
) -> SolverQuestionResponse:
    _require_solver_question_request(request)

    for question in list_selected_solver_questions():
        if question.id == request.question_id:
            return SolverQuestionResponse(question=question)

    raise SolverQuestionRequestError(
        f"Unsupported solver question: {request.question_id}"
    )


def selected_solver_question_request_to_contract(
    request: SolverQuestionRequest,
) -> dict[str, object]:
    return describe_solver_question_request(request).to_contract_dict()


def describe_solver_receipt(receipt: Mapping[str, object]) -> SolverReceiptContract:
    _require_solver_receipt_mapping(receipt)
    _require_supported_solver_receipt_command_status(receipt)
    _require_supported_solver_receipt_action_id(receipt)
    _require_supported_solver_receipt_question(receipt)
    _require_supported_solver_receipt_request(receipt)
    _require_supported_solver_receipt_result(receipt)

    return SolverReceiptContract(
        action_id=SUPPORTED_SOLVER_RECEIPT_ACTION_ID,
        question_id=SUPPORTED_SOLVER_RECEIPT_QUESTION_ID,
        variable=SUPPORTED_SOLVER_RECEIPT_VARIABLE,
        metric=SUPPORTED_SOLVER_RECEIPT_METRIC,
        target_value=SUPPORTED_SOLVER_RECEIPT_TARGET_VALUE,
        result_source=SUPPORTED_SOLVER_RECEIPT_SOURCE,
        trace_ids=SUPPORTED_SOLVER_RECEIPT_TRACE_IDS,
    )


def selected_solver_receipt_to_contract(
    receipt: Mapping[str, object],
) -> dict[str, object]:
    return describe_solver_receipt(receipt).to_contract_dict()


def describe_solved_value_apply_plan(
    plan: Mapping[str, object],
) -> SolvedValueApplyPlanContract:
    _require_solved_value_apply_plan_mapping(plan)
    _require_supported_solved_value_apply_action_id(plan)
    _require_supported_solved_value_apply_request(plan)
    _require_supported_solved_value_apply_result(plan)

    return SolvedValueApplyPlanContract(
        action_id=SUPPORTED_SOLVED_VALUE_APPLY_ACTION_ID,
        variable=SUPPORTED_SOLVED_VALUE_APPLY_VARIABLE,
        input_field=SUPPORTED_SOLVED_VALUE_APPLY_INPUT_FIELD,
        result_source=SUPPORTED_SOLVED_VALUE_APPLY_SOURCE,
        required_solver_result_status=SUPPORTED_SOLVED_VALUE_APPLY_RESULT_STATUS,
    )


def selected_solved_value_apply_plan_to_contract(
    plan: Mapping[str, object],
) -> dict[str, object]:
    return describe_solved_value_apply_plan(plan).to_contract_dict()


def _require_solver_question_request(request: SolverQuestionRequest) -> None:
    if not isinstance(request, SolverQuestionRequest):
        raise SolverQuestionRequestError(
            "Solver question boundary requires a SolverQuestionRequest."
        )


def _require_solver_receipt_mapping(receipt: Mapping[str, object]) -> None:
    if not isinstance(receipt, Mapping):
        raise SolverReceiptError("Solver receipt boundary requires a mapping.")


def _require_supported_solver_receipt_command_status(
    receipt: Mapping[str, object],
) -> None:
    if "ok" in receipt and receipt.get("ok") is not True:
        raise SolverReceiptError(
            "Solver receipt requires ok command status from JavaScript."
        )


def _require_supported_solver_receipt_action_id(
    receipt: Mapping[str, object],
) -> None:
    action_id = receipt.get("actionId")
    if action_id is not None and action_id != SUPPORTED_SOLVER_RECEIPT_ACTION_ID:
        raise SolverReceiptError(
            f"Unsupported solver receipt action id: {action_id}"
        )


def _require_supported_solver_receipt_question(
    receipt: Mapping[str, object],
) -> None:
    question = receipt.get("question")
    if not isinstance(question, Mapping):
        raise SolverReceiptError("Solver receipt requires question metadata.")

    if question.get("id") != SUPPORTED_SOLVER_RECEIPT_QUESTION_ID:
        raise SolverReceiptError(
            f"Unsupported solver receipt question: {question.get('id')}"
        )


def _require_supported_solver_receipt_request(
    receipt: Mapping[str, object],
) -> None:
    request = receipt.get("solverRequest")
    if not isinstance(request, Mapping):
        raise SolverReceiptError("Solver receipt requires solver request metadata.")

    if request.get("variable") != SUPPORTED_SOLVER_RECEIPT_VARIABLE:
        raise SolverReceiptError(
            f"Unsupported solver receipt variable: {request.get('variable')}"
        )

    if request.get("metric") != SUPPORTED_SOLVER_RECEIPT_METRIC:
        raise SolverReceiptError(
            f"Unsupported solver receipt metric: {request.get('metric')}"
        )

    if request.get("targetValue") != SUPPORTED_SOLVER_RECEIPT_TARGET_VALUE:
        raise SolverReceiptError(
            "Unsupported solver receipt target value: "
            f"{request.get('targetValue')}"
        )


def _require_supported_solver_receipt_result(
    receipt: Mapping[str, object],
) -> None:
    solver_result = receipt.get("result")
    if not isinstance(solver_result, Mapping):
        raise SolverReceiptError("Solver receipt requires result metadata.")

    if solver_result.get("ok") is not True:
        raise SolverReceiptError(
            "Solver receipt requires ok solver result from JavaScript."
        )

    result = solver_result.get("result")
    if not isinstance(result, Mapping):
        raise SolverReceiptError("Solver receipt requires solved result metadata.")

    traces = result.get("traces")
    if not isinstance(traces, Mapping):
        raise SolverReceiptError("Solver receipt requires solved trace metadata.")

    for trace_id in SUPPORTED_SOLVER_RECEIPT_TRACE_IDS:
        trace = traces.get(trace_id)
        if not isinstance(trace, Mapping) or trace.get("id") != trace_id:
            raise SolverReceiptError(
                f"Solver receipt missing trace metadata: {trace_id}"
            )


def _require_solved_value_apply_plan_mapping(plan: Mapping[str, object]) -> None:
    if not isinstance(plan, Mapping):
        raise SolvedValueApplyPlanError(
            "Solved-value apply plan boundary requires a mapping."
        )


def _require_supported_solved_value_apply_action_id(
    plan: Mapping[str, object],
) -> None:
    action_id = plan.get("actionId")
    if action_id is not None and action_id != SUPPORTED_SOLVED_VALUE_APPLY_ACTION_ID:
        raise SolvedValueApplyPlanError(
            f"Unsupported solved-value apply action id: {action_id}"
        )


def _require_supported_solved_value_apply_request(
    plan: Mapping[str, object],
) -> None:
    request = plan.get("solverRequest")
    if not isinstance(request, Mapping):
        raise SolvedValueApplyPlanError(
            "Solved-value apply plan requires solver request metadata."
        )

    if request.get("variable") != SUPPORTED_SOLVED_VALUE_APPLY_VARIABLE:
        raise SolvedValueApplyPlanError(
            f"Unsupported solved-value apply variable: {request.get('variable')}"
        )


def _require_supported_solved_value_apply_result(
    plan: Mapping[str, object],
) -> None:
    solver_result = plan.get("solverResult")
    if not isinstance(solver_result, Mapping):
        raise SolvedValueApplyPlanError(
            "Solved-value apply plan requires solver result metadata."
        )

    if solver_result.get("ok") is not True:
        raise SolvedValueApplyPlanError(
            "Solved-value apply plan requires ok solver result metadata."
        )
