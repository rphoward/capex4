from __future__ import annotations

from typing import Mapping

from capex3.presentation.htmx_format import (
    _attr,
    _control_value,
    _display_value,
    _html,
    _hx_post,
    _options,
    _selected,
)
from capex3.presentation.htmx_offer_ready import (
    _offer_ready_panel,
    _solver_preview_html,
    _solver_workbench_disclaimer_html,
)
from capex3.presentation.htmx_shell import (
    _calculator_card,
    _ledger_panel,
    _section_head,
    _step_rail,
)
from capex3.presentation.htmx_state import (
    UiState,
    _active_step,
    _journey_steps,
    _next_step_id,
)
from capex3.presentation.http_contracts import (
    _input_fields_by_id,
    _solver_metrics,
    _solver_variables,
)


def _input_panel(state: UiState) -> str:
    step = _active_step(state.workbench, state.active_step)
    component_hidden = "" if state.active_step == "walkthrough" else " hidden"
    solver_hidden = "" if state.active_step == "decision" else " hidden"
    journey_controls = _journey_local_controls(state)
    offer_ready = _offer_ready_panel(state) if state.active_step == "walkthrough" else ""

    calc_card_body = f"""
    {_step_rail("Steps", _journey_step_buttons(state))}
    <div class="input-content">
      <div class="active-step active-step-summary">
        <p class="step-kicker">You're on</p>
        <h2 id="active-step-title">{_html(step.get("title", ""))}</h2>
        <p id="active-step-description">{_html(step.get("description", ""))}</p>
      </div>
      <div class="field-grid" id="field-grid">{_input_fields(state, step)}</div>
      {journey_controls}
    </div>"""

    walkthrough_body = f"""
    <div class="secondary-controls" id="component-workbench"{component_hidden}>
      <div class="section-head compact">
        <h2>Walkthrough checks</h2>
        <button id="apply-override-button" type="button" {_hx_post("/ui/override")}>Apply</button>
      </div>
      <div class="override-grid">
        <label>
          Component
          <select id="component-select" name="overrideComponent">{_component_options(state)}</select>
        </label>
        <label>
          Quantity
          <input id="override-quantity" name="overrideQuantity" type="number" step="0.01">
        </label>
        <label>
          Age
          <input id="override-age" name="overrideAge" type="number" step="0.01">
        </label>
      </div>
      <div id="override-list" class="override-list">{_override_list(state)}</div>
    </div>"""

    solver_body = f"""
    <div class="secondary-controls" id="solver-workbench"{solver_hidden}>
      {_solver_workbench_disclaimer_html(state.workbench)}
      <div class="solver-grid">
        <label>
          Variable
          <select id="solver-variable" name="solverVariable">{_solver_variable_options(state)}</select>
        </label>
        <label>
          Metric
          <select id="solver-metric" name="solverMetric">{_solver_metric_options(state)}</select>
        </label>
        <label>
          Target
          <input id="solver-target" name="solverTarget" type="number" step="0.000001" value="{_attr(state.solver_target)}">
        </label>
        <label>
          Lower Bound
          <input id="solver-lower" name="solverLower" type="number" step="0.01" placeholder="auto" value="{_attr(state.solver_lower)}">
        </label>
        <label>
          Upper Bound
          <input id="solver-upper" name="solverUpper" type="number" step="0.01" placeholder="auto" value="{_attr(state.solver_upper)}">
        </label>
      </div>
      <div id="solver-result" class="solver-result">{_manual_solver_preview(state)}</div>
    </div>"""

    walkthrough_ledger_hidden = "" if state.active_step == "walkthrough" else " hidden"
    solver_ledger_hidden = "" if state.active_step == "decision" else " hidden"
    ledger_panels = _ledger_panel(
        "Walkthrough checks",
        walkthrough_body,
        panel_id="walkthrough-ledger",
        hidden=walkthrough_ledger_hidden,
    )
    ledger_panels += _ledger_panel(
        "What would work?",
        f"""
    <div class="section-head compact">
      <button id="solve-button" type="button" {_hx_post("/ui/solve")}>Solve</button>
    </div>
{solver_body}""",
        panel_id="solver-ledger",
        hidden=solver_ledger_hidden,
    )
    if state.active_step == "walkthrough":
        ledger_panels += offer_ready

    return f"""
<section class="input-panel left-panel calc-inputs">
{_section_head("Deal inputs", f'<button id="reset-button" type="button" {_hx_post("/ui/reset")}>Reset</button>')}
  <div class="input-workbench">
{_calculator_card(calc_card_body)}
{ledger_panels}
  </div>
</section>"""


