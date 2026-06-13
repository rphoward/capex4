# core — Agent Context

**Parent:** `AGENTS.md` (repo root)
**Scope:** `src/capex3/core/`

## OVERVIEW

Calculation domain center: deal inputs, validation, financial primitives, workbook assumption shapes, calc + solver — no HTTP, files, browser, or outer layers.

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Main calculation | `calculate_rental_capex.py` | Request/result types + `calculate_rental_capex` |
| Solver | `solve_rental_capex.py` | Bracketing, reserve-first shortfall |
| Deal input normalize/validate | `deal_inputs.py` | `RentalCapexDealInputRequest` |
| Workbook shapes (no I/O) | `workbook_assumptions.py` | `compose_workbook_model_spec`, `model_spec_record` |
| Emergency debt / survival | `emergency_debt_ledger.py` | Shock-adjusted cash flow, overlap |
| Reserve path trace | `repair_reserve_path_trace.py` | Teaching-adjacent numeric trace |
| Solver question catalog | `solver_question_catalog.py` | Selected questions contract |
| Public re-exports | `__init__.py` | Canonical import surface |

## core/teaching/ (pedagogy subdomain)

**Scope:** `src/capex3/core/teaching/` — evidence framing, journey metadata, solver display labels. **Not numeric truth.**

| Task | Location |
|------|----------|
| Result traces for UI | `calculation_result_traces.py` |
| Offer-ready copy | `offer_ready_evidence.py` |
| Cash-flow stability evidence | `cash_flow_stability_evidence.py`, `cash_flow_stability_trace.py` |
| Solver display / thresholds | `solver_question_display.py` |
| Workbench metadata constants | `workbench_metadata.py` |
| Evidence presentation helpers | `evidence_presentation.py` |
| Teaching catalog re-export | `teaching/solver_question_catalog.py` → core catalog |

`teaching/` imports `capex3.core.*`; modules outside `teaching/` do not import `core.teaching`.

## CONVENTIONS

- `core/__init__.py` docstring: no imports from infrastructure, presentation, bootstrap, HTTP, package resources, browser, or test fixtures
- Workbook assumption **types** live here; JSON files live in `infrastructure/workbook_assumptions/data/`
- Errors via `errors.py` — `RentalCapexError`, `VALIDATION_ERROR`, `LOOKUP_ERROR`

## ANTI-PATTERNS

- Any `import capex3.infrastructure` or `import capex3.presentation` in core modules
- String literals referencing `tests/fixtures` paths
- Loading JSON or calling `importlib.resources` from core

## TESTS / VERIFICATION

```powershell
$env:PYTHONPATH = 'src'
python -m unittest tests.test_architecture_gates tests.test_deal_input_round_trip tests.test_emergency_debt_ledger tests.test_reserve_first_shortfall_solver tests.test_shock_survival tests.test_calculation_result_traces -v
```

Architecture gate AST checks enforce core import bans — see `tests/test_architecture_gates.py`.
