# AGENTS.md — Capex4 standalone

## Boundaries

- **core/** — calculation truth; **core/teaching/** — pedagogy and evidence framing
- **infrastructure/** — workbook JSON load, HTTP server wiring
- **presentation/** — htmx, HTTP adapters, browser assets (no invented metrics)
- No `rental_capex_calculator`, `teaching_display_plan`, `bootstrap`, or top-level `workbook_assumptions` packages

## Proof

```powershell
cd C:\Project\capex4
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -p "test_*.py" -v
python -m unittest tests.test_architecture_gates tests.test_fixture_parity
```