def _journey_step_buttons(state: UiState) -> str:
    buttons = []
    for index, step in enumerate(_journey_steps(state.workbench), start=1):
        active = " active" if step["id"] == state.active_step else ""
        pressed = "true" if step["id"] == state.active_step else "false"
        buttons.append(
            f"""<button type="button" class="journey-step{active}" aria-pressed="{pressed}" aria-label="{_attr(step["title"])}" title="{_attr(step["title"])}" name="activeStep" value="{_attr(step["id"])}" {_hx_post("/ui/step")}>
  <span>{index}</span><strong>{_html(step["title"])}</strong>
</button>"""
        )
    return "\n".join(buttons)


def _input_fields(state: UiState, step: Mapping[str, object]) -> str:
    input_fields = _input_fields_by_id(state.workbench)
    fields = []
    for field in step.get("fields", []):
        field_id = str(field)
        metadata = input_fields.get(field_id, {"label": field_id, "kind": "number"})
        span = f" {metadata.get('span')}" if metadata.get("span") else ""
        hint = (
            f'<span class="field-hint">{_html(metadata.get("hint", ""))}</span>'
            if metadata.get("hint")
            else ""
        )
        fields.append(
            f"""<label class="field{_attr(span)}">
  <span class="field-label">{_html(metadata.get("label", field_id))}</span>
  {_field_control(state, field_id, metadata)}
  {hint}
</label>"""
        )
    return "\n".join(fields)


def _journey_local_controls(state: UiState) -> str:
    if state.active_step == "decision":
        return ""
    next_step_id = _next_step_id(state.workbench, state.active_step)
    next_button = (
        f"""<button id="next-step-button" type="button" name="activeStep" value="{_attr(next_step_id)}" {_hx_post("/ui/step")}>Next step</button>"""
        if next_step_id
        else ""
    )
    return f"""
<div class="journey-actions" id="journey-actions">
  <button id="recalculate-button" type="button" {_hx_post("/ui/calculate")}>Recalculate</button>
  {next_button}
</div>"""


def _field_control(
    state: UiState,
    field: str,
    metadata: Mapping[str, object],
) -> str:
    value = _control_value(state.inputs.get(field))
    kind = str(metadata.get("kind") or "number")
    common = f'name="{_attr(field)}" {_hx_post("/ui/calculate")} hx-trigger="change delay:250ms"'
    if kind == "select":
        source = str(metadata.get("optionsSource") or "")
        options = state.defaults.get("assumptions", {}).get(source, [])
        return f"<select {common}>{_options(options, value)}</select>"

    input_type = "text" if kind == "text" else "number"
    step = "0.0001" if kind == "rate" else "0.01"
    return (
        f'<input {common} type="{input_type}" step="{step}" '
        f'value="{_attr(value)}">'
    )


def _component_options(state: UiState) -> str:
    components = state.defaults.get("assumptions", {}).get("components", [])
    names = [component.get("name", "") for component in components if component.get("name")]
    return _options(names, "")


def _override_list(state: UiState) -> str:
    if not state.component_overrides:
        return "No active overrides"
    return "".join(
        f'<span class="override-chip">{_html(component)}: qty {_html(_display_value(override.get("quantity")))}, age {_html(_display_value(override.get("age")))}</span>'
        for component, override in sorted(state.component_overrides.items())
    )


def _solver_variable_options(state: UiState) -> str:
    variables = [
        variable
        for variable in _solver_variables(state.workbench)
        if variable.get("applyField") and variable.get("showInManualControls", True)
    ]
    return "".join(
        f'<option value="{_attr(variable["id"])}"{_selected(variable["id"], state.solver_variable)}>{_html(variable.get("label", variable["id"]))}</option>'
        for variable in variables
    )


def _solver_metric_options(state: UiState) -> str:
    return "".join(
        f'<option value="{_attr(metric["id"])}"{_selected(metric["id"], state.solver_metric)}>{_html(metric.get("label", metric["id"]))}</option>'
        for metric in _solver_metrics(state.workbench)
    )


def _manual_solver_preview(state: UiState) -> str:
    preview = state.solver_preview
    if not preview or preview.get("source") != "manual":
        if preview and str(preview.get("source", "")).startswith("threshold:"):
            return "Threshold preview is shown on the solved card."
        return ""
    return _solver_preview_html(preview)


def _deal_identity_label(state: UiState) -> str:
    address = str(state.inputs.get("propertyAddress") or "").strip()
    profile = str(state.inputs.get("propertyProfile") or "").strip()
    subregion = str(state.inputs.get("subregion") or "").strip()
    if not address or address == "[Type Address Here]":
        address = "New property"
    deal_type = profile or subregion or "Rental"
    return f"{address} · {deal_type}"
