# Rental CapEx Teaching App

Standalone Python app that teaches small rental investors whether a deal **survives its repairs**—through cash-flow stability evidence, walkthrough-to-offer workflow, a 10-year investment-path comparison, and a resilience-focused solver (planned). Workbook-faithful calculation supplies deterministic truth; **core/teaching** frames questions and evidence; presentation renders graphs and htmx UI.

## Language

**Calculation domain center**:
The inner package `capex3.core` where deal inputs, validation, financial primitives, workbook assumption shapes, and calculation meaning live without HTTP, files, or browser concepts.

**Teaching subdomain**:
Pedagogy and evidence framing in `capex3.core.teaching`—evidence layer copy, journey steps, solver question labels and grouping—not the reserve timeline or other calculation formulas. Physical home: `src/capex3/core/teaching/`.

**Rental CapEx calculation**:
The deterministic workbook-backed model that turns normalized deal inputs and workbook assumptions into calculated outputs (and related solver runs).

**Deal inputs**:
Structured field values describing a property and financing scenario (purchase price, rents, taxes, component overrides, etc.).

**Workbook assumptions**:
Baseline component costs, lifespans, quantity defaults, and related workbook-backed reference data—the calculation reads from `infrastructure/workbook_assumptions/data/`, not user-entered deal fields.

**Pro forma**:
The year-0–10 forecast rows produced by calculation—operating cash, reserve movement, sale bridge, and comparison paths. Reserve behavior belongs on pro forma, not on a separate shadow model.

**Reserve timeline**:
The year-by-year reserve balance on pro forma after contributions, interest, and scheduled repair draws. This is the numeric story Repair Fund and the 10-Year Story chart use for reserve hits and shortfalls.

**Reserve shortfall**:
A year in which the reserve timeline ends below zero after a repair draw—the fund did not fully cover that year's repairs.

**Repair draw**:
A scheduled component replacement cost applied in the reserve timeline in the year the sinking-fund schedule says the repair lands.

**No-reserve comparison path**:
Cumulative repair cost over time if nothing had been set aside—used to contrast funded reserve balance against surprise cost.

**Dashboard reserve rate**:
The monthly repair set-aside and target cap from the dashboard (`totalMonthlyCapexReserve`, `targetCapExReserve`)—inputs that feed the reserve timeline, not the timeline itself.

**10-Year Story**:
The evidence layer that compares five wealth paths over ten years: liquidation wealth, cash position, **pro forma reserve timeline**, money market, and IRA.

**Cash-flow stability**:
Teaching frame comparing funding repairs through the reserve timeline versus absorbing repairs as emergency debt.

**Evidence layer**:
A named teaching view in the workbench (Repair Fund, Cash Flow, 10-Year Story, What Would Work?) that explains one slice of the deal using shared calculation truth.

**Walkthrough-to-offer**:
Primary journey: after a property walkthrough, the user gets mechanical numbers to make or adjust an offer.

**Offer-ready screen**:
Minimal end-of-walkthrough summary: price that will work, bargaining levers, and eventually max offer from the resilience solver.

**Survival rule**:
A deal works when **shock-adjusted cash flow ≥ 0** AND **true monthly cash flow ≥ user cash-flow floor**.

**Infrastructure (layer)**:
Mechanisms only—loading workbook JSON, HTTP server plumbing, package resources—not business formulas or teaching journey rules.

**Presentation (layer)**:
HTTP routes, htmx rendering, browser assets. Imports calculation from `core` and teaching metadata from `core.teaching`; does not invent metrics.

## Relationships

- **Deal inputs** and **workbook assumptions** feed **Rental CapEx calculation** in `core`
- **Pro forma** carries the **reserve timeline**; **repair draws** and **reserve shortfalls** are reflected on that line
- **Dashboard reserve rate** supplies monthly set-aside and cap inputs to the **reserve timeline**
- **Repair Fund** evidence layer charts the **reserve timeline** against the **no-reserve comparison path** and explains year-by-year status
- **10-Year Story** compares five paths, including the **pro forma reserve timeline**, alongside liquidation wealth, cash position, and alternative investments
- **Reserve shortfalls** on the timeline connect forward to emergency debt and **survival rule** evidence
- **Teaching subdomain** (`core/teaching/`) owns evidence framing and journey copy—not reserve formulas
- **Presentation** renders server-side HTML and JSON API adapters via `presentation/http_contracts.py`
- **Walkthrough-to-offer** ends on the **offer-ready screen**; deeper material lives in the stakeholder dossier evidence layers

## Example dialogue

> **Investor:** "Where do I see whether my repair fund survives the roof in year seven?"
> **App:** "On **Repair Fund**—the chart plots your **reserve timeline** from **pro forma** against the **no-reserve comparison path**. A **reserve shortfall** means that year's **repair draw** exceeded what the fund could cover."
>
> **Investor:** "Is that the same line as on the 10-Year Story?"
> **App:** "Yes. The **10-Year Story** is five paths over ten years; the fifth is the **pro forma reserve timeline**. Repair hits and shortfalls belong on that line, not on a separate side calculation."

## Flagged ambiguities

- **"Reserve trace"** — means the **reserve timeline** on **pro forma**, not a separate teaching-only simulation. _Avoid:_ using "trace" alone without saying pro forma or reserve timeline.
- **"Teaching-only" reserve math** — retired for product language. Teaching still owns labels, notes, and evidence-layer copy; the **reserve timeline** is calculation truth on pro forma.
- **"Canonical"** — not used in this glossary. Prefer **workbook-parity fields** (spreadsheet-contract numbers) or **calculation truth** (what the app computes and graphs).
- **Product direction vs shipped UI** — terms such as five 10-Year paths and repair draws on the **pro forma reserve timeline** state agreed product language. Until calculation and charts match, treat this file as vocabulary contract, not a claim that every surface already plots that line.
