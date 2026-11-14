"""UCIE-only MCP read-only history verification via the owner's pinned local CLI.

This module has no MCP/network inputs, no Slack token access, no arbitrary
command execution and no service/process/task mutation. Runtime stdout is
reduced to a fixed-status receipt, never raw Slack messages or credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

SCHEMA = "UCIE_SLACK_MCP_FIXED_READONLY_V1"
ROOT = Path(r"D:\UCIE")
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
SOURCE = ROOT / "src"
PINS = {
    "__init__.py": "cffb47f11207512a235db1aa77456a2534fc60e7",
    "ucie_slack_windows_reader_v1.py": "251fea25134ed6a77d90116e61fe368a4643e218",
    "ucie_slack_history_adapter_v1.py": "2edd1416a44f82521ef5c4c463f80d340b8494e6",
    "ucie_admin_history_verdict_v1.py": "0440482f0829c3706ce2af6028d8c8e744ac8b0e",
}
ANCHORS = frozenset({
    "UCIE_ADMIN_PR78_OWNER_LAUNCH",
    "UCIE_C45_AUTH0_READONLY_SCOPE",
    "UCIE_P10_PROTECTED_ROOT_SELF_CHECK",
})
MAX_SOURCE_BYTES = 200_000
MAX_CLI_OUTPUT = 8_000


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _no_link(path: Path) -> bool:
    """Reject source symlinks and Windows junctions in a fixed UCIE root."""
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        return False
    for parent in path.parents:
        if parent.is_symlink() or getattr(parent, "is_junction", lambda: False)():
            return False
    return True


def _pinned_reader_present(root: Path = ROOT, pins: dict | None = None) -> bool:
    allowed = PINS if pins is None else pins
    package = root / "src" / "ucie_miner"
    exe = root / ".venv" / "Scripts" / "python.exe"
    if not exe.is_file() or not _no_link(exe) or not package.is_dir():
        return False
    for name, sha in allowed.items():
        if name not in PINS or not isinstance(sha, str):
            return False
        path = package / name
        if not path.is_file() or not _no_link(path):
            return False
        if path.stat().st_size > MAX_SOURCE_BYTES:
            return False
        if _git_blob_sha(path.read_bytes()) != sha:
            return False
    return len(allowed) == len(PINS)


def _result(ok: bool, code: str) -> dict:
    return {
        "schema": SCHEMA,
        "status": ("UCIE_SLACK_MCP_HISTORY_VERIFIED" if ok
                   else "HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT"),
        "block_code": None if ok else code,
        "pinned_history_anchors": sorted(ANCHORS) if ok else [],
        "readonly_only": True,
        "token_or_messages_returned": False,
        "owner_write_tools_enabled": False,
        "c40_or_scheduled_tasks_modified": False,
        "operating_database_modified": False,
    }


def _evaluate_cli(output: str, returncode: int) -> dict:
    """A positive result needs exact schema, status, anchors and no leakage."""
    if returncode != 0 or not isinstance(output, str) or len(output) > MAX_CLI_OUTPUT:
        return _result(False, "UCIE_SLACK_CLI_FAILED")
    lines = output.strip().splitlines()
    if len(lines) != 1:
        return _result(False, "UCIE_SLACK_CLI_OUTPUT_INVALID")
    try:
        row = json.loads(lines[0])
    except (TypeError, ValueError):
        return _result(False, "UCIE_SLACK_CLI_OUTPUT_INVALID")
    if (type(row) is dict and
            row.get("schema") == "UCIE_SLACK_WINDOWS_EVIDENCE_READER_V1" and
            row.get("status") == "UCIE_SLACK_WINDOWS_READ_ONLY_HISTORY_VERIFIED" and
            row.get("block_code") is None and
            type(row.get("pinned_history_anchors")) is list and
            set(row["pinned_history_anchors"]) == ANCHORS and
            len(row["pinned_history_anchors"]) == len(ANCHORS) and
            row.get("token_or_raw_messages_exposed") is False and
            row.get("new_owner_mcp_tools_enabled") is False and
            row.get("c40_or_scheduled_tasks_modified") is False and
            row.get("operating_database_modified") is False):
        return _result(True, "")
    return _result(False, "UCIE_SLACK_CLI_EVIDENCE_UNVERIFIED")


def verify_ucie_slack_history_fixed() -> dict:
    """No arguments; only one exact host interpreter and fixed UCIE channel."""
    if os.name != "nt":
        return _result(False, "UCIE_WINDOWS_HOST_REQUIRED")
    try:
        if not _pinned_reader_present():
            return _result(False, "UCIE_SLACK_READER_SOURCE_PIN_MISMATCH")
        environment = {
            "PYTHONPATH": str(SOURCE),
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
            "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
            "PATH": str(PYTHON.parent) + os.pathsep + r"C:\Windows\System32;C:\Windows",
        }
        completed = subprocess.run(
            [str(PYTHON), "-B", "-m",
             "ucie_miner.ucie_slack_windows_reader_v1", "verify"],
            cwd=str(ROOT),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=150,
            text=True,
            errors="replace",
            check=False,
            shell=False,
        )
        return _evaluate_cli(completed.stdout, completed.returncode)
    except (OSError, ValueError, subprocess.SubprocessError):
        return _result(False, "UCIE_SLACK_LOCAL_READER_UNAVAILABLE")
