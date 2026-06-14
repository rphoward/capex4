# presentation — Agent Context

**Parent:** `AGENTS.md` (repo root) — policy, boundaries, and commands live there.
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
├── htmx_state.py, htmx_format.py, htmx_shell.py
└── browser_assets/             # index.html, CSS, vendor/htmx.min.js
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| HTTP JSON contracts | `http_contracts.py` | Loads model_spec via infrastructure |
| Route handlers | `rental_capex_http_api.py` | `RentalCapexTeachingHeartbeatHandler` |
| Full page render | `htmx_page.py` (`render_full_page`; via `htmx_renderer.py`) | |
| Chart markup | `htmx_charts.py` | 10-year and repair-fund charts |
| Evidence panels | `htmx_evidence.py`, `htmx_evidence_primitives.py` | |
| Static assets | `browser_assets/` | Tokens in `tokens.css`; components in `styles.css` |
