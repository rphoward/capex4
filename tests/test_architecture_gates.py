import ast
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
CAPEX3_ROOT = SRC_ROOT / "capex3"
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
FORBIDDEN_FIXTURE_PATH_FRAGMENTS = (
    "tests/fixtures",
    "tests\\fixtures",
)
REJECTED_LAYER_NAMES = (
    "public",
    "workbench",
    "engine",
    "application",
    "python_runtime",
)
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
APPROVED_PRESENTATION_JAVASCRIPT = {
    Path("browser_assets/vendor/htmx.min.js"),
}


class ArchitectureDependencyGatesTest(unittest.TestCase):
    def test_core_imports_no_forbidden_runtime_or_outer_layers(self) -> None:
        violations: list[str] = []

        for source_path in _python_files(CORE_ROOT):
            tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_name = alias.name
                        if _is_forbidden_core_import(imported_name):
                            violations.append(f"{source_path}: import {imported_name}")

                if isinstance(node, ast.ImportFrom):
                    imported_module = node.module or ""
                    if node.level == 0 and _is_forbidden_core_import(imported_module):
                        violations.append(f"{source_path}: from {imported_module} import ...")

                    if (
                        imported_module == "importlib"
                        and node.level == 0
                        and any(
                            alias.name in FORBIDDEN_IMPORTLIB_RESOURCES_ALIASES
                            for alias in node.names
                        )
                    ):
                        violations.append(f"{source_path}: from importlib import resources")

        self.assertEqual([], violations)

    def test_core_does_not_reference_test_fixtures_as_runtime_data(self) -> None:
        violations: list[str] = []

        for source_path in _python_files(CORE_ROOT):
            tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if any(
                        fragment in node.value
                        for fragment in FORBIDDEN_FIXTURE_PATH_FRAGMENTS
                    ):
                        violations.append(f"{source_path}: {node.value}")

        self.assertEqual([], violations)

    def test_rejected_layer_package_names_do_not_exist(self) -> None:
        existing_rejected_layers = [
            name for name in REJECTED_LAYER_NAMES if (CAPEX3_ROOT / name).exists()
        ]

        self.assertEqual([], existing_rejected_layers)

    def test_rejected_layer_directory_names_do_not_exist_under_capex3(self) -> None:
        existing_rejected_directories = [
            str(path.relative_to(CAPEX3_ROOT))
            for path in CAPEX3_ROOT.rglob("*")
            if path.is_dir() and path.name in REJECTED_LAYER_NAMES
        ]

        self.assertEqual([], existing_rejected_directories)

    def test_real_layer_modules_exist(self) -> None:
        expected_modules = [
            CORE_ROOT / "workbook_assumptions.py",
            CORE_ROOT / "teaching" / "__init__.py",
            INFRASTRUCTURE_ROOT / "workbook_assumptions" / "__init__.py",
            PRESENTATION_ROOT / "http_contracts.py",
            PRESENTATION_ROOT / "rental_capex_http_api.py",
            INFRASTRUCTURE_ROOT / "server.py",
        ]

        missing_modules = [str(path) for path in expected_modules if not path.exists()]

        self.assertEqual([], missing_modules)

    def test_removed_shim_packages_do_not_exist(self) -> None:
        existing_shims = [
            name for name in REMOVED_SHIM_PACKAGES if (CAPEX3_ROOT / name).exists()
        ]

        self.assertEqual([], existing_shims)

    def test_presentation_does_not_import_removed_shim_packages(self) -> None:
        violations: list[str] = []

        for source_path in _python_files(PRESENTATION_ROOT):
            tree = ast.parse(source_path.read_text(encoding="utf-8"), source_path.name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if _is_forbidden_presentation_import(alias.name):
                            violations.append(f"{source_path}: import {alias.name}")

                if isinstance(node, ast.ImportFrom):
                    imported_module = node.module or ""
                    if node.level == 0 and _is_forbidden_presentation_import(
                        imported_module
                    ):
                        violations.append(
                            f"{source_path}: from {imported_module} import ..."
                        )

        self.assertEqual([], violations)

    def test_infrastructure_owns_workbook_resource_loading(self) -> None:
        infrastructure_imports = _imported_modules(
            INFRASTRUCTURE_ROOT / "workbook_assumptions" / "__init__.py"
        )

        self.assertIn("importlib", infrastructure_imports)
        self.assertIn("capex3.core.workbook_assumptions", infrastructure_imports)

    def test_presentation_owns_http_route_translation(self) -> None:
        source = (PRESENTATION_ROOT / "rental_capex_http_api.py").read_text(
            encoding="utf-8"
        )

        required_symbols = [
            "def handle_get(",
            "def handle_post(",
            "def invalid_json_response(",
            "def not_found_response(",
            "def exception_response(",
            "class RentalCapexTeachingHeartbeatHandler",
        ]
        missing_symbols = [
            symbol for symbol in required_symbols if symbol not in source
        ]

        self.assertEqual([], missing_symbols)

    def test_presentation_allows_only_vendored_htmx_javascript(self) -> None:
        javascript_files = {
            path.relative_to(PRESENTATION_ROOT)
            for path in PRESENTATION_ROOT.rglob("*.js")
            if path.is_file()
        }
        unapproved = sorted(
            str(path).replace("\\", "/")
            for path in javascript_files - APPROVED_PRESENTATION_JAVASCRIPT
        )

        self.assertEqual([], unapproved)
        self.assertEqual(APPROVED_PRESENTATION_JAVASCRIPT, javascript_files)

    def test_presentation_browser_assets_have_no_app_module_or_request_code(self) -> None:
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
        forbidden_fragments = [
            'type="' + 'module"',
            "/assets/" + "modules/",
            "fetch" + "(",
            "XML" + "HttpRequest",
            "new " + "Request(",
        ]
        violations = [
            fragment for fragment in forbidden_fragments if fragment in scanned_source
        ]

        self.assertEqual([], module_files)
        self.assertEqual([], violations)

    def test_handoff_visual_translation_stays_in_css_not_javascript(self) -> None:
        stylesheet = (PRESENTATION_ROOT / "browser_assets" / "styles.css").read_text(
            encoding="utf-8"
        )
        required_css_markers = [
            "--banana",
            "--depth-shadow",
            "border-radius: var(--radius);",
            "border-bottom: 1px solid var(--banana-dim);",
            "border-right: 1px solid var(--banana-dim);",
        ]
        missing_markers = [
            marker for marker in required_css_markers if marker not in stylesheet
        ]

        self.assertEqual([], missing_markers)
        self.assertNotIn("React", stylesheet)
        self.assertNotIn("Babel", stylesheet)

    def test_infrastructure_server_only_wires_entrypoint(self) -> None:
        server_path = INFRASTRUCTURE_ROOT / "server.py"
        server_imports = _imported_modules(server_path)
        forbidden_import_prefixes = (
            "capex3.rental_capex_calculator",
            "capex3.teaching_display_plan",
            "capex3.core",
            "capex3.bootstrap",
        )
        forbidden_payload_fragments = (
            "calculate_payload",
            "defaults_payload",
            "solve_payload",
            "workbench_payload",
            "Request body must be valid JSON.",
            "Route not found.",
        )

        forbidden_imports = [
            imported_name
            for imported_name in server_imports
            if any(
                imported_name == prefix or imported_name.startswith(f"{prefix}.")
                for prefix in forbidden_import_prefixes
            )
        ]
        source = server_path.read_text(encoding="utf-8")
        forbidden_payloads = [
            fragment for fragment in forbidden_payload_fragments if fragment in source
        ]

        self.assertEqual([], forbidden_imports)
        self.assertEqual([], forbidden_payloads)


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
