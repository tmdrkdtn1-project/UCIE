"""Owner-only one-shot UCIE MCP read-only Slack tool registration installer.

Default: read-only Preview. Apply: interactive owner approval, pinned PR78
registration byte-for-byte source, one new UCIE module and one existing UCIE
registration source with backup and atomic write. No tunnel/client restart,
no tool invocation, no Slack token read, no other project or scheduler changes.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

SCHEMA = "UCIE_SLACK_MCP_READONLY_OWNER_STAGE_V1"
PR78_GIT_BLOB = "8516baa69e768f2589d5df305200ebcd99b76e0d"
LIVE_OWNER_STAGE_GIT_BLOB = "c26be40528d421bf384acbccd1501a1c522cc666"
# Both are exact source versions observed and independently pinned.
ALLOWED_BASE_BLOBS = frozenset({PR78_GIT_BLOB, LIVE_OWNER_STAGE_GIT_BLOB})
MARKER = "# UCIE_SLACK_READONLY_ADMIN_MCP_V1"
CONFIRM = "UCIE_SLACK_MCP_READONLY_STAGE_ONLY"
ROOT = Path(r"D:\UCIE")
SOURCE = ROOT / "src" / "ucie_miner" / "ucie_slack_mcp_owner_dispatch_v1.py"
ADMIN = Path(r"D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin")
REGISTER = ADMIN / "mcp_registration.py"
DEST = ADMIN / "slack_history_readonly_mcp_v1.py"
EXPECTED_TOOLS = frozenset({
    "ucie_admin_capabilities", "ucie_admin_list_files",
    "ucie_admin_read_text", "ucie_admin_search_text",
    "ucie_admin_create_directory", "ucie_admin_write_text",
    "ucie_admin_replace_text", "ucie_admin_git_status",
    "ucie_admin_test_one_file",
})
MAX_SOURCE = 20_000


class UCIEStageError(ValueError):
    """Bounded, sanitized owner-stage denial; no raw source is printed."""


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_path(path: Path) -> bool:
    for p in (path, *path.parents):
        if p.is_symlink() or getattr(p, "is_junction", lambda: False)():
            return False
    return True


def patch_registration(source: str) -> str:
    """Insert a tenth, *non-admin-namespaced*, read-only tool before return.

    Preserve existing nine ucie_admin_* tools and original owner-launcher
    admin_count=9 acceptance. No source of the PR78 registration is removed.
    """
    if (not isinstance(source, str) or MARKER in source or
            len(source.encode("utf-8")) > MAX_SOURCE or "\0" in source):
        raise UCIEStageError("UCIE_ADMIN_REGISTRATION_SOURCE_NOT_ELIGIBLE")
    try:
        tree = ast.parse(source, filename="ucie_admin_registration")
    except SyntaxError as exc:
        raise UCIEStageError("UCIE_ADMIN_REGISTRATION_AST_INVALID") from exc
    defs = [x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
            and x.name == "register_ucie_local_admin_tools"]
    if len(defs) != 1:
        raise UCIEStageError("UCIE_ADMIN_REGISTRATION_FUNCTION_AMBIGUOUS")
    fn = defs[0]
    names = set()
    # Reject surprise executable statements while keeping PR78 docstrings,
    # original bridge initialization, nine handler defs, and return only.
    non_tools = [node for node in fn.body
                 if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if (len(non_tools) != 3 or
            not isinstance(non_tools[0], ast.Expr) or
            not isinstance(non_tools[1], ast.If) or
            not isinstance(non_tools[2], ast.Return)):
        raise UCIEStageError("UCIE_ADMIN_REGISTRATION_UNEXPECTED_STATEMENTS")
    names = set()
    for sub in fn.body:
        if not isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in sub.decorator_list:
            if (isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "tool"
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "fastmcp"):
                for key in decorator.keywords:
                    if (key.arg == "name" and isinstance(key.value, ast.Constant)
                            and isinstance(key.value.value, str)):
                        names.add(key.value.value)
    if names != EXPECTED_TOOLS:
        raise UCIEStageError("UCIE_EXISTING_NINE_ADMIN_HANDLERS_CHANGED")
    returns = [n for n in fn.body if isinstance(n, ast.Return)]
    if len(returns) != 1:
        raise UCIEStageError("UCIE_REGISTRATION_RETURN_AMBIGUOUS")
    ret = returns[0]
    lines = source.splitlines(keepends=True)
    expected = " " * ret.col_offset
    if (ret.col_offset != 4 or not lines[ret.lineno - 1].startswith(
            expected + "return {")):
        raise UCIEStageError("UCIE_REGISTRATION_RETURN_LAYOUT_CHANGED")
    newline = "\r\n" if "\r\n" in source else "\n"
    insertion = [
        'from ucie_admin.slack_history_readonly_mcp_v1 import verify_ucie_slack_history_fixed as _ucie_fixed_history_verify  ' + MARKER,
        '',
        '@fastmcp.tool(name="ucie_slack_history_verify_readonly")',
        'def ucie_slack_history_verify_readonly() -> dict:',
        '    """Only three pinned UCIE Slack history receipts; no request fields."""',
        '    return _ucie_fixed_history_verify()',
        '',
    ]
    addition = "".join(expected + line + newline if line else newline
                       for line in insertion)
    patched = "".join(lines[:ret.lineno - 1]) + addition + "".join(lines[ret.lineno - 1:])
    try:
        compile(patched, "mcp_registration.py", "exec")
    except SyntaxError as exc:
        raise UCIEStageError("UCIE_REGISTRATION_PATCH_SYNTAX_INVALID") from exc
    return patched


def prepare(source_file: Path = SOURCE, registration: Path = REGISTER,
            destination: Path = DEST) -> tuple[bytes, bytes, bytes]:
    if os.name != "nt":
        raise UCIEStageError("WINDOWS_OWNER_ONLY")
    if not all(_safe_path(path) for path in (source_file, registration, destination)):
        raise UCIEStageError("UCIE_OWNER_STAGE_REPARSE_PATH_DENIED")
    if not source_file.is_file() or not registration.is_file():
        raise UCIEStageError("UCIE_OWNER_STAGE_REQUIRED_SOURCE_ABSENT")
    if destination.exists():
        raise UCIEStageError("UCIE_OWNER_STAGE_ALREADY_PRESENT")
    content = source_file.read_bytes()
    original = registration.read_bytes()
    if not content or len(content) > MAX_SOURCE or _git_blob(original) not in ALLOWED_BASE_BLOBS:
        raise UCIEStageError("UCIE_OWNER_STAGE_SOURCE_BLOB_MISMATCH")
    try:
        compile(content.decode("utf-8"), "slack_history_readonly_mcp_v1.py", "exec")
        updated = patch_registration(original.decode("utf-8")).encode("utf-8")
    except UnicodeError as exc:
        raise UCIEStageError("UCIE_OWNER_STAGE_UTF8_REQUIRED") from exc
    return content, original, updated


def install_atomic(source_file: Path, registration: Path, destination: Path,
                   blob: bytes, original: bytes, patched: bytes) -> Path:
    """Only the fixed caller may use the function on the approved UCIE paths."""
    backup = registration.with_name(
        registration.name + ".ucie-slack-readonly-" + _sha(original)[:12] + ".bak"
    )
    if backup.exists() or destination.exists():
        raise UCIEStageError("UCIE_OWNER_STAGE_EXISTING_FILE_OR_BACKUP")
    with open(backup, "xb") as f:
        f.write(original)
        f.flush()
        os.fsync(f.fileno())
    temporary_registration = None
    temporary_module = None
    installed_module = False
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=destination.parent,
                                         prefix=".ucie-slack-mcp-",
                                         suffix=".tmp", delete=False) as f:
            temporary_module = Path(f.name)
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        with tempfile.NamedTemporaryFile(mode="wb", dir=registration.parent,
                                         prefix=".ucie-slack-reg-",
                                         suffix=".tmp", delete=False) as f:
            temporary_registration = Path(f.name)
            f.write(patched)
            f.flush()
            os.fsync(f.fileno())
        if (registration.read_bytes() != original or source_file.read_bytes() != blob
                or destination.exists()):
            raise UCIEStageError("UCIE_OWNER_STAGE_SOURCE_CHANGED_AT_COMMIT")
        # First write module (no current server import), then update registration.
        os.replace(temporary_module, destination)
        temporary_module = None
        installed_module = True
        os.replace(temporary_registration, registration)
        temporary_registration = None
        if (registration.read_bytes() != patched or destination.read_bytes() != blob):
            raise UCIEStageError("UCIE_OWNER_STAGE_POSTWRITE_VERIFY_FAILED")
        return backup
    except Exception:
        # Restore exactly our own target when a second write failed; leave
        # owner backup for recovery. Do not touch unrelated files.
        if installed_module and destination.is_file():
            destination.unlink()
        if registration.is_file() and registration.read_bytes() == patched:
            os.replace(backup, registration)
        raise
    finally:
        for name in (temporary_registration, temporary_module):
            if name is not None:
                name.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    result = {
        "schema": SCHEMA,
        "source_file": str(SOURCE),
        "admin_registration_file": str(REGISTER),
        "read_only_tool_name": "ucie_slack_history_verify_readonly",
        "c40_restarted": False,
        "existing_admin_tools_modified": False,
        "operating_database_modified": False,
        "slack_credentials_accessed": False,
        "new_mcp_tool_visible_in_running_c40": False,
    }
    try:
        blob, original, patched = prepare()
        result.update({
            "before_sha256": _sha(original),
            "after_sha256": _sha(patched),
            "new_module_sha256": _sha(blob),
            "status": "UCIE_SLACK_READONLY_STAGE_PREVIEW_READY",
            "registration_file_written": False,
        })
        if args.apply:
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise UCIEStageError("UCIE_OWNER_INTERACTIVE_CONSOLE_REQUIRED")
            phrase = input("Stage UCIE read-only Slack MCP tool only (no C40 restart)? "
                           "Type UCIE_SLACK_MCP_READONLY_STAGE_ONLY: ")
            if phrase != CONFIRM:
                raise UCIEStageError("UCIE_OWNER_CONFIRMATION_REJECTED")
            # Revalidate exact current sources immediately after local consent.
            one, two, three = prepare()
            if (one, two, three) != (blob, original, patched):
                raise UCIEStageError("UCIE_OWNER_STAGE_CHANGED_AFTER_APPROVAL")
            backup = install_atomic(SOURCE, REGISTER, DEST, blob, original, patched)
            result.update({
                "status": "UCIE_SLACK_READONLY_STAGE_APPLIED_NOT_RUNNING",
                "registration_file_written": True,
                "backup_created": bool(backup.is_file()),
            })
        print(json.dumps(result, sort_keys=True))
        return 0
    except (UCIEStageError, OSError, SyntaxError, ValueError, EOFError) as exc:
        result.update({
            "status": "UCIE_SLACK_READONLY_STAGE_FAIL_CLOSED",
            "block_code": str(exc) if isinstance(exc, UCIEStageError)
                          else "UCIE_STAGE_OS_OR_SYNTAX_FAILURE",
            "registration_file_written": False,
        })
        print(json.dumps(result, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
