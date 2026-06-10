"""Presentation adapter package for API and teaching-display boundaries."""

from .http_contracts import (
    calculate_payload,
    defaults_payload,
    error_payload,
    solve_payload,
    workbench_payload,
)
from .rental_capex_http_api import (
    READINESS_PATH,
    SERVICE_NAME,
    WHAT_WORKS_PRESENTATION_CONTRACT_PATH,
    HttpApiResponse,
    RentalCapexTeachingHeartbeatHandler,
    exception_response,
    handle_get,
    handle_post,
    invalid_json_response,
    not_found_response,
    readiness_payload,
    what_works_presentation_contract_payload,
)

__all__ = [
    "HttpApiResponse",
    "READINESS_PATH",
    "SERVICE_NAME",
    "WHAT_WORKS_PRESENTATION_CONTRACT_PATH",
    "RentalCapexTeachingHeartbeatHandler",
    "calculate_payload",
    "defaults_payload",
    "error_payload",
    "exception_response",
    "handle_get",
    "handle_post",
    "invalid_json_response",
    "not_found_response",
    "readiness_payload",
    "solve_payload",
    "what_works_presentation_contract_payload",
    "workbench_payload",
]
