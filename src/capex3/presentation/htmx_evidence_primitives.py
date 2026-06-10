from __future__ import annotations

from typing import Mapping

from capex3.core.teaching.evidence_presentation import (
    primary_reward_key,
    primary_reward_label_for_trace,
)
from capex3.presentation.htmx_format import _attr, _html
from capex3.presentation.htmx_state import (
    UiState,
    _metric_strip_navigation_by_field,
)


def _evidence_drilldown(title: str, inner_html: str) -> str:
    return f"""
<details class="evidence-drilldown">
  <summary><span>{_html(title)}</span></summary>
  <div class="evidence-drilldown-body">{inner_html}</div>
</details>"""


def _evidence_focus_class(state: UiState, layer_id: str) -> str:
    if state.active_evidence_layer != layer_id or not state.active_metric_field:
        return ""
    nav = _metric_strip_navigation_by_field(state.workbench).get(
        state.active_metric_field,
        {},
    )
    expected_focus = primary_reward_key(layer_id)
    if expected_focus and nav.get("focus") == expected_focus:
        return " evidence-focus"
    return ""


def _primary_reward_label_html(trace: Mapping[str, object], layer_id: str) -> str:
    label = primary_reward_label_for_trace(trace, layer_id)
    if not label:
        return ""
    return f'<p class="evidence-reward-label">{_html(label)}</p>'


def _teaching_reward_disclaimer(trace: Mapping[str, object]) -> str:
    teaching_meta = []
    if trace.get("teachingOnly"):
        teaching_meta.append("Teaching-only")
    decision_id = trace.get("decisionId")
    if decision_id:
        teaching_meta.append(f"decision {decision_id}")
    if trace.get("appRegressionOnly"):
        teaching_meta.append("App-side regression only")
    if trace.get("appOnlyResilience"):
        teaching_meta.append("App-only resilience")
    if trace.get("workbookCanonical") is False:
        teaching_meta.append("not workbook-canonical")
    if not teaching_meta:
        return ""
    source_note = trace.get("sourceNote") or ""
    meta_line = " · ".join(teaching_meta)
    decision_attr = (
        f' data-decision-id="{_attr(str(decision_id))}"' if decision_id else ""
    )
    note_suffix = f" — {_html(str(source_note))}" if source_note else ""
    return (
        f'<p class="layer-copy disclaimer teaching-only"{decision_attr}>'
        f"<strong>{_html(meta_line)}</strong>{note_suffix}</p>"
    )


def _evidence_layer_shell(
    layer_id: str,
    *,
    hidden: str,
    trace: Mapping[str, object],
    layer_copy: str = "",
    body_html: str,
) -> str:
    preamble = []
    if layer_copy:
        preamble.append(layer_copy)
    label = _primary_reward_label_html(trace, layer_id)
    if label:
        preamble.append(label)
    disclaimer = _teaching_reward_disclaimer(trace)
    if disclaimer:
        preamble.append(disclaimer)
    preamble_block = "\n  ".join(preamble)
    preamble_prefix = f"  {preamble_block}\n  " if preamble_block else ""
    return f"""
<section class="evidence-layer" data-evidence-layer="{layer_id}"{hidden}>
{preamble_prefix}{body_html}
</section>"""


def _drivers_table(table_id: str, table_rows: str) -> str:
    return f"""
<div class="tbl-scroll">
  <table class="drv-tbl" id="{table_id}">
    <thead>
      <tr><th>Repair item</th><th>Monthly reserve</th><th>Share</th><th>Quantity</th><th>Age / life</th><th>Remaining</th><th>Source</th></tr>
    </thead>
    <tbody>{table_rows}</tbody>
  </table>
</div>"""
