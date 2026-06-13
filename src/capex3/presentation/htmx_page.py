from __future__ import annotations

from typing import Mapping

from capex3.presentation.htmx_evidence import (
    _output_panel,
    _proforma_panel,
    _sinking_fund_panel,
)
from capex3.presentation.htmx_format import _attr, _html, _string_mapping
from capex3.presentation.htmx_inputs import _deal_identity_label, _input_panel
from capex3.presentation.htmx_state import UiState, _build_state, _hidden_state_fields

HTMX_VENDOR_ASSET_PATH = "/assets/vendor/htmx.min.js"
HIGHCHARTS_VENDOR_ASSET_PATH = "/assets/vendor/highcharts.js"
CHARTS_SCRIPT_PATH = "/assets/charts.js"
FONTS_STYLESHEET_PATH = "/assets/fonts.css"
TOKENS_STYLESHEET_PATH = "/assets/tokens.css"


def _font_head_markup() -> str:
    return f"""    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="{FONTS_STYLESHEET_PATH}">"""


def render_full_page() -> str:
    return _document(render_app_fragment())


def render_ui_fragment(form: Mapping[str, object] | None, action: str) -> str:
    return render_app_fragment(form, action)


def render_app_fragment(
    form: Mapping[str, object] | None = None,
    action: str = "calculate",
) -> str:
    state = _build_state(_string_mapping(form), action)
    return _render_app(state)


def _document(app_fragment: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Rental CapEx Model</title>
{_font_head_markup()}
    <link rel="stylesheet" href="{TOKENS_STYLESHEET_PATH}">
    <link rel="stylesheet" href="/assets/styles.css">
    <script src="{HIGHCHARTS_VENDOR_ASSET_PATH}" defer></script>
    <script src="{CHARTS_SCRIPT_PATH}" defer></script>
    <script src="{HTMX_VENDOR_ASSET_PATH}" defer></script>
  </head>
  <body>
    {app_fragment}
  </body>
</html>
"""


def _render_topbar(state: UiState) -> str:
    deal_label = _deal_identity_label(state)
    return f"""  <header class="topbar">
    <div class="topbar-left">
      <div class="brand-lockup">
        <p class="kicker">Rental Property</p>
        <h1>Deal Analyzer</h1>
      </div>
      <p class="deal-label" id="deal-label">{_html(deal_label)}</p>
    </div>
    <div class="run-status {_attr(state.status_kind)}" id="run-status" role="status" aria-live="polite">{_html(state.status_text)}</div>
  </header>"""


def _render_app(state: UiState) -> str:
    return f"""
<div id="app">
{_render_topbar(state)}

  <form id="deal-form">
    {_hidden_state_fields(state)}
    <main class="shell">
      <div class="calc-workbench">
        {_input_panel(state)}
        {_output_panel(state)}
      </div>
      {_sinking_fund_panel(state)}
      {_proforma_panel(state)}
    </main>
  </form>
</div>""".strip()
