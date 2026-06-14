from __future__ import annotations

from typing import Mapping, Sequence

from capex3.core.teaching.evidence_presentation import drilldown_title as _drilldown_title
from capex3.core.teaching.evidence_presentation import primary_reward_key
from capex3.presentation.htmx_evidence_primitives import (
    _drivers_table,
    _evidence_drilldown,
    _evidence_focus_class,
    _evidence_layer_shell,
    _receipt_empty_row,
    _receipt_panel,
    _receipt_waterfall,
)
from capex3.presentation.htmx_format import (
    _attr,
    _format,
    _format_receipt_value,
    _html,
    _hx_post,
)
from capex3.presentation.htmx_charts import _evidence_graph
from capex3.presentation.htmx_shell import _summary_panel
from capex3.presentation.htmx_state import (
    UiState,
    _active_evidence_layer,
    _active_step,
    _evidence_layers,
    _hidden_attr_for_layer,
    _metric_strip_navigation_by_field,
    _results_summary_for_state,
    _source_metric_strip_fields,
)
from capex3.presentation.htmx_trace import (
    _first_present,
    _result_trace,
    _trace_collection,
    _trace_value,
)


def _results_summary_strip(state: UiState) -> str:
    summary = _results_summary_for_state(state)
    return f"""
  <div class="results-summary" id="results-summary">
{_summary_panel(summary["label"], summary["value"], summary["footnote"])}
  </div>"""


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
        else f"Viewing: {layer.get('title', '')}"
    )
    checked = " checked" if state.evidence_follows_step else ""
    overview_button = (
        f"""<button id="overview-button" class="btn-ghost btn-sm overview-button" type="button" name="activeEvidenceLayer" value="tenYear" {_hx_post("/ui/evidence")}>Overview</button>"""
        if state.active_evidence_layer != "tenYear"
        else ""
    )
    pin_badge = ""
    return f"""
<section class="output-panel right-panel calc-results">
  {error}
{_results_summary_strip(state)}
  <div class="results-body">
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
              Follow current step
            </label>
          </div>
          <div class="evidence-hero chart-stage">
            {_evidence_graph(state)}
          </div>
          <div class="metric-grid metric-strip chart-summary" id="metric-grid" data-source-role="metric-strip">{_metric_cards(state)}</div>
          {_metric_breakdown_panel(state)}
          {_evidence_sections(state)}
        </div>
        <aside class="layer-rail" aria-label="Evidence layers">
          <p>Views</p>
          <div class="evidence-tabs" id="evidence-tabs">{_evidence_tabs(state)}</div>
        </aside>
      </div>
    </div>
  </div>
</section>"""


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
        is_active = field == state.active_metric_field
        if is_active or metric.get("evidenceLayerId") == state.active_evidence_layer:
            classes.append("active")
        expanded = "true" if is_active else "false"
        nav = _metric_strip_navigation_by_field(state.workbench).get(field, {})
        cta = "Hide breakdown" if is_active else str(nav.get("cta") or "Details")
        button_value = "" if is_active else field
        cards.append(
            f"""<button type="button" class="{' '.join(classes)}" aria-expanded="{expanded}" name="activeMetricField" value="{_attr(button_value)}" {_hx_post("/ui/metric")}>
  <strong>{_html(metric.get("label", field))}</strong>
  <span>{_html(_format(value, metric.get("kind") or metric.get("valueKind")))}</span>
  <small class="metric-cta">{_html(cta)}</small>
</button>"""
        )
    return "\n".join(cards)


def _metric_breakdown_panel(state: UiState) -> str:
    if not state.active_metric_field:
        return ""
    nav = _metric_strip_navigation_by_field(state.workbench).get(state.active_metric_field, {})
    layer_id = str(nav.get("layer") or "")
    if layer_id != state.active_evidence_layer:
        return ""
    expected_focus = primary_reward_key(layer_id)
    if expected_focus and nav.get("focus") != expected_focus:
        return ""
    if layer_id != "cashFlow":
        return ""
    receipt_html = _cash_flow_receipt_waterfall(
        state,
        extra_classes="evidence-reward evidence-focus",
    )
    return _receipt_panel(
        "Cash flow breakdown",
        receipt_html,
        panel_class="metric-breakdown-panel",
        panel_id="metric-breakdown-panel",
    )


def _evidence_sections(state: UiState) -> str:
    from capex3.presentation.htmx_offer_ready import (
        _cash_flow_stability_section,
        _what_works_section,
    )

    return "\n".join(
        [
            _ten_year_section(state),
            _cash_flow_section(state),
            _repair_drivers_section(state),
            _repair_fund_section(state),
            _cash_flow_stability_section(state),
            _what_works_section(state),
        ]
    )


def _cash_flow_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "cashFlow")
    trace = _result_trace(state, "cashFlow")
    focus_class = _evidence_focus_class(state, "cashFlow")
    layer_copy = (
        ""
        if focus_class
        else (
            '<p class="layer-copy">This layer shows the dashboard snapshot: '
            "true monthly cash flow after deducting the full monthly repair reserve every month—not "
            "the post-cap annual contribution from the pro forma. After the reserve cap fills, cash "
            "improvement shows up in accumulated cash flow; open the 10-Year Story "
            "view to follow that path.</p>"
        )
    )
    receipt_reward = _cash_flow_receipt_waterfall(
        state,
        extra_classes="evidence-reward",
        receipt_id="cash-flow-receipt",
    )
    receipt_detail = _cash_flow_receipt_waterfall(state, extra_classes="receipt-detail")
    drilldown = _evidence_drilldown(_drilldown_title(trace), receipt_detail)
    if focus_class:
        body = f"""
  {drilldown}"""
    else:
        body = f"""
  {_receipt_panel("Cash flow breakdown", receipt_reward)}
  {drilldown}"""
    return _evidence_layer_shell(
        "cashFlow",
        hidden=hidden,
        trace=trace,
        layer_copy=layer_copy,
        body_html=body,
        include_reward_label=False,
    )


