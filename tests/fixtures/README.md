# Model verification fixtures

These fixtures freeze behavior extracted from `rental-capex-model-v4-defaults.xlsx`.
Canonical workbook contract vs app-only extensions are summarized below; the full
**workbook cell → Python field → UI surface** inventory is in
[`workbook-parity-matrix.md`](workbook-parity-matrix.md).

## Workbook-canonical (fixture-gated)

Metrics asserted in `model-verification-cases.json` **calculation** cases (not `solver.*`)
and aligned with the V2 workbook contract in `spreadsheet-defaults.json` / `workbookContract`:

| Concept | Workbook | Python | In 17-case parity? |
|---------|----------|--------|-------------------|
| Year-10 ROI | Dashboard `B28` | `dashboard.year10Roi` | Yes (calculation cases) |
| Year-10 liquidation wealth | Pro Forma `L17` | `proForma[10].realEstateLiquidationWealth` | Yes (includes `L15` reserve addback at sale) |
| Pro forma reserve timeline | Pro Forma rows | `proForma[].annualCapexContribution`, `accumulatedCapexReserve`, `accumulatedTrueCashFlow`, … | Yes — years **0–10** on all five calculation cases (Slice 1, 2026-06-04) |
| Dashboard snapshot cash flow | Dashboard `B40` | `dashboard.trueMonthlyCashFlow` | Yes |
| Sinking fund / cap | `B34`, `B21` | `totalMonthlyCapexReserve`, `targetCapExReserve` | Yes (selected cases) |

**B28 vs L17:** `dashboard.year10Roi` follows workbook `B28` and **excludes** the `L15`
accumulated reserve returned at sale. `proForma[10].realEstateLiquidationWealth` follows `L17`
and **includes** that addback because reserve cash maintained the property during the hold.
Do not treat these as interchangeable “one return number.”

`Formula Audit` is legacy workbook diagnostics only — not an app input or output contract.

## App-only / not workbook-contract

| Surface | Python | Proof | UI today |
|---------|--------|-------|----------|
| Repair reserve path trace (teaching-only) | `result.repairReservePathTrace` | `tests/test_repair_reserve_path_trace.py` only — **no** workbook expected rows (**A4**) | Repair Fund evidence layer — **present** (teaching authority; not spreadsheet parity) |
| Solver bisection | `solve_rental_capex` / cases `solver.*` | 12 cases in `fixture_parity`; `fixtureContract.solverCasePolicy`: app-side regression, **not** workbook-canonical | Decision-step solver workbench — **present**; must not imply spreadsheet solver truth (**A5**) |
| Emergency loan APR / term | `emergencyLoanApr`, `emergencyLoanTermYears` | Defaults in `default-deal-inputs.json` (`0.125`, `5`); `core.deal_inputs` validation; **consumed** by `core.emergency_debt_ledger` on teaching trace (Phase 5 Slice 2) — **no** 17-case parity | Loan Terms journey (Phase 4 Slice 2) |
| Repair fund APY | `reserveAccountApy` | Workbook `Dashboard!B20`; **`proForma.reserveCapAccelerated.highReserveApy`** (`0.5` APY, cap shutoff) — see `tests/test_reserve_account_apy_parity.py` | Loan Terms journey (Phase 4 Slice 2); round-trip: `tests/test_deal_input_round_trip.py` |
| Landlord-paid utilities | `monthlyUtilitiesLandlordPaid` | Workbook `Dashboard!B25`; in 17-case parity via defaults | Loan Terms journey (Phase 4 Slice 3); calculator already consumes |
| Legal / advertising opex | `legalProfessionalAnnual`, `advertisingLeasingAnnual` | Workbook `Dashboard!B28` / `B29`; in 17-case parity via defaults | Walkthrough journey (Phase 4 Slice 3); calculator already consumes |

### Resolved — repair trace ownership (Phase 2 Slice 1, 2026-06-04)

- **Decision id:** `repair_reserve_path_trace_workbook_vs_teaching`
- **Approved option:** **(b) teaching-only** — trace timeline is app-owned teaching evidence; workbook-canonical reserve cap, diversion, and year-10 reserve story stay on **pro forma** and **dashboard** fields in the table above.
- **Proof:** `Planner/slice-runs/capex3-workbook-parity-and-resilience/PROOF-LOG.md` Phase 2 Slice 1; archived decision in `Planner/slice-runs/capex3-workbook-parity-and-resilience/archive/slice-1-repair-trace-ownership-architecture-decision.md`.
- **Rejected:** workbook-sourced trace rows in `model-verification-cases.json` (option a).

