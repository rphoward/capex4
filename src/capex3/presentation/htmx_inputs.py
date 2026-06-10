from __future__ import annotations

from typing import Mapping

from capex3.presentation.htmx_charts import _evidence_graph
from capex3.presentation.htmx_evidence import (
    _evidence_sections,
    _evidence_tabs,
    _metric_cards,
)
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
from capex3.presentation.htmx_state import (
    UiState,
    _active_evidence_layer,
    _active_step,
    _hidden_state_fields,
    _input_fields_by_id,
    _journey_steps,
    _next_step_id,
    _solver_metrics,
    _solver_variables,
)

def _input_panel(state: UiState) -> str:
    step = _active_step(state.workbench, state.active_step)
    component_hidden = "" if state.active_step == "walkthrough" else " hidden"
    solver_hidden = "" if state.active_step == "decision" else " hidden"
    journey_controls = _journey_local_controls(state)
    decision_packet = _decision_packet_placeholder() if state.active_step == "decision" else ""
    offer_ready = _offer_ready_panel(state) if state.active_step == "walkthrough" else ""
    return f"""
<section class="input-panel left-panel">
  <div class="section-head">
    <h2>Deal inputs</h2>
    <button id="reset-button" type="button" {_hx_post("/ui/reset")}>Reset</button>
  </div>
  <div class="input-workbench">
    <aside class="step-rail" aria-label="Journey steps">
      <p>Steps</p>
      <div class="journey-steps" id="journey-steps">{_journey_step_buttons(state)}</div>
    </aside>
    <div class="input-content">
      <div class="active-step active-step-summary">
        <p class="step-kicker">Active step</p>
        <h2 id="active-step-title">{_html(step.get("title", ""))}</h2>
        <p id="active-step-description">{_html(step.get("description", ""))}</p>
      </div>
      <div class="field-grid" id="field-grid">{_input_fields(state, step)}</div>
      {decision_packet}
      {journey_controls}
      <div class="secondary-controls" id="component-workbench"{component_hidden}>
        <div class="section-head compact">
          <h2>Walkthrough checks</h2>
          <button id="apply-override-button" type="button" {_hx_post("/ui/override")}>Apply</button>
        </div>
        <div class="walkthrough-checks" id="walkthrough-checks">
          <div>
            <strong>Age Check</strong>
            <span>How old or worn is it?</span>
          </div>
          <div>
            <strong>Size / Count Check</strong>
            <span>How much of it is there?</span>
          </div>
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
      </div>
      {offer_ready}
      <div class="secondary-controls" id="solver-workbench"{solver_hidden}>
        <div class="section-head compact">
          <h2>What would work?</h2>
          <button id="solve-button" type="button" {_hx_post("/ui/solve")}>Solve</button>
        </div>
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
      </div>
    </div>
  </div>
</section>"""


def _output_panel(state: UiState) -> str:
    error = (
        f'<div id="calculation-error" class="calculation-error">{_html(state.error_message)}</div>'
        if state.error_message
        else '<div id="calculation-error" class="calculation-error" hidden></div>'
    )
    layer = _active_evidence_layer(state)
    mode = (
        f"Following {_active_step(state.workbench, state.active_step).get('title', '')}"
        if state.evidence_follows_step
        else f"Pinned: {layer.get('title', '')}"
    )
    checked = " checked" if state.evidence_follows_step else ""
    overview_button = (
        f"""<button id="overview-button" class="btn-ghost btn-sm overview-button" type="button" name="activeEvidenceLayer" value="tenYear" {_hx_post("/ui/evidence")}>Overview</button>"""
        if state.active_evidence_layer != "tenYear"
        else ""
    )
    pin_badge = "" if state.evidence_follows_step else '<span class="pin-badge">Pinned</span>'
    return f"""
<section class="output-panel right-panel">
  <div class="section-head">
    <h2>Evidence layer</h2>
  </div>
  {error}
  <div class="evidence-panel">
    <div class="evidence-workbench">
      <div class="evidence-content">
        <div class="section-head compact evidence-head">
          <div class="evidence-title-wrap">
            <p class="step-kicker" id="evidence-mode">{_html(mode)}</p>
            <div class="evidence-title-row">
              {overview_button}
              <h2 id="evidence-title">{_html(layer.get("title", ""))}</h2>
              {pin_badge}
            </div>
            <p id="evidence-description" class="evidence-description">{_html(layer.get("description", ""))}</p>
          </div>
          <label class="follow-toggle">
            <input type="hidden" name="evidenceFollowsStep" value="false">
            <input id="evidence-follow" name="evidenceFollowsStep" type="checkbox" value="true"{checked} {_hx_post("/ui/calculate")} hx-trigger="change">
            Follow my step
          </label>
        </div>
        <div class="evidence-hero">
          {_evidence_graph(state)}
          <div class="metric-grid metric-strip" id="metric-grid" data-source-role="metric-strip">{_metric_cards(state)}</div>
        </div>
        {_evidence_sections(state)}
      </div>
      <aside class="layer-rail" aria-label="Evidence layers">
        <p>Layers</p>
        <div class="evidence-tabs" id="evidence-tabs">{_evidence_tabs(state)}</div>
      </aside>
    </div>
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
        f"""<button id="next-step-button" class="btn-ghost" type="button" name="activeStep" value="{_attr(next_step_id)}" {_hx_post("/ui/step")}>Next step</button>"""
        if next_step_id
        else ""
    )
    return f"""
<div class="journey-actions" id="journey-actions">
  <button id="recalculate-button" type="button" {_hx_post("/ui/calculate")}>Recalculate</button>
  {next_button}
</div>"""


def _decision_packet_placeholder() -> str:
    return """
<div class="coming-soon decision-packet-placeholder" id="decision-packet-placeholder" aria-disabled="true">
  <h3>Decision Packet</h3>
  <p>Printable summary of assumptions, repair fund story, solver thresholds, and risks is disabled until a later approved slice.</p>
  <button id="generate-packet-button" type="button" disabled>Generate packet</button>
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
        address = "Unlabeled deal"
    deal_type = profile or subregion or "Rental"
    return f"{address} · {deal_type}"
