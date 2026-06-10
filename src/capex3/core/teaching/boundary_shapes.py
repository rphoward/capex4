from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from .selected_scenario import (
    SUPPORTED_EVIDENCE_LAYER,
    SUPPORTED_EVALUATE_DEAL_INPUT_INTENT,
    SUPPORTED_EVALUATE_DEAL_RECEIPT_ACTION_ID,
    SUPPORTED_EVALUATE_DEAL_RECEIPT_SOURCE,
    SUPPORTED_EVALUATE_DEAL_RECEIPT_TRACE_IDS,
    SUPPORTED_EVALUATE_DEAL_REQUEST_INTENT,
    SUPPORTED_EVALUATE_DEAL_WORKBOOK_SOURCE_INTENT,
    SUPPORTED_TEACHING_STEP,
    SUPPORTED_THRESHOLD_QUESTION,
)
from .solver_question_boundary import (
    SolverQuestionRequest,
    selected_solver_question_request,
    selected_solver_question_request_to_contract,
)


@dataclass(frozen=True)
class TeachingDisplayPlanRequest:
    teaching_step: str
    threshold_question: str

    def __post_init__(self) -> None:
        if not isinstance(self.teaching_step, str) or not self.teaching_step:
            raise TeachingDisplayPlanError(
                "Teaching Display Plan request requires a teaching step."
            )

        if not isinstance(self.threshold_question, str) or not self.threshold_question:
            raise TeachingDisplayPlanError(
                "Teaching Display Plan request requires a threshold question."
            )


class TeachingDisplayPlanError(ValueError):
    pass


class EvaluateDealRequestError(ValueError):
    pass


class EvaluateDealReceiptError(ValueError):
    pass


@dataclass(frozen=True)
class EvaluateDealRequest:
    request_intent: str
    input_intent: str
    workbook_source_intent: str

    def __post_init__(self) -> None:
        if not isinstance(self.request_intent, str) or not self.request_intent:
            raise EvaluateDealRequestError(
                "Evaluate-deal request requires a request intent."
            )

        if not isinstance(self.input_intent, str) or not self.input_intent:
            raise EvaluateDealRequestError(
                "Evaluate-deal request requires an input intent."
            )

        if (
            not isinstance(self.workbook_source_intent, str)
            or not self.workbook_source_intent
        ):
            raise EvaluateDealRequestError(
                "Evaluate-deal request requires a workbook-source intent."
            )


@dataclass(frozen=True)
class EvaluateDealRequestContract:
    request: EvaluateDealRequest

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "requestIntent": self.request.request_intent,
            "inputIntent": self.request.input_intent,
            "workbookSourceIntent": self.request.workbook_source_intent,
            "status": "accepted",
        }


@dataclass(frozen=True)
class EvaluateDealReceiptContract:
    action_id: str
    result_source: str
    trace_ids: Sequence[str]

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "status": "accepted",
            "actionId": self.action_id,
            "resultSource": self.result_source,
            "traceReferences": [{"id": trace_id} for trace_id in self.trace_ids],
        }


@dataclass(frozen=True)
class TeachingStep:
    id: str
    title: str


@dataclass(frozen=True)
class SolverTarget:
    variable: str
    metric: str
    target_value: int


@dataclass(frozen=True)
class ThresholdQuestion:
    id: str
    title: str
    prompt: str
    solver: SolverTarget
    solved_value_kind: str
    solved_metric_kind: str
    workbench: bool


@dataclass(frozen=True)
class DisplayValue:
    label: str
    value: object
    kind: str
    note: str


@dataclass(frozen=True)
class ReceiptReference:
    id: str


@dataclass(frozen=True)
class PresentationDisplayField:
    id: str
    label: str
    kind: str
    trace_section: str
    value_role: str

    def __post_init__(self) -> None:
        _require_non_empty_contract_text(self.id, "display field id")
        _require_non_empty_contract_text(self.label, "display field label")
        _require_non_empty_contract_text(self.kind, "display field kind")
        _require_non_empty_contract_text(
            self.trace_section, "display field trace section"
        )
        _require_non_empty_contract_text(self.value_role, "display field value role")


