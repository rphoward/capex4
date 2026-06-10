from __future__ import annotations

import json
from typing import Mapping, Sequence

from capex3.core.teaching.calculation_result_traces import SOLVER_DISCLAIMER

from capex3.presentation.htmx_format import (
    _attr,
    _display_value,
    _format,
    _format_receipt_value,
    _html,
    _hx_post,
)
from capex3.presentation.htmx_state import (
    SOURCE_METRIC_STRIP_COPY,
    UiState,
    _evidence_layers,
    _hidden_attr_for_layer,
    _input_fields_by_id,
    _metric_by_field,
    _source_metric_strip_fields,
)

UTILITY_EVIDENCE_LAYERS = [
    {
        "id": "metricDetail",
        "title": "Field Detail",
        "description": "A closer look at the selected field from the latest engine result.",
        "showInTabs": False,
    },
    {
        "id": "diagnostics",
        "title": "Diagnostics",
        "description": "Inspect the UI-to-engine linkage without making raw JSON the main experience.",
        "shortLabel": "D",
    },
]


def _evidence_tabs(state: UiState) -> str:
    tabs = []
    for layer in _evidence_layers(state.workbench):
        if layer.get("showInTabs") is False:
            continue
        active = " active" if layer["id"] == state.active_evidence_layer else ""
        pressed = "true" if layer["id"] == state.active_evidence_layer else "false"
        label = layer.get("shortLabel") or str(layer.get("title", ""))[:1]
        tabs.append(
            f"""<button type="button" class="evidence-tab{active}" aria-pressed="{pressed}" aria-label="{_attr(layer["title"])}" title="{_attr(layer["title"])}" name="activeEvidenceLayer" value="{_attr(layer["id"])}" {_hx_post("/ui/evidence")}>
  <span>{_html(label)}</span><strong>{_html(layer["title"])}</strong>
</button>"""
        )
    return "\n".join(tabs)


def _metric_cards(state: UiState) -> str:
    dashboard = state.result.get("dashboard", {}) if state.result else {}
    cards = []
    for metric in _source_metric_strip_fields(state.workbench):
        field = metric["field"]
        value = dashboard.get(field)
        classes = ["metric"]
        if isinstance(value, (int, float)) and value < 0:
            classes.append("negative")
        if field == state.active_metric_field or metric.get("evidenceLayerId") == state.active_evidence_layer:
            classes.append("active")
        expanded = "true" if field == state.active_metric_field else "false"
        cards.append(
            f"""<button type="button" class="{' '.join(classes)}" aria-expanded="{expanded}" name="activeMetricField" value="{_attr(field)}" {_hx_post("/ui/metric")}>
  <strong>{_html(metric.get("label", field))}</strong>
  <span>{_html(_format(value, metric.get("kind") or metric.get("valueKind")))}</span>
  <small aria-hidden="true">{_html(SOURCE_METRIC_STRIP_COPY.get(field, 'Details'))}</small>
</button>"""
        )
    return "\n".join(cards)


def _evidence_sections(state: UiState) -> str:
    from capex3.presentation.htmx_offer_ready import (
        _cash_flow_stability_section,
        _what_works_section,
    )

    return "\n".join(
        [
            _cash_flow_section(state),
            _cash_flow_stability_section(state),
            _metric_detail_section(state),
            _repair_fund_section(state),
            _repair_drivers_section(state),
            _ten_year_section(state),
            _what_works_section(state),
            _diagnostics_section(state),
        ]
    )


def _cash_flow_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "cashFlow")
    trace = _result_trace(state, "cashFlow")
    rows = _trace_collection(trace, ("rows", "lines"))
    if rows:
        receipt_rows = "".join(_cash_flow_receipt_row(row) for row in rows)
    else:
        receipt_rows = '<div class="rcpt-row"><span>Evidence trace unavailable.</span><span class="rcpt-val">-</span></div>'
    return f"""
<section class="evidence-layer" data-evidence-layer="cashFlow"{hidden}>
  <p class="layer-copy">This layer shows the workbook dashboard snapshot (B40): true monthly cash flow after deducting the full monthly repair reserve every month—not the post-cap annual contribution from the pro forma. After the reserve cap fills, cash improvement shows up in pro forma accumulatedTrueCashFlow (L16); open the 10-Year Story evidence layer to follow that path.</p>
  <div class="receipt" id="cash-flow-receipt">{receipt_rows}</div>
</section>"""


