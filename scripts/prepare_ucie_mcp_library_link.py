"""One-time, fail-closed UCIE MCP handler link. No server restart.

A local operator runs this against the exact UCIE-owned MCP stdio server.
Default: structural preflight only, no file writes. --apply requires an exact
operator phrase; source is backed up and syntax-checked before atomic replace.
This tool is *not* installed or executed by committing it to GitHub.
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

TARGET = Path(r"D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py")
UCIE_SOURCE = Path(os.environ.get("UCIE_LIBRARY_SOURCE_DIR", r"D:\UCIE\src"))
ALLOWED_SOURCE_DIRS = (Path(r"D:\UCIE\src"),
                       Path(r"D:\UCIE_PREVIEW\UCIE\src"))
MCP_PYTHON = Path(r"D:\UCIE_DATA\.venv_mcp\Scripts\python.exe")
APPROVAL = "APPROVE_UCIE_EXISTING_MCP_LIBRARY_HANDLER_ONCE"
MARKER = "# UCIE_LIBRARY_BRIDGE_V1"
MAX_SOURCE_BYTES = 512_000
EXPECTED_STATUS = "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY"


class LinkError(ValueError):
    pass


class _ReturnCollector(ast.NodeVisitor):
    def __init__(self):
        self.returns = []

    def visit_Return(self, node):
        self.returns.append(node)

    def visit_FunctionDef(self, node):
        return  # A nested helper cannot be part of the MCP tool return.

    def visit_AsyncFunctionDef(self, node):
        return

    def visit_Lambda(self, node):
        return


def _offset(lines, line, byte_col):
    return sum(len(row.encode("utf-8")) for row in lines[:line - 1]) + byte_col


def propose_link(source: str) -> str:
    """Adapt every handler return without changing branch or error semantics.

    A handler can have many early returns (e.g. malformed query, empty
    evidence or unexpected upstream failure). Every nonempty return is
    evaluated exactly once and sent through a compatibility helper, which
    preserves ALL non-public-success results unchanged. No function rename,
    new FastMCP registration or server restart occurs.
    """
    if (type(source) is not str
            or len(source.encode("utf-8")) > MAX_SOURCE_BYTES
            or "\x00" in source):
        raise LinkError("invalid/oversized UCIE MCP handler source")
    if MARKER in source:
        raise LinkError("UCIE library bridge already present; do not double-patch")
    tree = ast.parse(source, filename="mcp_stdio_server.py")
    funcs = [node for node in ast.walk(tree) if isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "search_ucie_evidence"]
    if len(funcs) != 1:
        raise LinkError("need exactly one search_ucie_evidence handler")
    fn = funcs[0]
    args = fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs
    argnames = {arg.arg for arg in args}
    if not {"query", "category", "tag", "top"} <= argnames:
        raise LinkError("existing search handler arguments differ")
    visitor = _ReturnCollector()
    for statement in fn.body:
        visitor.visit(statement)
    if not visitor.returns or not any(r.value is not None for r in visitor.returns):
        raise LinkError("existing MCP handler has no usable value return")
    # The confirmed live MCP response identifies the public-success status,
    # but an installed handler may obtain that status from an imported
    # helper rather than a literal in this source file. The runtime bridge
    # matches the exact status after evaluating each original return.
    # Install the helper once at the beginning of this exact handler.
    # Do not insert into any nested function, or before its docstring.
    first_stmt = fn.body[0]
    if (isinstance(first_stmt, ast.Expr)
            and isinstance(first_stmt.value, ast.Constant)
            and isinstance(first_stmt.value.value, str)):
        if len(fn.body) < 2:
            raise LinkError("handler has a docstring but no statements")
        first_stmt = fn.body[1]
    lines = source.splitlines(keepends=True)
    if any("\r" in line and not line.endswith("\r\n")
           for line in lines):
        raise LinkError("unexpected source newline layout")
    indent = " " * first_stmt.col_offset
    if not indent or "\t" in lines[first_stmt.lineno - 1][
            :first_stmt.col_offset]:
        raise LinkError("unsupported handler indentation")
    helper = (
        indent + "import sys as _ucie_library_sys  " + MARKER + "\n"
        + indent + "_ucie_library_source = " + repr(str(UCIE_SOURCE)) + "\n"
        + indent + "if _ucie_library_source not in _ucie_library_sys.path:\n"
        + indent + "    _ucie_library_sys.path.insert(0, _ucie_library_source)\n"
        + indent + "from ucie_miner.public_library_mcp_adapter import (\n"
        + indent + "    extend_existing_ucie_mcp_wire_response_if_public "
        + "as _ucie_library_bridge\n"
        + indent + ")\n"
    )
    newline = "\r\n" if "\r\n" in source else "\n"
    helper_bytes = helper.replace("\n", newline).encode("utf-8")
    data = source.encode("utf-8")
    inserts = [
        (_offset(lines, first_stmt.lineno, 0),
         _offset(lines, first_stmt.lineno, 0), helper_bytes)
    ]
    for returned in visitor.returns:
        if returned.value is None:
            # Preserve bare returns and their original status/meaning.
            continue
        expr = ast.get_source_segment(source, returned.value)
        if not expr:
            raise LinkError("cannot identify handler return expression")
        start = _offset(lines, returned.value.lineno,
                        returned.value.col_offset)
        end = _offset(lines, returned.value.end_lineno,
                      returned.value.end_col_offset)
        if not (0 <= start < end <= len(data)):
            raise LinkError("invalid AST handler return source offsets")
        replacement = (
            '_ucie_library_bridge(r"D:\\UCIE", ('
            + expr + '), query=query, category=category, '
            'tag=tag, top=top)'
        )
        inserts.append((start, end, replacement.encode("utf-8")))
    # Reverse byte order, so every AST span remains anchored to the
    # original bytes, including mixed inline and early return branches.
    for start, end, replacement in sorted(inserts, reverse=True):
        data = data[:start] + replacement + data[end:]
    result = data.decode("utf-8")
    compile(result, "mcp_stdio_server.py", "exec")
    return result


def _require_exact_path(path):
    if UCIE_SOURCE not in ALLOWED_SOURCE_DIRS:
        raise LinkError("only UCIE or isolated UCIE preview source allowed")
    if os.name != "nt":
        raise LinkError("the operator patch is Windows UCIE-only")
    if path != TARGET or not path.is_file():
        raise LinkError("missing exact UCIE-owned MCP server file")
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise LinkError("linked MCP file/ancestor is not supported")
    if not UCIE_SOURCE.is_dir() or not MCP_PYTHON.is_file():
        raise LinkError("UCIE source or MCP Python runtime is not available")
    adapter = UCIE_SOURCE / "ucie_miner" / "public_library_mcp_adapter.py"
    if not adapter.is_file() or (
            "extend_existing_ucie_mcp_wire_response"
            not in adapter.read_text("utf-8")):
        raise LinkError("UCIE Library adapter not yet present at D:\\UCIE\\src")


def _import_probe():
    # No modifications to the host; check that this exact UCIE interpreter
    # can import the adapter after using the reviewed UCIE-only source.
    environment = dict(os.environ)
    environment["PYTHONPATH"] = (
        str(UCIE_SOURCE)
        + (os.pathsep + environment["PYTHONPATH"]
           if environment.get("PYTHONPATH") else ""))
    probe = subprocess.run(
        [str(MCP_PYTHON), "-B", "-c",
         "from ucie_miner.public_library_mcp_adapter import "
         "extend_existing_ucie_mcp_wire_response"],
        cwd=str(UCIE_SOURCE.parent), env=environment,
        capture_output=True, timeout=15, check=False)
    if probe.returncode != 0:
        raise LinkError("UCIE MCP Python cannot import new public Library adapter")


def _read_server(path):
    content = path.read_bytes()
    if len(content) > MAX_SOURCE_BYTES or not content:
        raise LinkError("unexpected UCIE MCP server file size")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LinkError("unexpected MCP server encoding") from exc


def _write_once(path, original, proposed):
    raw = original.encode("utf-8")
    dest = proposed.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    backup = path.with_name(path.name + ".ucie-backup-" + digest[:12] + ".bak")
    if backup.exists():
        raise LinkError("exact matching backup already exists; review prior patch")
    # Reserve the backup using exclusive creation to avoid replacing evidence.
    with open(backup, "xb") as file:
        file.write(raw)
        file.flush()
        os.fsync(file.fileno())
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="wb", dir=path.parent,
                prefix=".ucie-mcp-handler-", suffix=".tmp",
                delete=False) as output:
            temp_name = output.name
            output.write(dest)
            output.flush()
            os.fsync(output.fileno())
        # Do not override a changed server file between read and replace.
        if path.read_bytes() != raw:
            raise LinkError("running server file changed during patch preparation")
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
    return str(backup), hashlib.sha256(dest).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Opt-in: atomic file change; never restarts MCP")
    parser.add_argument("--approval", default="",
                        help="Exact approval required together with --apply")
    args = parser.parse_args(argv)
    try:
        _require_exact_path(TARGET)
        _import_probe()
        source = _read_server(TARGET)
        modified = propose_link(source)
        summary = {
            "status": "READY_FOR_ONE_TIME_UCIE_MCP_HANDLER_LINK",
            "server": str(TARGET),
            "before_sha256": hashlib.sha256(
                source.encode("utf-8")).hexdigest(),
            "after_sha256": hashlib.sha256(
                modified.encode("utf-8")).hexdigest(),
            "syntax_checked": True,
            "ucie_adapter_import_checked": True,
            "server_restarted": False,
            "tunnel_changed": False,
        }
        if args.apply:
            if args.approval != APPROVAL:
                raise LinkError("explicit UCIE MCP handler approval missing")
            backup, actual = _write_once(TARGET, source, modified)
            summary.update({
                "status": "UCIE_MCP_HANDLER_FILE_PATCHED_RESTART_NOT_PERFORMED",
                "backup": backup, "after_sha256": actual,
            })
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (LinkError, OSError, SyntaxError, TimeoutError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED_NO_OPERATION_CLAIM",
                          "reason": type(exc).__name__,
                          "detail": str(exc)[:160]}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
