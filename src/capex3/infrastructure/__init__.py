"""Infrastructure adapter package for concrete data and external resources."""

from .workbook_assumptions import (
    DATA_DIR,
    DATA_PACKAGE,
    compose_workbook_model_spec_from_sources,
    load_workbook_model_spec,
    load_workbook_model_spec_record,
    workbook_source_data_from_sources,
)

__all__ = [
    "DATA_DIR",
    "DATA_PACKAGE",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "LocalhostThreadingHTTPServer",
    "compose_workbook_model_spec_from_sources",
    "create_server",
    "load_workbook_model_spec",
    "load_workbook_model_spec_record",
    "main",
    "parse_args",
    "startup_event_payload",
    "workbook_source_data_from_sources",
]

_SERVER_EXPORTS = frozenset(
    {
        "DEFAULT_HOST",
        "DEFAULT_PORT",
        "LocalhostThreadingHTTPServer",
        "create_server",
        "main",
        "parse_args",
        "startup_event_payload",
    }
)


def __getattr__(name: str) -> object:
    if name in _SERVER_EXPORTS:
        from . import server

        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
