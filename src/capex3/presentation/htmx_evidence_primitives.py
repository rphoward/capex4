from __future__ import annotations

from typing import Mapping

from capex3.core.teaching.evidence_presentation import primary_reward_label_for_trace
from capex3.presentation.htmx_format import _attr, _html


def _evidence_drilldown(title: str, inner_html: str) -> str:
    return f"""
<details class="evidence-drilldown">
  <summary><span>{_html(title)}</span></summary>
  <div class="evidence-drilldown-body">{inner_html}</div>
</details>"""


def _receipt_empty_row() -> str:
    return '<div class="rcpt-row"><span>Evidence trace unavailable.</span><span class="rcpt-val">-</span></div>'


def _receipt_waterfall(
    rows_html: str,
    *,
    extra_classes: str = "",
    receipt_id: str = "",
) -> str:
    classes = "receipt receipt-waterfall"
    if extra_classes:
        classes = f"{classes} {extra_classes.strip()}"
    id_attr = f' id="{_attr(receipt_id)}"' if receipt_id else ""
    return f'<div class="{_attr(classes)}"{id_attr}>{rows_html}</div>'


def _receipt_panel(
    title: str,
    receipt_html: str,
    *,
    panel_class: str = "receipt-panel",
    panel_id: str = "",
) -> str:
    id_attr = f' id="{_attr(panel_id)}"' if panel_id else ""
    return f"""
<div class="{_attr(panel_class)}"{id_attr}>
  <p class="receipt-panel-kicker">{_html(title)}</p>
  {receipt_html}
</div>"""


def _simple_receipt_row(label: object, value_html: str, *, row_class: str = "") -> str:
    classes = "rcpt-row"
    if row_class:
        classes = f"{classes} {row_class}"
    return f"""
<div class="{_attr(classes)}">
  <span class="rcpt-label">{_html(label)}</span>
  <span class="rcpt-val">{value_html}</span>
</div>"""


def _primary_reward_label_html(trace: Mapping[str, object], layer_id: str) -> str:
    label = primary_reward_label_for_trace(trace, layer_id)
    if not label:
        return ""
    return f'<p class="evidence-reward-label">{_html(label)}</p>'


def _evidence_layer_shell(
    layer_id: str,
    *,
    hidden: str,
    trace: Mapping[str, object],
    layer_copy: str = "",
    body_html: str,
    include_reward_label: bool = True,
) -> str:
    preamble = []
    if layer_copy:
        preamble.append(layer_copy)
    label = _primary_reward_label_html(trace, layer_id) if include_reward_label else ""
    if label:
        preamble.append(label)
    preamble_block = "\n  ".join(preamble)
    preamble_prefix = f"  {preamble_block}\n  " if preamble_block else ""
    return f"""
<section class="evidence-layer" data-evidence-layer="{layer_id}"{hidden}>
{preamble_prefix}{body_html}
</section>"""


def _drivers_table(table_id: str, table_rows: str) -> str:
    return f"""
<div class="ledger-panel ledger-panel-inline">
  <div class="tbl-scroll">
    <table class="drv-tbl" id="{table_id}">
      <thead>
        <tr><th>Repair item</th><th>Monthly reserve</th><th>Share</th><th>Quantity</th><th>Age / life</th><th>Remaining</th><th>Source</th></tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</div>"""