@dataclass(frozen=True)
class PresentationEvidenceReference:
    id: str
    evidence_layer: str
    receipt_role: str

    def __post_init__(self) -> None:
        _require_non_empty_contract_text(self.id, "evidence reference id")
        _require_non_empty_contract_text(
            self.evidence_layer, "evidence reference layer"
        )
        _require_non_empty_contract_text(
            self.receipt_role, "evidence reference role"
        )


@dataclass(frozen=True)
class PresentationNextAction:
    id: str
    label: str
    question_id: str
    action_kind: str
    solver_variable: str
    solver_metric: str
    solver_target_value: int | float

    def __post_init__(self) -> None:
        _require_non_empty_contract_text(self.id, "next action id")
        _require_non_empty_contract_text(self.label, "next action label")
        _require_non_empty_contract_text(self.question_id, "next action question id")
        _require_non_empty_contract_text(self.action_kind, "next action kind")
        _require_non_empty_contract_text(
            self.solver_variable, "next action solver variable"
        )
        _require_non_empty_contract_text(
            self.solver_metric, "next action solver metric"
        )
        if not isinstance(self.solver_target_value, (int, float)):
            raise TeachingDisplayPlanError(
                "Presentation contract next action requires a solver target value."
            )


@dataclass(frozen=True)
class PresentationSection:
    id: str
    title: str
    section_role: str
    display_fields: Sequence[PresentationDisplayField]
    evidence_references: Sequence[PresentationEvidenceReference]
    next_actions: Sequence[PresentationNextAction]

    def __post_init__(self) -> None:
        _require_non_empty_contract_text(self.id, "presentation section id")
        _require_non_empty_contract_text(self.title, "presentation section title")
        _require_non_empty_contract_text(self.section_role, "presentation section role")
        _require_sequence(self.display_fields, "presentation display fields")
        _require_sequence(self.evidence_references, "presentation evidence references")
        _require_sequence(self.next_actions, "presentation next actions")


@dataclass(frozen=True)
class WhatWorksPresentationContract:
    teaching_step: str
    evidence_layer: str
    threshold_question: ThresholdQuestion
    sections: Sequence[PresentationSection]

    def __post_init__(self) -> None:
        _require_non_empty_contract_text(self.teaching_step, "teaching step")
        _require_non_empty_contract_text(self.evidence_layer, "evidence layer")
        if not isinstance(self.threshold_question, ThresholdQuestion):
            raise TeachingDisplayPlanError(
                "Presentation contract requires threshold question metadata."
            )
        _require_sequence(self.sections, "presentation sections")

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "teachingStep": self.teaching_step,
            "evidenceLayer": self.evidence_layer,
            "thresholdQuestion": {
                "id": self.threshold_question.id,
                "title": self.threshold_question.title,
                "prompt": self.threshold_question.prompt,
                "solver": {
                    "variable": self.threshold_question.solver.variable,
                    "metric": self.threshold_question.solver.metric,
                    "targetValue": self.threshold_question.solver.target_value,
                },
                "solvedValueKind": self.threshold_question.solved_value_kind,
                "solvedMetricKind": self.threshold_question.solved_metric_kind,
                "workbench": self.threshold_question.workbench,
            },
            "sections": [
                {
                    "id": section.id,
                    "title": section.title,
                    "sectionRole": section.section_role,
                    "displayFields": [
                        {
                            "id": field.id,
                            "label": field.label,
                            "kind": field.kind,
                            "traceSection": field.trace_section,
                            "valueRole": field.value_role,
                        }
                        for field in section.display_fields
                    ],
                    "evidenceReferences": [
                        {
                            "id": reference.id,
                            "evidenceLayer": reference.evidence_layer,
                            "receiptRole": reference.receipt_role,
                        }
                        for reference in section.evidence_references
                    ],
                    "nextActions": [
                        {
                            "id": action.id,
                            "label": action.label,
                            "questionId": action.question_id,
                            "actionKind": action.action_kind,
                            "solverRequest": {
                                "variable": action.solver_variable,
                                "metric": action.solver_metric,
                                "targetValue": action.solver_target_value,
                            },
                        }
                        for action in section.next_actions
                    ],
                }
                for section in self.sections
            ],
        }


@dataclass(frozen=True)
class NextSafeUserAction:
    id: str
    label: str
    solver_question_request: SolverQuestionRequest

    def __post_init__(self) -> None:
        selected_solver_question_request_to_contract(self.solver_question_request)

    @property
    def question_id(self) -> str:
        return self.solver_question_request.question_id


