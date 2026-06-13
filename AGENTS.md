# PROJECT KNOWLEDGE BASE — Capex4

**Generated:** 2026-06-12
**Commit:** f22ea7b
**Branch:** main

## OVERVIEW

Standalone Rental CapEx teaching app (Python 3.11+, stdlib only). Workbook-faithful calculation in `capex3.core`; pedagogy in `core/teaching/`; JSON load + HTTP in `infrastructure/`; htmx UI in `presentation/`. Repo folder `capex4`, import package `capex3`.

Domain language: `CONTEXT.md`.

## STRUCTURE

```
capex4/
├── src/capex3/
│   ├── core/              # calculation truth + core/teaching/
│   ├── infrastructure/    # server wiring, workbook JSON load
│   ├── presentation/      # HTTP adapters, htmx, browser_assets/
│   └── runtime/           # thin -m delegates (no logic)
├── tests/                 # unittest + architecture gates
└── tools/start-capex4.ps1
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Deal calc + solver | `src/capex3/core/calculate_rental_capex.py`, `solve_rental_capex.py` | Numeric truth |
| Workbook assumption shapes | `src/capex3/core/workbook_assumptions.py` | Types only — no file I/O |
| Teaching / evidence framing | `src/capex3/core/teaching/` | Not numeric truth |
| JSON load | `src/capex3/infrastructure/workbook_assumptions/` | `importlib.resources` |
| HTTP JSON payloads | `src/capex3/presentation/http_contracts.py` | Injects `model_spec` |
| htmx render + routes | `src/capex3/presentation/rental_capex_http_api.py`, `htmx_*.py` | |
| Server bootstrap | `src/capex3/infrastructure/server.py` | Wiring only |
| Architecture enforcement | `tests/test_architecture_gates.py` | AST import bans |
| Fixture parity | `tests/fixture_parity.py`, `tests/fixtures/` | 17-case gate |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `calculate_rental_capex` | fn | `src/capex3/core/calculate_rental_capex.py` | Main calc entry |
| `solve_rental_capex` | fn | `src/capex3/core/solve_rental_capex.py` | Solver orchestration |
| `load_workbook_model_spec_record` | fn | `src/capex3/infrastructure/workbook_assumptions/__init__.py` | Runtime JSON load |
| `model_spec_record` | fn | `src/capex3/core/workbook_assumptions.py` | Assumption shapes |
| `defaults_payload` / `calculate_payload` | fn | `src/capex3/presentation/http_contracts.py` | HTTP JSON adapters |
| `handle_get` / `handle_post` | fn | `src/capex3/presentation/rental_capex_http_api.py` | Route handlers |
| `render_full_page` | fn | `src/capex3/presentation/htmx_page.py` | htmx page (re-exported via `htmx_renderer.py`) |
| `build_calculation_result_traces` | fn | `src/capex3/core/teaching/calculation_result_traces.py` | Evidence traces |
| `main` | fn | `src/capex3/infrastructure/server.py` | stdlib HTTP server |

## BOUNDARIES

- **core/** — calculation truth; **core/teaching/** — pedagogy and evidence framing
- **infrastructure/** — workbook JSON load, HTTP server wiring
- **presentation/** — htmx, HTTP adapters, browser assets (no invented metrics)
- **Forbidden packages** under `src/capex3/`: `rental_capex_calculator`, `teaching_display_plan`, `bootstrap`, top-level `workbook_assumptions`
- **Forbidden layer dirs**: `public`, `workbench`, `engine`, `application`, `python_runtime`

## CONVENTIONS

- Always `$env:PYTHONPATH = 'src'` — no console_scripts in `pyproject.toml`
- Split workbook assumptions: shapes in `core/workbook_assumptions.py`; files + load in `infrastructure/workbook_assumptions/`
- Presentation calls core with `model_spec=` injected from infrastructure — never loads JSON directly in core
- Tests use **unittest**, not pytest (despite `.gitignore` listing `.pytest_cache/`)
- Zero declared deps — stdlib `http.server` + vendored htmx only
- Static check: `python -m compileall src\capex3 tests` (no ruff/mypy/black)

## ANTI-PATTERNS (THIS PROJECT)

- Core importing `infrastructure`, `presentation`, `runtime`, `http`, `importlib.resources`, `pydantic`, or `tests`
- `server.py` importing `capex3.core` or containing route/payload strings (`calculate_payload`, `"Route not found."`, etc.)
- Presentation inventing metrics or loading workbook JSON without `http_contracts` path
- Merging B28 vs L17 year-10 ROI metrics (distinct workbook fields)
- Using `spreadsheet-defaults.json` as CI/runtime truth (audit/regen only)
- Adding JS beyond `browser_assets/vendor/htmx.min.js`; no `fetch(`, `XMLHttpRequest`, `type="module"`

## COMMANDS

```powershell
cd C:\Users\bh\Documents\capex4   # docs may say C:\Project\capex4
$env:PYTHONPATH = 'src'

python -m compileall src\capex3 tests
python -m unittest discover -s tests -p "test_*.py" -v
python -m unittest tests.test_architecture_gates tests.test_fixture_parity

.\tools\start-capex4.ps1            # port 3000–3099, opens browser
python -m capex3.infrastructure.server
```

## CURSOR / AGENTS

- Nearest `AGENTS.md` wins when working in subtrees.
- Subtree context:
  - `src/capex3/core/AGENTS.md`
  - `src/capex3/infrastructure/AGENTS.md`
  - `src/capex3/presentation/AGENTS.md`
  - `tests/AGENTS.md`

## NOTES

- Triple server entry: `-m capex3.infrastructure`, `-m capex3.infrastructure.server`, `-m capex3.runtime.rental_capex_teaching_server`
- Duplicate catalog modules: `core/solver_question_catalog.py` and `core/teaching/solver_question_catalog.py` (teaching re-exports)
