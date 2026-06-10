"""Thin HTTP JSON adapters for rental CapEx workbench and calculator routes."""

from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from capex3.core.teaching.calculation_result_traces import (
    SOLVER_DISCLAIMER,
    build_calculation_result_traces,
)
from capex3.core.teaching.solver_question_display import (
    threshold_questions_to_contract,
    threshold_solver_tolerance,
)
from capex3.core.teaching.workbench_metadata import (
    CALCULATION_LINKAGE_FIELDS,
    EVIDENCE_CONCEPTS,
    EVIDENCE_METRIC_FIELDS,
    INPUT_FIELD_CONTROLS,
    JOURNEY_STAGES,
    METRIC_GUIDANCE,
    METRIC_SOURCE_NOTES,
    SOLVER_METRICS,
    SOLVER_VARIABLES,
    STAGE_EVIDENCE_MAPPING,
)
from capex3.infrastructure.workbook_assumptions import load_workbook_model_spec_record
from capex3.presentation.htmx_format import _parse_number, _parse_optional_number
from capex3.core.calculate_rental_capex import (
    RentalCapexCalculationRequest,
    RentalCapexCalculationResult,
    calculate_rental_capex,
)
from capex3.core.errors import RentalCapexError, VALIDATION_ERROR
from capex3.core.solve_rental_capex import (
    RentalCapexSolverRequest,
    solve_rental_capex,
)


def defaults_payload() -> dict[str, object]:
    model_spec = load_workbook_model_spec_record()
    assumptions = model_spec["assumptions"]
    return {
        "ok": True,
        "inputs": deepcopy(dict(model_spec["inputs"])),
        "assumptions": {
            "subregions": list(assumptions["subregions"]),
            "profiles": list(assumptions["profiles"]),
            "components": [
                {"name": component["name"], "lifespan": component["lifespan"]}
                for component in assumptions["components"]
            ],
        },
    }


def workbench_payload() -> dict[str, object]:
    return {
        "ok": True,
        "workbench": {
            "journeyStages": deepcopy(JOURNEY_STAGES),
            "evidenceConcepts": deepcopy(EVIDENCE_CONCEPTS),
            "stageEvidenceMapping": deepcopy(STAGE_EVIDENCE_MAPPING),
            "inputFields": [
                {"field": field, **deepcopy(metadata)}
                for field, metadata in INPUT_FIELD_CONTROLS.items()
            ],
            "thresholdQuestions": deepcopy(threshold_questions_to_contract()),
            "workbenchThresholdQuestions": deepcopy(threshold_questions_to_contract()),
            "solverVariables": deepcopy(SOLVER_VARIABLES),
            "solverMetrics": deepcopy(SOLVER_METRICS),
            "solverDisclaimer": deepcopy(SOLVER_DISCLAIMER),
            "metricGuidance": [
                {
                    "field": field,
                    "label": label,
                    "valueKind": value_kind,
                    "sourceNote": METRIC_SOURCE_NOTES.get(
                        field,
                        "This value comes from the Python calculator result.",
                    ),
                    "evidenceLayerId": evidence_layer_id,
                }
                for field, label, value_kind, evidence_layer_id in METRIC_GUIDANCE
            ],
            "evidenceMetricFields": deepcopy(EVIDENCE_METRIC_FIELDS),
            "calculationLinkageFields": [
                {
                    "workbookCell": workbook_cell,
                    "label": label,
                    "inputField": input_field,
                    "normalizedPath": normalized_path,
                    "outputPath": output_path,
                    "uiElement": ui_element,
                }
                for (
                    workbook_cell,
                    label,
                    input_field,
                    normalized_path,
                    output_path,
                    ui_element,
                ) in CALCULATION_LINKAGE_FIELDS
            ],
        },
    }


def calculate_payload(inputs: object | None) -> dict[str, object]:
    model_spec = load_workbook_model_spec_record()
    result = calculate_rental_capex(
        RentalCapexCalculationRequest.from_contract_dict(
            inputs if inputs is not None else {}
        ),
        model_spec=model_spec,
    )
    return {"ok": True, "result": result_with_traces(result)}


def solve_payload(request: object | None) -> tuple[int, dict[str, object]]:
    solver_request = _resolve_solver_request(request if request is not None else {})
    solver_request = {
        key: value
        for key, value in solver_request.items()
        if key
        in {
            "baseInput",
            "variable",
            "metric",
            "targetValue",
            "lowerBound",
            "upperBound",
            "tolerance",
            "maxIterations",
        }
    }
    result = solve_rental_capex(
        RentalCapexSolverRequest.from_contract_dict(solver_request),
        model_spec=load_workbook_model_spec_record(),
    )
    contract = result.to_contract_dict()
    return (200 if result.ok else 400, {"ok": result.ok, "result": contract})


def error_payload(error: Exception) -> tuple[int, dict[str, object]]:
    if isinstance(error, RentalCapexError):
        return (
            400,
            {
                "ok": False,
                "code": error.code,
                "message": str(error),
                "details": _json_safe(dict(error.details)),
            },
        )
    return (
        500,
        {
            "ok": False,
            "code": "SERVER_ERROR",
            "message": str(error) or "Python calculator request failed.",
        },
    )


