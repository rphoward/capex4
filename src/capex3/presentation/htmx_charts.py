from __future__ import annotations

from typing import Mapping, Sequence

from capex3.presentation.htmx_evidence import _result_trace, _trace_collection
from capex3.presentation.htmx_format import _attr, _format, _html
from capex3.presentation.htmx_state import UiState

TEN_YEAR_SERIES_CLASSES = {
    "rental": "rental",
    "cashFlow": "cash-flow",
    "moneyMarket": "money-market",
    "conservativeIra": "ira",
}


def _evidence_graph(state: UiState) -> str:
    if state.active_evidence_layer == "tenYear":
        return _ten_year_chart(state)
    if state.active_evidence_layer == "repairFund":
        return _repair_fund_chart(state)
    return ""


def _ten_year_chart(state: UiState) -> str:
    trace = _result_trace(state, "tenYear")
    graph = trace.get("graph", {}) if isinstance(trace.get("graph", {}), Mapping) else {}
    series = []
    for item in _trace_collection(graph, ("series", "lineSeries", "lines")):
        values = [value for value in item.get("values", []) if isinstance(value, (int, float))]
        if item.get("label") and values:
            series.append(
                {
                    "id": str(item.get("id") or item.get("label")),
                    "label": str(item["label"]),
                    "className": TEN_YEAR_SERIES_CLASSES.get(
                        str(item.get("id") or ""),
                        str(item.get("id") or "rental"),
                    ),
                    "values": values,
                }
            )
    if not series:
        return """
<div class="chart-wrap" id="ten-year-story-chart">
  <div class="error-text">Evidence trace unavailable.</div>
</div>"""

    width = 500.0
    height = 270.0
    plot = {"left": 50.0, "right": 40.0, "top": 16.0, "bottom": 30.0}
    all_values = [value for item in series for value in item["values"]]
    minimum = min(all_values)
    maximum = max(all_values)
    spread = max(maximum - minimum, 1.0)
    min_y = minimum - spread * 0.08
    max_y = maximum + spread * 0.08
    base_y = _scale_chart_y(min_y, min_y, max_y, height, plot)

    points_by_class: dict[str, list[tuple[float, float]]] = {}
    for item in series:
        points_by_class[item["className"]] = [
            _scale_chart_point(value, min_y, max_y, index, len(item["values"]), width, height, plot)
            for index, value in enumerate(item["values"])
        ]

    grid_lines = "".join(
        f"""
      <line class="chart-grid" x1="{plot['left']:.1f}" y1="{_scale_chart_y(value, min_y, max_y, height, plot):.1f}" x2="{width - plot['right']:.1f}" y2="{_scale_chart_y(value, min_y, max_y, height, plot):.1f}"></line>
      <text class="chart-y-label" x="{plot['left'] - 6:.1f}" y="{_scale_chart_y(value, min_y, max_y, height, plot):.1f}" text-anchor="end" dy="0.35em">{_html(_format_chart_k(value))}</text>"""
        for value in _chart_ticks(min_y, max_y, 6)
    )
    x_labels = "".join(
        _chart_x_label(year, width, height, plot)
        for year in (0, 2, 4, 6, 8, 10)
    )
    rental_points = points_by_class.get("rental", [])
    rental_area = (
        f'<path class="rental-area" d="{_attr(_area_svg_path(rental_points, base_y))}"></path>'
        if rental_points
        else ""
    )
    paths = "".join(
        f"<path class=\"ten-year-series {_attr(item['className'])}\" d=\"{_attr(_smooth_svg_path(points_by_class[item['className']]))}\"></path>"
        for item in series
        if points_by_class.get(item["className"])
    )
    endpoints = "".join(
        _ten_year_endpoint(item, points_by_class[item["className"]])
        for item in series
        if points_by_class.get(item["className"])
    )
    legend = "".join(
        f"""
      <span><i class="legend-swatch {_attr(item['className'])}"></i>{_html(item['label'])}</span>"""
        for item in series
    )
    note = trace.get("note") or (
        "The rental path is compared with calmer alternatives using the latest Python calculator result."
    )
    initial = _format(trace.get("initialInvestment"), "money")
    return f"""
<div class="chart-wrap" id="ten-year-story-chart">
  <div class="chart-hed">
    <div>
      <h3>Total wealth position over 10 years</h3>
      <p class="chart-sub">{_html(initial)} invested (down payment + closing costs) - four paths compared</p>
    </div>
  </div>
  <div class="ten-year-chart-frame">
    <div class="chart-side-legend" aria-label="10-year chart series">{legend}
    </div>
    <div class="svg-wrap">
      <svg viewBox="0 0 {width:.0f} {height:.0f}" width="100%" height="{height:.0f}" role="img" aria-labelledby="ten-year-chart-title">
        <title id="ten-year-chart-title">Total wealth position over 10 years</title>
        <defs>
          <linearGradient id="rentalGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#1f7a54" stop-opacity="0.15"></stop>
            <stop offset="100%" stop-color="#1f7a54" stop-opacity="0.02"></stop>
          </linearGradient>
        </defs>
        {grid_lines}
        {x_labels}
        {rental_area}
        {paths}
        {endpoints}
      </svg>
    </div>
  </div>
  <div class="chart-note">{_html(note)}</div>
</div>"""