@dataclass(frozen=True)
class TeachingDisplayPlan:
    teaching_step: TeachingStep
    evidence_layer: str
    explanation_group: str
    threshold_question: ThresholdQuestion
    display_values: Sequence[DisplayValue]
    receipt_references: Sequence[ReceiptReference]
    supported_user_decision: str
    next_safe_user_action: NextSafeUserAction

    def to_contract_dict(self) -> dict[str, object]:
        return {
            "teachingStep": asdict(self.teaching_step),
            "evidenceLayer": self.evidence_layer,
            "explanationGroup": self.explanation_group,
            "thresholdQuestion": {
                "id": self.threshold_question.id,
                "title": self.threshold_question.title,
                "prompt": self.threshold_question.prompt,
                "solver": {
                    "variable": self.threshold_question.solver.variable,
                    "metric": self.threshold_question.solver.metric,
                    "targetValue": self.threshold_question.solver.target_value,
                },
                "solvedValueKind": self.threshold_question.solved_value_kind,
                "solvedMetricKind": self.threshold_question.solved_metric_kind,
                "workbench": self.threshold_question.workbench,
            },
            "displayValues": [asdict(value) for value in self.display_values],
            "receiptReferences": [
                asdict(reference) for reference in self.receipt_references
            ],
            "supportedUserDecision": self.supported_user_decision,
            "nextSafeUserAction": {
                "id": self.next_safe_user_action.id,
                "label": self.next_safe_user_action.label,
                "questionId": self.next_safe_user_action.question_id,
            },
        }


def selected_teaching_display_plan_request() -> TeachingDisplayPlanRequest:
    """Build the only reviewed application request for this phase."""

    return TeachingDisplayPlanRequest(
        teaching_step=SUPPORTED_TEACHING_STEP,
        threshold_question=SUPPORTED_THRESHOLD_QUESTION,
    )


def selected_evaluate_deal_request() -> EvaluateDealRequest:
    return EvaluateDealRequest(
        request_intent=SUPPORTED_EVALUATE_DEAL_REQUEST_INTENT,
        input_intent=SUPPORTED_EVALUATE_DEAL_INPUT_INTENT,
        workbook_source_intent=SUPPORTED_EVALUATE_DEAL_WORKBOOK_SOURCE_INTENT,
    )


def describe_evaluate_deal_request(
    request: EvaluateDealRequest,
) -> EvaluateDealRequestContract:
    _require_evaluate_deal_request(request)
    _require_supported_evaluate_deal_request_intent(request)
    _require_supported_evaluate_deal_input_intent(request)
    _require_supported_evaluate_deal_workbook_source_intent(request)

    return EvaluateDealRequestContract(request=request)


def selected_evaluate_deal_request_to_contract() -> dict[str, object]:
    return describe_evaluate_deal_request(
        selected_evaluate_deal_request()
    ).to_contract_dict()


def describe_evaluate_deal_receipt(
    receipt: Mapping[str, object],
) -> EvaluateDealReceiptContract:
    _require_evaluate_deal_receipt_mapping(receipt)
    _require_supported_evaluate_deal_receipt_ok(receipt)
    _require_supported_evaluate_deal_receipt_action_id(receipt)
    _require_supported_evaluate_deal_receipt_traces(receipt)

    return EvaluateDealReceiptContract(
        action_id=SUPPORTED_EVALUATE_DEAL_RECEIPT_ACTION_ID,
        result_source=SUPPORTED_EVALUATE_DEAL_RECEIPT_SOURCE,
        trace_ids=SUPPORTED_EVALUATE_DEAL_RECEIPT_TRACE_IDS,
    )


def selected_evaluate_deal_receipt_to_contract(
    receipt: Mapping[str, object],
) -> dict[str, object]:
    return describe_evaluate_deal_receipt(receipt).to_contract_dict()


def selected_what_works_presentation_contract_to_contract() -> dict[str, object]:
    return create_what_works_presentation_contract(
        selected_teaching_display_plan_request()
    ).to_contract_dict()


