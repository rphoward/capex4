# tests — Agent Context

**Parent:** `AGENTS.md` (repo root) — policy, boundaries, and commands live there.
**Scope:** `tests/`

## OVERVIEW

stdlib `unittest` suite: architecture AST gates, workbook fixture parity, HTTP smoke, trace contracts, and htmx fragment smoke. Not colocated under `src/`.

## STRUCTURE

```
tests/
├── test_capex3.py          # consolidated gates, parity, contracts, htmx smoke
├── fixture_parity.py       # helper (not test_* — not auto-discovered)
└── fixtures/
    ├── model-verification-cases.json
    ├── spreadsheet-defaults.json   # audit/regen only — NOT CI truth
    └── README.md
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Layer boundary enforcement | `test_capex3.py::test_architecture_gates` | Core/presentation/infra rules |
| Workbook parity | `test_capex3.py::test_workbook_fixture_parity_17_cases` | 5 calc + 12 solver cases |
| Trace / solver contracts | `test_capex3.py` | lazy whatWorks, threshold catalog |
| Presentation / htmx | `test_capex3.py::test_htmx_evidence_layers_render` | fragment smoke |
| Fixture docs | `fixtures/README.md`, `workbook-parity-matrix.md` | Tolerances, B28 vs L17 |
