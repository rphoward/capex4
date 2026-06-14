from __future__ import annotations

from typing import Mapping, Sequence

from capex3.presentation.htmx_format import _attr, _format, _html
from capex3.presentation.htmx_state import UiState
from capex3.presentation.htmx_trace import _result_trace, _trace_collection

TEN_YEAR_SERIES_CLASSES = {
    "rental": "rental",
    "cashFlow": "cash-flow",
    "moneyMarket": "money-market",
    "conservativeIra": "ira",
}

# Chart colors must mirror --chart-series-* in tokens.css.
CHART_RENTAL = "#1a7a4c"
CHART_CASHFLOW = "#a43d12"
CHART_STONE = "#61594a"
CHART_COPPER = "#b85c28"
CHART_AREA_OPACITY_TOP = 0.12
CHART_AREA_OPACITY_BOTTOM = 0.02

SVG_WIDTH = 640
TEN_YEAR_SVG_HEIGHT = 280
REPAIR_FUND_SVG_HEIGHT = 260
CHART_PAD_LEFT = 58
CHART_PAD_RIGHT = 28
CHART_PAD_TOP = 18
CHART_PAD_BOTTOM = 34
ENDPOINT_LABEL_INSET = 6.0
ENDPOINT_LABEL_FLIP_AT = 40.0


def _hex_alpha(hex_color: str, alpha: float) -> str:
    return (
        f"rgba({int(hex_color[1:3], 16)}, {int(hex_color[3:5], 16)}, "
        f"{int(hex_color[5:7], 16)}, {alpha})"
    )


def _line_series_from_graph(
    graph: Mapping[str, object],
    *,
    class_for_id: Mapping[str, str] | None = None,
) -> list[dict[str, object]]:
    series: list[dict[str, object]] = []
    for item in _trace_collection(graph, ("series", "lineSeries", "lines")):
        values = [value for value in item.get("values", []) if isinstance(value, (int, float))]
        if not item.get("label") or not values:
            continue
        series_id = str(item.get("id") or item.get("label"))
        entry: dict[str, object] = {
            "id": series_id,
            "label": str(item["label"]),
            "values": values,
        }
        if class_for_id is not None:
            entry["className"] = class_for_id.get(series_id, series_id)
        series.append(entry)
    return series


def _endpoint_label_position(x: float, height: int) -> tuple[float, str]:
    left, _, width, _ = _plot_area(height)
    if x >= left + width - ENDPOINT_LABEL_FLIP_AT:
        return x - ENDPOINT_LABEL_INSET, "end"
    return x + ENDPOINT_LABEL_INSET, "start"


def _evidence_graph(state: UiState) -> str:
    if state.active_evidence_layer == "tenYear":
        return _ten_year_chart(state)
    if state.active_evidence_layer == "repairFund":
        return _repair_fund_chart(state)
    return ""


def _plot_area(height: int) -> tuple[float, float, float, float]:
    left = float(CHART_PAD_LEFT)
    top = float(CHART_PAD_TOP)
    width = float(SVG_WIDTH - CHART_PAD_LEFT - CHART_PAD_RIGHT)
    plot_height = float(height - CHART_PAD_TOP - CHART_PAD_BOTTOM)
    return left, top, width, plot_height


def _point(
    index: int,
    value: float,
    count: int,
    min_y: float,
    max_y: float,
    height: int,
) -> tuple[float, float]:
    left, top, width, plot_height = _plot_area(height)
    if count <= 1:
        x = left + width / 2
    else:
        x = left + (index / (count - 1)) * width
    span = max(max_y - min_y, 1.0)
    y = top + plot_height - ((value - min_y) / span) * plot_height
    return x, y


def _line_path(points: Sequence[tuple[float, float]]) -> str:
    if not points:
        return ""
    parts = [f"M {points[0][0]:.2f},{points[0][1]:.2f}"]
    for x, y in points[1:]:
        parts.append(f"L {x:.2f},{y:.2f}")
    return " ".join(parts)


def _area_path(points: Sequence[tuple[float, float]], baseline_y: float) -> str:
    if not points:
        return ""
    line = _line_path(points)
    first_x, _ = points[0]
    last_x, _ = points[-1]
    return f"{line} L {last_x:.2f},{baseline_y:.2f} L {first_x:.2f},{baseline_y:.2f} Z"


def _step_path(points: Sequence[tuple[float, float]]) -> str:
    if not points:
        return ""
    parts = [f"M {points[0][0]:.2f},{points[0][1]:.2f}"]
    for index in range(1, len(points)):
        x, y = points[index]
        prev_x, prev_y = points[index - 1]
        parts.append(f"L {x:.2f},{prev_y:.2f} L {x:.2f},{y:.2f}")
    return " ".join(parts)


