"""Debug-only evidence render helpers — not included in stakeholder page assembly."""

from __future__ import annotations

import json
from typing import Mapping

from capex3.presentation.htmx_evidence import _summary_cards_html
from capex3.presentation.htmx_format import _display_value, _html
from capex3.presentation.htmx_shell import _section_head
from capex3.presentation.htmx_state import UiState, _hidden_attr_for_layer


def _value_at_path(result: Mapping[str, object], path: str) -> object:
    if not path:
        return None
    current: object = result
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _diagnostics_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "diagnostics")
    workbook_source = "-"
    if state.result:
        workbook_source = state.result.get("audit", {}).get("sourceWorkbook", "fixture model")
    cards = [
        {
            "label": "Tracked UI links",
            "value": str(len(state.workbench.get("calculationLinkageFields", []))),
            "note": "Fields with raw, sent, normalized, and output values.",
        },
        {
            "label": "Rendered input version",
            "value": "0",
            "note": f"Latest change: {state.last_input_change_reason or 'none'}",
        },
        {
            "label": "Workbook source",
            "value": workbook_source,
            "note": "Diagnostics remain downstream of engine output.",
        },
    ]
    diagnostic_rows = _diagnostic_trace_rows(state)
    body = f"""
  <div id="diagnostic-summary" class="evidence-summary">{_summary_cards_html(cards)}</div>
  <details class="diagnostics-drilldown" id="diagnostics-drilldown">
    <summary>
      <span>Show table</span>
      <small>Raw engine traceability from calculationLinkageFields.</small>
    </summary>
    <div class="tbl-scroll">
      <table class="diag-tbl" id="diagnostics-table">
        <thead>
          <tr><th>Engine field</th><th>User label</th><th>UI value</th><th>Engine value</th><th>Workbook cell</th></tr>
        </thead>
        <tbody>{diagnostic_rows}</tbody>
      </table>
    </div>
  </details>"""
    return f"""
<section class="evidence-layer ledger-panel" data-evidence-layer="diagnostics"{hidden} id="diagnostics-ledger">
{_section_head("Calculation diagnostics")}
{body}
</section>"""


def _diagnostic_trace_rows(state: UiState) -> str:
    if not state.result:
        return '<tr><td>Evidence trace unavailable.</td><td></td><td></td><td></td><td></td></tr>'
    rows = []
    for field in state.workbench.get("calculationLinkageFields", []):
        input_field = field.get("inputField")
        rows.append(
            f"""<tr>
  <td class="mono">{_html(field.get("outputPath") or field.get("normalizedPath") or "")}</td>
  <td>{_html(field.get("label", ""))}</td>
  <td class="mono">{_html(_display_value(state.inputs.get(input_field)))}</td>
  <td class="mono">{_html(_display_value(_value_at_path(state.result, field.get("outputPath", ""))))}</td>
  <td class="ref">{_html(field.get("workbookCell", ""))}</td>
</tr>"""
        )
    return "".join(rows)


def _debug_panel(state: UiState) -> str:
    return f"""
<details class="debug-panel">
  <summary>Calculation diagnostics</summary>
  <div id="linkage-debug" class="linkage-debug">{_linkage_debug_table(state)}</div>
  <pre id="debug-output">{_html(_debug_json(state))}</pre>
</details>"""


def _linkage_debug_table(state: UiState) -> str:
    if not state.result:
        return "No calculation result yet."
    rows = []
    for field in state.workbench.get("calculationLinkageFields", []):
        input_field = field.get("inputField")
        rows.append(
            f"""<tr>
  <td>{_html(field.get("workbookCell", ""))}</td>
  <td>{_html(field.get("label", ""))}</td>
  <td>{_html(input_field)}</td>
  <td>{_html(field.get("normalizedPath", ""))}</td>
  <td>{_html(field.get("uiElement", ""))}</td>
  <td>{_html(_display_value(state.inputs.get(input_field)))}</td>
  <td>{_html(_display_value(state.inputs.get(input_field)))}</td>
  <td>{_html(_display_value(_value_at_path(state.result, field.get("normalizedPath", ""))))}</td>
  <td>{_html(_display_value(_value_at_path(state.result, field.get("outputPath", ""))))}</td>
</tr>"""
        )
    return f"""
<table class="debug-table">
  <thead>
    <tr>
      <th>Workbook cell</th><th>Field</th><th>App input</th><th>Engine path</th><th>UI element</th><th>Raw UI value</th><th>Sent value</th><th>Normalized value</th><th>Output value</th>
    </tr>
  </thead>
  <tbody>{''.join(rows)}</tbody>
</table>"""


def _debug_json(state: UiState) -> str:
    debug = {
        "sentInput": state.inputs,
        "normalizedInput": state.result.get("input") if state.result else None,
        "dashboard": state.result.get("dashboard") if state.result else None,
        "audit": state.result.get("audit") if state.result else None,
    }
    return json.dumps(debug, indent=2, sort_keys=True)