### Resolved — year-10 return metrics presentation (Phase 3 Slice 1, 2026-06-04)

- **Decision id:** `year10_return_metrics_b28_vs_l17`
- **Approved option:** **(a) teach-only dual-label** — keep B28 and L17; UI must label both and forbid implying one combined “return.”
- **Rejected:** new workbook-canonical full-exit ROI field (option b).
- **Proof:** `Planner/slice-runs/capex3-workbook-parity-and-resilience/PROOF-LOG.md` Phase 3 Slice 1.

**Phase 3 UI gaps (remaining):** sale bridge receipt (**B1**); dual-label render (**B2**, per decision); repair-fund copy (**B6**); pro forma table columns (**B7**). See [`workbook-parity-matrix.md`](workbook-parity-matrix.md).

### Phase 5 — repair resilience metrics (app-only, 2026-06-05)

Not workbook-canonical; no rows in `model-verification-cases.json` calculation cases. Design authority: `Planner/slice-runs/capex3-workbook-parity-and-resilience/debt-ledger-design.md` (Slices 1–2 decisions). Matrix rows **R1–R7** in [`workbook-parity-matrix.md`](workbook-parity-matrix.md).

| Metric / surface | Python path | Proof module |
|----------------|-------------|--------------|
| Emergency debt ledger | `result.emergencyDebtLedger` | `tests/test_emergency_debt_ledger.py` |
| Shock-adjusted cash flow | `result.shockAdjustedCashFlow`, `shockSurvival.*` | `tests/test_shock_survival.py`, `tests/test_calculator_resilience_contract.py` |
| Overlap warning | `result.overlapDetected` | `tests/test_emergency_debt_ledger.py`, `tests/test_presentation_htmx_renderer.py` |
| User cash-flow floor | `input.minimumTrueMonthlyCashFlow` | `tests/test_deal_input_round_trip.py`, `tests/test_calculator_resilience_contract.py` |
| Reserve-first-shortfall solver | `core.reserve_first_shortfall_solver`, offer-ready apply | `tests/test_reserve_first_shortfall_solver.py` |
| Cash-flow stability evidence | `teaching_display_plan.cash_flow_stability_evidence` | `tests/test_cash_flow_stability_evidence.py`, `tests/test_offer_ready_evidence.py` |
| Offer-ready / dossier wiring | presentation `htmx_renderer` | `tests/test_presentation_htmx_renderer.py`, `tests/test_offer_ready_evidence.py` |

**Consolidated Phase 5 proof block** (from repo root; 100 tests at Slice 8 closeout):

```powershell
cd C:\Project\capex3
$env:PYTHONPATH = 'src'
python -m unittest tests.test_architecture_gates tests.test_fixture_parity tests.test_reserve_first_shortfall_solver tests.test_emergency_debt_ledger tests.test_deal_input_round_trip tests.test_presentation_htmx_renderer tests.test_reserve_account_apy_parity tests.test_repair_reserve_path_trace tests.test_shock_survival tests.test_cash_flow_stability_evidence tests.test_calculator_resilience_contract tests.test_offer_ready_evidence
```

17-case workbook parity remains on calculation-case fields only; resilience metrics are explicitly app-only per Slice 8 closeout.

## Year-10 return presentation contract (Phase 3)

Slices 2–3 must render existing calculator truth only:

| Concept | Workbook | Python | UI label (minimum) | Teach |
|---------|----------|--------|-------------------|-------|
| Year-10 ROI | `B28` | `dashboard.year10Roi` | Year-10 ROI (B28) | Excludes reserve addback at sale (`L15`). |
| Liquidation wealth | `L17` | `proForma[10].realEstateLiquidationWealth` | Liquidation wealth (L17) | Includes `accumulatedCapexReserve` returned at sale. |

Do not add a third invented ROI. Metric strip and tenYear summary must show both labels when both values are visible.

## Files

