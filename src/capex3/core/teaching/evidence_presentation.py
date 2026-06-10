"""Per-layer presentation hints for evidence trace rendering."""

from __future__ import annotations

from typing import Mapping

EVIDENCE_LAYER_PRESENTATION: dict[str, dict[str, str]] = {
    "cashFlow": {
        "primaryReward": "receipt",
        "drilldownTitle": "Show workbook math",
    },
    "repairDrivers": {
        "primaryReward": "drivers",
        "drilldownTitle": "Full component table",
    },
    "repairFund": {
        "primaryReward": "summary",
        "drilldownTitle": "Year-by-year table",
    },
    "tenYear": {
        "primaryReward": "summary",
        "drilldownTitle": "10-year table",
    },
    "cashFlowStability": {
        "primaryReward": "twoPath",
        "drilldownTitle": "Emergency ledger tables",
    },
    "whatWorks": {
        "primaryReward": "thresholds",
        "drilldownTitle": "Solver assumptions",
    },
}


def presentation_for_layer(layer_id: str) -> dict[str, str]:
    presentation = EVIDENCE_LAYER_PRESENTATION.get(layer_id)
    return dict(presentation) if presentation else {}


def drilldown_title(trace: Mapping[str, object], fallback: str = "Show the math") -> str:
    presentation = trace.get("presentation")
    if isinstance(presentation, Mapping):
        title = presentation.get("drilldownTitle")
        if title:
            return str(title)
    return fallback
