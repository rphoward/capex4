from __future__ import annotations

from typing import Mapping

from capex3.core.teaching.calculation_result_traces import SOLVER_DISCLAIMER
from capex3.core.teaching.offer_ready_evidence import build_offer_ready_copy
from capex3.presentation.htmx_format import (
    _attr,
    _control_value,
    _format,
    _format_abs_money,
    _hidden,
    _html,
    _hx_post,
)
from capex3.presentation.htmx_evidence import (
    _result_trace,
    _summary_cards_html,
    _trace_collection,
    _trace_summary_cards,
)
from capex3.presentation.htmx_state import UiState, _hidden_attr_for_layer


def _offer_ready_panel(state: UiState) -> str:
    copy = build_offer_ready_copy(state.result)
    shock: Mapping[str, object] = {}
    ledger: Mapping[str, object] = {}
    if state.result:
        shock_value = state.result.get("shockSurvival", {})
        ledger_value = state.result.get("emergencyDebtLedger", {})
        shock = shock_value if isinstance(shock_value, Mapping) else {}
        ledger = ledger_value if isinstance(ledger_value, Mapping) else {}

    survives = bool(state.result.get("dealSurvives")) if state.result else False
    survival_class = "offer-ready-pass" if survives else "offer-ready-fail"
    cards = [
        {
            "label": copy["survivalHeadline"],
            "value": copy["survivalDetail"],
            "note": "",
        },
        {
            "label": copy["shockAdjustedLabel"],
            "value": _format(shock.get("shockAdjustedCashFlow"), "moneyCents"),
            "note": "",
        },
        {
            "label": copy["trueMonthlyLabel"],
            "value": _format(shock.get("trueMonthlyCashFlow"), "moneyCents"),
            "note": (
                f"{copy['floorLabel']}: "
                f"{_format(shock.get('minimumTrueMonthlyCashFlow'), 'moneyCents')}"
            ),
        },
    ]

    warnings = ""
    if state.overlap_warning_latched:
        warnings += (
            f'<div class="offer-ready-warning overlap-warning" id="overlap-warning">'
            f"{_html(copy['overlapWarning'])}</div>"
        )
    if ledger.get("makeReadyShortfallFlag"):
        reason = ledger.get("reason") or ""
        warnings += f"""
<div class="offer-ready-warning make-ready-warning" id="make-ready-warning">
  <strong>{_html(copy["makeReadyIntro"])}</strong>
  <p>{_html(reason)}</p>
</div>"""

    reserve_solver = _offer_ready_reserve_solver_html(state, copy)

    return f"""
<div class="offer-ready-panel" id="offer-ready-panel">
  <div class="section-head compact">
    <h2>Offer-ready survival</h2>
    <button id="new-walkthrough-button" type="button" {_hx_post("/ui/new-walkthrough")}>New walkthrough</button>
  </div>
  <div class="offer-ready-status {_attr(survival_class)}">{_summary_cards_html(cards)}</div>
  {warnings}
  {reserve_solver}
</div>"""


