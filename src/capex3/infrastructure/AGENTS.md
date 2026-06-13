# infrastructure — Agent Context

**Parent:** `AGENTS.md` (repo root)
**Scope:** `src/capex3/infrastructure/`

## OVERVIEW

Mechanisms only: stdlib HTTP server wiring and workbook JSON loading via `importlib.resources`. No business formulas, route translation, or teaching rules.

## STRUCTURE

```
infrastructure/
├── server.py                          # HTTP bootstrap → presentation handlers
├── __main__.py                        # python -m capex3.infrastructure
└── workbook_assumptions/
    ├── __init__.py                    # load_workbook_model_spec_record
    └── data/*.json                    # shipped via setuptools package-data
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Server entry | `server.py` | Delegates to `presentation.rental_capex_http_api` |
| Workbook JSON load | `workbook_assumptions/__init__.py` | Must import `capex3.core.workbook_assumptions` |
| Default deal/workbook data | `workbook_assumptions/data/*.json` | Runtime truth (not `tests/fixtures/spreadsheet-defaults.json`) |

## CONVENTIONS

- `workbook_assumptions/__init__.py` owns all `importlib.resources` access for workbook JSON
- `server.py` is wiring-only: imports presentation handler, binds port, serves static assets path
- `__main__.py` delegates to `server.main`

## ANTI-PATTERNS

- `server.py` importing `capex3.core` or legacy shims
- Route/payload logic in `server.py` (strings like `calculate_payload`, `"Route not found."`)
- Business formulas or teaching journey rules in this layer
- Top-level `workbook_assumptions` package (removed — use `infrastructure/workbook_assumptions/`)

## TESTS / VERIFICATION

```powershell
$env:PYTHONPATH = 'src'
python -m unittest tests.test_architecture_gates tests.test_focused_verification tests.test_reserve_account_apy_parity -v
python -m capex3.infrastructure.server   # manual smoke; port from env or default
```
