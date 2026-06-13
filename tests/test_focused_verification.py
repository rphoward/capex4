import json
from http import HTTPStatus
from importlib import resources
import threading
import unittest
from unittest import mock
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from capex3.infrastructure.server import (
    create_server as infrastructure_create_server,
    startup_event_payload,
)
from capex3.core import RentalCapexError, calculate_rental_capex, solve_rental_capex
from capex3.infrastructure.workbook_assumptions import (
    DATA_DIR as INFRASTRUCTURE_DATA_DIR,
    DATA_PACKAGE as INFRASTRUCTURE_DATA_PACKAGE,
    load_workbook_model_spec_record as load_infrastructure_workbook_model_spec_record,
)
from capex3.presentation.htmx_page import FONTS_STYLESHEET_PATH
from capex3.presentation.http_contracts import (
    defaults_payload,
    workbench_payload,
)
from capex3.presentation.rental_capex_http_api import (
    HtmlResponse,
    NO_STORE_CACHE_CONTROL,
    PRESENTATION_ASSET_DIR,
    PRESENTATION_ASSET_PACKAGE,
    PRESENTATION_ASSET_ROOT,
    READINESS_PATH,
    STATIC_BROWSER_ASSET_CACHE_CONTROL,
    StaticAssetResponse,
    WHAT_WORKS_PRESENTATION_CONTRACT_PATH,
    handle_get,
    handle_post,
    invalid_json_response,
    not_found_response,
    readiness_payload,
    what_works_presentation_contract_payload,
)
from tests.fixture_parity import run_fixture_parity


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO_ROOT = Path("C:/Project" + "/rental_" + "capex2")