def _cash_flow_stability_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "cashFlowStability")
    trace = _result_trace(state, "cashFlowStability")
    if not trace:
        return f"""
<section class="evidence-layer" data-evidence-layer="cashFlowStability"{hidden}>
  <div class="error-text">Evidence trace unavailable.</div>
</section>"""

    two_path = trace.get("twoPathComparison", {})
    if not isinstance(two_path, Mapping):
        two_path = {}
    planned = two_path.get("plannedReservePath", {})
    debt_shock = two_path.get("debtShockPath", {})
    if not isinstance(planned, Mapping):
        planned = {}
    if not isinstance(debt_shock, Mapping):
        debt_shock = {}

    planned_rows = "".join(
        _cash_flow_stability_path_row(row)
        for row in _trace_collection(planned, ("rows",))
    )
    debt_shock_rows = "".join(
        _cash_flow_stability_path_row(row)
        for row in _trace_collection(debt_shock, ("rows",))
    )
    if not planned_rows:
        planned_rows = '<div class="rcpt-row"><span>Evidence trace unavailable.</span><span class="rcpt-val">-</span></div>'
    if not debt_shock_rows:
        debt_shock_rows = '<div class="rcpt-row"><span>Evidence trace unavailable.</span><span class="rcpt-val">-</span></div>'

    timeline = trace.get("debtLedgerTimeline", {})
    if not isinstance(timeline, Mapping):
        timeline = {}
    refi_rows = "".join(
        _cash_flow_stability_refi_row(event)
        for event in _trace_collection(timeline, ("refinanceEvents",))
    )
    if not refi_rows:
        refi_rows = "<tr><td colspan=\"6\">No emergency refi events in the modeled window.</td></tr>"

    payment_rows = "".join(
        _cash_flow_stability_payment_row(row)
        for row in _trace_collection(timeline, ("paymentMonths",))
        if float(row.get("debtService") or 0.0) > 0.0
    )
    if not payment_rows:
        payment_rows = "<tr><td colspan=\"3\">No emergency debt service months.</td></tr>"

    teaching = trace.get("teaching")
    framing = trace.get("primaryFramingCopy") or (
        teaching.get("primaryFramingCopy", "")
        if isinstance(teaching, Mapping)
        else ""
    )
    source_note = trace.get("sourceNote") or "App-only resilience evidence."
    meta_line = "App-only resilience · not workbook-canonical"
    return f"""
<section class="evidence-layer" data-evidence-layer="cashFlowStability"{hidden}>
  <p class="layer-copy">{_html(framing)}</p>
  <div id="cash-flow-stability-cards" class="evidence-summary cash-flow-stability-cards">{_summary_cards_html(_trace_summary_cards(trace))}</div>
  <p class="layer-copy disclaimer app-regression">
    <strong>{_html(meta_line)}</strong> — {_html(str(source_note))}
  </p>
  <div class="two-path-comparison" id="cash-flow-stability-two-path">
    <div class="two-path-column">
      <h3>{_html(planned.get("title", "Planned reserve path"))}</h3>
      <div class="receipt">{planned_rows}</div>
    </div>
    <div class="two-path-column">
      <h3>{_html(debt_shock.get("title", "Debt-shock path"))}</h3>
      <div class="receipt">{debt_shock_rows}</div>
    </div>
  </div>
  <div class="tbl-scroll">
    <table class="ledger-tbl" id="cash-flow-stability-refi-table">
      <thead>
        <tr><th>Year</th><th>Emergency gap</th><th>Principal</th><th>Monthly payment</th><th>Prior schedule active</th><th>Start month</th></tr>
      </thead>
      <tbody>{refi_rows}</tbody>
    </table>
  </div>
  <div class="tbl-scroll">
    <table class="ledger-tbl" id="cash-flow-stability-payment-table">
      <thead>
        <tr><th>Month</th><th>Debt service</th><th>Active refi year</th></tr>
      </thead>
      <tbody>{payment_rows}</tbody>
    </table>
  </div>
</section>"""


def _cash_flow_stability_path_row(row: Mapping[str, object]) -> str:
    value = row.get("value")
    kind = row.get("kind")
    if kind == "boolean":
        display = "Yes" if value else "No"
    else:
        display = _format(value, kind)
    return f"""
<div class="rcpt-row">
  <span>{_html(row.get("label") or row.get("role") or "")}</span>
  <span class="rcpt-val">{_html(display)}</span>
</div>"""


def _cash_flow_stability_refi_row(event: Mapping[str, object]) -> str:
    prior = "Yes" if event.get("priorScheduleActive") else "No"
    return f"""<tr>
  <td>{_html(event.get("year"))}</td>
  <td class="num">{_html(_format(event.get("emergencyGap"), "money"))}</td>
  <td class="num">{_html(_format(event.get("outstandingPrincipal"), "money"))}</td>
  <td class="num">{_html(_format(event.get("monthlyPayment"), "moneyCents"))}</td>
  <td>{_html(prior)}</td>
  <td class="num">{_html(event.get("paymentStartMonth"))}</td>
</tr>"""


def _cash_flow_stability_payment_row(row: Mapping[str, object]) -> str:
    return f"""<tr>
  <td class="num">{_html(row.get("month"))}</td>
  <td class="num">{_html(_format(row.get("debtService"), "moneyCents"))}</td>
  <td class="num">{_html(row.get("activeRefiYear") or "-")}</td>
</tr>"""


def _what_works_section(state: UiState) -> str:
    hidden = _hidden_attr_for_layer(state, "whatWorks")
    trace = _result_trace(state, "whatWorks")
    questions = _trace_collection(trace, ("questions", "thresholdQuestions", "solverQuestions"))
    threshold_cards = "".join(_threshold_card(state, question) for question in questions)
    if not threshold_cards:
        threshold_cards = '<div class="error-text">Evidence trace unavailable.</div>'
    layer_copy = trace.get("layerCopy") or SOLVER_DISCLAIMER["layerCopy"]
    solver_note = trace.get("solverNote") or SOLVER_DISCLAIMER["solverNote"]
    disclaimer = _solver_disclaimer_html(trace)
    return f"""
<section class="evidence-layer" data-evidence-layer="whatWorks"{hidden}>
  {disclaimer}
  <p class="layer-copy">{_html(str(layer_copy))}</p>
  <div class="slv-grid" id="threshold-grid">{threshold_cards}</div>
  <div class="slv-note">{_html(str(solver_note))}</div>
</section>"""