def create_what_works_presentation_contract(
    request: TeachingDisplayPlanRequest,
) -> WhatWorksPresentationContract:
    _require_selected_scenario(request)

    return WhatWorksPresentationContract(
        teaching_step=SUPPORTED_TEACHING_STEP,
        evidence_layer=SUPPORTED_EVIDENCE_LAYER,
        threshold_question=ThresholdQuestion(
            id="breakEvenRent",
            title="Break-even rent",
            prompt="What rent would make monthly cash flow hit zero?",
            solver=SolverTarget(
                variable="rent",
                metric="monthlyCashFlow",
                target_value=0,
            ),
            solved_value_kind="moneyCents",
            solved_metric_kind="moneyCents",
            workbench=True,
        ),
        sections=(
            PresentationSection(
                id="whatWorksThresholdQuestion",
                title="Break-even rent",
                section_role=(
                    "Renderer-safe description of the selected threshold "
                    "question card."
                ),
                display_fields=(
                    PresentationDisplayField(
                        id="currentCashFlow",
                        label="Current cash flow",
                        kind="moneyCents",
                        trace_section="summary",
                        value_role="currentMetricBeforeThresholdQuestion",
                    ),
                    PresentationDisplayField(
                        id="cashNeededUpFront",
                        label="Cash needed up front",
                        kind="money",
                        trace_section="summary",
                        value_role="initialInvestmentContext",
                    ),
                ),
                evidence_references=(
                    PresentationEvidenceReference(
                        id="solverMonthlyCashFlowMetricPath",
                        evidence_layer=SUPPORTED_EVIDENCE_LAYER,
                        receipt_role="solverMetricPath",
                    ),
                    PresentationEvidenceReference(
                        id="solverBreakevenGrossRentMetricPath",
                        evidence_layer=SUPPORTED_EVIDENCE_LAYER,
                        receipt_role="solverMetricPath",
                    ),
                ),
                next_actions=(
                    PresentationNextAction(
                        id="runThresholdQuestion",
                        label="Run the break-even rent question",
                        question_id=SUPPORTED_THRESHOLD_QUESTION,
                        action_kind="askSelectedThresholdQuestion",
                        solver_variable="rent",
                        solver_metric="monthlyCashFlow",
                        solver_target_value=0,
                    ),
                ),
            ),
        ),
    )


def _require_evaluate_deal_request(request: EvaluateDealRequest) -> None:
    if not isinstance(request, EvaluateDealRequest):
        raise EvaluateDealRequestError(
            "Evaluate-deal boundary requires an EvaluateDealRequest."
        )


def _require_supported_evaluate_deal_request_intent(
    request: EvaluateDealRequest,
) -> None:
    if request.request_intent != SUPPORTED_EVALUATE_DEAL_REQUEST_INTENT:
        raise EvaluateDealRequestError(
            f"Unsupported evaluate-deal request intent: {request.request_intent}"
        )


def _require_supported_evaluate_deal_input_intent(
    request: EvaluateDealRequest,
) -> None:
    if request.input_intent != SUPPORTED_EVALUATE_DEAL_INPUT_INTENT:
        raise EvaluateDealRequestError(
            f"Unsupported evaluate-deal input intent: {request.input_intent}"
        )


def _require_supported_evaluate_deal_workbook_source_intent(
    request: EvaluateDealRequest,
) -> None:
    if (
        request.workbook_source_intent
        != SUPPORTED_EVALUATE_DEAL_WORKBOOK_SOURCE_INTENT
    ):
        raise EvaluateDealRequestError(
            "Unsupported evaluate-deal workbook-source intent: "
            f"{request.workbook_source_intent}"
        )


def _require_evaluate_deal_receipt_mapping(
    receipt: Mapping[str, object],
) -> None:
    if not isinstance(receipt, Mapping):
        raise EvaluateDealReceiptError(
            "Evaluate-deal receipt boundary requires a mapping."
        )


def _require_supported_evaluate_deal_receipt_ok(
    receipt: Mapping[str, object],
) -> None:
    if receipt.get("ok") is not True:
        raise EvaluateDealReceiptError(
            "Evaluate-deal receipt requires ok status from JavaScript."
        )


def _require_supported_evaluate_deal_receipt_action_id(
    receipt: Mapping[str, object],
) -> None:
    if receipt.get("actionId") != SUPPORTED_EVALUATE_DEAL_RECEIPT_ACTION_ID:
        raise EvaluateDealReceiptError(
            "Unsupported evaluate-deal receipt action id: "
            f"{receipt.get('actionId')}"
        )


