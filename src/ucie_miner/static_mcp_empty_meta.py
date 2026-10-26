"""Candidate-only MCP JSON-RPC empty-meta compatibility detector.

Upstream modelcontextprotocol/python-sdk PR #3628 (merged 2026-10-02).
Only parses explicit bounded Python text; it never executes or imports source.
It is NOT part of the existing owner-signed Serial4/Serial5 rulepacks.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys

RULE_ID = "MCP_EMPTY_META_LEGACY_COMPAT"
EVIDENCE = "https://github.com/modelcontextprotocol/python-sdk/pull/3628"
UPSTREAM_MERGE = "0b2fd3ea60efb16b349e8c887cf91bf2f9f773fc"
MAX_SOURCE_BYTES = 131072
MAX_NODES = 25000
MAX_FINDINGS = 20


class SourceRejected(ValueError):
    """Untrusted inert source failed a bounded static input requirement."""


def _fn_nodes(fn: ast.FunctionDef | ast.AsyncFunctionDef, parents: dict):
    for node in ast.walk(fn):
        if node is fn:
            continue
        anc = parents.get(node)
        nested = False
        while anc is not None and anc is not fn:
            if isinstance(anc, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                nested = True
                break
            anc = parents.get(anc)
        if not nested:
            yield node


def _writes_meta(node: ast.AST):
    """Return params variable and meta variable for a subscript assignment."""
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return None
    target = node.targets[0]
    if not (isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and isinstance(target.slice, ast.Constant)
            and target.slice.value == "_meta"
            and isinstance(node.value, ast.Name)):
        return None
    return target.value.id, node.value.id


def _possibly_empty_meta_init(node: ast.AST, name: str) -> bool:
    if not (isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name):
        return False
    value = node.value
    return (
        isinstance(value, ast.Dict) and len(value.keys) == 0
    ) or (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "dict"
        and not value.keywords
    )


def _outbound_request(node: ast.AST, params_name: str) -> bool:
    if not (isinstance(node, ast.Call)
            and isinstance(node.func, (ast.Name, ast.Attribute))
            and (node.func.id if isinstance(node.func, ast.Name)
                 else node.func.attr) == "JSONRPCRequest"):
        return False
    kw = {item.arg: item.value for item in node.keywords if item.arg}
    return (
        isinstance(kw.get("params"), ast.Name)
        and kw["params"].id == params_name
        and isinstance(kw.get("method"), (ast.Name, ast.Constant))
        and isinstance(kw.get("jsonrpc"), ast.Constant)
        and kw["jsonrpc"].value == "2.0"
    )


def _under_nonempty_guard(node: ast.AST, meta_name: str,
                          parents: dict) -> bool:
    """Only recognize the safe explicit truthiness if-branch."""
    child = node
    while (parent := parents.get(child)) is not None:
        if isinstance(parent, ast.If):
            if (isinstance(parent.test, ast.Name)
                    and parent.test.id == meta_name
                    and child in parent.body):
                return True
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.Lambda)):
            break
        child = parent
    return False


def inspect_mcp_empty_meta_source(source: str) -> dict:
    """Find manual-review candidates matching the verified upstream mistake."""
    if type(source) is not str:
        raise SourceRejected("source must be text")
    raw = source.encode("utf-8", errors="surrogatepass")
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise SourceRejected("empty or oversized source")
    try:
        tree = ast.parse(source, filename="<ucie-mcp-inert>")
        nodes = list(ast.walk(tree))
    except (SyntaxError, ValueError, MemoryError, RecursionError) as exc:
        raise SourceRejected("invalid Python syntax or AST") from exc
    if len(nodes) > MAX_NODES:
        raise SourceRejected("AST bound exceeded")

    parents = {child: parent for parent in nodes
               for child in ast.iter_child_nodes(parent)}
    findings = []
    for fn in nodes:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        local = list(_fn_nodes(fn, parents))
        constructors = [node for node in local if isinstance(node, ast.Call)]
        for node in local:
            written = _writes_meta(node)
            if written is None:
                continue
            params_name, meta_name = written
            possible_empty = any(
                item.lineno < node.lineno and
                _possibly_empty_meta_init(item, meta_name)
                for item in local
            )
            uses = any(
                call.lineno > node.lineno
                and _outbound_request(call, params_name)
                for call in constructors
            )
            if (not possible_empty or not uses
                    or _under_nonempty_guard(node, meta_name, parents)):
                continue
            findings.append({
                "rule_id": RULE_ID,
                "line": node.lineno,
                "column": node.col_offset,
                "function": fn.name,
                "risk": "EMPTY_MCP_META_MAY_BREAK_LEGACY_PEER",
                "public_evidence": EVIDENCE,
                "safe_guidance": (
                    "Attach _meta only when it has content; omit params "
                    "when no arguments remain. Preserve real progress and "
                    "trace metadata. Review legacy MCP peer compatibility."
                ),
                "manual_review_required": True,
                "runtime_bug_confirmed_for_input": False,
            })
            if len(findings) > MAX_FINDINGS:
                raise SourceRejected("finding bound exceeded")
    findings.sort(key=lambda item: (item["line"], item["column"]))
    return {
        "schema": "UCIE_SIXTH_MCP_EMPTY_META_CANDIDATE_V1",
        "status": ("STATIC_CANDIDATES_FOR_MANUAL_REVIEW" if findings else
                   "NO_MATCH_NOT_A_SAFETY_PASS"),
        "rule_id": RULE_ID,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "candidate_count": len(findings),
        "candidates": findings,
        "source_executed": False,
        "source_files_read": 0,
        "auto_fix": False,
        "auto_promoted": False,
        "owner_signed": False,
        "released_sdk_version_fix_verified": False,
        "independent_human_qa": False,
    }


def main() -> int:
    raw = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
    try:
        if not raw or len(raw) > MAX_SOURCE_BYTES:
            raise SourceRejected("empty or oversized stdin")
        result = inspect_mcp_empty_meta_source(
            raw.decode("utf-8-sig", errors="strict")
        )
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (UnicodeError, SourceRejected) as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__,
            "source_executed": False,
            "auto_promoted": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
