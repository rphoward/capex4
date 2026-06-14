import argparse
import json
import os
from http.server import ThreadingHTTPServer
from typing import Sequence

from capex3.presentation.rental_capex_http_api import (
    READINESS_PATH,
    SERVICE_NAME,
    WHAT_WORKS_PRESENTATION_CONTRACT_PATH,
    RentalCapexTeachingHeartbeatHandler,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3000


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), RentalCapexTeachingHeartbeatHandler)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Rental CapEx teaching runtime heartbeat server."
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("RENTAL_CAPEX_PYTHON_HOST", DEFAULT_HOST),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("RENTAL_CAPEX_PYTHON_PORT", DEFAULT_PORT)),
    )
    return parser.parse_args(argv)


def startup_event_payload(host: object, port: object) -> dict[str, object]:
    return {
        "event": "listening",
        "service": SERVICE_NAME,
        "host": host,
        "port": port,
        "readinessPath": READINESS_PATH,
        "whatWorksPresentationContractPath": WHAT_WORKS_PRESENTATION_CONTRACT_PATH,
        "runtimeSurface": "python-http",
        "staticBrowserSurface": "capex3-presentation-assets",
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    server = create_server(args.host, args.port)
    host, port = server.server_address[:2]

    print(
        json.dumps(
            startup_event_payload(host, port),
            separators=(",", ":"),
            sort_keys=True,
        ),
        flush=True,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