def _repair_fund_chart_subtitle(trace: Mapping[str, object]) -> str:
    pattern = str(trace.get("reserveContributionPattern") or "building")
    monthly = _format(trace.get("monthlyContribution"), "moneyCents")
    target = _format(trace.get("targetReserve"), "money")
    if pattern == "none":
        return "No monthly repair reserve is modeled for this deal."
    if pattern == "stops_at_cap":
        return (
            f"Dashboard rate {monthly}/mo (B34) — annual trace contributions stop once "
            f"the reserve cap ({target}, B21) is full; not every year adds new set-aside"
        )
    return (
        f"Dashboard rate {monthly}/mo (B34) — trace contributions continue until "
        f"the reserve cap (B21) is reached"
    )


def _repair_fund_chart(state: UiState) -> str:
    trace = _result_trace(state, "repairFund")
    graph = trace.get("graph", {}) if isinstance(trace.get("graph", {}), Mapping) else {}
    rows = _trace_collection(trace, ("rows", "years"))
    series = []
    for item in _trace_collection(graph, ("series", "lineSeries", "lines")):
        values = [value for value in item.get("values", []) if isinstance(value, (int, float))]
        if item.get("label") and values:
            series.append(
                {
                    "id": str(item.get("id") or item.get("label")),
                    "label": str(item["label"]),
                    "values": values,
                }
            )
    if not rows or len(series) < 2:
        return """
<div class="chart-wrap" id="repair-fund-story-chart">
  <div class="error-text">Repair reserve path trace unavailable.</div>
</div>"""

    width = 540.0
    height = 260.0
    plot = {"left": 52.0, "right": 18.0, "top": 18.0, "bottom": 30.0}
    all_values = [0.0] + [value for item in series for value in item["values"]]
    events = _repair_fund_chart_events(_trace_collection(graph, ("events", "eventMarkers")))
    all_values += [
        event.get("amount")
        for event in events
        if isinstance(event.get("amount"), (int, float))
    ]
    minimum = min(value for value in all_values if isinstance(value, (int, float)))
    maximum = max(value for value in all_values if isinstance(value, (int, float)))
    spread = max(maximum - minimum, 1.0)
    min_y = min(0.0, minimum - spread * 0.08)
    max_y = maximum + spread * 0.10
    base_y = _scale_chart_y(0, min_y, max_y, height, plot)

    values_by_id = {item["id"]: item["values"] for item in series}
    reserve_points = [
        _scale_chart_point(value, min_y, max_y, index, len(values_by_id["reserveBalance"]), width, height, plot)
        for index, value in enumerate(values_by_id.get("reserveBalance", []))
    ]
    no_reserve_points = [
        _scale_chart_point(value, min_y, max_y, index, len(values_by_id["noReserveSurpriseCost"]), width, height, plot)
        for index, value in enumerate(values_by_id.get("noReserveSurpriseCost", []))
    ]

    grid_lines = "".join(
        f"""
      <line class="chart-grid" x1="{plot['left']:.1f}" y1="{_scale_chart_y(value, min_y, max_y, height, plot):.1f}" x2="{width - plot['right']:.1f}" y2="{_scale_chart_y(value, min_y, max_y, height, plot):.1f}"></line>
      <text class="chart-y-label" x="{plot['left'] - 6:.1f}" y="{_scale_chart_y(value, min_y, max_y, height, plot):.1f}" text-anchor="end" dy="0.35em">{_html(_format_chart_k(value))}</text>"""
        for value in _chart_ticks(min_y, max_y, 5)
    )
    x_labels = "".join(
        _chart_x_label(year, width, height, plot)
        for year in (0, 2, 4, 6, 8, 10)
    )
    markers = "".join(
        _repair_fund_event_marker(event, min_y, max_y, width, height, plot, base_y)
        for event in events
    )
    chart_sub = _repair_fund_chart_subtitle(trace)
    info_copy = trace.get("infoCopy") or (
        "Teaching-only trace comparing reserve balance vs. no-reserve surprise cost."
    )
    note = trace.get("note") or "Repair reserve trace comes from the Python calculator."
    return f"""
<div class="info-box repair-fund-info" id="repair-fund-info">
  {_html(info_copy)}
</div>
<div class="chart-wrap repair-fund-chart" id="repair-fund-story-chart">
  <p class="teaching-only-cue"><small>Teaching-only trace — not workbook parity.</small></p>
  <div class="chart-hed">
    <div>
      <h3>Reserve balance vs. no-reserve surprise cost</h3>
      <p class="chart-sub">{_html(chart_sub)}</p>
    </div>
  </div>
  <div class="svg-wrap">
    <svg viewBox="0 0 {width:.0f} {height:.0f}" width="100%" height="{height:.0f}" role="img" aria-labelledby="repair-fund-chart-title">
      <title id="repair-fund-chart-title">Reserve balance vs no-reserve surprise cost</title>
      <defs>
        <linearGradient id="repairBalanceGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1f7a54" stop-opacity="0.22"></stop>
          <stop offset="100%" stop-color="#1f7a54" stop-opacity="0.03"></stop>
        </linearGradient>
        <linearGradient id="surpriseCostGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#a43d35" stop-opacity="0.15"></stop>
          <stop offset="100%" stop-color="#a43d35" stop-opacity="0.02"></stop>
        </linearGradient>
      </defs>
      {grid_lines}
      {x_labels}
      <path class="surprise-cost-area" d="{_attr(_step_area_svg_path(no_reserve_points, base_y))}"></path>
      <path class="repair-surprise-series" d="{_attr(_step_svg_path(no_reserve_points))}"></path>
      <path class="repair-balance-area" d="{_attr(_area_svg_path(reserve_points, base_y))}"></path>
      <path class="repair-balance-series" d="{_attr(_linear_svg_path(reserve_points))}"></path>
      {markers}
    </svg>
  </div>
  <div class="chart-legend repair-fund-legend">
    <span><i class="legend-swatch reserve-balance"></i>Reserve balance (with monthly fund)</span>
    <span><i class="legend-swatch surprise-cost"></i>Cumulative surprise cost (no reserve)</span>
  </div>
  <div class="chart-note">{_html(note)}</div>
</div>"""