def _step_area_path(points: Sequence[tuple[float, float]], baseline_y: float) -> str:
    if not points:
        return ""
    line = _step_path(points)
    first_x, _ = points[0]
    last_x, _ = points[-1]
    return f"{line} L {last_x:.2f},{baseline_y:.2f} L {first_x:.2f},{baseline_y:.2f} Z"


def _year_categories(count: int) -> list[str]:
    return ["Now" if year == 0 else f"Yr {year}" for year in range(count)]


def _axis_markup(point_count: int, min_y: float, max_y: float, height: int) -> str:
    left, top, width, plot_height = _plot_area(height)
    baseline_y = top + plot_height
    tick_count = 5
    span = max(max_y - min_y, 1.0)
    parts: list[str] = []

    for tick in range(tick_count):
        fraction = tick / (tick_count - 1) if tick_count > 1 else 0.0
        value = max_y - fraction * span
        _, y = _point(0, value, point_count, min_y, max_y, height)
        parts.append(
            f'<line class="chart-grid" x1="{left:.2f}" y1="{y:.2f}" '
            f'x2="{left + width:.2f}" y2="{y:.2f}"/>'
        )
        parts.append(
            f'<text class="chart-y-label" x="{left - 8:.2f}" y="{y + 3:.2f}" '
            f'text-anchor="end">{_html(_format_chart_k(value))}</text>'
        )

    parts.append(
        f'<line class="chart-baseline" x1="{left:.2f}" y1="{baseline_y:.2f}" '
        f'x2="{left + width:.2f}" y2="{baseline_y:.2f}"/>'
    )

    categories = _year_categories(point_count)
    tick_interval = 2 if point_count > 6 else 1
    for index, label in enumerate(categories):
        if index % tick_interval != 0 and index != point_count - 1:
            continue
        x, _ = _point(index, min_y, point_count, min_y, max_y, height)
        parts.append(
            f'<text class="chart-x-label" x="{x:.2f}" y="{baseline_y + 16:.2f}" '
            f'text-anchor="middle">{_html(label)}</text>'
        )

    return "\n      ".join(parts)


def _svg_defs(kind: str) -> str:
    if kind == "ten-year":
        return f"""<defs>
        <linearGradient id="rentalGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="{_hex_alpha(CHART_RENTAL, CHART_AREA_OPACITY_TOP)}"/>
          <stop offset="1" stop-color="{_hex_alpha(CHART_RENTAL, CHART_AREA_OPACITY_BOTTOM)}"/>
        </linearGradient>
      </defs>"""
    if kind == "repair-fund":
        return f"""<defs>
        <linearGradient id="repairBalanceGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="{_hex_alpha(CHART_RENTAL, CHART_AREA_OPACITY_TOP)}"/>
          <stop offset="1" stop-color="{_hex_alpha(CHART_RENTAL, CHART_AREA_OPACITY_BOTTOM)}"/>
        </linearGradient>
        <linearGradient id="surpriseCostGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="{_hex_alpha(CHART_CASHFLOW, CHART_AREA_OPACITY_TOP)}"/>
          <stop offset="1" stop-color="{_hex_alpha(CHART_CASHFLOW, CHART_AREA_OPACITY_BOTTOM)}"/>
        </linearGradient>
      </defs>"""
    return ""


def _series_points(
    values: Sequence[float],
    point_count: int,
    min_y: float,
    max_y: float,
    height: int,
) -> list[tuple[float, float]]:
    return [
        _point(index, value, point_count, min_y, max_y, height)
        for index, value in enumerate(values)
    ]


def _ten_year_endpoints(
    series: Sequence[Mapping[str, object]],
    point_count: int,
    min_y: float,
    max_y: float,
    height: int,
) -> str:
    parts: list[str] = []
    for item in series:
        class_name = str(item["className"])
        if class_name == "rental":
            continue
        values = item["values"]
        if not isinstance(values, list) or not values:
            continue
        last_value = float(values[-1])
        x, y = _point(len(values) - 1, last_value, point_count, min_y, max_y, height)
        label = _format_chart_k(last_value)
        label_x, anchor = _endpoint_label_position(x, height)
        css_class = _attr(class_name)
        parts.append(
            f"""<g class="endpoint {css_class}">
        <circle cx="{x:.2f}" cy="{y:.2f}" r="4"/>
        <title>{_html(str(item["label"]))}: {_html(label)}</title>
        <text class="endpoint-label {css_class}" x="{label_x:.2f}" y="{y - 6:.2f}" text-anchor="{anchor}">{_html(label)}</text>
      </g>"""
        )
    return "\n      ".join(parts)


