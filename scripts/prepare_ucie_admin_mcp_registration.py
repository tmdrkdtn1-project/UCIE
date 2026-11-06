"""One-time, opt-in registration link for existing UCIE MCP make_server().

Operator-run against one fixed UCIE-owned server source path. Default performs
a read-only AST/import/syntax preflight. --apply writes one backup and atomically
edits only that server source; never restarts or changes the tunnel.

The registered privileged UCIE-only admin tools remain DISABLED unless the
existing authenticated server process explicitly receives
UCIE_ADMIN_TOOLS_ENABLED=1 from its owner-controlled launch configuration.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SERVER_FILE = Path(r"D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py")
MCP_PYTHON = Path(r"D:\UCIE_DATA\.venv_mcp\Scripts\python.exe")
ADMIN_SOURCE = Path(os.environ.get(
    "UCIE_ADMIN_SOURCE_DIR", r"D:\UCIE_PREVIEW\UCIE_ADMIN\src"))
ALLOWED_SOURCES = (
    Path(r"D:\UCIE_PREVIEW\UCIE_ADMIN\src"),
    Path(r"D:\UCIE\src"),
)
EXPECTED_CURRENT_SHA256 = "1a9ce892cbbf17d11078082150cea2b286528ef113935a28b254b511cd1b5304"
APPROVAL = "APPROVE_UCIE_ADMIN_MCP_HANDLER_REGISTRATION_ONCE"
MARKER = "# UCIE_ADMIN_REGISTRATION_V1"
MAX_SOURCE_BYTES = 512_000


class RegistrationError(ValueError):
    pass


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _node_is_server_assignment(node: ast.AST) -> bool:
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == "server"
                   for t in node.targets)
    if isinstance(node, ast.AnnAssign):
        return isinstance(node.target, ast.Name) and node.target.id == "server"
    return False


def _server_tool_decorator(node: ast.AST) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    for dec in node.decorator_list:
        decorated = dec.func if isinstance(dec, ast.Call) else dec
        if (isinstance(decorated, ast.Attribute)
                and decorated.attr == "tool"
                and isinstance(decorated.value, ast.Name)
                and decorated.value.id == "server"):
            return True
    return False


def prepare_registration(source: str, admin_source: Path = ADMIN_SOURCE) -> str:
    """Patch exactly one UCIE make_server() server instance, in memory.

    The existing query handler and previous UCIE Library linkage remain
    untouched. The new source contains only a gated one-time call before
    existing @server.tool decorator registration.
    """
    if (type(source) is not str or not source
            or len(source.encode("utf-8")) > MAX_SOURCE_BYTES
            or "\x00" in source):
        raise RegistrationError("invalid or oversized UCIE server source")
    if MARKER in source:
        raise RegistrationError("admin bridge already registered in source")
    if Path(admin_source) not in ALLOWED_SOURCES:
        raise RegistrationError("UCIE admin source must be an exact approved path")
    tree = ast.parse(source, filename="mcp_stdio_server.py")
    factories = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "make_server"
    ]
    if len(factories) != 1:
        raise RegistrationError("requires exactly one UCIE make_server function")
    make_server = factories[0]
    assigns = [n for n in make_server.body if _node_is_server_assignment(n)]
    if len(assigns) != 1:
        raise RegistrationError("requires one top-level server assignment")
    assignment = assigns[0]
    if assignment.end_lineno is None:
        raise RegistrationError("server assignment source span unknown")
    handlers = [
        n for n in make_server.body if isinstance(
            n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "search_ucie_evidence"
        and _server_tool_decorator(n)
    ]
    if (len(handlers) != 1
            or assignment.end_lineno >= min(
                [d.lineno for d in handlers[0].decorator_list]
                or [handlers[0].lineno])):
        raise RegistrationError("UCIE search handler is not attached to this server")

    lines = source.splitlines(keepends=True)
    if len(lines) <= assignment.end_lineno:
        raise RegistrationError("no insertion line after server assignment")
    # Only a standalone statement at the expected function indentation.
    first_line = lines[assignment.lineno - 1]
    indent = first_line[:assignment.col_offset]
    if (not indent or indent.strip() or "\t" in indent
            or not all(x.endswith(("\n", "\r\n")) for x in lines[:assignment.end_lineno])):
        raise RegistrationError("unsupported UCIE make_server indentation/layout")

    nl = "\r\n" if "\r\n" in source else "\n"
    insertion = [
        indent + "import os as _ucie_admin_os  " + MARKER,
        indent + 'if _ucie_admin_os.environ.get("UCIE_ADMIN_TOOLS_ENABLED") == "1":',
        indent + "    import sys as _ucie_admin_sys",
        indent + "    _ucie_admin_source = " + repr(str(admin_source)),
        indent + "    if _ucie_admin_source not in _ucie_admin_sys.path:",
        indent + "        _ucie_admin_sys.path.insert(0, _ucie_admin_source)",
        indent + "    from ucie_admin.mcp_registration import (",
        indent + "        register_ucie_local_admin_tools as _ucie_admin_register",
        indent + "    )",
        indent + "    _ucie_admin_register(server)",
    ]
    result_lines = (lines[:assignment.end_lineno]
                    + [entry + nl for entry in insertion]
                    + lines[assignment.end_lineno:])
    updated = "".join(result_lines)
    compile(updated, "mcp_stdio_server.py", "exec")
    return updated


def _require_ucie_host():
    if os.name != "nt":
        raise RegistrationError("UCIE local admin registration requires Windows")
    if ADMIN_SOURCE not in ALLOWED_SOURCES:
        raise RegistrationError("unexpected UCIE admin worktree path")
    if (not SERVER_FILE.is_file() or SERVER_FILE.is_symlink()
            or not MCP_PYTHON.is_file() or not ADMIN_SOURCE.is_dir()
            or ADMIN_SOURCE.is_symlink()):
        raise RegistrationError("exact UCIE MCP server/interpreter/source absent")
    if any(p.is_symlink() for p in SERVER_FILE.parents):
        raise RegistrationError("linked server parent path denied")


def _probe_import():
    env = dict(os.environ)
    env["PYTHONPATH"] = (
        str(ADMIN_SOURCE)
        + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    )
    task = subprocess.run(
        [str(MCP_PYTHON), "-B", "-c",
         "from ucie_admin.mcp_registration import "
         "register_ucie_local_admin_tools"],
        cwd=str(ADMIN_SOURCE.parent),
        env=env, timeout=15,
        capture_output=True, text=True, check=False,
    )
    if task.returncode != 0:
        raise RegistrationError("UCIE MCP interpreter cannot import admin tools")


def _load_source():
    content = SERVER_FILE.read_bytes()
    if not content or len(content) > MAX_SOURCE_BYTES or b"\x00" in content:
        raise RegistrationError("unexpected UCIE MCP server source format")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RegistrationError("UCIE MCP source must be UTF-8") from exc


def _apply_patch(original: str, updated: str):
    original_bytes = original.encode("utf-8")
    result_bytes = updated.encode("utf-8")
    backup = SERVER_FILE.with_name(
        SERVER_FILE.name + ".ucie-admin-backup-"
        + _digest(original_bytes)[:12] + ".bak"
    )
    if backup.exists():
        raise RegistrationError("UCIE admin backup already exists: stop duplicate apply")
    # Secure against accidental overwrite and mismatched source versions.
    with open(backup, "xb") as stream:
        stream.write(original_bytes)
        stream.flush()
        os.fsync(stream.fileno())
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="wb", dir=SERVER_FILE.parent,
                prefix=".ucie-admin-", suffix=".tmp", delete=False) as stream:
            tmp_path = Path(stream.name)
            stream.write(result_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        if SERVER_FILE.read_bytes() != original_bytes:
            raise RegistrationError("UCIE server changed since preflight")
        os.replace(tmp_path, SERVER_FILE)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    return str(backup)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--approval", default="")
    args = parser.parse_args(argv)
    try:
        _require_ucie_host()
        _probe_import()
        original = _load_source()
        if _digest(original.encode("utf-8")) != EXPECTED_CURRENT_SHA256:
            raise RegistrationError(
                "UCIE MCP server changed after Library patch; do not overwrite"
            )
        updated = prepare_registration(original)
        result = {
            "status": "READY_FOR_UCIE_ADMIN_REGISTRATION",
            "file": str(SERVER_FILE),
            "before_sha256": _digest(original.encode("utf-8")),
            "after_sha256": _digest(updated.encode("utf-8")),
            "python_syntax": "PASS",
            "admin_import": "PASS",
            "admin_tools_enabled": False,
            "requires_process_env": "UCIE_ADMIN_TOOLS_ENABLED=1",
            "restarted": False,
            "tunnel_modified": False,
            "file_written": False,
        }
        if args.apply:
            if args.approval != APPROVAL:
                raise RegistrationError("missing explicit UCIE admin file-edit approval")
            backup = _apply_patch(original, updated)
            result.update({
                "status": "UCIE_ADMIN_REGISTRATION_FILE_PATCHED_GATED",
                "file_written": True,
                "backup": backup,
            })
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (RegistrationError, OSError, SyntaxError,
            UnicodeError, TimeoutError) as exc:
        print(json.dumps({
            "status": "UCIE_ADMIN_REGISTRATION_FAIL_CLOSED",
            "reason": type(exc).__name__, "detail": str(exc)[:180],
            "restarted": False, "tunnel_modified": False,
        }, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