| File | Role |
|------|------|
| `../test_deal_input_round_trip.py` | Phase 4 input defaults, round-trip, and validation (not 17-case parity) |
| `../test_reserve_account_apy_parity.py` | Phase 4 Slice 5: `proForma.reserveCapAccelerated.highReserveApy` (`reserveAccountApy` 0.5) parity + drift guard |
| `model-verification-cases.json` | Active **17-case** gate: 5 calculation + 12 `solver.*` regression cases |
| `spreadsheet-defaults.json` | Large extraction artifact: `workbookContract`, formulas, named ranges — **provenance/regen only** |
| `workbook-parity-matrix.md` | Cell → field → UI inventory (Phase 1 Slice 2) |
| `default-deal-inputs.json` | Default input bundle for manual/browser runs (if present) |

### spreadsheet-defaults.json (Option A — no CI)

**Human decision 2026-06-04:** `spreadsheet-defaults.json` is **not** executed in automated CI
at Phase 1 closeout. It supports audit, regeneration, and `workbookContract` reference — not
runtime truth. Regenerate after refreshing parity-v2 analysis:

```text
analysis/parity-v2/extract_xlsx_inventory.py
tools/generate-verification-fixtures.mjs
```

Do **not** add CI that loads the full JSON blob unless a later approved slice replaces Option A.

## Repair trace disclaimer contract (Phase 3)

Machine-readable fields on `result.traces.repairFund` (from `browser_app_contracts._repair_fund_trace`):

| Key | Value / intent |
|-----|----------------|
| `workbookCanonical` | `false` — not in 17-case workbook parity |
| `teachingOnly` | `true` — teaching timeline, not spreadsheet contract |
| `decisionId` | `repair_reserve_path_trace_workbook_vs_teaching` |
| `canonicalReserveSource` | `proForma_and_dashboard` |
| `canonicalReserveFields` | `proForma[].annualCapexContribution`, `proForma[].accumulatedCapexReserve`, `dashboard.totalMonthlyCapexReserve`, `dashboard.targetCapExReserve` |
| `sourceNote` | Required copy: trace is teaching-only; cap/Y10 reserve story uses pro forma + dashboard; forbid spreadsheet-parity language |

**Phase 3 UI behavior (deferred):** show `sourceNote` on the Repair Fund layer; do not imply workbook fixture parity for the trace chart/table. HTML rendering lives in `presentation/` (not Slice 2).

## Regeneration

Use `tools/generate-verification-fixtures.mjs` after refreshing `analysis/parity-v2/` with
`analysis/parity-v2/extract_xlsx_inventory.py`.

Use `currencyAbsolute` and `ratioAbsolute` tolerances from `model-verification-cases.json`.

## Proof commands (from repo root)

```powershell
cd C:\Project\capex3
$env:PYTHONPATH = 'src'
python -m unittest tests.test_architecture_gates
python -m unittest tests.test_pro_forma_fixture_contract
python -m unittest tests.test_fixture_parity
python -m unittest tests.test_fixture_drift_trial
python -m unittest tests.test_deal_input_round_trip
python -m unittest tests.test_reserve_account_apy_parity
```

`tests.test_fixture_drift_trial` proves the parity harness fails on intentional
expected-value drift (temp copy of `model-verification-cases.json` only; canonical
file on disk is never mutated).

Legacy shim (same 17-case JSON report):

```powershell
python -m capex3.rental_capex_calculator.fixture_parity
```

Optional: `python -m unittest tests.test_repair_reserve_path_trace`

## Slice history (workbook parity run)

| Slice | Outcome |
|-------|---------|
| 1 (2026-06-04) | Pro forma years 0–10 on all calculation cases; `solver.*` waiver in PHASE-BACKLOG |
| 2 (2026-06-04) | Phase 1: this README + `workbook-parity-matrix.md`; honest UI gap inventory |
| 2 (Phase 2, 2026-06-04) | Teaching-only A4 labeling; repair trace disclaimer contract; `browser_app_contracts` view-model keys for Phase 3 |
| 3 (2026-06-04) | Parity harness under `tests/`; primary proof `tests.test_fixture_parity` |
| 4 (2026-06-04) | Intentional drift trial (`tests.test_fixture_drift_trial`); Phase 1 proof contract closed |

**Known documentation gaps remaining until later phases:** UI does not yet surface all
workbook-aligned dashboard year-10 sale fields; repair trace and solver remain app-owned
per matrix above.