def _ten_year_svg(
    series: Sequence[Mapping[str, object]],
    point_count: int,
    min_y: float,
    max_y: float,
) -> str:
    height = TEN_YEAR_SVG_HEIGHT
    _, top, _, plot_height = _plot_area(height)
    baseline_y = top + plot_height
    parts: list[str] = [
        f"""<svg class="server-svg-chart" width="{SVG_WIDTH}" height="{height}" """
        f"""viewBox="0 0 {SVG_WIDTH} {height}" role="img" """
        f"""aria-label="{_attr("Total wealth position over 10 years")}">
      <title>Total wealth position over 10 years</title>
      <desc>Four wealth paths compared over ten years: rental liquidation, """
        """cash position, money market, and IRA.</desc>""",
        _svg_defs("ten-year"),
        _axis_markup(point_count, min_y, max_y, height),
    ]

    rental_item = next((item for item in series if item["className"] == "rental"), None)
    if rental_item is not None:
        rental_values = rental_item["values"]
        if isinstance(rental_values, list) and rental_values:
            rental_points = _series_points(rental_values, point_count, min_y, max_y, height)
            parts.append(
                f'<path class="rental-area" d="{_attr(_area_path(rental_points, baseline_y))}"/>'
            )
            parts.append(
                f'<path class="ten-year-series rental" d="{_attr(_line_path(rental_points))}"/>'
            )

    for item in series:
        class_name = str(item["className"])
        if class_name == "rental":
            continue
        values = item["values"]
        if not isinstance(values, list) or not values:
            continue
        points = _series_points(values, point_count, min_y, max_y, height)
        css_class = _attr(class_name)
        parts.append(
            f'<path class="ten-year-series {css_class}" '
            f'd="{_attr(_line_path(points))}"/>'
        )

    parts.append(_ten_year_endpoints(series, point_count, min_y, max_y, height))
    parts.append("</svg>")
    return "\n      ".join(parts)


def _repair_event_markers(
    events: Sequence[Mapping[str, object]],
    point_count: int,
    min_y: float,
    max_y: float,
    height: int,
) -> str:
    _, top, _, plot_height = _plot_area(height)
    baseline_y = top + plot_height
    parts: list[str] = []
    for event in events:
        year = event.get("year")
        amount = event.get("amount")
        if not isinstance(year, int) or not isinstance(amount, (int, float)):
            continue
        label = str(event.get("label") or "Repair")
        x, marker_y = _point(year, float(amount), point_count, min_y, max_y, height)
        marker_label = f"{_format_chart_k(amount)} · {label}"
        parts.append(
            f"""<g class="repair-event-marker">
        <line x1="{x:.2f}" y1="{top:.2f}" x2="{x:.2f}" y2="{baseline_y:.2f}"/>
        <circle cx="{x:.2f}" cy="{marker_y:.2f}" r="4"/>
        <title>{_html(marker_label)}</title>
        <text class="event-amount" x="{x:.2f}" y="{top + 10:.2f}" text-anchor="middle">{_html(marker_label)}</text>
      </g>"""
        )
    return "\n      ".join(parts)


def _repair_fund_svg(
    reserve_values: Sequence[float],
    no_reserve_values: Sequence[float],
    events: Sequence[Mapping[str, object]],
    point_count: int,
    min_y: float,
    max_y: float,
) -> str:
    height = REPAIR_FUND_SVG_HEIGHT
    _, top, _, plot_height = _plot_area(height)
    baseline_y = top + plot_height
    reserve_points = _series_points(reserve_values, point_count, min_y, max_y, height)
    surprise_points = _series_points(no_reserve_values, point_count, min_y, max_y, height)

    return f"""<svg class="server-svg-chart" width="{SVG_WIDTH}" height="{height}" viewBox="0 0 {SVG_WIDTH} {height}" role="img" aria-label="{_attr("Reserve balance vs no-reserve surprise cost")}">
      <title>Reserve balance vs no-reserve surprise cost</title>
      <desc>Reserve balance with monthly funding compared to cumulative surprise repair cost without a reserve.</desc>
      {_svg_defs("repair-fund")}
      {_axis_markup(point_count, min_y, max_y, height)}
      <path class="repair-balance-area" d="{_attr(_area_path(reserve_points, baseline_y))}"/>
      <path class="repair-balance-series" d="{_attr(_line_path(reserve_points))}"/>
      <path class="surprise-cost-area" d="{_attr(_step_area_path(surprise_points, baseline_y))}"/>
      <path class="repair-surprise-series" d="{_attr(_step_path(surprise_points))}"/>
      {_repair_event_markers(events, point_count, min_y, max_y, height)}
    </svg>"""


def _value_bounds(values: Sequence[float], *, floor_at_zero: bool = False) -> tuple[float, float]:
    minimum = min(values)
    maximum = max(values)
    spread = max(maximum - minimum, 1.0)
    min_y = min(0.0, minimum - spread * 0.08) if floor_at_zero else minimum - spread * 0.08
    max_y = maximum + spread * 0.10
    return min_y, max_y


