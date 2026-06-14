# core — Agent Context

**Parent:** `AGENTS.md` (repo root) — policy, boundaries, and commands live there.
**Scope:** `src/capex3/core/`

## OVERVIEW

Calculation domain: deal inputs, validation, financial primitives, workbook assumption shapes, calc + solver. No HTTP, files, browser, or outer layers.

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

## core/teaching/

Pedagogy subdomain — evidence framing, journey metadata, solver display labels. Not numeric truth.

| Task | Location |
|------|----------|
| Result traces for UI | `teaching/calculation_result_traces.py` |
| Offer-ready copy | `teaching/offer_ready_evidence.py` |
| Cash-flow stability evidence | `teaching/cash_flow_stability_evidence.py`, `cash_flow_stability_trace.py` |
| Solver display / thresholds | `teaching/solver_question_display.py` |
| Workbench metadata constants | `teaching/workbench_metadata.py` |
| Evidence presentation helpers | `teaching/evidence_presentation.py` |
| Teaching catalog re-export | `teaching/solver_question_catalog.py` → core catalog |

`teaching/` imports `capex3.core.*`; modules outside `teaching/` do not import `core.teaching`.