def _cash_flow_receipt_row(row: Mapping[str, object]) -> str:
    receipt_kind = str(row.get("receiptKind") or "")
    row_class = "total-row" if receipt_kind == "total" else "sub" if receipt_kind == "subtotal" else ""
    value = _trace_value(row, ("value", "amount"))
    value_class = "rcpt-val"
    if receipt_kind == "deduction":
        value_class += " ded"
    elif receipt_kind == "total":
        value_class += " neg" if isinstance(value, (int, float)) and value < 0 else " pos"
    engine = ""
    if receipt_kind not in {"subtotal", "total"}:
        engine_field = row.get("engineField") or row.get("source") or row.get("formula") or ""
        engine = f'<span class="rcpt-eng">{_html(engine_field)}</span>' if engine_field else ""
    return f"""
<div class="rcpt-row {row_class}">
  <span>{_html(row.get("label") or row.get("title") or row.get("id") or "")}</span>
  <span class="{_attr(value_class)}">{_html(_format_receipt_value(value, row.get("kind")))}</span>
  {engine}
</div>"""


def _metric_detail_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "metricDetail")
    selected = _metric_by_field(state.workbench).get(state.active_metric_field)
    dashboard = state.result.get("dashboard", {}) if state.result else {}
    if selected:
        cards = _summary_cards_html(
            [
                {
                    "label": selected.get("label"),
                    "value": _format(
                        dashboard.get(selected["field"]),
                        selected.get("kind") or selected.get("valueKind"),
                    ),
                    "note": selected.get("sourceNote") or "This value comes from the latest engine result.",
                },
                {
                    "label": "Engine field",
                    "value": selected["field"],
                    "note": "Stable workbook/parity name.",
                },
            ]
        )
    else:
        cards = _summary_cards_html(
            [
                {
                    "label": "No field selected",
                    "value": "Tap a snapshot field",
                    "note": "Fields with a details caret open their supporting evidence here.",
                }
            ]
        )
    return f"""
<section class="evidence-layer" data-evidence-layer="metricDetail"{hidden}>
  <div id="metric-detail-summary" class="evidence-summary">{cards}</div>
</section>"""


def _repair_fund_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "repairFund")
    trace = _result_trace(state, "repairFund")
    rows = _trace_collection(trace, ("rows", "years"))
    table_rows = "".join(_repair_fund_year_row(row) for row in rows)
    if not table_rows:
        table_rows = '<tr><td>Evidence trace unavailable.</td><td></td><td></td><td></td><td></td><td></td></tr>'
    source_note = trace.get("sourceNote") or "Source: repairReservePathTrace from Python-owned calculator data."
    teaching_meta = []
    if trace.get("teachingOnly"):
        teaching_meta.append("Teaching-only")
    decision_id = trace.get("decisionId")
    if decision_id:
        teaching_meta.append(f"decision {decision_id}")
    if trace.get("workbookCanonical") is False:
        teaching_meta.append("not workbook-canonical")
    meta_line = " · ".join(teaching_meta)
    return f"""
<section class="evidence-layer" data-evidence-layer="repairFund"{hidden}>
  <div id="repair-fund-cards" class="evidence-summary repair-fund-cards">{_summary_cards_html(_trace_summary_cards(trace))}</div>
  <p class="layer-copy disclaimer teaching-only"{' data-decision-id="' + _attr(str(decision_id)) + '"' if decision_id else ""}>
    <strong>{_html(meta_line)}</strong> — {_html(source_note)}
  </p>
  <div class="tbl-scroll">
    <table class="fund-tbl" id="repair-fund-table">
      <thead>
        <tr><th>Year</th><th>Contribution</th><th>Repairs</th><th>Reserve balance</th><th>No-reserve shock</th><th>Status</th></tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</section>"""


def _repair_fund_year_row(row: Mapping[str, object]) -> str:
    events = _trace_collection(row, ("events",))
    event_labels = ", ".join(
        str(event.get("label") or event.get("component") or "Repair")
        for event in events
    )
    status = str(row.get("status") or "building")
    status_class = "fund-shortfall" if status == "shortfall" else "fund-depleted" if status == "depleted" else ""
    status_text = status.replace("-", " ")
    if event_labels:
        status_text = f"{status_text}: {event_labels}"
    return f"""<tr>
  <td>{_html(row.get("year"))}</td>
  <td class="num">{_html(_format(row.get("annualContribution"), "moneyCents"))}</td>
  <td class="num">{_html(_format(row.get("repairCost"), "money"))}</td>
  <td class="num">{_html(_format(row.get("endingBalance"), "money"))}</td>
  <td class="num">{_html(_format(row.get("noReserveSurpriseCost"), "money"))}</td>
  <td class="{_attr(status_class)}">{_html(status_text)}</td>
</tr>"""