def _require_supported_evaluate_deal_receipt_traces(
    receipt: Mapping[str, object],
) -> None:
    result = receipt.get("result")
    if not isinstance(result, Mapping):
        raise EvaluateDealReceiptError(
            "Evaluate-deal receipt requires a result mapping."
        )

    traces = result.get("traces")
    if not isinstance(traces, Mapping):
        raise EvaluateDealReceiptError(
            "Evaluate-deal receipt requires trace metadata."
        )

    for trace_id in SUPPORTED_EVALUATE_DEAL_RECEIPT_TRACE_IDS:
        trace = traces.get(trace_id)
        if not isinstance(trace, Mapping) or trace.get("id") != trace_id:
            raise EvaluateDealReceiptError(
                f"Evaluate-deal receipt missing trace metadata: {trace_id}"
            )


def _require_teaching_display_plan_request(
    request: TeachingDisplayPlanRequest,
) -> None:
    if not isinstance(request, TeachingDisplayPlanRequest):
        raise TeachingDisplayPlanError(
            "Teaching Display Plan requires a TeachingDisplayPlanRequest."
        )


def _require_supported_teaching_step(request: TeachingDisplayPlanRequest) -> None:
    if request.teaching_step != SUPPORTED_TEACHING_STEP:
        raise TeachingDisplayPlanError(
            f"Unsupported Teaching Display Plan scenario: {request.teaching_step}"
        )


def _require_supported_threshold_question(
    request: TeachingDisplayPlanRequest,
) -> None:
    if request.threshold_question != SUPPORTED_THRESHOLD_QUESTION:
        raise TeachingDisplayPlanError(
            "Unsupported Teaching Display Plan threshold question: "
            f"{request.threshold_question}"
        )


def _require_selected_scenario(request: TeachingDisplayPlanRequest) -> None:
    _require_teaching_display_plan_request(request)
    _require_supported_teaching_step(request)
    _require_supported_threshold_question(request)


def _require_non_empty_contract_text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise TeachingDisplayPlanError(
            f"Presentation contract requires a {name}."
        )


def _require_sequence(value: object, name: str) -> None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TeachingDisplayPlanError(
            f"Presentation contract requires {name}."
        )


def create_teaching_display_plan(
    request: TeachingDisplayPlanRequest,
    evidence: Mapping[str, object],
) -> TeachingDisplayPlan:
    _require_selected_scenario(request)
    next_action_request = selected_solver_question_request(request.threshold_question)

    return TeachingDisplayPlan(
        teaching_step=TeachingStep(id="decision", title="Decision Packet"),
        evidence_layer=SUPPORTED_EVIDENCE_LAYER,
        explanation_group=(
            "Threshold questions that test what would need to change before the "
            "buyer chases the deal further."
        ),
        threshold_question=ThresholdQuestion(
            id="breakEvenRent",
            title="Break-even rent",
            prompt="What rent would make monthly cash flow hit zero?",
            solver=SolverTarget(
                variable="rent",
                metric="monthlyCashFlow",
                target_value=0,
            ),
            solved_value_kind="moneyCents",
            solved_metric_kind="moneyCents",
            workbench=True,
        ),
        display_values=[
            DisplayValue(
                label="Current cash flow",
                value=-117.47631339454142,
                kind="moneyCents",
                note="Before running a threshold question.",
            ),
            DisplayValue(
                label="Cash needed up front",
                value=68750,
                kind="money",
                note="Purchase cash, closing costs, and make-ready.",
            ),
        ],
        receipt_references=[
            ReceiptReference(id="solverMonthlyCashFlowMetricPath"),
            ReceiptReference(id="solverCashOnCashMetricPath"),
            ReceiptReference(id="solverYear10RoiMetricPath"),
            ReceiptReference(id="solverYear10AnnualizedRoiMetricPath"),
            ReceiptReference(id="solverDscrMetricPath"),
            ReceiptReference(id="solverYearOneReturnOnEquityMetricPath"),
            ReceiptReference(id="solverBreakevenGrossRentMetricPath"),
            ReceiptReference(id="solverRentToValueMetricPath"),
        ],
        supported_user_decision=(
            "Decide whether the rent required to break even is plausible enough "
            "to keep investigating the deal."
        ),
        next_safe_user_action=NextSafeUserAction(
            id="runThresholdQuestion",
            label="Run the break-even rent question",
            solver_question_request=next_action_request,
        ),
    )
