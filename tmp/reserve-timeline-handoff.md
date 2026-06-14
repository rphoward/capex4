# Handoff — Reserve timeline, 10-Year chart, and parity language

**Status:** discussion draft (not an implementation plan)  
**Date:** 2026-06-14  
**Glossary:** `CONTEXT.md` (updated this session)  
**Related prior work:** server-rendered SVG charts (`htmx_charts.py`); `htmx_trace.py` extraction (uncommitted in working tree)

---

## Why this handoff exists

We aligned on **product language** in `CONTEXT.md`: the **reserve timeline** (contributions, interest, repair draws, shortfalls) belongs on **pro forma**, and Repair Fund + 10-Year Story should graph that line—not a separate “teaching-only” simulation.

Code, tests, and parity docs still largely reflect the **older split** (smooth `accumulatedCapexReserve` on pro forma; discrete `repairReservePathTrace` marked teaching-only). This document captures **decisions, open questions, and constraints** for a planning conversation—not a task list.

---

## Agreed language (see `CONTEXT.md`)

| Term | Meaning |
|------|---------|
| **Reserve timeline** | Year-by-year reserve balance on pro forma after contributions, interest, and **repair draws** |
| **Reserve shortfall** | Timeline ends below zero after a repair |
| **No-reserve comparison path** | Cumulative repair cost if nothing was set aside (Repair Fund chart) |
| **Dashboard reserve rate** | Monthly set-aside + cap (`totalMonthlyCapexReserve`, `targetCapExReserve`)—inputs, not the timeline |
| **10-Year Story** | Compare paths over 10 years; **target** includes a **pro forma reserve timeline** line |

**Retired in conversation:** “reserve trace” without qualification; “teaching-only” for reserve **math** (teaching still owns copy/labels).

**Honesty flag in CONTEXT:** glossary may run ahead of shipped charts/calculator.

---

## Current code reality (for planners)

### 10-Year Story chart — **four** series today

From `calculation_result_traces._ten_year_trace`:

1. **Liquidation wealth** — `realEstateLiquidationWealth` (operating cash + net proceeds; at year 10 adds reserve addback)
2. **Cash position (operating + initial)** — `initialInvestment + accumulatedTrueCashFlow`
3. **Money market** — comparison path
4. **IRA** — comparison path

**Not plotted:** `accumulatedCapexReserve` (smooth reserve buildup, no repair debits).

### Repair Fund — separate engine today

- `compute_repair_reserve_path_trace()` → discrete repair hits, shortfalls, no-reserve cumulative line
- Marked **teaching-only** in traces; matrix row A4; no 17-case parity rows
- Repair Fund SVG chart reads `traces.repairFund`, not pro forma rows directly

### Pro forma reserve today

- `accumulatedCapexReserve`: grows toward cap with interest; **no repair withdrawals**
- `accumulatedTrueCashFlow`: operating cash pile (L16 path); workbook parity

---

## Open discussion: “fifth line” and cash position

### What you asked

You wanted a **fifth** 10-Year line for the growing reserve / repair-hit story on pro forma. On closer look, a **cash position** line already exists—and you’re unsure if it belongs, if the math is wrong, or where investors “feel” it in real life.

### Answer for the discussion (not a final decision)

**You did not necessarily make a mistake** about wanting a reserve line on pro forma. You may have **merged two different pockets** in your head:

| Line | What it models | Where an investor feels it |
|------|----------------|---------------------------|
| **Cash position** (`initial + accumulatedTrueCashFlow`) | Liquid **operating** cash after expenses and reserve **transfers** (money that left your pocket for the repair fund is not in this pile) | Monthly checking account: can I cover the mortgage, vacancies, life, the next deal? |
| **Reserve timeline** (what you want to add) | Balance **inside the repair fund** after contributions, interest, and **repair bills** | When the roof invoice arrives: is the fund full, depleted, or short? |
| **Liquidation wealth** | Operating cash + **hypothetical sale** (and at Y10, reserve returned to you on that path) | Exit: what do I walk away with if I sell? |

So:

- **Cash position is not bad math** for what it claims—it’s workbook L16 + initial, parity-tested, with an explicit teach note that year 10 excludes sale proceeds and reserve addback on **that** series.
- **It is the wrong line for repair survival**—that’s the reserve timeline, not operating cash.
- **Adding a fifth line for reserve timeline does not require removing cash position** unless the chart becomes unreadable or the story duplicates liquidation wealth awkwardly.

### Tensions to resolve in planning (not answered here)

1. **Five lines on one chart** — pedagogical clarity vs clutter. Is reserve timeline on 10-Year Story, or only on Repair Fund?
2. **Double-counting narrative** — operating cash excludes reserve transfers; reserve line shows the bucket; liquidation adds reserve back at sale. Do we need stronger copy so users don’t add lines mentally?
3. **Post-cap quirk** — when reserve cap is hit, pro forma adds `annual_capex_reserve` back into `accumulatedTrueCashFlow` (cash that no longer funds the cap). Does that match how you explain “felt” liquidity?
4. **Merge vs coexist** — should `repairReservePathTrace` fold into pro forma rows, or stay a derived view of the same truth?

---

## Parity and tests (discussion only)

Phase 2 decision **`repair_reserve_path_trace_workbook_vs_teaching`** (option b) said: path trace is app-owned; cap/monthly/Y10 reserve on pro forma + dashboard.

**If reserve timeline moves onto pro forma with repair draws:**

- Matrix row **A4** and `tests/test_repair_reserve_path_trace.py` teaching-only assertions need a **policy conversation**, not a drive-by string fix.
- Options sketched earlier: workbook parity extension, app-only parity cases (like Phase 5 resilience), or hybrid.
- Failing `test_repair_fund_trace_view_model_is_teaching_only_not_workbook_canonical` (`tests/test_repair_reserve_path_trace.py`) expects `sourceNote` phrases (`teaching-only`, `not in the 17-case`, …) that the shortened copy no longer contains—a **symptom** of the old policy, not a string-only fix.

---

## SVG / presentation notes (context for planners)

- Charts are server-rendered SVG (`htmx_charts.py`); no Highcharts.
- Repair Fund chart: reserve balance vs stepped no-reserve path; event markers plot **repair amount** on Y, not post-repair balance dip.
- `htmx_trace.py` breaks circular import between evidence and charts (uncommitted in working tree).

---

## Suggested planning agenda (questions, not tasks)

1. **Single source of truth:** What is the one year-loop that produces reserve timeline rows on pro forma?
2. **10-Year Story composition:** Five lines as in CONTEXT, or four on 10-Year + full story on Repair Fund only?
3. **Cash position line:** Keep, relabel, or demote to table-only?
4. **Repair draws on pro forma:** Same event schedule as today’s path trace, or recomputed from sinking fund only?
5. **Shortfalls:** Graph negative reserve on 10-Year, Repair Fund only, or both?
6. **Parity:** What gets 17-case rows vs app-only regression vs teaching disclaimer?
7. **CONTEXT.md:** Update “five paths” if planning chooses a different chart composition.

---

## Out of scope for this handoff

- Step-by-step implementation slices
- File-level edit lists
- Commit/PR strategy

---

## How to use this doc

Bring it to a planning session (human or agent). Resolve the **open discussion** bullets before writing an implementation plan. Treat `CONTEXT.md` as vocabulary contract; change it if planning overturns “five paths” or reserve-on-pro-forma direction.
