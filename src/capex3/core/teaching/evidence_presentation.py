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

PRIMARY_REWARD_LABELS: dict[str, str] = {
    "receipt": "Receipt waterfall",
    "drivers": "Summary cards + top drivers",
    "summary": "Summary cards",
    "twoPath": "Two-path comparison",
    "thresholds": "Threshold questions",
}


def presentation_for_layer(layer_id: str) -> dict[str, str]:
    presentation = EVIDENCE_LAYER_PRESENTATION.get(layer_id)
    return dict(presentation) if presentation else {}


def primary_reward_key(layer_id: str) -> str:
    return presentation_for_layer(layer_id).get("primaryReward", "")


def primary_reward_label(layer_id: str) -> str:
    key = primary_reward_key(layer_id)
    return PRIMARY_REWARD_LABELS.get(key, "")


def primary_reward_label_for_trace(
    trace: Mapping[str, object],
    layer_id: str,
) -> str:
    presentation = trace.get("presentation")
    if isinstance(presentation, Mapping):
        key = presentation.get("primaryReward")
        if key:
            return PRIMARY_REWARD_LABELS.get(str(key), "")
    return primary_reward_label(layer_id)


def drilldown_title(trace: Mapping[str, object], fallback: str = "Show the math") -> str:
    presentation = trace.get("presentation")
    if isinstance(presentation, Mapping):
        title = presentation.get("drilldownTitle")
        if title:
            return str(title)
    return fallback
