# Capex4 — Rental CapEx standalone app

Self-contained Rental CapEx teaching app. Copy this folder anywhere, set `PYTHONPATH=src`, run tests, and start the server — no factory or planner dependencies.

**Folder name:** `capex4`  
**Python package:** `capex3` (imports stay `capex3.*` for this port)

## Layout

```text
capex4/
  src/capex3/
    core/                 # calculation + core/teaching/ pedagogy
    infrastructure/       # server, workbook JSON load
    presentation/         # HTTP, htmx, browser assets
    runtime/              # thin -m entry delegates
  tests/
  tools/start-capex4.ps1
  start-capex4.cmd
```

## Quick start

```powershell
cd C:\Project\capex4
$env:PYTHONPATH = 'src'
.\tools\start-capex4.ps1
```

`-NoBrowser` skips opening a tab. `-NoWait` returns after `/ready` without waiting for Escape.

## Proof commands

```powershell
cd C:\Project\capex4
$env:PYTHONPATH = 'src'

python -m compileall src\capex3 tests
python -m unittest discover -s tests -p "test_*.py" -v

python -m unittest tests.test_architecture_gates tests.test_fixture_parity tests.test_focused_verification tests.test_presentation_htmx_renderer tests.test_calculator_resilience_contract tests.test_cash_flow_stability_evidence tests.test_calculation_result_traces tests.test_offer_ready_evidence tests.test_emergency_debt_ledger tests.test_reserve_first_shortfall_solver tests.test_shock_survival tests.test_deal_input_round_trip tests.test_reserve_account_apy_parity tests.test_repair_reserve_path_trace tests.test_solver_question_catalog tests.test_pro_forma_fixture_contract
```

## Server entry points

- `python -m capex3.infrastructure.server`
- `python -m capex3.infrastructure`
- `python -m capex3.runtime.rental_capex_teaching_server`

Product language: see `CONTEXT.md`.
