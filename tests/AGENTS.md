# tests — Agent Context

**Parent:** `AGENTS.md` (repo root)
**Scope:** `tests/`

## OVERVIEW

stdlib `unittest` suite: architecture AST gates, workbook fixture parity, and behavioral contracts. Not colocated under `src/`.

## STRUCTURE

```
tests/
├── test_architecture_gates.py    # layer import + asset policy enforcement
├── test_fixture_parity.py        # 17-case workbook parity gate
├── fixture_parity.py             # helper (not test_* — not auto-discovered)
├── test_*.py                     # 19 discoverable modules
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
| Fixture docs | `fixtures/README.md`, `workbook-parity-matrix.md` | Tolerances, B28 vs L17 |

## CONVENTIONS

- Discovery pattern: `test_*.py` only — helpers like `fixture_parity.py` are imported explicitly
- Always run with `$env:PYTHONPATH = 'src'`
- `solver.*` fixture cases = app regression, not workbook-canonical
- Repair reserve path trace fixtures are teaching-only (`workbookCanonical: false`)
- Tolerances from fixture JSON: `currencyAbsolute`, `ratioAbsolute`

## ANTI-PATTERNS

- Adding pytest without updating project docs and `.gitignore` policy
- Placing architecture rules only in docs — must be enforced in `test_architecture_gates.py`

## TESTS / VERIFICATION

```powershell
$env:PYTHONPATH = 'src'
python -m compileall src\capex3 tests

# Minimum gate (root AGENTS.md)
python -m unittest tests.test_architecture_gates tests.test_fixture_parity -v

# Full discover
python -m unittest discover -s tests -p "test_*.py" -v
```

Full named-module list: `README.md` § Proof commands, `PROOF.md`.
