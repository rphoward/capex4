import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from importlib import resources
import mimetypes
from pathlib import Path
from pathlib import PurePosixPath
from typing import Mapping
from urllib.parse import parse_qs
from urllib.parse import unquote
from urllib.parse import urlsplit

from capex3.core.errors import RentalCapexError, json_safe_value
from capex3.core.teaching.boundary_shapes import (
    selected_what_works_presentation_contract_to_contract,
)
from capex3.presentation.htmx_renderer import render_full_page, render_ui_fragment
from capex3.presentation.http_contracts import (
    calculate_payload,
    defaults_payload,
    solve_payload,
    workbench_payload,
)


SERVICE_NAME = "rental-capex-teaching-server"
READINESS_PATH = "/ready"
WHAT_WORKS_PRESENTATION_CONTRACT_PATH = "/teaching/what-works"
PRESENTATION_ASSET_PACKAGE = "capex3.presentation"
PRESENTATION_ASSET_ROOT = "browser_assets"
PRESENTATION_ASSET_DIR = Path(__file__).resolve().parent / "browser_assets"
PRESENTATION_STATIC_ROUTE_PREFIX = "/assets/"
NO_STORE_CACHE_CONTROL = "no-store"
STATIC_BROWSER_ASSET_CACHE_CONTROL = "private, max-age=300"
_CACHEABLE_BROWSER_ASSETS = {
    PurePosixPath("fonts.css"),
    PurePosixPath("tokens.css"),
    PurePosixPath("styles.css"),
    PurePosixPath("vendor/htmx.min.js"),
}


@dataclass(frozen=True)
class HttpApiResponse:
    status: HTTPStatus
    payload: dict[str, object]


@dataclass(frozen=True)
class StaticAssetResponse:
    status: HTTPStatus
    body: bytes
    content_type: str
    cache_control: str


@dataclass(frozen=True)
class HtmlResponse:
    status: HTTPStatus
    body: str


def readiness_payload() -> dict[str, object]:
    return {
        "status": "ready",
        "service": SERVICE_NAME,
        "calculationAndSolverOwner": "python",
        "runtimeSurface": "python-http",
        "staticBrowserSurface": "capex3-presentation-assets",
    }


def what_works_presentation_contract_payload() -> dict[str, object]:
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "transport": {
            "kind": "python-runtime-http",
            "path": WHAT_WORKS_PRESENTATION_CONTRACT_PATH,
        },
        "contractSource": "capex3.core.teaching",
        "contract": selected_what_works_presentation_contract_to_contract(),
    }


def handle_get(raw_path: str) -> HttpApiResponse | StaticAssetResponse | HtmlResponse:
    request_path = _request_path(raw_path)

    if request_path in ("", "/"):
        return HtmlResponse(HTTPStatus.OK, render_full_page())

    if request_path == "/ui/app":
        return HtmlResponse(HTTPStatus.OK, render_ui_fragment({}, "calculate"))

    static_response = static_asset_response(request_path)
    if static_response is not None:
        return static_response

    if request_path == READINESS_PATH:
        return HttpApiResponse(HTTPStatus.OK, readiness_payload())

    if request_path == WHAT_WORKS_PRESENTATION_CONTRACT_PATH:
        return HttpApiResponse(HTTPStatus.OK, what_works_presentation_contract_payload())

    if request_path == "/api/defaults":
        return HttpApiResponse(HTTPStatus.OK, defaults_payload())

    if request_path == "/api/workbench":
        return HttpApiResponse(HTTPStatus.OK, workbench_payload())

    return not_found_response()


def static_asset_response(request_path: str) -> StaticAssetResponse | None:
    if not request_path.startswith(PRESENTATION_STATIC_ROUTE_PREFIX):
        return None

    relative_asset_path = request_path.removeprefix(PRESENTATION_STATIC_ROUTE_PREFIX)
    safe_asset_path = _safe_asset_path(relative_asset_path)
    if safe_asset_path is None:
        return None

    return _read_static_asset(safe_asset_path)


def handle_post(raw_path: str, body: object) -> HttpApiResponse | HtmlResponse:
    request_path = _request_path(raw_path)
    request_body = body if isinstance(body, Mapping) else {}

    try:
        ui_action = _ui_action(request_path)
        if ui_action is not None:
            return HtmlResponse(
                HTTPStatus.OK,
                render_ui_fragment(request_body, ui_action),
            )

        if request_path == "/api/calculate":
            inputs = request_body.get("inputs")
            return HttpApiResponse(HTTPStatus.OK, calculate_payload(inputs))

        if request_path == "/api/solve":
            request = request_body.get("request")
            status_code, payload = solve_payload(request)
            return HttpApiResponse(HTTPStatus(status_code), payload)
    except Exception as error:
        return exception_response(error)

    return not_found_response()


def invalid_json_response() -> HttpApiResponse:
    return HttpApiResponse(
        HTTPStatus.BAD_REQUEST,
        {
            "ok": False,
            "code": "SERVER_ERROR",
            "message": "Request body must be valid JSON.",
        },
    )