class FocusedTargetVerificationTest(unittest.TestCase):
    def test_calculator_imports_and_fixture_parity_cover_17_cases(self) -> None:
        self.assertTrue(callable(calculate_rental_capex))
        self.assertTrue(callable(solve_rental_capex))
        self.assertTrue(issubclass(RentalCapexError, Exception))

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

    def test_workbook_assumptions_load_from_runtime_data_home(self) -> None:
        expected_data_dir = (
            REPO_ROOT
            / "src"
            / "capex3"
            / "infrastructure"
            / "workbook_assumptions"
            / "data"
        )
        self.assertEqual(INFRASTRUCTURE_DATA_DIR.resolve(), expected_data_dir.resolve())

        model_spec = load_infrastructure_workbook_model_spec_record()

        self.assertEqual(
            model_spec["sourceWorkbook"],
            "rental-capex-model-v4-defaults.xlsx",
        )
        self.assertIn("inputs", model_spec)
        self.assertIn("assumptions", model_spec)
        self.assertGreater(len(model_spec["assumptions"]["components"]), 0)

    def test_workbook_assumptions_are_package_data_resources(self) -> None:
        data_files = {
            resource.name
            for resource in resources.files(INFRASTRUCTURE_DATA_PACKAGE).iterdir()
            if resource.name.endswith(".json")
        }

        self.assertEqual(
            data_files,
            {
                "capex-component-costs.json",
                "component-lifespans.json",
                "default-deal-inputs.json",
                "quantity-defaults.json",
                "rent-vacancy-baselines.json",
            },
        )

    def test_browser_assets_are_package_data_resources(self) -> None:
        asset_root = resources.files(PRESENTATION_ASSET_PACKAGE).joinpath(
            PRESENTATION_ASSET_ROOT
        )
        asset_files = {
            "charts.js",
            "fonts.css",
            "index.html",
            "styles.css",
            "tokens.css",
            "vendor/highcharts.js",
            "vendor/htmx.min.js",
        }
        module_root = asset_root.joinpath("modules")
        module_files = (
            [resource.name for resource in module_root.iterdir()]
            if module_root.is_dir()
            else []
        )

        self.assertTrue(asset_root.joinpath("index.html").is_file())
        self.assertTrue(asset_root.joinpath("styles.css").is_file())
        self.assertTrue(asset_root.joinpath("vendor").joinpath("htmx.min.js").is_file())
        self.assertEqual([], module_files)
        self.assertEqual(
            asset_files,
            {
                "charts.js",
                "fonts.css",
                "index.html",
                "styles.css",
                "tokens.css",
                "vendor/highcharts.js",
                "vendor/htmx.min.js",
            },
        )

    def test_all_runtime_data_and_fixture_json_files_parse(self) -> None:
        paths = list(
            (
                REPO_ROOT
                / "src"
                / "capex3"
                / "infrastructure"
                / "workbook_assumptions"
                / "data"
            ).glob("*.json")
        )
        paths += list((REPO_ROOT / "tests" / "fixtures").glob("*.json"))

        self.assertEqual(len(paths), 7)
        for path in paths:
            with self.subTest(path=path):
                with path.open("r", encoding="utf-8") as source_file:
                    self.assertIsInstance(json.load(source_file), dict)

    def test_runtime_payload_contracts(self) -> None:
        readiness = readiness_payload()
        defaults = defaults_payload()
        workbench = workbench_payload()
        what_works = what_works_presentation_contract_payload()

        self.assertEqual(readiness["status"], "ready")
        self.assertEqual(readiness["calculationAndSolverOwner"], "python")
        self.assertEqual(readiness["runtimeSurface"], "python-http")
        self.assertEqual(readiness["staticBrowserSurface"], "capex3-presentation-assets")
        self.assertTrue(defaults["ok"])
        self.assertIn("inputs", defaults)
        self.assertTrue(workbench["ok"])
        self.assertIn("thresholdQuestions", workbench["workbench"])
        self.assertTrue(what_works["ok"])
        self.assertEqual(what_works["contractSource"], "capex3.core.teaching")
        self.assertEqual(
            what_works["transport"]["path"],
            WHAT_WORKS_PRESENTATION_CONTRACT_PATH,
        )

    def test_workbench_payload_owns_teaching_ui_metadata(self) -> None:
        payload = workbench_payload()["workbench"]
        input_fields = {field["field"]: field for field in payload["inputFields"]}
        solver_variables = {
            variable["id"]: variable for variable in payload["solverVariables"]
        }
        solver_metrics = {metric["id"]: metric for metric in payload["solverMetrics"]}
        linkage_fields = payload["calculationLinkageFields"]

        self.assertEqual(input_fields["subregion"]["optionsSource"], "subregions")
        self.assertEqual(input_fields["propertyProfile"]["optionsSource"], "profiles")
        self.assertEqual(input_fields["actualGrossMonthlyRent"]["kind"], "currency")
        self.assertEqual(
            solver_variables["rent"]["applyField"],
            "actualGrossMonthlyRent",
        )
        self.assertEqual(
            solver_variables["purchasePriceWithDefaultDownPayment"]["applyField"],
            "purchasePrice",
        )
        self.assertTrue(
            solver_variables["purchasePriceWithDefaultDownPayment"][
                "showInManualControls"
            ]
        )
        self.assertFalse(
            solver_variables["purchasePriceWithFixedDownPayment"][
                "showInManualControls"
            ]
        )
        self.assertEqual(solver_metrics["cashOnCashReturn"]["valueKind"], "percent")
        self.assertEqual(solver_metrics["monthlyCashFlow"]["valueKind"], "moneyCents")
        self.assertTrue(all(field.get("uiElement") for field in linkage_fields))

    def test_presentation_routes_and_server_wiring_are_exercised(self) -> None:
        ready_response = handle_get(READINESS_PATH)
        index_response = handle_get("/")
        stylesheet_response = handle_get("/assets/styles.css")
        htmx_response = handle_get("/assets/vendor/htmx.min.js")
        calculate_response = handle_post("/api/calculate", {"inputs": {}})
        solve_response = handle_post(
            "/api/solve",
            {"request": {"questionId": "breakEvenRent", "baseInput": {}}},
        )
        ui_step_response = handle_post("/ui/step", {"activeStep": "decision"})
        not_found = not_found_response()
        invalid_json = invalid_json_response()

        self.assertEqual(ready_response.status, HTTPStatus.OK)
        self.assertEqual(ready_response.payload, readiness_payload())
        self.assertIsInstance(index_response, HtmlResponse)
        self.assertIn('src="/assets/vendor/htmx.min.js"', index_response.body)
        self.assertIn('hx-post="/ui/calculate"', index_response.body)
        self.assertNotIn('type="' + 'module"', index_response.body)
        self.assertIsInstance(stylesheet_response, StaticAssetResponse)
        self.assertEqual(
            stylesheet_response.cache_control,
            STATIC_BROWSER_ASSET_CACHE_CONTROL,
        )
        self.assertIn(b".topbar", stylesheet_response.body)
        self.assertIsInstance(htmx_response, StaticAssetResponse)
        self.assertEqual(htmx_response.cache_control, STATIC_BROWSER_ASSET_CACHE_CONTROL)
        self.assertIn(b"htmx", htmx_response.body)
        self.assertEqual(calculate_response.status, HTTPStatus.OK)
        self.assertTrue(calculate_response.payload["ok"])
        self.assertEqual(solve_response.status, HTTPStatus.OK)
        self.assertTrue(solve_response.payload["ok"])
        self.assertIsInstance(ui_step_response, HtmlResponse)
        self.assertIn("Decision Packet", ui_step_response.body)
        self.assertIn('id="solver-variable"', ui_step_response.body)
        self.assertEqual(not_found.status, HTTPStatus.NOT_FOUND)
        self.assertEqual(invalid_json.status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            startup_event_payload("127.0.0.1", 3000)["readinessPath"],
            READINESS_PATH,
        )

    def test_static_asset_cache_policy_is_bounded_and_html_json_stay_no_store(self) -> None:
        stylesheet_response = handle_get("/assets/styles.css")
        htmx_response = handle_get("/assets/vendor/htmx.min.js")
        index_asset_response = handle_get("/assets/index.html")

        self.assertIsInstance(stylesheet_response, StaticAssetResponse)
        self.assertIsInstance(htmx_response, StaticAssetResponse)
        self.assertIsInstance(index_asset_response, StaticAssetResponse)
        self.assertEqual(
            STATIC_BROWSER_ASSET_CACHE_CONTROL,
            stylesheet_response.cache_control,
        )
        self.assertEqual(STATIC_BROWSER_ASSET_CACHE_CONTROL, htmx_response.cache_control)
        self.assertEqual(NO_STORE_CACHE_CONTROL, index_asset_response.cache_control)

        server = infrastructure_create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address[:2]
            base_url = f"{'http'}://{host}:{port}"
            expected_no_store_paths = [
                "/",
                "/assets/index.html",
                READINESS_PATH,
                WHAT_WORKS_PRESENTATION_CONTRACT_PATH,
                "/api/defaults",
                "/api/workbench",
                "/missing-route",
            ]

            for path in expected_no_store_paths:
                with self.subTest(path=path):
                    _status, cache_control = self._request_cache_control(
                        f"{base_url}{path}"
                    )
                    self.assertEqual(NO_STORE_CACHE_CONTROL, cache_control)

            for path in [
                "/assets/tokens.css",
                "/assets/styles.css",
                "/assets/charts.js",
                "/assets/vendor/highcharts.js",
                "/assets/vendor/htmx.min.js",
            ]:
                with self.subTest(path=path):
                    _status, cache_control = self._request_cache_control(
                        f"{base_url}{path}"
                    )
                    self.assertEqual(STATIC_BROWSER_ASSET_CACHE_CONTROL, cache_control)

            post_expectations = [
                (
                    "/ui/calculate",
                    urllib.parse.urlencode({"activeStep": "decision"}).encode("utf-8"),
                    {"Content-Type": "application/x-www-form-urlencoded"},
                ),
                (
                    "/api/calculate",
                    json.dumps({"inputs": {}}).encode("utf-8"),
                    {"Content-Type": "application/json"},
                ),
                (
                    "/api/solve",
                    json.dumps(
                        {"request": {"questionId": "breakEvenRent", "baseInput": {}}},
                    ).encode("utf-8"),
                    {"Content-Type": "application/json"},
                ),
                (
                    "/api/calculate",
                    b"{bad-json",
                    {"Content-Type": "application/json"},
                ),
            ]
            for path, data, headers in post_expectations:
                with self.subTest(path=path, data=data):
                    _status, cache_control = self._request_cache_control(
                        f"{base_url}{path}",
                        data=data,
                        headers=headers,
                    )
                    self.assertEqual(NO_STORE_CACHE_CONTROL, cache_control)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_head_requests_mirror_get_status_and_length_without_body(self) -> None:
        cases = [
            ("/", HTTPStatus.OK),
            (READINESS_PATH, HTTPStatus.OK),
            ("/assets/tokens.css", HTTPStatus.OK),
            ("/assets/styles.css", HTTPStatus.OK),
            ("/missing-route", HTTPStatus.NOT_FOUND),
        ]
        server = infrastructure_create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address[:2]
            base_url = f"http://{host}:{port}"
            for path, expected_status in cases:
                with self.subTest(path=path):
                    get_status, get_length, get_body = self._request_with_length(
                        f"{base_url}{path}",
                        method="GET",
                    )
                    head_status, head_length, head_body = self._request_with_length(
                        f"{base_url}{path}",
                        method="HEAD",
                    )
                    self.assertEqual(get_status, expected_status.value)
                    self.assertEqual(head_status, expected_status.value)
                    self.assertEqual(head_length, get_length)
                    self.assertEqual(len(get_body), get_length)
                    self.assertGreater(get_length, 0)
                    self.assertEqual(b"", head_body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_presentation_preserves_malformed_nested_post_validation(self) -> None:
        malformed_calculate = handle_post("/api/calculate", {"inputs": ["bad"]})
        malformed_solve = handle_post("/api/solve", {"request": ["bad"]})

        self.assertEqual(malformed_calculate.status, HTTPStatus.BAD_REQUEST)
        self.assertFalse(malformed_calculate.payload["ok"])
        self.assertEqual(malformed_calculate.payload["code"], "VALIDATION_ERROR")
        self.assertEqual(
            malformed_calculate.payload["message"],
            "Calculator input request must be an object.",
        )
        self.assertEqual(malformed_calculate.payload["details"], {"input": ["bad"]})

        self.assertEqual(malformed_solve.status, HTTPStatus.BAD_REQUEST)
        self.assertFalse(malformed_solve.payload["ok"])
        self.assertEqual(malformed_solve.payload["code"], "VALIDATION_ERROR")
        self.assertEqual(
            malformed_solve.payload["message"],
            "Solver request must be an object.",
        )
        self.assertEqual(malformed_solve.payload["details"], {"request": ["bad"]})

    def test_runtime_http_api_routes(self) -> None:
        server = infrastructure_create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address[:2]
            base_url = f"{'http'}://{host}:{port}"

            ready = self._request_json(f"{base_url}{READINESS_PATH}")
            teaching = self._request_json(
                f"{base_url}{WHAT_WORKS_PRESENTATION_CONTRACT_PATH}"
            )
            defaults = self._request_json(f"{base_url}/api/defaults")
            workbench = self._request_json(f"{base_url}/api/workbench")
            calculate = self._request_json(
                f"{base_url}/api/calculate",
                {"inputs": {}},
            )
            solve = self._request_json(
                f"{base_url}/api/solve",
                {
                    "request": {
                        "questionId": "breakEvenRent",
                        "baseInput": {},
                    }
                },
            )

            self.assertEqual(ready["status"], "ready")
            self.assertEqual(ready["runtimeSurface"], "python-http")
            self.assertEqual(ready["staticBrowserSurface"], "capex3-presentation-assets")
            self.assertEqual(teaching["contractSource"], "capex3.core.teaching")
            self.assertTrue(defaults["ok"])
            self.assertTrue(workbench["ok"])
            self.assertTrue(calculate["ok"])
            self.assertTrue(solve["ok"])
            index = self._request_text(f"{base_url}/")
            stylesheet = self._request_text(f"{base_url}/assets/styles.css")
            htmx = self._request_text(f"{base_url}/assets/vendor/htmx.min.js")
            ui_step = self._request_text(
                f"{base_url}/ui/step",
                {"activeStep": "decision"},
            )

            self.assertIn("Deal Analyzer", index)
            self.assertIn("/assets/vendor/htmx.min.js", index)
            self.assertIn('hx-post="/ui/calculate"', index)
            self.assertNotIn("/assets/" + "modules/", index)
            self.assertIn(".topbar", stylesheet)
            self.assertIn("htmx", htmx)
            self.assertIn("Decision Packet", ui_step)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_standalone_runtime_does_not_read_source_repo(self) -> None:
        original_path_open = Path.open

        def guarded_path_open(path: Path, *args: object, **kwargs: object) -> object:
            resolved = Path(path).resolve()
            if _is_relative_to(resolved, SOURCE_REPO_ROOT):
                raise AssertionError(f"runtime read from source repo: {resolved}")
            return original_path_open(path, *args, **kwargs)

        with mock.patch.object(Path, "open", guarded_path_open):
            server = infrastructure_create_server("127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                host, port = server.server_address[:2]
                base_url = f"{'http'}://{host}:{port}"

                self.assertEqual(
                    self._request_json(f"{base_url}{READINESS_PATH}")["status"],
                    "ready",
                )
                self.assertIn("Deal Analyzer", self._request_text(f"{base_url}/"))
                self.assertIn(
                    ".topbar",
                    self._request_text(f"{base_url}/assets/styles.css"),
                )
                self.assertIn(
                    "htmx",
                    self._request_text(f"{base_url}/assets/vendor/htmx.min.js"),
                )
                self.assertTrue(self._request_json(f"{base_url}/api/defaults")["ok"])
                self.assertTrue(self._request_json(f"{base_url}/api/workbench")["ok"])
                self.assertTrue(
                    self._request_json(
                        f"{base_url}/api/calculate",
                        {"inputs": {}},
                    )["ok"]
                )
                self.assertTrue(
                    self._request_json(
                        f"{base_url}/api/solve",
                        {
                            "request": {
                                "questionId": "breakEvenRent",
                                "baseInput": {},
                            }
                        },
                    )["ok"]
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def _request_json(
        self,
        url: str,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            self.fail(f"{url} failed with HTTP {error.code}: {error.read()!r}")

    def _request_status(self, url: str) -> int:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.status
        except urllib.error.HTTPError as error:
            try:
                return error.code
            finally:
                error.close()

    def _request_cache_control(
        self,
        url: str,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str | None]:
        request = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                response.read()
                return response.status, response.headers.get("Cache-Control")
        except urllib.error.HTTPError as error:
            try:
                error.read()
                return error.code, error.headers.get("Cache-Control")
            finally:
                error.close()

    def _request_with_length(
        self,
        url: str,
        *,
        method: str = "GET",
    ) -> tuple[int, int, bytes]:
        request = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = response.read()
                content_length = int(response.headers.get("Content-Length", len(body)))
                return response.status, content_length, body
        except urllib.error.HTTPError as error:
            try:
                body = error.read()
                content_length = int(error.headers.get("Content-Length", len(body)))
                return error.code, content_length, body
            finally:
                error.close()

    def _request_text(
        self,
        url: str,
        payload: dict[str, object] | None = None,
    ) -> str:
        data = None
        headers = {}
        if payload is not None:
            data = urllib.parse.urlencode(payload).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            self.fail(f"{url} failed with HTTP {error.code}: {error.read()!r}")


class PresentationAssetMigrationTest(unittest.TestCase):
    def test_corrective_browser_assets_exist_in_capex3_presentation(self) -> None:
        expected_assets = {
            "charts.js",
            "fonts.css",
            "index.html",
            "styles.css",
            "tokens.css",
            "vendor/highcharts.js",
            "vendor/htmx.min.js",
        }
        actual_assets = {
            path.relative_to(PRESENTATION_ASSET_DIR).as_posix()
            for path in PRESENTATION_ASSET_DIR.rglob("*")
            if path.is_file()
        }

        self.assertEqual(expected_assets, actual_assets)

    def test_migrated_index_uses_htmx_static_asset_routes(self) -> None:
        index = (PRESENTATION_ASSET_DIR / "index.html").read_text(encoding="utf-8")

        self.assertIn('href="/assets/tokens.css"', index)
        self.assertIn('href="/assets/styles.css"', index)
        self.assertIn('src="/assets/vendor/highcharts.js"', index)
        self.assertIn('src="/assets/charts.js"', index)
        self.assertIn('src="/assets/vendor/htmx.min.js"', index)
        self.assertIn('hx-get="/ui/app"', index)
        self.assertIn('rel="preconnect" href="https://fonts.googleapis.com"', index)
        self.assertIn(FONTS_STYLESHEET_PATH, index)
        self.assertNotIn('href="/styles.css"', index)
        self.assertNotIn('src="' + "/workbench" + '/main.js"', index)
        self.assertNotIn('type="' + 'module"', index)
        self.assertNotIn("/assets/" + "modules/", index)

    def test_static_asset_route_rejects_path_traversal(self) -> None:
        traversal_paths = [
            "/assets/../presentation/http_contracts.py",
            "/assets/%2e%2e/presentation/http_contracts.py",
            "/assets/..\\..\\presentation\\http_contracts.py",
            "/assets/%2e%2e%5c%2e%2e%5cpresentation%5chttp_contracts.py",
            "/assets//styles.css",
            "/assets/./styles.css",
            "/assets/missing.css",
        ]

        for path in traversal_paths:
            with self.subTest(path=path):
                response = handle_get(path)

                self.assertNotIsInstance(response, StaticAssetResponse)
                self.assertEqual(response.status, HTTPStatus.NOT_FOUND)

    def test_server_rendered_htmx_uses_only_capex3_presentation_endpoints(self) -> None:
        index_response = handle_get("/")
        self.assertIsInstance(index_response, HtmlResponse)
        rendered_html = index_response.body
        all_browser_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(PRESENTATION_ASSET_DIR.rglob("*"))
            if path.is_file()
            and path.suffix in {".html", ".css", ".js"}
            and path.as_posix().endswith("/vendor/htmx.min.js") is False
            and path.as_posix().endswith("/vendor/highcharts.js") is False
        )

        expected_routes = {
            'hx-post="/ui/calculate"',
            'hx-post="/ui/solve"',
            'hx-post="/ui/reset"',
            'hx-post="/ui/step"',
            'hx-post="/ui/evidence"',
        }
        actual_routes = {
            token
            for token in expected_routes
            if token in rendered_html
        }

        self.assertEqual(expected_routes, actual_routes)
        self.assertEqual(0, all_browser_source.count("fetch" + "("))
        self.assertNotIn("XML" + "HttpRequest", all_browser_source)
        self.assertNotIn("http" + "://", all_browser_source)
        forbidden_https = [
            line.strip()
            for line in all_browser_source.splitlines()
            if "https://" in line
            and "fonts.googleapis.com" not in line
            and "fonts.gstatic.com" not in line
        ]
        self.assertEqual([], forbidden_https)
        self.assertNotIn("rental_" + "capex2", all_browser_source)
        self.assertNotIn("C:\\Project\\rental_" + "capex2", all_browser_source)
        self.assertNotIn("/workbench" + "/", all_browser_source)
        self.assertNotIn('"/styles.css"', all_browser_source)

    def test_teaching_ui_is_server_rendered_from_python_metadata(self) -> None:
        index = handle_get("/")
        self.assertIsInstance(index, HtmlResponse)

        self.assertIn("Listing Check", index.body)
        self.assertIn("Decision Packet", index.body)
        self.assertIn('id="solver-variable"', index.body)
        self.assertIn('id="solver-metric"', index.body)
        self.assertIn('data-evidence-layer="repairDrivers"', index.body)
        self.assertIn('class="evidence-drilldown"', index.body)
        self.assertIn("See the breakdown", index.body)
        self.assertNotIn('id="diagnostic-summary"', index.body)
        self.assertNotIn('class="debug-panel"', index.body)
        self.assertNotIn("const fieldMeta", index.body)
        self.assertNotIn("const variableLabels", index.body)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent.resolve())
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    unittest.main()
