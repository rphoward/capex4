# Capex4 standalone port proof

Date: 2026-06-05  
Source plan: `capex3/.cursor/plans/capex4_standalone_port_64399264.plan.md`

## Tranche summary

| Tranche | Result |
|---|---|
| 1 Scaffold | `C:\Project\capex4` created; bulk copy from factory; `pyproject.toml` name `capex4`; launchers added |
| 2 Canonical imports | Presentation + `core.teaching` contractSource cutover |
| 3 Tests | 13 modules migrated; `test_core_facade_reexport` → `test_no_compat_shim_packages` |
| 4 Shim deletion | Removed `rental_capex_calculator`, `teaching_display_plan`, `bootstrap`, top-level `workbook_assumptions`, `heartbeat_server.py` |
| 5 Gates + docs | `test_architecture_gates` updated; standalone README, CONTEXT, AGENTS |
| 6 Portability | All proof commands below |

## Deviation: model_spec injection

After removing facade shims, `presentation/http_contracts.py` must pass `model_spec=` to `calculate_rental_capex` and `solve_rental_capex`. Four tests that call core directly were updated to use keyword `model_spec=`.

## Compile proof (`C:\Project\capex4`)

```powershell
cd C:\Project\capex4
$env:PYTHONPATH = 'src'
python -m compileall src\capex3 tests
```

**Result:** OK (exit 0)

## Full discover

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

**Result:** Ran **139** tests, **0 failures**, **0 errors** (exit 0)

Note: Plan estimated 144 after excluding factory-only tests; actual count is 139 because `test_core_facade_reexport` (9 tests) was replaced by `test_no_compat_shim_packages` (2 tests).

## Minimum regression block (135 tests)

```powershell
python -m unittest tests.test_architecture_gates tests.test_fixture_parity tests.test_focused_verification tests.test_presentation_htmx_renderer tests.test_calculator_resilience_contract tests.test_cash_flow_stability_evidence tests.test_calculation_result_traces tests.test_offer_ready_evidence tests.test_emergency_debt_ledger tests.test_reserve_first_shortfall_solver tests.test_shock_survival tests.test_deal_input_round_trip tests.test_reserve_account_apy_parity tests.test_repair_reserve_path_trace tests.test_solver_question_catalog tests.test_pro_forma_fixture_contract
```

**Result:** Ran **135** tests, **0 failures** (exit 0)

## Server /ready

```powershell
.\tools\start-capex4.ps1 -NoBrowser -NoWait
```

**Result:** Server started on `http://127.0.0.1:3001/`; `/ready` returned **200** within 20s (launcher `Wait-ForReady` succeeded). Log: `tmp/capex4-server.log`.

## Portability copy proof

```powershell
Copy-Item -Recurse C:\Project\capex4 C:\Temp\capex4-port-proof
cd C:\Temp\capex4-port-proof
$env:PYTHONPATH = 'src'
python -m compileall src\capex3 tests
python -m unittest discover -s tests -p "test_*.py"
```

**Result:** Ran **139** tests, **0 failures** (exit 0)

## Grep proof (shim imports)

```text
rg "from capex3\.(rental_capex_calculator|teaching_display_plan|bootstrap)" src/ tests/*.py
```

**Result:** No Python import hits in `src/` or `tests/test_*.py`.

Historical references remain in `tests/fixtures/README.md` and `workbook-parity-matrix.md` (factory proof archaeology only).

No `Planner/` or `docs/slice-runs/` directories in capex4 tree.

## Factory pointer

One line added to `capex3/README.md`: standalone app artifact at `../capex4`.