def _threshold_card(state: UiState, question: Mapping[str, object]) -> str:
    question_id = str(question.get("id") or "")
    label = question.get("label") or question.get("title") or question.get("question") or question_id
    detail = question.get("detail") or question.get("description") or question.get("prompt") or question.get("target") or ""
    disabled = "" if question_id and question.get("solver") else " disabled"
    solver_preview = question.get("solverPreview", {})
    solved_value = solver_preview.get("solvedValue") if isinstance(solver_preview, Mapping) else None
    solved_text = (
        _format(solved_value, question.get("solvedValueKind") or "number")
        if solved_value is not None
        else str(solver_preview.get("message") or "No solved value")
        if isinstance(solver_preview, Mapping)
        else "No solved value"
    )
    state_class = "threshold-ok" if question.get("thresholdState") == "ok" else "threshold-warn"
    gap_text = _threshold_gap_text(question)
    preview = ""
    if state.solver_preview and state.solver_preview.get("source") == f"threshold:{question_id}":
        preview = _solver_preview_html(state.solver_preview)
    return f"""
<div class="slv-card threshold-card {state_class}">
  <p class="threshold-id">{_html(question_id)}</p>
  <p class="slv-q">{_html(detail or label)}</p>
  <p class="slv-v">{_html(solved_text)}</p>
  <p class="slv-gap">{_html(gap_text)}</p>
  <button type="button" name="questionId" value="{_attr(question_id)}" {_hx_post("/ui/solve-threshold")}{disabled}>Solve</button>
  {preview}
</div>"""


def _threshold_gap_text(question: Mapping[str, object]) -> str:
    solver_preview = question.get("solverPreview", {})
    if isinstance(solver_preview, Mapping) and not solver_preview.get("ok"):
        return str(solver_preview.get("message") or "Solver could not bracket this target.")
    gap_value = question.get("gapValue")
    if not isinstance(gap_value, (int, float)):
        return "Current input already matches this threshold."
    baseline_by_question = {
        "breakEvenRent": "current rent",
        "maxPurchasePriceCashFlowZero": "current price",
        "requiredDownPaymentCashFlowZero": "current down payment",
        "maxRehabBudgetCashOnCash8Pct": "current rehab estimate",
    }
    baseline = baseline_by_question.get(str(question.get("id")), "current input")
    direction = "above" if gap_value > 0 else "below"
    return f"{_format_abs_money(gap_value)} {direction} {baseline}"


def _offer_ready_reserve_solver_html(
    state: UiState,
    copy: Mapping[str, str],
) -> str:
    result = state.result or {}
    first_raw_year = result.get("firstRawShortfallYear")
    first_gap_year = result.get("firstEmergencyGapYear")
    preview_html = ""
    if (
        state.solver_preview
        and state.last_input_change_reason == "solve-reserve-first-shortfall"
    ):
        preview_html = _reserve_solver_preview_html(state.solver_preview, copy)

    if first_raw_year == 1:
        return f"""
<section class="offer-ready-reserve-solver" id="reserve-first-shortfall-solver">
  <h3>{_html(copy["reserveSolverTitle"])}</h3>
  <p class="layer-copy">{_html(copy["reserveSolverYearOneDeclined"])}</p>
</section>"""

    if first_gap_year is None:
        return ""

    solve_button = (
        f'<button type="button" name="questionId" value="reserveIncreaseFirstShortfall" '
        f'{_hx_post("/ui/solve-reserve-first-shortfall")}>Solve reserve bump</button>'
    )
    overlap_note = ""
    if state.overlap_warning_latched:
        overlap_note = (
            f'<p class="offer-ready-warning overlap-warning-note">'
            f'{_html(copy["reserveSolverOverlapNote"])}</p>'
        )

    return f"""
<section class="offer-ready-reserve-solver" id="reserve-first-shortfall-solver">
  <h3>{_html(copy["reserveSolverTitle"])}</h3>
  <p class="layer-copy">{_html(copy["reserveSolverPrompt"])}</p>
  <p class="layer-copy disclaimer app-regression"><small>{_html(copy["reserveSolverDisclaimer"])}</small></p>
  {overlap_note}
  <p class="layer-copy"><small>First emergency gap at year {_html(first_gap_year)}.</small></p>
  <div class="reserve-solver-actions">{solve_button}</div>
  {preview_html}
</section>"""


