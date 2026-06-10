from __future__ import annotations

from typing import Mapping

from capex3.presentation.htmx_evidence import _proforma_panel, _sinking_fund_panel
from capex3.presentation.htmx_format import _attr, _html, _string_mapping
from capex3.presentation.htmx_inputs import _deal_identity_label, _input_panel, _output_panel
from capex3.presentation.htmx_state import UiState, _build_state, _hidden_state_fields

HTMX_VENDOR_ASSET_PATH = "/assets/vendor/htmx.min.js"


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
    <link rel="stylesheet" href="/assets/styles.css">
    <script src="{HTMX_VENDOR_ASSET_PATH}" defer></script>
  </head>
  <body>
    {app_fragment}
  </body>
</html>
"""


def _render_app(state: UiState) -> str:
    deal_label = _deal_identity_label(state)
    return f"""
<div id="app">
  <header class="topbar">
    <div class="topbar-left">
      <div class="brand-lockup">
        <p class="kicker">Rental CapEx</p>
        <h1>Deal Workbench</h1>
      </div>
      <span class="deal-label" id="deal-label">{_html(deal_label)}</span>
    </div>
    <div class="run-status {_attr(state.status_kind)}" id="run-status">{_html(state.status_text)}</div>
  </header>

  <form id="deal-form">
    {_hidden_state_fields(state)}
    <main class="shell">
      {_input_panel(state)}
      {_output_panel(state)}
      {_sinking_fund_panel(state)}
      {_proforma_panel(state)}
    </main>
  </form>
</div>""".strip()
