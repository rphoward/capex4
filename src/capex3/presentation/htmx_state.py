from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from capex3.presentation.http_contracts import (
    calculate_payload,
    defaults_payload,
    solver_preview_payload,
    workbench_payload,
)
from capex3.presentation.htmx_format import (
    _bool_text,
    _control_value,
    _form_bool,
    _hidden,
    _json_for_hidden,
    _parse_number,
    _parse_optional_number,
)

SOURCE_METRIC_STRIP_FIELDS = (
    "trueMonthlyCashFlow",
    "totalMonthlyCapexReserve",
    "breakevenGrossRent",
)


SOURCE_METRIC_STRIP_COPY = {
    "trueMonthlyCashFlow": "Tap for full breakdown",
    "totalMonthlyCapexReserve": "Tap to see drivers",
    "breakevenGrossRent": "Tap for thresholds",
}


@dataclass(frozen=True)
class UiState:
    defaults: Mapping[str, object]
    workbench: Mapping[str, object]
    inputs: dict[str, object]
    component_overrides: dict[str, dict[str, object]]
    active_step: str
    active_evidence_layer: str
    active_metric_field: str
    evidence_follows_step: bool
    solver_variable: str
    solver_metric: str
    solver_target: str
    solver_lower: str
    solver_upper: str
    result: Mapping[str, object] | None
    error_message: str
    solver_preview: Mapping[str, object] | None
    status_text: str
    status_kind: str
    last_input_change_reason: str
    overlap_warning_latched: bool
    overlap_warning_age_snapshot_key: str
    walkthrough_age_snapshot_key: str


def _build_state(form: Mapping[str, str], action: str) -> UiState:
    defaults = defaults_payload()
    workbench = workbench_payload()["workbench"]
    input_fields = _input_fields_by_id(workbench)
    input_defaults = dict(defaults["inputs"])

    if action == "reset" or not form:
        inputs = {
            key: value
            for key, value in input_defaults.items()
            if key != "componentOverrides"
        }
        component_overrides: dict[str, dict[str, object]] = {}
    else:
        inputs = _inputs_from_form(form, input_defaults, input_fields)
        component_overrides = _component_overrides_from_form(form)

    if action == "override":
        _apply_component_override(form, component_overrides)

    if action == "new-walkthrough":
        inputs["effectiveAgeYears"] = input_defaults["effectiveAgeYears"]
        component_overrides = {}

    if action == "apply-solver":
        apply_field = form.get("solverApplyField", "")
        solved_value = _parse_number(form.get("solverSolvedValue", ""))
        if apply_field:
            inputs[apply_field] = solved_value

    inputs["componentOverrides"] = component_overrides

    walkthrough_age_snapshot_key = _walkthrough_age_snapshot_key(
        inputs,
        component_overrides,
    )

    journey_steps = _journey_steps(workbench)
    active_step = form.get("activeStep", "") or _first_id(journey_steps) or "listing"
    if action == "new-walkthrough":
        active_step = "walkthrough"
    if active_step not in {step["id"] for step in journey_steps}:
        active_step = _first_id(journey_steps) or "listing"

    active_evidence_layer = form.get("activeEvidenceLayer", "") or "tenYear"
    active_metric_field = form.get("activeMetricField", "")
    evidence_follows_step = _form_bool(form, "evidenceFollowsStep", True)
    if action == "evidence":
        evidence_follows_step = False
        active_evidence_layer = form.get("activeEvidenceLayer", active_evidence_layer)
        active_metric_field = ""

    if action == "metric":
        active_metric_field = form.get("activeMetricField", "")
        evidence_follows_step = False
        metric = _metric_by_field(workbench).get(active_metric_field)
        if metric:
            active_evidence_layer = str(metric.get("evidenceLayerId") or active_evidence_layer)

    if evidence_follows_step:
        active_evidence_layer = _evidence_layer_for_step(workbench, active_step)

    evidence_ids = {layer["id"] for layer in _evidence_layers(workbench)}
    if active_evidence_layer not in evidence_ids:
        active_evidence_layer = _evidence_layer_for_step(workbench, active_step)

    solver_variables = _solver_variables(workbench)
    solver_metrics = _solver_metrics(workbench)
    solver_variable = form.get("solverVariable", "") or _first_manual_solver_variable_id(solver_variables)
    solver_metric = form.get("solverMetric", "") or _first_id(solver_metrics) or "monthlyCashFlow"
    solver_target = form.get("solverTarget", "0")
    solver_lower = form.get("solverLower", "")
    solver_upper = form.get("solverUpper", "")

    result: Mapping[str, object] | None
    error_message = ""
    status_text = "Current"
    status_kind = "ok"
    try:
        result = calculate_payload(inputs)["result"]
    except Exception as error:
        result = None
        error_message = str(error)
        status_text = "Input error"
        status_kind = "error"

    overlap_detected = bool(result.get("overlapDetected")) if result else False
    overlap_warning_latched, overlap_warning_age_snapshot_key = _resolve_overlap_warning_latch(
        action=action,
        form=form,
        current_snapshot_key=walkthrough_age_snapshot_key,
        overlap_detected=overlap_detected,
    )

    solver_preview: Mapping[str, object] | None = None
    if result is not None and action in {"solve", "solve-threshold", "solve-reserve-first-shortfall"}:
        solver_preview = solver_preview_payload(
            form=form,
            workbench=workbench,
            inputs=inputs,
            solver_variable=solver_variable,
            solver_metric=solver_metric,
            solver_target=solver_target,
            solver_lower=solver_lower,
            solver_upper=solver_upper,
            threshold=action in {"solve-threshold", "solve-reserve-first-shortfall"},
            reserve_first_shortfall=action == "solve-reserve-first-shortfall",
        )
        status_text = "Solved preview" if solver_preview.get("ok") else "Solver error"
        status_kind = "ok" if solver_preview.get("ok") else "error"
        if action == "solve-threshold":
            active_evidence_layer = "whatWorks"
            evidence_follows_step = False

    return UiState(
        defaults=defaults,
        workbench=workbench,
        inputs=inputs,
        component_overrides=component_overrides,
        active_step=active_step,
        active_evidence_layer=active_evidence_layer,
        active_metric_field=active_metric_field,
        evidence_follows_step=evidence_follows_step,
        solver_variable=solver_variable,
        solver_metric=solver_metric,
        solver_target=solver_target,
        solver_lower=solver_lower,
        solver_upper=solver_upper,
        result=result,
        error_message=error_message,
        solver_preview=solver_preview,
        status_text=status_text,
        status_kind=status_kind,
        last_input_change_reason=action,
        overlap_warning_latched=overlap_warning_latched,
        overlap_warning_age_snapshot_key=overlap_warning_age_snapshot_key,
        walkthrough_age_snapshot_key=walkthrough_age_snapshot_key,
    )


