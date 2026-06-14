# infrastructure — Agent Context

**Parent:** `AGENTS.md` (repo root) — policy, boundaries, and commands live there.
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
| Workbook JSON load | `workbook_assumptions/__init__.py` | Imports `capex3.core.workbook_assumptions` |
| Default deal/workbook data | `workbook_assumptions/data/*.json` | Runtime truth (not `tests/fixtures/spreadsheet-defaults.json`) |