def _repair_drivers_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "repairDrivers")
    trace = _result_trace(state, "repairDrivers")
    rows = _trace_collection(trace, ("displayRows", "rows", "drivers", "topDrivers"))
    table_rows = "".join(_repair_driver_row(row) for row in rows)
    if not table_rows:
        table_rows = '<tr><td>Evidence trace unavailable.</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>'
    return f"""
<section class="evidence-layer" data-evidence-layer="repairDrivers"{hidden}>
  <div id="repair-drivers-cards" class="evidence-summary repair-driver-cards">{_summary_cards_html(_trace_summary_cards(trace))}</div>
  <div class="tbl-scroll">
    <table class="drv-tbl" id="repair-drivers-table">
      <thead>
        <tr><th>Repair item</th><th>Monthly reserve</th><th>Share</th><th>Quantity</th><th>Age / life</th><th>Remaining</th><th>Source</th></tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</section>"""


def _repair_driver_row(row: Mapping[str, object]) -> str:
    share = _trace_value(row, ("shareOfReserve", "share", "percentOfReserve"))
    reserve = _trace_formatted_value(row, ("monthlyReserve", "value", "amount"), "moneyCents")
    source_text = str(row.get("source") or row.get("overrideStatus") or "Workbook default")
    source_class = "source-override" if source_text == "Walkthrough override" else ""
    remaining_life = _trace_value(row, ("remainingLife",))
    remaining_text = row.get("remainingLifeLabel") or (
        f"{_format(remaining_life, None)} yr" if remaining_life is not None else "-"
    )
    remaining_class = (
        "age-warn"
        if isinstance(remaining_life, (int, float)) and remaining_life < 5
        else ""
    )
    return f"""<tr>
  <td>{_html(row.get("component") or row.get("label") or row.get("name") or "")}</td>
  <td class="num">{_html(reserve)}</td>
  <td>{_repair_driver_share_bar(share)}</td>
  <td>{_html(_repair_driver_quantity_text(row))}</td>
  <td>{_html(_repair_driver_age_text(row))}</td>
  <td class="{_attr(remaining_class)}">{_html(remaining_text)}</td>
  <td class="{_attr(source_class)}">{_html(source_text)}</td>
</tr>"""


def _repair_driver_share_bar(share: object) -> str:
    percent = share * 100 if isinstance(share, (int, float)) else 0
    width = max(3, min(100, percent))
    return f"""
<div class="share-cell">
  <div class="bar-tr"><div class="bar-fl" style="width: {width:.1f}%"></div></div>
  <span>{_html(_format(share, "percent") if isinstance(share, (int, float)) else "-")}</span>
</div>"""


def _repair_driver_details(trace: Mapping[str, object]) -> str:
    cards = _trace_receipt_cards(trace)
    if not cards:
        return """
<div>
  <strong>Evidence trace unavailable</strong>
  <span>Run a calculation with core repair-driver trace data.</span>
</div>"""
    return "".join(
        f"""<div>
  <strong>{_html(card["label"])}</strong>
  <span>{_html(" | ".join(filter(None, [card["value"], card["note"]])))}</span>
</div>"""
        for card in cards
    )


def _ten_year_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "tenYear")
    trace = _result_trace(state, "tenYear")
    rows = _trace_collection(trace, ("rows", "years"))
    initial_investment = trace.get("initialInvestment", 0)
    table_rows = "".join(
        _ten_year_table_row(row, initial_investment)
        for row in rows
    )
    empty_columns = 12
    if not table_rows:
        table_rows = (
            f'<tr><td colspan="{empty_columns}">Evidence trace unavailable.</td></tr>'
        )
    cards = _trace_summary_cards(trace) + _trace_receipt_cards(trace)
    return f"""
<section class="evidence-layer" data-evidence-layer="tenYear"{hidden}>
  <div id="ten-year-summary" class="evidence-summary">{_summary_cards_html(cards)}</div>
  <div class="table-wrap">
    <table class="evidence-table">
      <thead><tr>
        <th>Year</th>
        <th>Liquidation wealth (L17)</th>
        <th>Accumulated cash (L16)</th>
        <th>Annual reserve contribution</th>
        <th>Accumulated reserve (L15)</th>
        <th>Future property value (B23)</th>
        <th>Remaining loan balance (B24)</th>
        <th>Cost of sale (B25)</th>
        <th>Net proceeds (B26)</th>
        <th>Cash position (L16 + initial)</th>
        <th>Money market</th>
        <th>Conservative IRA</th>
      </tr></thead>
      <tbody id="ten-year-table">{table_rows}</tbody>
    </table>
  </div>
</section>"""