def _ten_year_chart(state: UiState) -> str:
    trace = _result_trace(state, "tenYear")
    graph = trace.get("graph", {}) if isinstance(trace.get("graph", {}), Mapping) else {}
    series = _line_series_from_graph(graph, class_for_id=TEN_YEAR_SERIES_CLASSES)
    if not series:
        return """
<div class="chart-wrap chart-stage" id="ten-year-story-chart">
  <div class="error-text">Evidence trace unavailable.</div>
</div>"""

    point_count = max(len(item["values"]) for item in series)
    all_values = [value for item in series for value in item["values"]]
    min_y, max_y = _value_bounds(all_values)
    svg = _ten_year_svg(series, point_count, min_y, max_y)

    legend = "".join(
        f"""
      <span><i class="legend-swatch {_attr(item['className'])}"></i>{_html(item['label'])}</span>"""
        for item in series
    )
    note = trace.get("note") or (
        "The rental path is compared with calmer alternatives using your current assumptions."
    )
    initial = _format(trace.get("initialInvestment"), "money")
    return f"""
<div class="chart-wrap chart-stage" id="ten-year-story-chart">
  <div class="chart-hed chart-summary">
    <div>
      <h3>Total wealth position over 10 years</h3>
      <p class="chart-sub">{_html(initial)} invested (down payment + closing costs) - four paths compared</p>
    </div>
  </div>
  <div class="ten-year-chart-frame">
    <div class="chart-side-legend" aria-label="10-year chart series">{legend}
    </div>
    <div class="svg-wrap chart-canvas">
      {svg}
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
            f"Dashboard rate {monthly}/mo — annual trace contributions stop once "
            f"the reserve cap ({target}) is full; not every year adds new set-aside"
        )
    return (
        f"Dashboard rate {monthly}/mo — trace contributions continue until "
        f"the reserve cap is reached"
    )


def _repair_fund_chart(state: UiState) -> str:
    trace = _result_trace(state, "repairFund")
    graph = trace.get("graph", {}) if isinstance(trace.get("graph", {}), Mapping) else {}
    rows = _trace_collection(trace, ("rows", "years"))
    series = _line_series_from_graph(graph)
    if not rows or len(series) < 2:
        return """
<div class="chart-wrap chart-stage" id="repair-fund-story-chart">
  <div class="error-text">Repair reserve path trace unavailable.</div>
</div>"""

    values_by_id = {item["id"]: item["values"] for item in series}
    reserve_values = values_by_id.get("reserveBalance", [])
    no_reserve_values = values_by_id.get("noReserveSurpriseCost", [])
    point_count = max(len(reserve_values), len(no_reserve_values), 1)
    all_values = [0.0, *reserve_values, *no_reserve_values]
    events = _repair_fund_chart_events(_trace_collection(graph, ("events", "eventMarkers")))
    all_values.extend(
        event.get("amount")
        for event in events
        if isinstance(event.get("amount"), (int, float))
    )
    min_y, max_y = _value_bounds(all_values, floor_at_zero=True)
    svg = _repair_fund_svg(
        reserve_values,
        no_reserve_values,
        events,
        point_count,
        min_y,
        max_y,
    )

    chart_sub = _repair_fund_chart_subtitle(trace)
    info_copy = trace.get("infoCopy") or (
        "Compare reserve balance vs. no-reserve surprise cost when repairs land."
    )
    note = trace.get("note") or "Reserve timeline based on your monthly contribution and repair schedule."
    return f"""
<div class="info-box repair-fund-info" id="repair-fund-info">
  {_html(info_copy)}
</div>
<div class="chart-wrap chart-stage repair-fund-chart" id="repair-fund-story-chart">
  <div class="chart-hed chart-summary">
    <div>
      <h3>Reserve balance vs. no-reserve surprise cost</h3>
      <p class="chart-sub">{_html(chart_sub)}</p>
    </div>
  </div>
  <div class="svg-wrap chart-canvas">
    {svg}
  </div>
  <div class="chart-legend repair-fund-legend" aria-label="Repair fund chart series">
    <span><i class="legend-swatch reserve-balance"></i>Reserve balance (with monthly fund)</span>
    <span><i class="legend-swatch surprise-cost"></i>Cumulative surprise cost (no reserve)</span>
  </div>
  <div class="chart-note">{_html(note)}</div>
</div>"""


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


def _format_chart_k(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    prefix = "-$" if value < 0 else "$"
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{prefix}{magnitude / 1_000_000:.1f}M"
    if magnitude >= 1_000:
        return f"{prefix}{magnitude / 1000:.0f}k"
    return f"{prefix}{magnitude:.0f}"
