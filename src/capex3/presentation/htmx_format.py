from __future__ import annotations

import json
from html import escape
from typing import Mapping, Sequence


def _format(value: object, value_kind: object = None) -> str:
    if value is None:
        return "-"
    if not isinstance(value, (int, float)):
        return str(value)
    if value_kind == "percent":
        return f"{value:.2%}"
    if value_kind == "moneyCents":
        return f"${value:,.2f}"
    if value_kind == "money":
        return f"${value:,.0f}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _format_receipt_value(value: object, value_kind: object = None) -> str:
    if not isinstance(value, (int, float)):
        return _format(value, value_kind)
    if value_kind in {"moneyCents", "money"}:
        cents = 2 if value_kind == "moneyCents" else 0
        prefix = "-$" if value < 0 else "$"
        return f"{prefix}{abs(value):,.{cents}f}"
    return _format(value, value_kind)


def _format_abs_money(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return f"${abs(value):,.0f}"


def _format_chart_compact_money(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    prefix = "-$" if value < 0 else "$"
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{prefix}{magnitude / 1_000_000:.1f}M"
    if magnitude >= 1_000:
        return f"{prefix}{magnitude / 1000:.0f}k"
    return f"{prefix}{magnitude:.0f}"


def _display_value(value: object) -> str:
    if value is None:
        return "(blank)"
    return str(value)


def _control_value(value: object) -> str:
    return "" if value is None else str(value)


def _options(values: Sequence[object], selected_value: str) -> str:
    return "".join(
        f'<option value="{_attr(value)}"{_selected(str(value), selected_value)}>{_html(value)}</option>'
        for value in values
    )


def _selected(value: object, selected_value: object) -> str:
    return " selected" if str(value) == str(selected_value) else ""


def _hidden(name: str, value: object) -> str:
    return f'<input type="hidden" name="{_attr(name)}" value="{_attr(value)}">'


def _hx_post(path: str) -> str:
    return f'hx-post="{path}" hx-target="#app" hx-swap="outerHTML" hx-include="#deal-form"'


def _json_for_hidden(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _form_bool(form: Mapping[str, str], name: str, default: bool) -> bool:
    value = form.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "on", "yes"}


def _parse_number(raw: object) -> float | None:
    try:
        if raw is None or raw == "":
            return None
        return float(str(raw))
    except ValueError:
        return None


def _string_mapping(form: Mapping[str, object] | None) -> dict[str, str]:
    if not form:
        return {}
    return {str(key): str(value) for key, value in form.items()}


def _html(value: object) -> str:
    return escape("" if value is None else str(value))


def _attr(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)
