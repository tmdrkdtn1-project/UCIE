"""UCIE C1 only: path-independent, disposable first-party localhost preview.

This module is deliberately NOT an approved customer launcher. It can run only
from an exact UCIE-named disposable staging root with the immutable C1 marker,
without .git, without owner task registration and without public interfaces.
All HTTP traffic is in-process to 127.0.0.1 using an OS-allocated port.
"""
from __future__ import annotations

import argparse
from http.client import HTTPConnection
import json
from pathlib import Path
from threading import Thread

SCHEMA = "UCIE_C1_PORTABLE_LOCALHOST_PREVIEW_V01"
REVISION = "UCIE_C1_DISPOSABLE_GENERATION_A"
MARKER_NAME = ".ucie_c1_staging_only"
MARKER_BYTES = b"UCIE_C1_DISPOSABLE_PREVIEW_NO_CUSTOMER_RELEASE_V01\n"
BOUND_HOST = "127.0.0.1"


class PortablePreviewError(ValueError):
    """No owner deployment, external binding, symlink or customer rights."""


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir() or
            (root / ".git").exists() or (root / ".git").is_symlink()):
        raise PortablePreviewError("exact disposable UCIE-only root required")
    marker = root / MARKER_NAME
    source = root / "src" / "ucie_miner" / "local_v1_app_v01.py"
    if (marker.is_symlink() or not marker.is_file()
            or marker.read_bytes() != MARKER_BYTES
            or source.is_symlink() or not source.is_file()):
        raise PortablePreviewError("unmarked or incomplete UCIE preview")
    return root


def source_revision() -> str:
    """Actual code revision marker; never a signed/approved release version."""
    return REVISION


def _check_http(connection: HTTPConnection, route: str,
                marker: bytes, *, allowed: tuple[int, ...] = (200,)) -> int:
    connection.request("GET", route, headers={"Host": BOUND_HOST + ":" +
                                              str(connection.port)})
    response = connection.getresponse()
    mime = response.getheader("Content-Type", "")
    content = response.read(400_001)
    if (response.status not in allowed or len(content) > 400_000
            or marker not in content
            or (route.endswith(".json") and "application/json" not in mime)):
        raise PortablePreviewError("disposable UCIE localhost HTTP contract drift")
    return response.status


def probe_preview_root(root: Path) -> dict:
    """Run and close one exact in-process temporary loopback server, no task."""
    root = _root(root)
    from .local_v1_app_v01 import (
        APP_SCHEMA, LOCAL_SERVER_CLASS, make_handler
    )
    # No forwarded root, user-selected file, public bind or background service.
    with LOCAL_SERVER_CLASS((BOUND_HOST, 0), make_handler(root)) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_port
            with HTTPConnection(BOUND_HOST, port, timeout=6) as conn:
                _check_http(conn, "/local/health", APP_SCHEMA.encode("ascii"))
                _check_http(conn, "/local", b"/local/library")
                _check_http(conn, "/local/guide/python-scandir.json",
                            b"UCIE_PYTHON_SCANDIR_SKILLBOOK_REVIEW_V01")
                _check_http(
                    conn, "/local/engine?purpose=PYTHON_SCANDIR_SAFE&case=single_owner",
                    b"UCIE FIRST-PARTY TEST"
                )
                _check_http(
                    conn, "/local/engine?purpose=PYTHON_SCANDIR_SAFE&case=shared_guarded",
                    b"UCIE FIRST-PARTY TEST"
                )
            with HTTPConnection(BOUND_HOST, port, timeout=6) as conn:
                conn.request("POST", "/local/guide/python-scandir",
                             headers={"Host": f"{BOUND_HOST}:{port}"})
                response = conn.getresponse()
                response.read(4096)
                if response.status != 405:
                    raise PortablePreviewError("POST failed to close")
        finally:
            server.shutdown()
            thread.join(timeout=5)
            if thread.is_alive():
                raise PortablePreviewError("loopback preview did not stop")
    return {
        "schema": SCHEMA,
        "status": "UCIE_C1_DISPOSABLE_LOOPBACK_SMOKE_PASS_NOT_CUSTOMER_GO",
        "revision": source_revision(),
        "actual_first_party_code_revision_observed": True,
        "loopback_http_routes_checked": 5,
        "negative_post_checked": True,
        "bound_host": BOUND_HOST,
        "port_allocated_ephemerally": True,
        "owner_local_v1_acceptance_inherited": False,
        "independent_customer_qa_attested": False,
        "customer_distribution_authorized": False,
        "customer_license_issued": False,
        "owner_signature_verified": False,
        "public_tunnel_started": False,
        "task_scheduler_modified": False,
        "operating_database_writes": 0,
        "arbitrary_customer_files_read": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE C1 disposable local-only preview; NOT customer release"
    )
    parser.add_argument("--self-probe", action="store_true", required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        result = probe_preview_root(root)
    except (PortablePreviewError, OSError, RuntimeError, ValueError):
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_C1_PORTABLE_PREVIEW_FAIL_CLOSED_CUSTOMER_NO_GO",
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
