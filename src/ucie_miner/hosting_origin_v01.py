"""UCIE O1 always-on host *internal preparation* origin; NEVER a product release.

Run only behind a separate deny-by-default identity access gateway. This
component proves a dedicated Linux loopback origin can be kept running; it
does NOT expose local UCIE data, public candidates, SkillBooks or customer
routes. Online customer release requires an independent later owner gate.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlsplit

from . import local_v1_priority_v01 as priority

SCHEMA = "UCIE_O1_INDEPENDENT_HOSTING_ORIGIN_PREPARATION_V01"
STATUS = "HOSTING_PREPARATION_ONLY_NO_CUSTOMER_RELEASE"
HOST = "127.0.0.1"
DEFAULT_PORT = 8811


class HostingPreparationError(ValueError):
    """An online permission or origin exposure would violate the owner gate."""


def assert_preparation_gate() -> None:
    """Fail closed if user-approved LOCAL V1 / pending ONLINE state drifts."""
    if (priority.LOCAL_V1_ACCEPTED_BY_OWNER is not True
            or priority.ONLINE_RELEASE_AUTHORIZED is not False
            or priority.PERIPHERAL_EXPANSION_AUTHORIZED is not False):
        raise HostingPreparationError("ONLINE_HOSTING_OWNER_RELEASE_GATE_NOT_MET")


def readiness() -> dict:
    """No real data or credentials; this is *origin alive*, NOT customer-ready."""
    assert_preparation_gate()
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "bind_host": HOST,
        "online_release_authorized": False,
        "customer_distribution_authorized": False,
        "customer_routes_enabled": False,
        "customer_authentication_implemented_here": False,
        "access_gateway_required": True,
        "owner_local_v1_accepted": True,
        "operating_database_writes": 0,
        "public_miner_or_scheduler_modified": False,
        "network_fetches_by_origin": 0,
        "other_project_access": False,
        "serves_source_code_or_local_database": False,
    }


def make_handler():
    """Serve ONLY the non-sensitive internal health check on loopback."""
    assert_preparation_gate()

    class OriginHandler(BaseHTTPRequestHandler):
        server_version = "UCIEHostingOrigin"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args) -> None:
            # Do not print caller-controlled request paths or token headers.
            pass

        def _respond(self, status: int, value: dict, *, body: bool = True) -> None:
            raw = json.dumps(value, sort_keys=True, ensure_ascii=True).encode("ascii")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'none'")
            self.send_header("Connection", "close")
            self.end_headers()
            if body:
                self.wfile.write(raw)

        def _dispatch(self, *, body: bool) -> None:
            expected = HOST + ":" + str(self.server.server_port)
            if (self.headers.get("Host") != expected
                    or self.client_address[0] != HOST):
                return self._respond(403, {
                    "schema": SCHEMA, "status": "LOOPBACK_ORIGIN_ONLY"
                }, body=body)
            try:
                assert_preparation_gate()
                parsed = urlsplit(self.path)
                if parsed.path == "/internal/healthz" and not (
                        parsed.query or parsed.fragment):
                    return self._respond(200, readiness(), body=body)
                return self._respond(503, {
                    "schema": SCHEMA,
                    "status": "CUSTOMER_APPLICATION_NOT_DEPLOYED_OR_AUTHORIZED",
                    "online_release_authorized": False,
                }, body=body)
            except (ValueError, HostingPreparationError):
                return self._respond(503, {
                    "schema": SCHEMA,
                    "status": "OWNER_RELEASE_GATE_FAIL_CLOSED",
                    "online_release_authorized": False,
                }, body=body)

        def do_GET(self) -> None:
            self._dispatch(body=True)

        def do_HEAD(self) -> None:
            self._dispatch(body=False)

        def do_POST(self) -> None:
            self._respond(405, {
                "schema": SCHEMA, "status": "WRITE_METHOD_DISABLED"
            })

        def do_PUT(self) -> None:
            self.do_POST()

        def do_DELETE(self) -> None:
            self.do_POST()

        def do_PATCH(self) -> None:
            self.do_POST()

    return OriginHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE dedicated hosting loopback origin, NOT online release")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--internal-preparation-only", action="store_true",
        help="acknowledge that this does not serve customer product routes")
    args = parser.parse_args(argv)
    if not args.internal_preparation_only or not 1024 <= args.port <= 65535:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "INTERNAL_PREPARATION_ACK_AND_VALID_PORT_REQUIRED",
            "online_release_authorized": False,
        }, sort_keys=True))
        return 2
    try:
        assert_preparation_gate()
        with ThreadingHTTPServer((HOST, args.port), make_handler()) as server:
            server.daemon_threads = True
            print(json.dumps({
                "schema": SCHEMA,
                "status": STATUS,
                "internal_health_url": "http://" + HOST + ":" +
                str(server.server_port) + "/internal/healthz",
                "customer_routes_enabled": False,
                "online_release_authorized": False,
            }, sort_keys=True), flush=True)
            server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except (OSError, HostingPreparationError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "HOSTING_ORIGIN_FAIL_CLOSED",
            "online_release_authorized": False,
        }, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
