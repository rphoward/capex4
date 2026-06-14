"""Single unittest module: architecture gates, workbook parity, HTTP smoke."""

from __future__ import annotations

import ast
import json
import unittest
from http import HTTPStatus
from pathlib import Path

from capex3.core import RentalCapexError
from capex3.core.solver_question_catalog import (
    threshold_questions_to_contract,
    threshold_solver_request_dict,
)
from capex3.infrastructure.server import startup_event_payload
from capex3.infrastructure.workbook_assumptions import load_workbook_model_spec_record
from capex3.presentation.http_contracts import (
    calculate_payload,
    defaults_payload,
    workbench_payload,
)
from capex3.presentation.htmx_renderer import render_ui_fragment
from capex3.presentation.rental_capex_http_api import (
    READINESS_PATH,
    STATIC_BROWSER_ASSET_CACHE_CONTROL,
    HtmlResponse,
    StaticAssetResponse,
    handle_get,
    handle_post,
    invalid_json_response,
    not_found_response,
    readiness_payload,
    what_works_presentation_contract_payload,
)
from tests.fixture_parity import run_fixture_parity

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPEX3_ROOT = REPO_ROOT / "src" / "capex3"
CORE_ROOT = CAPEX3_ROOT / "core"
INFRASTRUCTURE_ROOT = CAPEX3_ROOT / "infrastructure"
PRESENTATION_ROOT = CAPEX3_ROOT / "presentation"

FORBIDDEN_CORE_CAPEX3_PREFIXES = (
    "capex3.infrastructure",
    "capex3.presentation",
    "capex3.runtime",
)
FORBIDDEN_CORE_IMPORTS = {
    "http",
    "http.server",
    "importlib.resources",
    "pydantic",
    "tests",
}
FORBIDDEN_IMPORTLIB_RESOURCES_ALIASES = {"resources"}
FORBIDDEN_FIXTURE_PATH_FRAGMENTS = ("tests/fixtures", "tests\\fixtures")
REJECTED_LAYER_NAMES = ("public", "workbench", "engine", "application", "python_runtime")
REMOVED_SHIM_PACKAGES = (
    "rental_capex_calculator",
    "teaching_display_plan",
    "bootstrap",
    "workbook_assumptions",
)
FORBIDDEN_PRESENTATION_IMPORT_PREFIXES = (
    "capex3.rental_capex_calculator",
    "capex3.teaching_display_plan",
    "capex3.bootstrap",
    "capex3.workbook_assumptions",
)
APPROVED_PRESENTATION_JAVASCRIPT = {Path("browser_assets/vendor/htmx.min.js")}


