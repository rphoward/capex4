# tests — Agent Context

**Parent:** `AGENTS.md` (repo root) — policy, boundaries, and commands live there.
**Scope:** `tests/`

## OVERVIEW

stdlib `unittest` suite: architecture AST gates, workbook fixture parity, and behavioral contracts. Not colocated under `src/`.

## STRUCTURE

```
tests/
├── test_architecture_gates.py    # layer import + asset policy enforcement
├── test_fixture_parity.py        # 17-case workbook parity gate
├── fixture_parity.py             # helper (not test_* — not auto-discovered)
├── test_*.py                     # discoverable modules
└── fixtures/
    ├── model-verification-cases.json
    ├── spreadsheet-defaults.json   # audit/regen only — NOT CI truth
    └── README.md
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Layer boundary enforcement | `test_architecture_gates.py` | Core/presentation/infra rules |
| Shim package ban | `test_no_compat_shim_packages.py` | |
| Workbook parity | `test_fixture_parity.py` + `fixture_parity.py` | 5 calc + 12 solver.* cases |
| Presentation / htmx | `test_presentation_htmx_renderer.py`, `test_focused_verification.py` | Charts, assets, page shell |
| Fixture docs | `fixtures/README.md`, `workbook-parity-matrix.md` | Tolerances, B28 vs L17 |
