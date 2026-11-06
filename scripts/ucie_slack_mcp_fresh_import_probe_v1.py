"""UCIE MCP fresh interpreter / registered-tool read-only proof.

This executable is intentionally INERT: no MCP server, tool invocation,
network, credentials, host mutation, system environment edits or C40 restart.
It simulates the registration decorations using the real pinned UCIE staging
modules, inside the existing approved MCP interpreter, never the running C40.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import types

SCHEMA = "UCIE_MCP_FRESH_REGISTRATION_IMPORT_V1"
SOURCE = Path(r"D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin")
REG = SOURCE / "mcp_registration.py"
READER = SOURCE / "slack_history_readonly_mcp_v1.py"
INTERPRETER = Path(r"D:\UCIE_DATA\.venv_mcp\Scripts\python.exe")
PINNED_REG_SHA256 = "f75a9780bbf745b547af8a6d7ca830269aa3ebffb25cef690724d0ffe4184962"
PINNED_READER_SHA256 = "92e273f93495bd2e0c0c6b4da70e70cc1c0406a81c1ce70b7ac169edce7f08ac"
KNOWN_ADMIN = frozenset((
    "ucie_admin_capabilities", "ucie_admin_list_files",
    "ucie_admin_read_text", "ucie_admin_search_text",
    "ucie_admin_create_directory", "ucie_admin_write_text",
    "ucie_admin_replace_text", "ucie_admin_git_status",
    "ucie_admin_test_one_file",
))
NEW_TOOL = "ucie_slack_history_verify_readonly"
MAX_FILE = 25_000


class ProbeError(RuntimeError):
    pass


def _sha(path: Path, expected: str) -> bytes:
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
           for p in (path, *path.parents)):
        raise ProbeError("UCIE_REPARSE_PATH_DENIED")
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_FILE:
        raise ProbeError("UCIE_SOURCE_FILE_MISSING_OR_INVALID")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ProbeError("UCIE_SOURCE_SHA_MISMATCH")
    return raw


class FakeFastMCP:
    def __init__(self):
        self.handlers = {}

    def tool(self, *, name: str):
        def attach(fn):
            if not isinstance(name, str) or name in self.handlers:
                raise ProbeError("DUPLICATE_OR_INVALID_TOOL")
            self.handlers[name] = fn
            return fn
        return attach


def probe() -> dict:
    if os.name != "nt":
        raise ProbeError("UCIE_WINDOWS_OWNER_HOST_ONLY")
    if Path(sys.executable).resolve() != INTERPRETER.resolve():
        raise ProbeError("UCIE_EXPECTED_MCP_INTERPRETER_REQUIRED")
    reg_bytes = _sha(REG, PINNED_REG_SHA256)
    reader_bytes = _sha(READER, PINNED_READER_SHA256)

    # UCIE package origin is exactly the approved staging path, never
    # another project's or user-site's installed package.
    package = types.ModuleType("ucie_admin")
    package.__path__ = [str(SOURCE)]
    package.__package__ = "ucie_admin"
    package.__file__ = str(SOURCE / "__init__.py")
    bridge = types.ModuleType("ucie_admin.local_write_bridge")
    bridge.UCIEFileBridge = type("UCIEFileBridge", (), {})
    bridge.BridgeError = type("BridgeError", (Exception,), {})
    sys.modules["ucie_admin"] = package
    sys.modules["ucie_admin.local_write_bridge"] = bridge

    imported = importlib.import_module("ucie_admin.mcp_registration")
    reader = importlib.import_module("ucie_admin.slack_history_readonly_mcp_v1")
    if (Path(imported.__file__).resolve() != REG.resolve()
            or Path(reader.__file__).resolve() != READER.resolve()):
        raise ProbeError("UCIE_IMPORT_ORIGIN_MISMATCH")
    if (reg_bytes != _sha(REG, PINNED_REG_SHA256)
            or reader_bytes != _sha(READER, PINNED_READER_SHA256)):
        raise ProbeError("UCIE_SOURCE_CHANGED_DURING_IMPORT")

    fake = FakeFastMCP()
    # Explicit inert injected object prevents UCIEFileBridge initializers.
    # Decorators are registered but handlers are NEVER called.
    result = imported.register_ucie_local_admin_tools(fake, bridge=object())
    names = frozenset(fake.handlers)
    if (names != KNOWN_ADMIN | {NEW_TOOL}
            or result.get("tool_count") != 9
            or result.get("status")
               != "UCIE_ADMIN_TOOLS_REGISTERED_WITH_EXISTING_FASTMCP_INSTANCE"):
        raise ProbeError("UCIE_FRESH_REGISTRATION_NAMES_MISMATCH")
    return {
        "schema": SCHEMA,
        "status": "UCIE_FRESH_PROCESS_TEN_TOOLS_PASS",
        "interpreter_matches_existing_mcp": True,
        "registration_source_pinned": True,
        "reader_source_pinned": True,
        "registered_admin_count": len(names & KNOWN_ADMIN),
        "registered_extra_readonly_count": len(names - KNOWN_ADMIN),
        "new_slack_tool_registered_in_fresh_python": NEW_TOOL in names,
        "actual_running_c40_tools_list_verified": False,
        "chatgpt_plugin_tool_cache_verified": False,
        "slack_token_or_message_read": False,
        "registered_handler_invoked": False,
        "c40_or_task_modified": False,
        "operating_database_modified": False,
    }


def main() -> int:
    try:
        result = probe()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        # Never reveal source contents, exceptions, credentials or private paths.
        code = str(exc) if isinstance(exc, ProbeError) else "UCIE_IMPORT_OR_REGISTRATION_EXCEPTION"
        print(json.dumps({
            "schema": SCHEMA, "status": "UCIE_FRESH_PROCESS_REGISTRATION_BLOCKED",
            "block_code": code,
            "actual_running_c40_tools_list_verified": False,
            "slack_token_or_message_read": False,
            "registered_handler_invoked": False,
            "c40_or_task_modified": False,
        }, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
