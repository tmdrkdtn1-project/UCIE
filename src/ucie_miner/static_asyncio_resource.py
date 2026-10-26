"""Candidate-only inert detector for CPython asyncio pre-transport resource leaks.

Approved upstream: python/cpython PR #156401, merged 2026-09-05.
Do not confuse this detection with an installed Python version's behavior.
No source execution, file reads, network, auto-fix, rule signing, or promotion.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys

RULE_ID = "PY_ASYNCIO_PROTOCOL_FACTORY_PRETRANSPORT_LEAK"
EVIDENCE = "https://github.com/python/cpython/pull/156401"
UPSTREAM_MERGE = "ba4a0790aa8438ccd847e86910f71c9823849d05"
MAX_BYTES = 131072
MAX_NODES = 20000
MAX_FINDINGS = 20

# Narrowly reflect the *actual* three upstream before/after call sites.
# _make_* ownership begins only after protocol_factory returns.
TARGETS = {
    "create_datagram_endpoint": ("_make_datagram_transport", "sock"),
    "connect_read_pipe": ("_make_read_pipe_transport", "pipe"),
    "connect_write_pipe": ("_make_write_pipe_transport", "pipe"),
}


class CandidateScanError(ValueError):
    pass


def _is_protocol_factory(call: object) -> bool:
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == "protocol_factory"
        and not call.args and not call.keywords
    )


def _constructs_transport(call: object, factory: str,
                          resource: str, protocol: str) -> bool:
    return (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == factory
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "self"
        and len(call.args) >= 2
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == resource
        and isinstance(call.args[1], ast.Name)
        and call.args[1].id == protocol
    )


def _catches_all_errors(exc: ast.ExceptHandler) -> bool:
    # 'except Exception' misses BaseException subclasses (including
    # KeyboardInterrupt/SystemExit). Conservative: never label them safe.
    return exc.type is None or (
        isinstance(exc.type, ast.Name) and exc.type.id == "BaseException"
    )


def _first_action_closes(statements: list[ast.stmt], resource: str) -> bool:
    """Require an unconditional top-level close before any other action.

    A close inside 'if False', another function, or after a return/raise is
    not evidence of guaranteed cleanup on the factory-exception path.
    """
    for statement in statements:
        if isinstance(statement, ast.Pass):
            continue
        if (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)):
            continue  # docstring, if present
        if not isinstance(statement, ast.Expr):
            return False
        call = statement.value
        return (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "close"
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == resource
            and not call.args and not call.keywords
        )
    return False


def _try_branch(node: ast.AST, block: ast.Try | ast.TryStar,
                parents: dict) -> str | None:
    """Determine which part of a try owns this call, without executing code."""
    child = node
    while (parent := parents.get(child)) is not None:
        if parent is block:
            if child in block.body:
                return "body"
            if child in block.handlers:
                return "handler"
            if child in block.orelse:
                return "else"
            if child in block.finalbody:
                return "finally"
            return None
        child = parent
    return None


def _protected_by_cleanup(assign: ast.Assign, ancestors: dict,
                          resource: str) -> bool:
    current = ancestors.get(assign)
    while current is not None:
        if isinstance(current, (ast.Try, ast.TryStar)):
            branch = _try_branch(assign, current, ancestors)
            if branch != "finally" and _first_action_closes(
                    current.finalbody, resource):
                return True
            # A try does NOT catch errors raised inside its own except/else
            # handlers. In Python 3.11+ except* does not cover every plain
            # BaseException, so use only ordinary try handlers.
            if branch == "body" and isinstance(current, ast.Try) and any(
                    _catches_all_errors(handler)
                    and _first_action_closes(handler.body, resource)
                    for handler in current.handlers):
                return True
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef,
                                ast.Lambda)):
            return False
        current = ancestors.get(current)
    return False


def inspect_asyncio_protocol_factory_source(source: str) -> dict:
    """Only report the upstream-shape candidate. No runtime safety verdict."""
    if type(source) is not str:
        raise CandidateScanError("source must be a literal Python string")
    data = source.encode("utf-8", errors="surrogatepass")
    if not data or len(data) > MAX_BYTES:
        raise CandidateScanError("empty or oversized inert source")
    try:
        tree = ast.parse(source, filename="<ucie-fifth-inert>", mode="exec")
        nodes = list(ast.walk(tree))
    except (SyntaxError, ValueError, MemoryError, RecursionError) as exc:
        raise CandidateScanError("invalid or too-deep Python AST") from exc
    if len(nodes) > MAX_NODES:
        raise CandidateScanError("AST node bound exceeded")

    parents = {child: parent for parent in nodes
               for child in ast.iter_child_nodes(parent)}
    findings = []
    for fn in nodes:
        if not isinstance(fn, ast.AsyncFunctionDef) or fn.name not in TARGETS:
            continue
        factory, resource = TARGETS[fn.name]

        # Scope fence: do not attribute another nested function's code
        # to this lifecycle method. The functions in upstream are methods.
        local = [n for n in ast.walk(fn)
                 if n is not fn and not any(
                     isinstance(parent, (ast.FunctionDef,
                                         ast.AsyncFunctionDef,
                                         ast.Lambda))
                     for parent in _ancestors_until(n, parents, fn))]
        constructors = [
            c for c in local if
            _constructs_transport(c, factory, resource, "protocol")
        ]
        for node in local:
            if not (isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "protocol"
                    and _is_protocol_factory(node.value)):
                continue
            if not any(c.lineno > node.lineno for c in constructors):
                continue
            if _protected_by_cleanup(node, parents, resource):
                continue
            findings.append({
                "rule_id": RULE_ID,
                "line": node.lineno,
                "column": node.col_offset,
                "function": fn.name,
                "resource": resource,
                "risk": "PROTOCOL_FACTORY_RAISES_BEFORE_TRANSPORT_OWNS_RESOURCE",
                "public_evidence": EVIDENCE,
                "suggested_review": (
                    "If protocol_factory raises before transport creation, "
                    "close the acquired " + resource +
                    " in an exception handler and re-raise; check ownership."
                ),
                "runtime_bug_confirmed_for_input": False,
            })
            if len(findings) > MAX_FINDINGS:
                raise CandidateScanError("finding bound exceeded")

    findings.sort(key=lambda x: (x["line"], x["column"], x["function"]))
    return {
        "schema": "UCIE_FIFTH_ASYNCIO_RESOURCE_CANDIDATE_V1",
        "status": ("STATIC_CANDIDATE_REVIEW_REQUIRED" if findings
                   else "NO_PATTERN_DETECTED_NOT_A_SAFETY_PASS"),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "rule_id": RULE_ID,
        "candidate_count": len(findings),
        "candidates": findings,
        "source_executed": False,
        "source_files_read": 0,
        "persistent_writes": 0,
        "auto_fix": False,
        "auto_promoted": False,
        "owner_signed": False,
        "released_python_version_fix_coverage_verified": False,
        "independent_human_qa": False,
    }


def _ancestors_until(node: ast.AST, parents: dict,
                     stop: ast.AST):
    parent = parents.get(node)
    while parent is not None and parent is not stop:
        yield parent
        parent = parents.get(parent)


def main() -> int:
    """Read ONLY explicit stdin, bounded; print metadata without source."""
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    try:
        if not raw or len(raw) > MAX_BYTES:
            raise CandidateScanError("source length outside bound")
        result = inspect_asyncio_protocol_factory_source(
            raw.decode("utf-8-sig", errors="strict"))
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (CandidateScanError, UnicodeError) as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__,
            "source_executed": False,
            "auto_promoted": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