def not_found_response() -> HttpApiResponse:
    return HttpApiResponse(
        HTTPStatus.NOT_FOUND,
        {
            "ok": False,
            "code": "NOT_FOUND",
            "message": "Route not found.",
        },
    )


def exception_response(error: Exception) -> HttpApiResponse:
    if isinstance(error, RentalCapexError):
        return HttpApiResponse(
            HTTPStatus.BAD_REQUEST,
            {
                "ok": False,
                "code": error.code,
                "message": str(error),
                "details": json_safe_value(dict(error.details)),
            },
        )

    return HttpApiResponse(
        HTTPStatus.INTERNAL_SERVER_ERROR,
        {
            "ok": False,
            "code": "SERVER_ERROR",
            "message": str(error) or "Python calculator request failed.",
        },
    )


class RentalCapexTeachingHeartbeatHandler(BaseHTTPRequestHandler):
    server_version = "RentalCapexTeachingServer/0.2"

    def do_GET(self) -> None:
        self._write_response(handle_get(self.path))

    def do_POST(self) -> None:
        try:
            self._write_response(handle_post(self.path, self._read_request_body()))
        except json.JSONDecodeError:
            self._write_response(invalid_json_response())
        except Exception as error:
            self._write_response(exception_response(error))

    def do_HEAD(self) -> None:
        self._write_response(handle_get(self.path), include_body=False)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_request_body(self) -> dict[str, object]:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length == 0:
            return {}
        raw_body = self.rfile.read(content_length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")
        if "application/x-www-form-urlencoded" in content_type:
            return {
                key: values[-1] if values else ""
                for key, values in parse_qs(raw_body, keep_blank_values=True).items()
            }
        return json.loads(raw_body)

    def _write_response(
        self,
        response: HttpApiResponse | StaticAssetResponse | HtmlResponse,
        *,
        include_body: bool = True,
    ) -> None:
        if isinstance(response, StaticAssetResponse):
            self.send_response(response.status.value)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(response.body)))
            self.send_header("Cache-Control", response.cache_control)
            self.end_headers()
            if include_body:
                self.wfile.write(response.body)
            return

        if isinstance(response, HtmlResponse):
            encoded = response.body.encode("utf-8")
            self.send_response(response.status.value)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", NO_STORE_CACHE_CONTROL)
            self.end_headers()
            if include_body:
                self.wfile.write(encoded)
            return

        encoded = json.dumps(
            response.payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self.send_response(response.status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", NO_STORE_CACHE_CONTROL)
        self.end_headers()
        if include_body:
            self.wfile.write(encoded)


def _request_path(raw_path: str) -> str:
    return urlsplit(raw_path).path


def _ui_action(request_path: str) -> str | None:
    return {
        "/ui/calculate": "calculate",
        "/ui/step": "step",
        "/ui/evidence": "evidence",
        "/ui/metric": "metric",
        "/ui/reset": "reset",
        "/ui/new-walkthrough": "new-walkthrough",
        "/ui/override": "override",
        "/ui/solve": "solve",
        "/ui/solve-threshold": "solve-threshold",
        "/ui/solve-reserve-first-shortfall": "solve-reserve-first-shortfall",
        "/ui/apply-solver": "apply-solver",
    }.get(request_path)


def _read_static_asset(relative_asset_path: PurePosixPath) -> StaticAssetResponse | None:
    asset = _presentation_asset(relative_asset_path)
    if not asset.is_file():
        return None

    content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
    if PurePosixPath(asset.name).suffix == ".js":
        content_type = "text/javascript"

    return StaticAssetResponse(
        HTTPStatus.OK,
        asset.read_bytes(),
        f"{content_type}; charset=utf-8" if _is_text_asset(asset.name) else content_type,
        _static_asset_cache_control(relative_asset_path),
    )


def _presentation_asset(relative_asset_path: PurePosixPath):
    asset = resources.files(PRESENTATION_ASSET_PACKAGE).joinpath(PRESENTATION_ASSET_ROOT)
    for part in relative_asset_path.parts:
        asset = asset.joinpath(part)
    return asset


def _safe_asset_path(relative_asset_path: str) -> PurePosixPath | None:
    decoded_path = unquote(relative_asset_path)
    if "\\" in decoded_path:
        return None

    parts = decoded_path.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None

    return PurePosixPath(decoded_path)


def _is_text_asset(asset_name: str) -> bool:
    return PurePosixPath(asset_name).suffix in {
        ".css",
        ".html",
        ".js",
        ".mjs",
        ".txt",
        ".json",
        ".svg",
    }


def _static_asset_cache_control(relative_asset_path: PurePosixPath) -> str:
    if relative_asset_path in _CACHEABLE_BROWSER_ASSETS:
        return STATIC_BROWSER_ASSET_CACHE_CONTROL
    return NO_STORE_CACHE_CONTROL