def result_with_traces(result: RentalCapexCalculationResult) -> dict[str, object]:
    contract = result.to_contract_dict()
    contract["audit"] = {
        **dict(contract["audit"]),
        "sourceWorkbook": "rental-capex-model-v4-defaults.xlsx",
        "runtimeOwner": "python",
    }
    contract["traces"] = build_calculation_result_traces(
        contract,
        solver_variables=SOLVER_VARIABLES,
        model_spec=load_workbook_model_spec_record(),
    )
    return contract


def solver_preview_payload(
    *,
    form: Mapping[str, str],
    workbench: Mapping[str, object],
    inputs: Mapping[str, object],
    solver_variable: str,
    solver_metric: str,
    solver_target: str,
    solver_lower: str,
    solver_upper: str,
    threshold: bool,
    reserve_first_shortfall: bool = False,
) -> Mapping[str, object]:
    questions = {
        str(question.get("id")): question
        for question in workbench.get("thresholdQuestions", [])
        if question.get("id")
    }
    variables = {variable["id"]: variable for variable in _solver_variables(workbench)}
    metrics = {metric["id"]: metric for metric in _solver_metrics(workbench)}
    question_id = (
        "reserveIncreaseFirstShortfall"
        if reserve_first_shortfall
        else form.get("questionId", "")
    )
    question = questions.get(question_id) if threshold else None
    if question:
        solver_request = {**dict(question.get("solver", {})), "baseInput": dict(inputs)}
        metric_id = str(solver_request.get("metric") or solver_metric)
        request = {
            "questionId": question["id"],
            "baseInput": dict(inputs),
            "tolerance": threshold_solver_tolerance(metric=metric_id),
        }
        source = f"threshold:{question['id']}"
        variable_id = str(solver_request.get("variable") or solver_variable)
    else:
        metric_metadata = metrics.get(solver_metric, {})
        target = _parse_number(solver_target) or 0
        if metric_metadata.get("valueKind") == "percent" and abs(target) > 1:
            target = target / 100
        request = {
            "baseInput": dict(inputs),
            "variable": solver_variable,
            "metric": solver_metric,
            "targetValue": target,
            "tolerance": threshold_solver_tolerance(
                value_kind=str(metric_metadata.get("valueKind") or ""),
            ),
        }
        lower = _parse_optional_number(solver_lower)
        upper = _parse_optional_number(solver_upper)
        if lower is not None:
            request["lowerBound"] = lower
        if upper is not None:
            request["upperBound"] = upper
        solver_request = request
        source = "manual"
        variable_id = solver_variable
        metric_id = solver_metric

    try:
        _status, payload = solve_payload(request)
        solver_result = payload.get("result", {})
    except Exception as error:
        solver_result = {"ok": False, "message": str(error)}

    variable = variables.get(variable_id, {})
    metric = metrics.get(metric_id, {})
    apply_field = variable.get("applyField")
    return {
        "source": source,
        "ok": bool(solver_result.get("ok")),
        "solverResult": solver_result,
        "solverRequest": solver_request,
        "applyField": apply_field,
        "applyLabel": _input_fields_by_id(workbench).get(str(apply_field), {}).get(
            "label", apply_field
        ),
        "previousValue": inputs.get(str(apply_field)) if apply_field else None,
        "solvedValue": solver_result.get("solvedValue"),
        "solvedMetricValue": solver_result.get("solvedMetricValue"),
        "solvedValueKind": (question or {}).get("solvedValueKind")
        or variable.get("valueKind")
        or "number",
        "solvedMetricKind": (question or {}).get("solvedMetricKind")
        or metric.get("valueKind")
        or "moneyCents",
        "variableLabel": variable.get("previewLabel") or variable.get("label") or variable_id,
        "metricLabel": metric.get("label") or metric_id,
        "assumptionText": variable.get("assumptionText")
        or "Solved under the current input assumptions. Apply updates one input only.",
        "message": solver_result.get("message") or "The solver could not produce a preview.",
        "previewFootnote": SOLVER_DISCLAIMER["previewFootnote"],
    }


def _resolve_solver_request(request: object) -> dict[str, object]:
    if not isinstance(request, Mapping):
        raise RentalCapexError(
            VALIDATION_ERROR,
            "Solver request must be an object.",
            {"request": request},
        )

    if "questionId" not in request:
        return dict(request)

    question = next(
        (
            candidate
            for candidate in threshold_questions_to_contract()
            if candidate["id"] == request["questionId"]
        ),
        None,
    )
    if question is None:
        raise RentalCapexError(
            "UNKNOWN_THRESHOLD_QUESTION",
            f"Unknown threshold question: {request['questionId']}",
            {"questionId": request["questionId"]},
        )

    solver = dict(question["solver"])
    tolerance = request.get(
        "tolerance",
        threshold_solver_tolerance(metric=str(solver.get("metric") or "")),
    )
    return {
        **solver,
        "baseInput": request.get("baseInput", {}),
        "tolerance": tolerance,
    }


def _solver_variables(workbench: Mapping[str, object]) -> list[Mapping[str, object]]:
    return [
        variable for variable in workbench.get("solverVariables", []) if variable.get("id")
    ]


def _solver_metrics(workbench: Mapping[str, object]) -> list[Mapping[str, object]]:
    return [metric for metric in workbench.get("solverMetrics", []) if metric.get("id")]


def _input_fields_by_id(workbench: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {
        str(field.get("field")): field
        for field in workbench.get("inputFields", [])
        if field.get("field")
    }


def _json_safe(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)
