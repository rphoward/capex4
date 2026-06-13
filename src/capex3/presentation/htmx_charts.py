from __future__ import annotations

import json
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

# Highcharts colors must mirror --chart-series-* in tokens.css.
CHART_RENTAL = "#1a7a4c"
CHART_CASHFLOW = "#a43d12"
CHART_STONE = "#61594a"
CHART_COPPER = "#b85c28"
CHART_AREA_OPACITY_TOP = 0.12
CHART_AREA_OPACITY_BOTTOM = 0.02
CHART_GRID = "rgba(38, 27, 7, 0.05)"
CHART_AXIS = "#61594a"
CHART_LINE = "#dbdad7"

TEN_YEAR_SERIES_STYLES: dict[str, dict[str, object]] = {
    "rental": {
        "type": "areaspline",
        "color": CHART_RENTAL,
        "lineWidth": 2.5,
        "fillColor": {
            "linearGradient": {"x1": 0, "y1": 0, "x2": 0, "y2": 1},
            "stops": [
                [0, f"rgba(26, 122, 76, {CHART_AREA_OPACITY_TOP})"],
                [1, f"rgba(26, 122, 76, {CHART_AREA_OPACITY_BOTTOM})"],
            ],
        },
    },
    "cash-flow": {
        "type": "spline",
        "color": CHART_CASHFLOW,
        "dashStyle": "ShortDash",
        "lineWidth": 1.8,
        "marker": {"enabled": False},
    },
    "money-market": {
        "type": "spline",
        "color": CHART_STONE,
        "dashStyle": "ShortDot",
        "lineWidth": 2,
        "marker": {"enabled": False},
    },
    "ira": {
        "type": "spline",
        "color": CHART_COPPER,
        "dashStyle": "Dot",
        "lineWidth": 2,
        "marker": {"enabled": False},
    },
}


def _evidence_graph(state: UiState) -> str:
    if state.active_evidence_layer == "tenYear":
        return _ten_year_chart(state)
    if state.active_evidence_layer == "repairFund":
        return _repair_fund_chart(state)
    return ""


def _chart_json(config: Mapping[str, object]) -> str:
    return _attr(json.dumps(config, separators=(",", ":")))


def _highcharts_host(
    host_id: str,
    config: Mapping[str, object],
    *,
    aria_label: str,
) -> str:
    return (
        f'<div class="highcharts-host" id="{_attr(host_id)}" '
        f'data-highcharts-config="{_chart_json(config)}" role="img" '
        f'aria-label="{_attr(aria_label)}"></div>'
    )


def _year_categories(count: int) -> list[str]:
    return ["Now" if year == 0 else f"Yr {year}" for year in range(count)]


def _axis_style() -> dict[str, object]:
    return {
        "lineColor": CHART_LINE,
        "tickColor": CHART_LINE,
        "gridLineColor": CHART_GRID,
        "labels": {"style": {"color": CHART_AXIS, "fontSize": "10px"}},
    }


def _base_highcharts_config(*, height: int) -> dict[str, object]:
    return {
        "chart": {
            "backgroundColor": "transparent",
            "height": height,
            "spacing": [8, 8, 8, 8],
            "style": {"fontFamily": "Source Sans 3, system-ui, sans-serif"},
        },
        "title": {"text": None},
        "credits": {"enabled": False},
        "legend": {"enabled": False},
        "tooltip": {
            "shared": True,
            "__format": "money",
            "borderColor": CHART_LINE,
            "backgroundColor": "#ffffff",
        },
    }


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
<div class="chart-wrap chart-stage" id="ten-year-story-chart">
  <div class="error-text">Evidence trace unavailable.</div>
</div>"""

    point_count = max(len(item["values"]) for item in series)
    all_values = [value for item in series for value in item["values"]]
    min_y, max_y = _value_bounds(all_values)
    config = _base_highcharts_config(height=280)
    config["xAxis"] = {
        **_axis_style(),
        "categories": _year_categories(point_count),
        "tickInterval": 2 if point_count > 6 else 1,
    }
    config["yAxis"] = {
        "title": {"text": None},
        **_axis_style(),
        "min": min_y,
        "max": max_y,
        "labels": {
            "style": {"color": CHART_AXIS, "fontSize": "10px"},
            "__format": "moneyK",
        },
    }
    config["series"] = []
    for item in series:
        style = dict(TEN_YEAR_SERIES_STYLES.get(item["className"], TEN_YEAR_SERIES_STYLES["rental"]))
        entry: dict[str, object] = {
            "name": item["label"],
            "data": item["values"],
            **style,
        }
        if item["className"] != "rental":
            entry["dataLabels"] = {
                "enabled": True,
                "__format": "moneyK",
                "__lastPointOnly": True,
                "style": {"fontWeight": "700", "fontSize": "10px", "textOutline": "2px #ffffff"},
            }
        config["series"].append(entry)

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
      {_highcharts_host("ten-year-story-chart-mount", config, aria_label="Total wealth position over 10 years")}
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


def _repair_fund_plot_lines(events: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    plot_lines: list[dict[str, object]] = []
    for event in events:
        year = event.get("year")
        amount = event.get("amount")
        if not isinstance(year, (int, float)) or not isinstance(amount, (int, float)):
            continue
        label = event.get("label") or event.get("component") or "Repair"
        plot_lines.append(
            {
                "value": year,
                "width": 1,
                "color": "rgba(38, 27, 7, 0.14)",
                "zIndex": 2,
                "label": {
                    "text": f"{_format_chart_k(amount)} · {label}",
                    "rotation": 0,
                    "y": 12,
                    "style": {"color": CHART_AXIS, "fontSize": "10px", "fontWeight": "600"},
                },
            }
        )
    return plot_lines


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
    config = _base_highcharts_config(height=260)
    config["xAxis"] = {
        **_axis_style(),
        "categories": _year_categories(point_count),
        "tickInterval": 2 if point_count > 6 else 1,
        "plotLines": _repair_fund_plot_lines(events),
    }
    config["yAxis"] = {
        "title": {"text": None},
        **_axis_style(),
        "min": min_y,
        "max": max_y,
        "labels": {
            "style": {"color": CHART_AXIS, "fontSize": "10px"},
            "__format": "moneyK",
        },
    }
    config["series"] = [
        {
            "name": "Reserve balance (with monthly fund)",
            "type": "areaspline",
            "color": CHART_RENTAL,
            "lineWidth": 2,
            "data": reserve_values,
            "fillColor": {
                "linearGradient": {"x1": 0, "y1": 0, "x2": 0, "y2": 1},
                "stops": [
                    [0, f"rgba(26, 122, 76, {CHART_AREA_OPACITY_TOP})"],
                    [1, f"rgba(26, 122, 76, {CHART_AREA_OPACITY_BOTTOM})"],
                ],
            },
        },
        {
            "name": "Cumulative surprise cost (no reserve)",
            "type": "area",
            "step": "left",
            "color": CHART_CASHFLOW,
            "lineWidth": 2,
            "data": no_reserve_values,
            "fillColor": {
                "linearGradient": {"x1": 0, "y1": 0, "x2": 0, "y2": 1},
                "stops": [
                    [0, f"rgba(164, 61, 18, {CHART_AREA_OPACITY_TOP})"],
                    [1, f"rgba(164, 61, 18, {CHART_AREA_OPACITY_BOTTOM})"],
                ],
            },
        },
    ]

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
    {_highcharts_host("repair-fund-story-chart-mount", config, aria_label="Reserve balance vs no-reserve surprise cost")}
  </div>
  <div class="chart-legend repair-fund-legend">
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