def _cash_flow_receipt_rows(state: UiState) -> str:
    trace = _result_trace(state, "cashFlow")
    rows = _trace_collection(trace, ("rows", "lines"))
    if not rows:
        return _receipt_empty_row()
    return "".join(_cash_flow_receipt_row(row) for row in rows)


def _cash_flow_receipt_waterfall(
    state: UiState,
    *,
    extra_classes: str = "",
    receipt_id: str = "",
) -> str:
    return _receipt_waterfall(
        _cash_flow_receipt_rows(state),
        extra_classes=extra_classes,
        receipt_id=receipt_id,
    )


def _cash_flow_receipt_row(row: Mapping[str, object]) -> str:
    receipt_kind = str(row.get("receiptKind") or "")
    row_class = "total-row" if receipt_kind == "total" else "sub" if receipt_kind == "subtotal" else ""
    value = _trace_value(row, ("value", "amount"))
    value_class = "rcpt-val"
    if receipt_kind == "deduction":
        value_class += " ded"
    elif receipt_kind == "total":
        value_class += " neg" if isinstance(value, (int, float)) and value < 0 else " pos"
    return f"""
<div class="rcpt-row {row_class}">
  <span class="rcpt-label">{_html(row.get("label") or row.get("title") or row.get("id") or "")}</span>
  <span class="{_attr(value_class)}">{_html(_format_receipt_value(value, row.get("kind")))}</span>
</div>"""


def _repair_fund_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "repairFund")
    trace = _result_trace(state, "repairFund")
    rows = _trace_collection(trace, ("rows", "years"))
    table_rows = "".join(_repair_fund_year_row(row) for row in rows)
    if not table_rows:
        table_rows = (
            '<tr><td>Evidence trace unavailable.</td><td></td><td></td>'
            "<td></td><td></td><td></td><td></td></tr>"
        )
    table_html = f"""
<div class="tbl-scroll">
  <table class="fund-tbl" id="repair-fund-table">
    <thead>
      <tr><th>Year</th><th>Contribution</th><th>Interest earned</th><th>Repairs</th><th>Reserve balance</th><th>No-reserve shock</th><th>Status</th></tr>
    </thead>
    <tbody>{table_rows}</tbody>
  </table>
</div>"""
    drilldown = _evidence_drilldown(_drilldown_title(trace), table_html)
    body = f"""
  <div id="repair-fund-cards" class="evidence-summary repair-fund-cards evidence-reward">{_summary_cards_html(_trace_summary_cards(trace))}</div>
  {drilldown}"""
    return _evidence_layer_shell(
        "repairFund",
        hidden=hidden,
        trace=trace,
        body_html=body,
    )


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
  <td class="num">{_html(_format(row.get("interestEarned"), "money"))}</td>
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
    top_rows = rows[:5]
    reward_table_rows = "".join(_repair_driver_row(row) for row in top_rows)
    if not reward_table_rows:
        reward_table_rows = table_rows
    focus_class = _evidence_focus_class(state, "repairDrivers")
    reward_table = _drivers_table("repair-drivers-reward-table", reward_table_rows)
    drilldown = _evidence_drilldown(
        _drilldown_title(trace),
        _drivers_table("repair-drivers-table", table_rows),
    )
    body = f"""
  <div id="repair-drivers-cards" class="evidence-summary repair-driver-cards evidence-reward{focus_class}">{_summary_cards_html(_trace_summary_cards(trace))}</div>
  {reward_table}
  {drilldown}"""
    return _evidence_layer_shell(
        "repairDrivers",
        hidden=hidden,
        trace=trace,
        body_html=body,
    )


def _repair_driver_row(row: Mapping[str, object]) -> str:
    share = _trace_value(row, ("shareOfReserve", "share", "percentOfReserve"))
    reserve = _trace_formatted_value(row, ("monthlyReserve", "value", "amount"), "moneyCents")
    source_text = str(row.get("source") or row.get("overrideStatus") or "Default")
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
    table_html = f"""
<div class="table-wrap">
  <table class="evidence-table">
    <thead><tr>
      <th>Year</th>
      <th>Liquidation wealth</th>
      <th>Accumulated cash</th>
      <th>Annual reserve contribution</th>
      <th>Accumulated reserve</th>
      <th>Future property value</th>
      <th>Remaining loan balance</th>
      <th>Cost of sale</th>
      <th>Net proceeds</th>
      <th>Cash position (operating + initial)</th>
      <th>Money market</th>
      <th>Conservative IRA</th>
    </tr></thead>
    <tbody id="ten-year-table">{table_rows}</tbody>
  </table>
</div>"""
    drilldown = _evidence_drilldown(_drilldown_title(trace), table_html)
    body = f"""
  <div id="ten-year-summary" class="evidence-summary evidence-reward">{_summary_cards_html(cards)}</div>
  {drilldown}"""
    return _evidence_layer_shell(
        "tenYear",
        hidden=hidden,
        trace=trace,
        body_html=body,
    )


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


def _trace_formatted_value(
    source: Mapping[str, object],
    keys: Sequence[str],
    fallback_kind: object,
) -> str:
    formatted = source.get("formattedValue") or source.get("displayValue")
    if formatted is not None:
        return str(formatted)
    return _format(_trace_value(source, keys), source.get("kind") or source.get("valueKind") or fallback_kind)


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

