from __future__ import annotations

from typing import Mapping, Sequence

from capex3.presentation.htmx_format import _format, _html
from capex3.presentation.htmx_state import UiState


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


def _first_present(source: Mapping[str, object], keys: Sequence[str]) -> object:
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return None


def _result_trace(state: UiState, name: str) -> Mapping[str, object]:
    if not state.result:
        return {}
    trace = state.result.get("traces", {}).get(name, {})
    return trace if isinstance(trace, Mapping) else {}


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
                "value": _trace_formatted_value(
                    card,
                    ("value", "amount", "metricValue"),
                    card.get("kind"),
                ),
                "note": card.get("note") or card.get("description") or card.get("detail") or "",
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
    return _format(
        _first_present(source, keys),
        source.get("kind") or source.get("valueKind") or fallback_kind,
    )