def _ten_year_table_row(
    row: Mapping[str, object],
    initial_investment: object,
) -> str:
    accumulated_cash = row.get("accumulatedTrueCashFlow")
    cash_position = None
    if isinstance(accumulated_cash, (int, float)) and isinstance(
        initial_investment,
        (int, float),
    ):
        cash_position = initial_investment + accumulated_cash
    return f"""<tr>
  <td>{_html(_trace_value(row, ("year", "label")))}</td>
  <td>{_html(_trace_formatted_value(row, ("realEstateLiquidationWealth", "rentalPath", "rentalWealth"), "money"))}</td>
  <td>{_html(_format(accumulated_cash, "money"))}</td>
  <td>{_html(_format(row.get("annualCapexContribution"), "money"))}</td>
  <td>{_html(_format(row.get("accumulatedCapexReserve"), "money"))}</td>
  <td>{_html(_format(row.get("futurePropertyValue"), "money"))}</td>
  <td>{_html(_format(row.get("remainingLoanBalance"), "money"))}</td>
  <td>{_html(_format(row.get("costOfSale"), "money"))}</td>
  <td>{_html(_format(row.get("netProceeds"), "money"))}</td>
  <td>{_html(_format(cash_position, "money"))}</td>
  <td>{_html(_trace_formatted_value(row, ("moneyMarketComparison", "moneyMarket"), "money"))}</td>
  <td>{_html(_trace_formatted_value(row, ("conservativeIraComparison", "conservativeIra"), "money"))}</td>
</tr>"""


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
    return f"""
<section class="evidence-layer" data-evidence-layer="diagnostics"{hidden}>
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
  </details>
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


def _sinking_fund_panel(state: UiState) -> str:
    rows = []
    if state.result:
        rows = [
            f"""<tr>
  <td>{_html(row.get("component"))}</td>
  <td>{_html(_format(row.get("localUnitCost"), "moneyCents"))}</td>
  <td>{_html(_format(row.get("effectiveQuantity"), None))}</td>
  <td>{_html(_format(row.get("effectiveAge"), None))}</td>
  <td>{_html(_format(row.get("remainingLife"), None))}</td>
  <td>{_html(_format(row.get("futureCost"), "money"))}</td>
  <td>{_html(_format(row.get("monthlyReserve"), "moneyCents"))}</td>
</tr>"""
            for row in state.result.get("sinkingFundRows", [])
        ]
    return f"""
<section class="table-panel">
  <div class="section-head"><h2>Sinking Fund</h2></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Component</th><th>Unit Cost</th><th>Qty</th><th>Age</th><th>Life</th><th>Future Cost</th><th>Monthly Reserve</th></tr></thead>
      <tbody id="sinking-table">{''.join(rows)}</tbody>
    </table>
  </div>
</section>"""


def _proforma_panel(state: UiState) -> str:
    rows = []
    if state.result:
        rows = [
            f"""<tr>
  <td>{_html(row.get("year"))}</td>
  <td>{_html(_format(row.get("accumulatedTrueCashFlow"), "money"))}</td>
  <td>{_html(_format(row.get("realEstateLiquidationWealth"), "money"))}</td>
  <td>{_html(_format(row.get("moneyMarketComparison"), "money"))}</td>
  <td>{_html(_format(row.get("conservativeIraComparison"), "money"))}</td>
</tr>"""
            for row in state.result.get("proForma", [])
        ]
    return f"""
<section class="table-panel">
  <div class="section-head"><h2>10-Year Pro Forma</h2></div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Year</th><th>Cash Flow</th><th>Liquidation Wealth</th><th>Money Market</th><th>Conservative IRA</th></tr></thead>
      <tbody id="proforma-table">{''.join(rows)}</tbody>
    </table>
  </div>