def _repair_fund_event_marker(
    event: Mapping[str, object],
    minimum: float,
    maximum: float,
    width: float,
    height: float,
    plot: Mapping[str, float],
    base_y: float,
) -> str:
    year = event.get("year")
    amount = event.get("amount")
    ending_balance = event.get("endingBalance")
    if not isinstance(year, (int, float)) or not isinstance(amount, (int, float)):
        return ""
    x = _scale_chart_x(year, 10, width, plot)
    label_y = _scale_chart_y(amount, minimum, maximum, height, plot) - 9
    balance_y = (
        _scale_chart_y(ending_balance, minimum, maximum, height, plot)
        if isinstance(ending_balance, (int, float))
        else base_y
    )
    label = event.get("label") or event.get("component") or "Repair"
    anchor = "end" if x > width - 80 else "start" if x < plot["left"] + 42 else "middle"
    return f"""
      <g class="repair-event-marker">
        <line x1="{x:.1f}" y1="{plot['top']:.1f}" x2="{x:.1f}" y2="{base_y:.1f}"></line>
        <circle cx="{x:.1f}" cy="{balance_y:.1f}" r="5"></circle>
        <text class="event-amount" x="{x:.1f}" y="{label_y - 10:.1f}" text-anchor="{anchor}">{_html(_format_chart_k(amount))}</text>
        <text class="event-label" x="{x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}">{_html(label)}</text>
      </g>"""


