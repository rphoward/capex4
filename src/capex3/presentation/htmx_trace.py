from __future__ import annotations

from typing import Mapping, Sequence

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


def _trace_value(source: Mapping[str, object], keys: Sequence[str]) -> object:
    return _first_present(source, keys)


def _result_trace(state: UiState, name: str) -> Mapping[str, object]:
    if not state.result:
        return {}
    trace = state.result.get("traces", {}).get(name, {})
    return trace if isinstance(trace, Mapping) else {}