class Capex3Test(unittest.TestCase):
    def test_workbook_fixture_parity_17_cases(self) -> None:
        report = run_fixture_parity()
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(report["calculationCaseCount"], 5)
        self.assertEqual(report["solverCaseCount"], 12)
        self.assertEqual(report["totalCaseCount"], 17)
        self.assertEqual(
            report["runtimeSource"],
            "src/capex3/infrastructure/workbook_assumptions/data",
        )
        self.assertEqual(
            report["fixtureSource"],
            "tests/fixtures/model-verification-cases.json",
        )

    def test_core_entrypoints_and_workbook_load(self) -> None:
        self.assertTrue(issubclass(RentalCapexError, Exception))
        model_spec = load_workbook_model_spec_record()
        self.assertEqual(model_spec["sourceWorkbook"], "rental-capex-model-v4-defaults.xlsx")
        self.assertIn("inputs", model_spec)
        self.assertIn("assumptions", model_spec)
        self.assertGreater(len(model_spec["assumptions"]["components"]), 0)

    def test_runtime_payload_and_http_smoke(self) -> None:
        self.assertEqual(readiness_payload()["status"], "ready")
        self.assertTrue(defaults_payload()["ok"])
        self.assertTrue(workbench_payload()["ok"])
        contract = what_works_presentation_contract_payload()
        self.assertTrue(contract["ok"])
        self.assertEqual(contract["contractSource"], "capex3.core.teaching")

        ready = handle_get(READINESS_PATH)
        index = handle_get("/")
        stylesheet = handle_get("/assets/styles.css")
        calculate = handle_post("/api/calculate", {"inputs": {}})
        solve = handle_post(
            "/api/solve",
            {"request": {"questionId": "breakEvenRent", "baseInput": {}}},
        )

        self.assertEqual(ready.status, HTTPStatus.OK)
        self.assertEqual(ready.payload, readiness_payload())
        self.assertIsInstance(index, HtmlResponse)
        self.assertIn('src="/assets/vendor/htmx.min.js"', index.body)
        self.assertIsInstance(stylesheet, StaticAssetResponse)
        self.assertEqual(stylesheet.cache_control, STATIC_BROWSER_ASSET_CACHE_CONTROL)
        self.assertEqual(calculate.status, HTTPStatus.OK)
        self.assertTrue(calculate.payload["ok"])
        self.assertEqual(solve.status, HTTPStatus.OK)
        self.assertTrue(solve.payload["ok"])
        self.assertEqual(not_found_response().status, HTTPStatus.NOT_FOUND)
        self.assertEqual(invalid_json_response().status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            startup_event_payload("127.0.0.1", 3000)["readinessPath"],
            READINESS_PATH,
        )

    def test_threshold_questions_single_catalog_source(self) -> None:
        questions = threshold_questions_to_contract()
        self.assertEqual(5, len(questions))
        ids = {str(question["id"]) for question in questions}
        self.assertIn("breakEvenRent", ids)
        self.assertIn("reserveIncreaseFirstShortfall", ids)
        workbench = workbench_payload()["workbench"]
        self.assertEqual(questions, workbench["thresholdQuestions"])
        self.assertNotIn("workbenchThresholdQuestions", workbench)

    def test_lazy_what_works_trace_skips_solver_fanout(self) -> None:
        full = calculate_payload({})["result"]
        lazy = calculate_payload({}, build_what_works_solvers=False)["result"]
        full_questions = full["traces"]["whatWorks"]["questions"]
        lazy_questions = lazy["traces"]["whatWorks"]["questions"]
        self.assertGreater(len(full_questions), 0)
        self.assertEqual([], lazy_questions)
        self.assertEqual(
            full["traces"]["repairFund"]["id"],
            lazy["traces"]["repairFund"]["id"],
        )

    def test_solve_threshold_action_builds_what_works_questions(self) -> None:
        fragment = render_ui_fragment(
            {
                "activeEvidenceLayer": "tenYear",
                "evidenceFollowsStep": "false",
                "questionId": "breakEvenRent",
            },
            "solve-threshold",
        )
        self.assertNotIn("Evidence trace unavailable", fragment)
        self.assertIn('data-evidence-layer="whatWorks"', fragment)
        self.assertIn("Break-even rent", fragment)

    def test_threshold_solver_request_dict_matches_question(self) -> None:
        question = threshold_questions_to_contract()[0]
        request = threshold_solver_request_dict(question, base_input={"rent": 1000})
        self.assertEqual(question["solver"]["variable"], request["variable"])
        self.assertEqual({"rent": 1000}, request["baseInput"])

    def test_htmx_evidence_layers_render(self) -> None:
        fragment = render_ui_fragment({}, "reset")
        for marker in (
            'data-evidence-layer="tenYear"',
            'data-evidence-layer="cashFlow"',
            'data-evidence-layer="repairFund"',
            "evidence-panel",
        ):
            self.assertIn(marker, fragment)

    def test_architecture_gates(self) -> None:
        core_import_violations: list[str] = []
        fixture_violations: list[str] = []
        presentation_import_violations: list[str] = []

        for source_path in _python_files(CORE_ROOT):
            tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_forbidden_core_import(alias.name):
                            core_import_violations.append(
                                f"{source_path}: import {alias.name}"
                            )
                if isinstance(node, ast.ImportFrom):
                    imported_module = node.module or ""
                    if node.level == 0 and _is_forbidden_core_import(imported_module):
                        core_import_violations.append(
                            f"{source_path}: from {imported_module} import ..."
                        )
                    if (
                        imported_module == "importlib"
                        and node.level == 0
                        and any(
                            alias.name in FORBIDDEN_IMPORTLIB_RESOURCES_ALIASES
                            for alias in node.names
                        )
                    ):
                        core_import_violations.append(
                            f"{source_path}: from importlib import resources"
                        )
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if any(fragment in node.value for fragment in FORBIDDEN_FIXTURE_PATH_FRAGMENTS):
                        fixture_violations.append(f"{source_path}: {node.value}")

        for source_path in _python_files(PRESENTATION_ROOT):
            tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_forbidden_presentation_import(alias.name):
                            presentation_import_violations.append(
                                f"{source_path}: import {alias.name}"
                            )
                if isinstance(node, ast.ImportFrom):
                    imported_module = node.module or ""
                    if node.level == 0 and _is_forbidden_presentation_import(imported_module):
                        presentation_import_violations.append(
                            f"{source_path}: from {imported_module} import ..."
                        )

        self.assertEqual([], core_import_violations)
        self.assertEqual([], fixture_violations)
        self.assertEqual([], presentation_import_violations)
        self.assertEqual(
            [],
            [name for name in REJECTED_LAYER_NAMES if (CAPEX3_ROOT / name).exists()],
        )
        self.assertEqual(
            [],
            [
                str(path.relative_to(CAPEX3_ROOT))
                for path in CAPEX3_ROOT.rglob("*")
                if path.is_dir() and path.name in REJECTED_LAYER_NAMES
            ],
        )
        self.assertEqual(
            [],
            [name for name in REMOVED_SHIM_PACKAGES if (CAPEX3_ROOT / name).exists()],
        )
        self.assertFalse(
            (
                CAPEX3_ROOT
                / "runtime"
                / "rental_capex_teaching_server"
                / "heartbeat_server.py"
            ).exists()
        )

        expected_modules = [
            CORE_ROOT / "workbook_assumptions.py",
            CORE_ROOT / "teaching" / "__init__.py",
            INFRASTRUCTURE_ROOT / "workbook_assumptions" / "__init__.py",
            PRESENTATION_ROOT / "http_contracts.py",
            PRESENTATION_ROOT / "rental_capex_http_api.py",
            INFRASTRUCTURE_ROOT / "server.py",
        ]
        self.assertEqual([], [str(path) for path in expected_modules if not path.exists()])

        infra_imports = _imported_modules(
            INFRASTRUCTURE_ROOT / "workbook_assumptions" / "__init__.py"
        )
        self.assertIn("importlib", infra_imports)
        self.assertIn("capex3.core.workbook_assumptions", infra_imports)

        api_source = (PRESENTATION_ROOT / "rental_capex_http_api.py").read_text(
            encoding="utf-8"
        )
        required_symbols = (
            "def handle_get(",
            "def handle_post(",
            "def invalid_json_response(",
            "def not_found_response(",
            "def exception_response(",
            "class RentalCapexTeachingHeartbeatHandler",
        )
        self.assertEqual([], [symbol for symbol in required_symbols if symbol not in api_source])

        javascript_files = {
            path.relative_to(PRESENTATION_ROOT)
            for path in PRESENTATION_ROOT.rglob("*.js")
            if path.is_file()
        }
        self.assertEqual(APPROVED_PRESENTATION_JAVASCRIPT, javascript_files)

        browser_assets_root = PRESENTATION_ROOT / "browser_assets"
        modules_root = browser_assets_root / "modules"
        module_files = (
            sorted(str(path.relative_to(browser_assets_root)) for path in modules_root.rglob("*") if path.is_file())
            if modules_root.exists()
            else []
        )
        scanned_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(browser_assets_root.rglob("*"))
            if path.is_file()
            and path.suffix in {".html", ".css", ".js"}
            and path.relative_to(browser_assets_root) != Path("vendor/htmx.min.js")
        )
        forbidden_fragments = (
            'type="' + 'module"',
            "/assets/" + "modules/",
            "fetch" + "(",
            "XML" + "HttpRequest",
            "new " + "Request(",
        )
        self.assertEqual([], module_files)
        self.assertEqual([], [f for f in forbidden_fragments if f in scanned_source])

        tokens = (browser_assets_root / "tokens.css").read_text(encoding="utf-8")
        stylesheet = (browser_assets_root / "styles.css").read_text(encoding="utf-8")
        combined_css = tokens + stylesheet
        required_css_markers = (
            "--canvas",
            "--amber",
            "--hairline",
            "--font-ui",
            "--font-display",
            "--chart-grid",
            "border-radius: var(--radius-shell);",
            "border: 1px solid var(--hairline)",
        )
        self.assertEqual([], [m for m in required_css_markers if m not in combined_css])
        self.assertNotIn("React", stylesheet)
        self.assertNotIn("Babel", stylesheet)

        server_path = INFRASTRUCTURE_ROOT / "server.py"
        server_imports = _imported_modules(server_path)
        forbidden_import_prefixes = (
            "capex3.rental_capex_calculator",
            "capex3.teaching_display_plan",
            "capex3.core",
            "capex3.bootstrap",
        )
        forbidden_imports = [
            name
            for name in server_imports
            if any(name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden_import_prefixes)
        ]
        server_source = server_path.read_text(encoding="utf-8")
        forbidden_payloads = [
            fragment
            for fragment in (
                "calculate_payload",
                "defaults_payload",
                "solve_payload",
                "workbench_payload",
                "Request body must be valid JSON.",
                "Route not found.",
            )
            if fragment in server_source
        ]
        self.assertEqual([], forbidden_imports)
        self.assertEqual([], forbidden_payloads)

        json_paths = list(
            (INFRASTRUCTURE_ROOT / "workbook_assumptions" / "data").glob("*.json")
        ) + list((REPO_ROOT / "tests" / "fixtures").glob("*.json"))
        self.assertEqual(len(json_paths), 7)
        for path in json_paths:
            with path.open("r", encoding="utf-8") as source_file:
                self.assertIsInstance(json.load(source_file), dict)


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _imported_modules(source_path: Path) -> set[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module)
    return imports


def _is_forbidden_core_import(imported_name: str) -> bool:
    if imported_name in FORBIDDEN_CORE_IMPORTS:
        return True
    if any(
        imported_name == prefix or imported_name.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_CORE_CAPEX3_PREFIXES
    ):
        return True
    return any(
        imported_name == forbidden or imported_name.startswith(f"{forbidden}.")
        for forbidden in FORBIDDEN_CORE_IMPORTS
    )


def _is_forbidden_presentation_import(imported_name: str) -> bool:
    return any(
        imported_name == prefix or imported_name.startswith(f"{prefix}.")
        for prefix in FORBIDDEN_PRESENTATION_IMPORT_PREFIXES
    )


if __name__ == "__main__":
    unittest.main()