def _hidden_state_fields(state: UiState) -> str:
    visible_fields = set(_active_step(state.workbench, state.active_step).get("fields", []))
    hidden_inputs = [
        _hidden("activeStep", state.active_step),
        _hidden("activeEvidenceLayer", state.active_evidence_layer),
        _hidden("activeMetricField", state.active_metric_field),
        _hidden("evidenceFollowsStep", _bool_text(state.evidence_follows_step)),
        _hidden("componentOverridesJson", _json_for_hidden(state.component_overrides)),
        _hidden("overlapWarningLatched", _bool_text(state.overlap_warning_latched)),
        _hidden("overlapWarningAgeSnapshotKey", state.overlap_warning_age_snapshot_key),
    ]
    for field, value in state.inputs.items():
        if field == "componentOverrides" or field in visible_fields:
            continue
        hidden_inputs.append(_hidden(field, _control_value(value)))
    return "\n".join(hidden_inputs)


def _snapshot_age_value(value: object) -> object:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _walkthrough_age_snapshot_key(
    inputs: Mapping[str, object],
    component_overrides: Mapping[str, Mapping[str, object]],
) -> str:
    component_ages: dict[str, object] = {}
    for component_id in sorted(component_overrides):
        override = component_overrides[component_id]
        age = override.get("age")
        if age is not None:
            component_ages[component_id] = _snapshot_age_value(age)
    return json.dumps(
        {
            "effectiveAgeYears": _snapshot_age_value(inputs.get("effectiveAgeYears")),
            "componentAges": component_ages,
        },
        separators=(",", ":"),
    )


def _snapshot_keys_match(stored_key: str, current_snapshot_key: str) -> bool:
    if not stored_key:
        return False
    if stored_key == current_snapshot_key:
        return True
    try:
        stored = json.loads(stored_key)
        current = json.loads(current_snapshot_key)
    except json.JSONDecodeError:
        return False
    return isinstance(stored, Mapping) and stored == current


def _resolve_overlap_warning_latch(
    *,
    action: str,
    form: Mapping[str, str],
    current_snapshot_key: str,
    overlap_detected: bool,
) -> tuple[bool, str]:
    if action in {"reset", "new-walkthrough"} or not form:
        return False, ""

    stored_key = form.get("overlapWarningAgeSnapshotKey", "")
    latched = _form_bool(form, "overlapWarningLatched", False)
    if stored_key and not _snapshot_keys_match(stored_key, current_snapshot_key):
        latched = False
        stored_key = ""

    if overlap_detected and not latched:
        return True, current_snapshot_key

    if latched:
        return True, stored_key or current_snapshot_key

    return False, ""


def _hidden_attr_for_layer(state: UiState, layer_id: str) -> str:
    return "" if state.active_evidence_layer == layer_id else " hidden"


def _active_step(workbench: Mapping[str, object], step_id: str) -> Mapping[str, object]:
    steps = _journey_steps(workbench)
    return next((step for step in steps if step["id"] == step_id), steps[0] if steps else {})


def _active_evidence_layer(state: UiState) -> Mapping[str, object]:
    layers = _evidence_layers(state.workbench)
    return next(
        (layer for layer in layers if layer["id"] == state.active_evidence_layer),
        layers[0] if layers else {},
    )


