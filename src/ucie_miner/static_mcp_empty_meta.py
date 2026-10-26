"""UCIE sixth candidate: unconditional MCP JSON-RPC empty metadata on the wire.

Approved public source: modelcontextprotocol/python-sdk PR #3628.
Pure bounded Python AST analysis only. Never executes analyzed code,
opens files, contacts servers, signs releases or approves promotion.
"""
from __future__ import annotations
import ast
import hashlib
import json
import sys

RULE_ID = "MCP_JSONRPC_UNCONDITIONAL_EMPTY_META"
UPSTREAM = "https://github.com/modelcontextprotocol/python-sdk/pull/3628"
UPSTREAM_MERGE = "0b2fd3ea60efb16b349e8c887cf91bf2f9f773fc"
MAX_SOURCE_BYTES = 131072
MAX_AST_NODES = 20000
MAX_FINDINGS = 20


class SixthCandidateError(ValueError):
    pass


def _scope(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> ast.AST | None:
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef,
                             ast.Lambda)):
            return node
    return None


def _meta_assign(node: ast.AST) -> bool:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return False
    target = node.targets[0]
    return (
        isinstance(target, ast.Subscript)
        and isinstance(target.value, ast.Name)
        and target.value.id == "out_params"
        and isinstance(target.slice, ast.Constant)
        and target.slice.value == "_meta"
        and isinstance(node.value, ast.Name)
        and node.value.id == "out_meta"
    )


def _guarded_by_nonempty_meta(node: ast.AST,
                              parents: dict[ast.AST, ast.AST],
                              function: ast.AST) -> bool:
    child = node
    while child in parents and parents[child] is not function:
        parent = parents[child]
        # Recognize only the upstream fix's positive if out_meta guard,
        # not arbitrary boolean conditions.
        if (isinstance(parent, ast.If)
                and isinstance(parent.test, ast.Name)
                and parent.test.id == "out_meta"
                and child in parent.body):
            return True
        child = parent
    return False


def _request_sink(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "JSONRPCRequest"
        and any(
            kw.arg == "params"
            and isinstance(kw.value, ast.Name)
            and kw.value.id == "out_params"
            for kw in node.keywords
        )
    )


def inspect_mcp_empty_meta_source(source: str) -> dict:
    """Report possible legacy incompatibility; never a runtime PASS."""
    if type(source) is not str:
        raise SixthCandidateError("source must be an inert Python string")
    raw = source.encode("utf-8", "surrogatepass")
    if not raw or len(raw) > MAX_SOURCE_BYTES:
        raise SixthCandidateError("empty or oversized input")
    try:
        tree = ast.parse(source, filename="<ucie-mcp-sixth-inert>")
        nodes = list(ast.walk(tree))
    except (SyntaxError, MemoryError, RecursionError, ValueError) as exc:
        raise SixthCandidateError("invalid source syntax or AST") from exc
    if len(nodes) > MAX_AST_NODES:
        raise SixthCandidateError("AST size limit exceeded")
    parents = {child: parent for parent in nodes
               for child in ast.iter_child_nodes(parent)}
    findings = []
    for function in nodes:
        if not isinstance(function, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        if function.name != "send_raw_request":
            continue
        local = [node for node in ast.walk(function)
                 if node is not function and _scope(node, parents) is function]
        # Both parts of the upstream failure must occur in the same scope.
        if not any(_request_sink(node) for node in local):
            continue
        for node in local:
            if (not _meta_assign(node)
                    or _guarded_by_nonempty_meta(node, parents, function)):
                continue
            findings.append({
                "rule_id": RULE_ID,
                "line": node.lineno, "column": node.col_offset,
                "method": function.name,
                "pattern": "UNGUARDED_OUT_PARAMS_META_ASSIGNMENT_WITH_JSONRPC_SINK",
                "public_evidence": UPSTREAM,
                "safe_guidance": (
                    "Only attach out_params['_meta'] if out_meta is nonempty; "
                    "omit params entirely when resulting dict is empty. "
                    "Preserve caller metadata, progress and tracing."
                ),
                "manual_review_required": True,
                "legacy_peer_failure_confirmed_for_this_input": False,
            })
            if len(findings) > MAX_FINDINGS:
                raise SixthCandidateError("finding limit exceeded")
    findings.sort(key=lambda f: (f["line"], f["column"]))
    return {
        "schema": "UCIE_SIXTH_MCP_EMPTY_META_STATIC_CANDIDATE_V1",
        "status": ("STATIC_CANDIDATE_REVIEW_REQUIRED" if findings
                   else "NO_MATCH_NOT_A_SAFETY_PASS"),
        "rule_id": RULE_ID,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "candidate_count": len(findings), "candidates": findings,
        "source_executed": False, "source_files_read": 0,
        "external_requests": 0, "persistent_writes": 0,
        "auto_fix": False, "auto_promoted": False, "owner_signed": False,
        "independent_qa_verified": False,
    }


def main() -> int:
    """Read only caller-provided, bounded UTF-8 stdin."""
    raw = sys.stdin.buffer.read(MAX_SOURCE_BYTES + 1)
    try:
        if not raw or len(raw) > MAX_SOURCE_BYTES:
            raise SixthCandidateError("stdin outside size bounds")
        result = inspect_mcp_empty_meta_source(
            raw.decode("utf-8-sig", errors="strict"))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (SixthCandidateError, UnicodeError) as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED", "reason": type(exc).__name__,
            "source_executed": False, "auto_promoted": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