</section>"""


def _summary_cards_html(cards: Sequence[Mapping[str, object]]) -> str:
    if not cards:
        cards = [
            {
                "label": "Evidence trace unavailable",
                "value": "-",
                "note": "Run a calculation with core trace data.",
            }
        ]
    return "".join(
        f"""<div class="evidence-card">
  <strong>{_html(card.get("label", ""))}</strong>
  <span>{_html(card.get("value", ""))}</span>
  {f'<small>{_html(card.get("note", ""))}</small>' if card.get("note") else ""}
</div>"""
        for card in cards
    )


def _trace_summary_cards(trace: Mapping[str, object]) -> list[dict[str, object]]:
    cards = []
    for card in _trace_collection(trace, ("summaryCards", "summary", "cards")):
        label = card.get("label") or card.get("title") or card.get("id")
        if not label:
            continue
        cards.append(
            {
                "label": label,
                "value": _trace_formatted_value(card, ("value", "amount", "metricValue"), card.get("kind")),
                "note": card.get("note") or card.get("description") or card.get("detail") or "",
            }
        )
    return cards


def _trace_receipt_cards(trace: Mapping[str, object]) -> list[dict[str, object]]:
    cards = []
    for receipt in _trace_collection(trace, ("receipts",)):
        label = receipt.get("label") or receipt.get("title") or receipt.get("id")
        if not label:
            continue
        details = [
            f"Source: {receipt['workbookSource']}" if receipt.get("workbookSource") else "",
            f"Formula: {receipt['formula']}" if receipt.get("formula") else "",
            receipt.get("sourceNote") or "",
        ]
        cards.append(
            {
                "label": label,
                "value": _trace_formatted_value(receipt, ("value", "amount"), receipt.get("kind")),
                "note": " | ".join(filter(None, details)),
            }
        )
    return cards


def _trace_collection(
    source: object,
    keys: Sequence[str],
) -> list[Mapping[str, object]]:
    if isinstance(source, list):
        return [item for item in source if isinstance(item, Mapping)]
    if not isinstance(source, Mapping):
        return []
    for key in keys:
        value = source.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _trace_value(source: Mapping[str, object], keys: Sequence[str]) -> object:
    return _first_present(source, keys)


def _trace_formatted_value(
    source: Mapping[str, object],
    keys: Sequence[str],
    fallback_kind: object,
) -> str:
    formatted = source.get("formattedValue") or source.get("displayValue")
    if formatted is not None:
        return str(formatted)
    return _format(_trace_value(source, keys), source.get("kind") or source.get("valueKind") or fallback_kind)


def _trace_check_text(check: object) -> str:
    if not check:
        return ""
    if isinstance(check, str):
        return check
    if not isinstance(check, Mapping):
        return str(check)
    parts = []
    if check.get("engineValue") is not None:
        parts.append(f"engine {_format(check.get('engineValue'), check.get('kind'))}")
    if check.get("delta") is not None:
        parts.append(f"delta {_format(check.get('delta'), check.get('kind') or 'moneyCents')}")
    return "; ".join(parts)


def _result_trace(state: UiState, name: str) -> Mapping[str, object]:
    if not state.result:
        return {}
    trace = state.result.get("traces", {}).get(name, {})
    return trace if isinstance(trace, Mapping) else {}


def _repair_driver_quantity_text(row: Mapping[str, object]) -> str:
    if row.get("quantityLabel") is not None:
        return str(row["quantityLabel"])
    effective = _trace_value(row, ("effectiveQuantity", "quantity"))
    default = _trace_value(row, ("defaultQuantity",))
    source = row.get("quantitySource") or ""
    effective_text = _format(effective, None)
    if default is None or default == effective:
        return f"{effective_text} ({source})" if source else effective_text
    return f"{effective_text} from {_format(default, None)} default"


def _repair_driver_age_text(row: Mapping[str, object]) -> str:
    if row.get("ageLifeLabel") is not None:
        return str(row["ageLifeLabel"])
    age = _trace_value(row, ("effectiveAge", "age"))
    remaining_life = _trace_value(row, ("remainingLife", "life"))
    age_source = row.get("ageSource") or ""
    parts = []
    if age is not None:
        parts.append(f"{_format(age, None)} years old")
    if remaining_life is not None:
        parts.append(f"{_format(remaining_life, None)} years left")
    if age_source:
        parts.append(str(age_source))
    return " / ".join(parts)


def _value_at_path(source: Mapping[str, object], path: str) -> object:
    current: object = source
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _first_present(source: Mapping[str, object], keys: Sequence[str]) -> object:
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return None
