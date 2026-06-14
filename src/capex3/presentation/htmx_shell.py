"""Shared HTML layout primitives for the Rental CapEx htmx workbench.

Refero reference lock (composite — no single dashboard to copy):

| Role | Refero source | UUID |
|------|---------------|------|
| Shell tokens + CTA | Runway runway.com | style 436e4ca8-dcfe-43ee-ae50-5b4e2fc88b15 |
| Data surfaces / ledger | Midday midday.ai | style 7eb5e800-dff7-473b-84c2-71a98ebac23c |
| 40/60 calculator layout | Trulia rent-vs-buy | screen 7b0275ff-d717-4a37-afca-db681e5b279c |
| KPI + chart rhythm | Wealthsimple retirement calc | screen 4f2cb529-3a19-4ce3-9d5c-4f29a7cdc038 |
| Workbook tables | Equals cash burn template | screen 33bfb3dd-f2d2-4bdc-9d76-f815ec52b134 |

Tokens live in ``browser_assets/tokens.css``. Charts are server-rendered inline
SVG from ``htmx_charts.py``, refreshed by htmx swaps. CSS applies Runway 12px shell cards +
amber CTA, Midday 0px data radius + hairline grids, Trulia split, Wealthsimple serif KPIs.

**Explicit rejects:** dark sidebar shell, bento KPI grid, banana accents, grid-paper body,
 muddy Runway+Public+Midday blend, dark terminal charts, ultramarine CTA fill.
"""

from __future__ import annotations

from capex3.presentation.htmx_format import _attr, _html


def _section_head(title: str, actions_html: str = "") -> str:
    actions = f"\n    {actions_html}" if actions_html else ""
    return f"""
  <div class="section-head">
    <h2>{_html(title)}</h2>{actions}
  </div>"""


def _calculator_card(inner_html: str, *, extra_class: str = "") -> str:
    classes = "calc-card"
    if extra_class:
        classes = f"{classes} {_attr(extra_class).strip()}"
    return f"""
  <div class="{classes}">
{inner_html}
  </div>"""


def _summary_panel(label: str, value: str, footnote: str = "") -> str:
    footnote_html = (
        f'<p class="summary-footnote">{_html(footnote)}</p>' if footnote else ""
    )
    return f"""
  <div class="summary-panel results-hero-kpi">
    <p class="summary-label">{_html(label)}</p>
    <p class="summary-value num-display">{_html(value)}</p>
    {footnote_html}
  </div>"""


def _step_rail(label: str, buttons_html: str) -> str:
    return f"""
    <aside class="step-rail" aria-label="{_html(label)}">
      <p>{_html(label)}</p>
      <div class="journey-steps" id="journey-steps">{buttons_html}</div>
    </aside>"""


def _ledger_panel(title: str, body_html: str, *, panel_id: str = "") -> str:
    id_attr = f' id="{_attr(panel_id)}"' if panel_id else ""
    return f"""
  <section class="ledger-panel"{id_attr}>
{_section_head(title)}
{body_html}
  </section>"""