def _reserve_solver_preview_html(
    preview: Mapping[str, object],
    copy: Mapping[str, str],
) -> str:
    footnote = (
        f'<p class="solver-preview-footnote"><small>{_html(copy["reserveSolverApplyNote"])}</small></p>'
    )
    if not preview.get("ok"):
        return f"""
<div class="solver-preview error reserve-solver-preview">
  <div class="solver-preview-head"><span class="preview-badge error">Solver error</span></div>
  <p>{_html(preview.get("message", "The reserve solver could not produce a preview."))}</p>
  {footnote}
</div>"""
    solved_value = preview.get("solvedValue")
    return f"""
<div class="solver-preview current reserve-solver-preview">
  <div class="solver-preview-head">
    <span class="preview-badge current">Reserve solver preview</span>
    <span>{_html(preview.get("assumptionText", ""))}</span>
  </div>
  <dl class="solver-preview-grid">
    <div><dt>Monthly reserve increase</dt><dd>{_html(_format(solved_value, preview.get("solvedValueKind")))}</dd></div>
    <div><dt>First-gap check</dt><dd>{_html(_format(preview.get("solvedMetricValue"), preview.get("solvedMetricKind")))}</dd></div>
  </dl>
  {_hidden("solverApplyField", preview.get("applyField", ""))}
  {_hidden("solverSolvedValue", _control_value(solved_value))}
  <div class="solver-preview-actions">
    <button type="button" data-solver-apply {_hx_post("/ui/apply-solver")}>Apply monthly reserve increase</button>
    <small>{_html(copy["reserveSolverApplyNote"])}</small>
  </div>
  {footnote}
</div>"""


def _solver_preview_footnote_html(preview: Mapping[str, object]) -> str:
    footnote = preview.get("previewFootnote") or SOLVER_DISCLAIMER["previewFootnote"]
    return (
        f'<p class="solver-preview-footnote"><small>{_html(str(footnote))}</small></p>'
        if footnote
        else ""
    )


def _solver_preview_html(preview: Mapping[str, object]) -> str:
    footnote = _solver_preview_footnote_html(preview)
    if not preview.get("ok"):
        return f"""
<div class="solver-preview error">
  <div class="solver-preview-head"><span class="preview-badge error">Solver error</span></div>
  <p>{_html(preview.get("message", "The solver could not produce a preview."))}</p>
  {footnote}
</div>"""
    solved_value = preview.get("solvedValue")
    return f"""
<div class="solver-preview current">
  <div class="solver-preview-head">
    <span class="preview-badge current">Solved preview</span>
    <span>{_html(preview.get("assumptionText", ""))}</span>
  </div>
  <dl class="solver-preview-grid">
    <div><dt>Would change</dt><dd>{_html(preview.get("applyLabel", ""))}</dd></div>
    <div><dt>From</dt><dd>{_html(_format(preview.get("previousValue"), preview.get("solvedValueKind")))}</dd></div>
    <div><dt>To</dt><dd>{_html(_format(solved_value, preview.get("solvedValueKind")))}</dd></div>
    <div><dt>Target check</dt><dd>{_html(_format(preview.get("solvedMetricValue"), preview.get("solvedMetricKind")))} {_html(preview.get("metricLabel", ""))}</dd></div>
  </dl>
  {_hidden("solverApplyField", preview.get("applyField", ""))}
  {_hidden("solverSolvedValue", _control_value(solved_value))}
  <div class="solver-preview-actions">
    <button type="button" data-solver-apply {_hx_post("/ui/apply-solver")}>Apply {_html(preview.get("variableLabel", "value"))}</button>
    <small>Apply this one solved input, then recalculate.</small>
  </div>
  {footnote}
</div>"""


def _solver_disclaimer_html(disclaimer: Mapping[str, object]) -> str:
    source_note = disclaimer.get("sourceNote")
    if not source_note:
        return ""
    meta_parts = []
    if disclaimer.get("appRegressionOnly"):
        meta_parts.append("App-side regression only")
    if disclaimer.get("workbookCanonical") is False:
        meta_parts.append("not workbook-canonical")
    meta_line = " · ".join(meta_parts) if meta_parts else "Solver disclaimer"
    return f"""
  <p class="layer-copy disclaimer app-regression">
    <strong>{_html(meta_line)}</strong> — {_html(str(source_note))}
  </p>"""


def _solver_workbench_disclaimer_html(workbench: Mapping[str, object]) -> str:
    disclaimer = workbench.get("solverDisclaimer")
    if not isinstance(disclaimer, Mapping):
        disclaimer = SOLVER_DISCLAIMER
    block = _solver_disclaimer_html(disclaimer)
    if not block:
        return ""
    return block.replace(
        'class="layer-copy disclaimer app-regression"',
        'class="layer-copy disclaimer app-regression solver-workbench-disclaimer"',
        1,
    )
