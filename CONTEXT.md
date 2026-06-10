# Rental CapEx Teaching App

Standalone Python app that teaches small rental investors whether a deal **survives its repairs**—through cash-flow stability evidence, walkthrough-to-offer workflow, a 10-year investment-path comparison, and a resilience-focused solver (planned). Workbook-faithful calculation supplies deterministic truth; **core/teaching** frames questions and evidence; presentation renders graphs and htmx UI.

## Language

**Calculation domain center**:
The inner package `capex3.core` where deal inputs, validation, financial primitives, workbook assumption shapes, and calculation meaning live without HTTP, files, or browser concepts.

**Teaching subdomain**:
Pedagogy and evidence framing in `capex3.core.teaching`—**evidence layer** framing, journey steps, solver question labels and grouping—not numeric truth. Physical home: `src/capex3/core/teaching/`.

**Rental CapEx calculation**:
The deterministic workbook-backed model that turns normalized deal inputs and workbook assumptions into calculated outputs (and related solver runs).

**Deal inputs**:
Structured field values describing a property and financing scenario (purchase price, rents, taxes, component overrides, etc.).

**Workbook assumptions**:
Baseline component costs, lifespans, quantity defaults, and related workbook-backed reference data—the calculation reads from `infrastructure/workbook_assumptions/data/`, not user-entered deal fields.

**Cash-flow stability**:
Teaching frame comparing funding repairs through planned reserves versus absorbing repairs as emergency debt.

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
- **Teaching subdomain** (`core/teaching/`) owns evidence framing and journey—not numeric truth
- **Presentation** renders server-side HTML and JSON API adapters via `presentation/http_contracts.py`
- **Walkthrough-to-offer** ends on the **offer-ready screen**; deeper material lives in the stakeholder dossier evidence layers
