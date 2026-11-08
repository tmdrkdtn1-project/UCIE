"""UCIE Local V1 -- Windows Task Scheduler owner-only launch target.

An auto-started localhost process must NOT open a browser, reuse an old
dynamic port, scan customer files or start any public Cloudflare tunnel.
Task registration is manual/opt-in through the companion PowerShell script.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

SCHEMA = "UCIE_LOCAL_V1_WINDOWS_AUTOSTART_V01"
TASK_NAME = "UCIE-LocalV1-Web"
DEFAULT_PORT = 18767


class AutostartPreflightError(ValueError):
    """The exact owner-only Windows environment cannot be confirmed."""


def validate_owner_environment(
    root: Path, executable: Path, *, platform: str
) -> Path:
    """Fail closed before importing any application modules."""
    expected_root = Path("D:/UCIE")
    if (platform != "nt"
            or root.resolve() != expected_root.resolve()
            or root.is_symlink()
            or not (root / ".git").is_dir()
            or not (root / "src" / "ucie_miner" / "local_v1_app_v01.py").is_file()
            or not (root / "docs" / "UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md").is_file()):
        raise AutostartPreflightError("UCIE_EXACT_OWNER_WINDOWS_ROOT_REQUIRED")
    expected_python = root / ".venv" / "Scripts" / "python.exe"
    if (not expected_python.is_file()
            or executable.resolve() != expected_python.resolve()):
        raise AutostartPreflightError("UCIE_EXACT_OWNER_VENV_REQUIRED")
    return root / "src"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE Local V1 Windows logon auto-start (private loopback only)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535 or args.port == 8767:
        print(json.dumps({
            "schema": SCHEMA, "status": "UCIE_AUTOSTART_INVALID_OR_LEGACY_PORT"
        }, sort_keys=True))
        return 2
    root = Path(__file__).resolve().parents[1]
    try:
        src = validate_owner_environment(root, Path(sys.executable),
                                         platform=os.name)
        # Do not import any unrelated project; no browser launch and no
        # privileged service process. Existing W04 storage remains read-only.
        sys.path.insert(0, str(src))
        from ucie_miner.local_v1_app_v01 import main as app_main
        from ucie_miner.local_v1_priority_v01 import require_local_work
        require_local_work("LOCAL_APP")
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_LOCAL_V1_AUTOSTART_FOREGROUND_SERVER_BEGIN",
            "task_name": TASK_NAME,
            "bind_host": "127.0.0.1",
            "bind_port": args.port,
            "online_release_authorized": False,
            "cloudflare_tunnel_modified": False,
            "operating_database_writes": 0,
        }, sort_keys=True), flush=True)
        # No --open-browser: the fixed local URL is a user bookmark.
        # An occupied port causes app_main to fail closed; no other
        # listener is killed or adopted.
        return app_main(["--port", str(args.port)])
    except (AutostartPreflightError, ImportError, ValueError) as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_LOCAL_V1_AUTOSTART_PREFLIGHT_FAILED",
            "reason": type(exc).__name__,
            "online_release_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