def _repair_fund_chart_events(
    events: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[int, dict[str, object]] = {}
    for event in events:
        year = event.get("year")
        amount = event.get("amount")
        if not isinstance(year, int) or not isinstance(amount, (int, float)):
            continue
        grouped.setdefault(
            year,
            {
                "year": year,
                "amount": 0.0,
                "labels": [],
                "endingBalance": event.get("endingBalance"),
            },
        )
        grouped[year]["amount"] += amount
        grouped[year]["labels"].append(event.get("label") or event.get("component") or "Repair")
        grouped[year]["endingBalance"] = event.get("endingBalance")
    markers = []
    for year in sorted(grouped):
        marker = grouped[year]
        labels = marker.pop("labels")
        marker["label"] = labels[0] if len(labels) == 1 else f"{len(labels)} repairs"
        markers.append(marker)
    return markers


def _ten_year_endpoint(
    series: Mapping[str, object],
    points: Sequence[tuple[float, float]],
) -> str:
    if not points:
        return ""
    x, y = points[-1]
    values = series.get("values", [])
    last_value = values[-1] if isinstance(values, list) and values else None
    class_name = str(series.get("className") or "")
    return f"""
        <g class="endpoint {_attr(class_name)}">
          <circle cx="{x:.1f}" cy="{y:.1f}" r="3.5"></circle>
          <text class="endpoint-label {_attr(class_name)}" x="{x + 6:.1f}" y="{y:.1f}" dy="0.35em">{_html(_format_chart_k(last_value))}</text>
        </g>"""


def _chart_x_label(
    year: int,
    width: float,
    height: float,
    plot: Mapping[str, float],
) -> str:
    label = "Now" if year == 0 else f"Yr {year}"
    return (
        f'<text class="chart-x-label" x="{_scale_chart_x(year, 10, width, plot):.1f}" '
        f'y="{height - 7:.1f}" text-anchor="middle">{_html(label)}</text>'
    )


def _scale_chart_point(
    value: float,
    minimum: float,
    maximum: float,
    index: int,
    total: int,
    width: float,
    height: float,
    plot: Mapping[str, float],
) -> tuple[float, float]:
    return (
        _scale_chart_x(index, max(total - 1, 1), width, plot),
        _scale_chart_y(value, minimum, maximum, height, plot),
    )


def _scale_chart_x(
    value: float,
    maximum: float,
    width: float,
    plot: Mapping[str, float],
) -> float:
    plot_width = width - plot["left"] - plot["right"]
    return plot["left"] + (value / maximum) * plot_width if maximum else plot["left"]


def _scale_chart_y(
    value: float,
    minimum: float,
    maximum: float,
    height: float,
    plot: Mapping[str, float],
) -> float:
    plot_height = height - plot["top"] - plot["bottom"]
    ratio = 0.5 if maximum == minimum else (value - minimum) / (maximum - minimum)
    return plot["top"] + (1 - max(0, min(1, ratio))) * plot_height


def _smooth_svg_path(points: Sequence[tuple[float, float]]) -> str:
    if not points:
        return ""
    path = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for previous, current in zip(points, points[1:]):
        mid_x = (previous[0] + current[0]) / 2
        path += (
            f" C{mid_x:.1f},{previous[1]:.1f} "
            f"{mid_x:.1f},{current[1]:.1f} "
            f"{current[0]:.1f},{current[1]:.1f}"
        )
    return path


def _area_svg_path(points: Sequence[tuple[float, float]], base_y: float) -> str:
    if not points:
        return ""
    last_x = points[-1][0]
    first_x = points[0][0]
    return f"{_smooth_svg_path(points)} L{last_x:.1f},{base_y:.1f} L{first_x:.1f},{base_y:.1f} Z"


def _linear_svg_path(points: Sequence[tuple[float, float]]) -> str:
    if not points:
        return ""
    return " ".join(
        [f"M{points[0][0]:.1f},{points[0][1]:.1f}"]
        + [f"L{x:.1f},{y:.1f}" for x, y in points[1:]]
    )


def _step_svg_path(points: Sequence[tuple[float, float]]) -> str:
    if not points:
        return ""
    path = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for x, y in points[1:]:
        path += f" H{x:.1f} V{y:.1f}"
    return path


def _step_area_svg_path(points: Sequence[tuple[float, float]], base_y: float) -> str:
    if not points:
        return ""
    return (
        f"{_step_svg_path(points)} V{base_y:.1f} "
        f"H{points[0][0]:.1f} Z"
    )


def _chart_ticks(minimum: float, maximum: float, count: int) -> list[float]:
    if count <= 1:
        return [minimum]
    step = (maximum - minimum) / (count - 1)
    return [minimum + step * index for index in range(count)]


def _format_chart_k(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    prefix = "-$" if value < 0 else "$"
    return f"{prefix}{abs(value) / 1000:.0f}k"


def _graph_content(state: UiState) -> tuple[str, str, str]:
    if not state.result:
        return ("Evidence trace unavailable", '<div class="error-text">Evidence trace unavailable.</div>', "")
    layer_id = state.active_evidence_layer
    traces = state.result.get("traces", {})
    if layer_id == "tenYear":
        return _line_graph("Rental vs calmer alternatives", traces.get("tenYear", {}))
    if layer_id == "repairDrivers":
        return _bar_graph(
            "Largest monthly repair fund drivers",
            _trace_collection(traces.get("repairDrivers", {}).get("graph", {}), ("bars", "drivers", "rows", "topDrivers")),
        )
    if layer_id == "cashFlow":
        return _bar_graph(
            "Rent to true monthly cash flow",
            _trace_collection(traces.get("cashFlow", {}).get("graph", {}), ("bars", "graphBars")),
        )
    if layer_id == "whatWorks":
        return _bar_graph(
            "Current threshold pressure",
            _trace_collection(traces.get("whatWorks", {}).get("graph", {}), ("bars", "graphBars")),
        )
    dashboard = state.result.get("dashboard", {})
    return _bar_graph(
        "Diagnostic values in play",
        [
            {"label": "Market rent", "value": dashboard.get("marketRent"), "kind": "moneyCents"},
            {"label": "Repair fund", "value": dashboard.get("totalMonthlyCapexReserve"), "kind": "moneyCents"},
            {"label": "Loan payment", "value": dashboard.get("monthlyMortgagePI"), "kind": "moneyCents"},
        ],
    )


def _line_graph(title: str, trace: Mapping[str, object]) -> tuple[str, str, str]:
    class_by_id = {
        "rental": "rental",
        "moneyMarket": "money-market",
        "conservativeIra": "ira",
    }
    series = []
    for item in _trace_collection(trace.get("graph", {}), ("series", "lineSeries", "lines")):
        values = [value for value in item.get("values", []) if isinstance(value, (int, float))]
        if item.get("label") and values:
            series.append(
                {
                    "label": item["label"],
                    "className": class_by_id.get(item.get("id"), item.get("id", "rental")),
                    "values": values,
                }
            )
    if not series:
        return (title, '<div class="error-text">Evidence trace unavailable.</div>', "")

    values = [value for item in series for value in item["values"]]
    minimum = min(values)
    maximum = max(values)
    lines = []
    for item in series:
        points = " ".join(
            _graph_point(value, minimum, maximum, index, len(item["values"]))
            for index, value in enumerate(item["values"])
        )
        lines.append(
            f'<polyline class="graph-series {_attr(item["className"])}" points="{_attr(points)}"></polyline>'
        )
    body = f"""
<svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img">
  <line class="graph-axis" x1="6" y1="88" x2="96" y2="88"></line>
  <line class="graph-axis" x1="6" y1="8" x2="6" y2="88"></line>
  {''.join(lines)}
</svg>"""
    legend = "".join(
        f'<span><i class="{_attr(item["className"])}"></i>{_html(item["label"])}</span>'
        for item in series
    )
    return (title, body, legend)


def _bar_graph(title: str, rows: Sequence[Mapping[str, object]]) -> tuple[str, str, str]:
    bars = [
        {
            "label": row.get("label") or row.get("title") or row.get("name"),
            "value": _first_present(row, ("value", "amount", "metricValue", "monthlyReserve")),
            "kind": row.get("kind") or row.get("valueKind") or "moneyCents",
        }
        for row in rows
    ]
    bars = [
        bar
        for bar in bars
        if bar["label"] and isinstance(bar["value"], (int, float))
    ]
    if not bars:
        return (title, '<div class="error-text">Evidence trace unavailable.</div>', "")
    maximum = max([abs(bar["value"]) for bar in bars] + [1])
    body = "".join(
        f"""
<div class="graph-bar-row">
  <span>{_html(bar["label"])}</span>
  <div class="graph-bar-track">
    <div class="graph-bar {'negative' if bar["value"] < 0 else ''}" style="width: {max(4, abs(bar["value"]) / maximum * 100):.1f}%"></div>
  </div>
  <strong>{_html(_format(bar["value"], bar["kind"]))}</strong>
</div>"""
        for bar in bars
    )
    return (title, body, "")


def _graph_point(value: float, minimum: float, maximum: float, index: int, total: int) -> str:
    x = 50 if total <= 1 else 6 + (index / (total - 1)) * 88
    ratio = 0.5 if maximum == minimum else (value - minimum) / (maximum - minimum)
    y = 88 - max(0, min(1, ratio)) * 76
    return f"{x:.2f},{y:.2f}"
