# presentation — Agent Context

**Parent:** `AGENTS.md` (repo root)
**Scope:** `src/capex3/presentation/`

## OVERVIEW

HTTP route handlers, JSON contract adapters, and server-side htmx HTML rendering. Imports calculation from `core` and teaching metadata from `core.teaching`; does not invent metrics.

## STRUCTURE

```
presentation/
├── http_contracts.py           # JSON payloads (defaults, calculate, workbench)
├── rental_capex_http_api.py    # handle_get, handle_post, handler class
├── htmx_renderer.py            # re-export barrel → htmx_page.py
├── htmx_page.py, htmx_inputs.py, htmx_evidence*.py, htmx_charts.py, htmx_offer_ready.py
├── htmx_state.py, htmx_format.py
└── browser_assets/             # index.html, tokens.css, fonts.css, styles.css, vendor/htmx.min.js
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| HTTP JSON contracts | `http_contracts.py` | Loads model_spec via infrastructure |
| Route handlers | `rental_capex_http_api.py` | `RentalCapexTeachingHeartbeatHandler` |
| Full page render | `htmx_page.py` (`render_full_page`; imported via `htmx_renderer.py`) | |
| Evidence panels | `htmx_evidence.py`, `htmx_evidence_primitives.py` | |
| Static assets | `browser_assets/` | Refero tokens in `tokens.css`; components in `styles.css` |

## CONVENTIONS

- `http_contracts.py` is the adapter boundary: injects `model_spec=` from `load_workbook_model_spec_record()`
- htmx modules use `from __future__ import annotations` (existing style)
- Only allowed JS: `browser_assets/vendor/htmx.min.js`, `browser_assets/vendor/highcharts.js`, `browser_assets/charts.js`
- CSS must retain handoff markers in `tokens.css` + `styles.css` (`--canvas`, `--amber`, `--hairline`, `--font-ui`, `--font-display`, `border-radius: var(--radius-shell);`, `border: 1px solid var(--hairline)` — see `test_handoff_visual_translation_stays_in_css_not_javascript` in `tests/test_architecture_gates.py`)
- Font stack: Source Sans 3 (UI), Source Serif 4 (KPI/display), IBM Plex Mono (ledger) — loaded via `browser_assets/fonts.css` (linked from `htmx_page.py` and `index.html`)

## ANTI-PATTERNS

- Invented metrics not backed by core calculation or teaching metadata
- Direct core calls without `model_spec` injection where infrastructure load is required
- `browser_assets/modules/` tree
- Client JS patterns: `type="module"`, `/assets/modules/`, `fetch(`, `XMLHttpRequest`, `new Request(`
- React/Babel strings in HTML/CSS/JS
- Removed shim imports (`rental_capex_calculator`, etc.)

## TESTS / VERIFICATION

```powershell
$env:PYTHONPATH = 'src'
python -m unittest tests.test_architecture_gates tests.test_presentation_htmx_renderer tests.test_evidence_debug_render tests.test_offer_ready_evidence tests.test_calculation_result_traces -v
```

Architecture gate verifies handler exports and browser asset policy in `tests/test_architecture_gates.py`.