def _journey_steps(workbench: Mapping[str, object]) -> list[dict[str, object]]:
    return [
        {
            "id": str(step.get("id")),
            "title": step.get("title") or step.get("label") or step.get("id"),
            "description": step.get("description") or "",
            "fields": list(step.get("fields", [])),
        }
        for step in workbench.get("journeyStages", [])
        if step.get("id")
    ]


def _next_step_id(workbench: Mapping[str, object], step_id: str) -> str:
    steps = _journey_steps(workbench)
    for index, step in enumerate(steps):
        if step["id"] == step_id and index < len(steps) - 1:
            return str(steps[index + 1]["id"])
    return ""


def _evidence_layers(workbench: Mapping[str, object]) -> list[dict[str, object]]:
    layers = [
        {
            "id": str(layer.get("id")),
            "title": layer.get("title") or layer.get("label") or layer.get("id"),
            "description": layer.get("description") or "",
            "shortLabel": layer.get("shortLabel") or str(layer.get("title") or layer.get("id"))[:1],
            "showInTabs": layer.get("showInTabs", True),
        }
        for layer in workbench.get("evidenceConcepts", [])
        if layer.get("id")
    ]
    known_ids = {layer["id"] for layer in layers}
    from capex3.presentation.htmx_evidence import UTILITY_EVIDENCE_LAYERS

    layers.extend(
        layer for layer in UTILITY_EVIDENCE_LAYERS if layer["id"] not in known_ids
    )
    return layers


def _input_fields_by_id(workbench: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {
        str(field.get("field")): field
        for field in workbench.get("inputFields", [])
        if field.get("field")
    }


def _metric_by_field(workbench: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    return {
        str(metric.get("field")): metric
        for metric in workbench.get("metricGuidance", [])
        if metric.get("field")
    }


def _metric_fields_for_layer(
    workbench: Mapping[str, object],
    layer_id: str,
) -> list[Mapping[str, object]]:
    metrics = _metric_by_field(workbench)
    fields_by_layer = workbench.get("evidenceMetricFields", {})
    field_ids = fields_by_layer.get(layer_id) or fields_by_layer.get("tenYear") or list(metrics)
    return [metrics[field] for field in field_ids if field in metrics]


def _source_metric_strip_fields(workbench: Mapping[str, object]) -> list[Mapping[str, object]]:
    metrics = _metric_by_field(workbench)
    return [
        metrics[field]
        for field in SOURCE_METRIC_STRIP_FIELDS
        if field in metrics
    ]


def _evidence_layer_for_step(workbench: Mapping[str, object], step_id: str) -> str:
    mapping = workbench.get("stageEvidenceMapping", {})
    return str(mapping.get(step_id) or "tenYear")


def _solver_variables(workbench: Mapping[str, object]) -> list[Mapping[str, object]]:
    return [variable for variable in workbench.get("solverVariables", []) if variable.get("id")]


def _solver_metrics(workbench: Mapping[str, object]) -> list[Mapping[str, object]]:
    return [metric for metric in workbench.get("solverMetrics", []) if metric.get("id")]


def _first_manual_solver_variable_id(variables: Sequence[Mapping[str, object]]) -> str:
    for variable in variables:
        if variable.get("applyField") and variable.get("showInManualControls", True):
            return str(variable["id"])
    return _first_id(variables) or "rent"


def _first_id(items: Sequence[Mapping[str, object]]) -> str:
    return str(items[0]["id"]) if items else ""


def _inputs_from_form(
    form: Mapping[str, str],
    defaults: Mapping[str, object],
    input_fields: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    inputs: dict[str, object] = {}
    for field, default in defaults.items():
        if field == "componentOverrides":
            continue
        raw = form.get(field, _control_value(default))
        kind = input_fields.get(field, {}).get("kind")
        inputs[field] = _parse_input_value(raw, kind, default)
    return inputs


def _parse_input_value(raw: str, kind: object, default: object) -> object:
    if kind in {"text", "select"} or isinstance(default, str):
        return raw
    if raw == "":
        return None
    number = _parse_number(raw)
    return number if number is not None else raw


def _component_overrides_from_form(form: Mapping[str, str]) -> dict[str, dict[str, object]]:
    raw = form.get("componentOverridesJson", "{}")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(decoded, Mapping):
        return {}
    overrides: dict[str, dict[str, object]] = {}
    for component, value in decoded.items():
        if isinstance(value, Mapping):
            overrides[str(component)] = {
                "quantity": value.get("quantity"),
                "age": value.get("age"),
            }
    return overrides


def _apply_component_override(
    form: Mapping[str, str],
    overrides: dict[str, dict[str, object]],
) -> None:
    component = form.get("overrideComponent", "")
    if not component:
        return
    quantity = _parse_optional_number(form.get("overrideQuantity", ""))
    age = _parse_optional_number(form.get("overrideAge", ""))
    if quantity is None and age is None:
        overrides.pop(component, None)
        return
    overrides[component] = {"quantity": quantity, "age": age}
