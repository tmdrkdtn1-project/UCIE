"""Stage 5/6: narrow, offline Python AST detector for raw scandir thread sharing.

Only parses a supplied string. Never reads files, imports/analyzes imported
modules, evaluates AST, executes snippets, downloads code, or writes a DB.
Findings are deliberately conservative human-review *candidates*, not proofs.
"""
from __future__ import annotations

import ast
import hashlib

MAX_SOURCE_BYTES = 131072
MAX_AST_NODES = 10000
MAX_FINDINGS = 100
PATTERN_CODE = "PY_SCANDIR_SHARED_ITERATOR_RACE"
PUBLIC_EVIDENCE = "https://github.com/python/cpython/pull/153462"


class CandidateScanError(ValueError):
    """Invalid or oversized inert input; never interpret as a PASS."""


def _scope_nodes(scope):
    """Walk statements in a single lexical scope, excluding nested scopes."""
    pending = list(reversed(scope.body))
    while pending:
        node = pending.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Lambda)):
            continue
        pending.extend(reversed(list(ast.iter_child_nodes(node))))


def _raw_scandir(expr):
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Attribute)
        and isinstance(expr.func.value, ast.Name)
        and expr.func.value.id == "os"
        and expr.func.attr == "scandir"
    )


def _assigned_names(node):
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        found = set()
        for child in node.elts:
            found.update(_assigned_names(child))
        return found
    return set()


def _name_used(expr, name):
    return any(isinstance(n, ast.Name) and n.id == name
               and isinstance(n.ctx, ast.Load)
               for n in ast.walk(expr))


def _closures(scope_nodes, name):
    result = set()
    for node in scope_nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # A nested function accessing the iterator can be submitted with
            # no explicit iterator argument. This remains a *candidate* only.
            if any(_name_used(statement, name) for statement in node.body):
                result.add((node.name, node.lineno))
    return result


def _thread_boundary(call, name, closures):
    func = call.func
    if (isinstance(func, ast.Attribute)
            and func.attr in ("submit", "map")):
        if any(_name_used(arg, name) for arg in call.args[1:]):
            return "EXECUTOR_ARGUMENT"
        if any(_name_used(kw.value, name) for kw in call.keywords):
            return "EXECUTOR_KEYWORD"
        if call.args and isinstance(call.args[0], ast.Name):
            if any(call.args[0].id == fn and defined_at <= call.lineno
                   for fn, defined_at in closures):
                return "EXECUTOR_CAPTURED_CLOSURE"
    if (isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id == "threading"
            and func.attr == "Thread"):
        for kw in call.keywords:
            if kw.arg in ("args", "kwargs") and _name_used(kw.value, name):
                return "THREAD_ARGUMENT"
        target = next((kw.value for kw in call.keywords if kw.arg == "target"),
                      None)
        if isinstance(target, ast.Name):
            if any(target.id == fn and defined_at <= call.lineno
                   for fn, defined_at in closures):
                return "THREAD_CAPTURED_CLOSURE"
    return None


def inspect_python_scandir_source(source: str) -> dict:
    """Return bounded evidence-linked findings, never automatic approvals."""
    if not isinstance(source, str):
        raise CandidateScanError("source must be inert Python text")
    if not source or len(source.encode("utf-8", errors="surrogatepass")) > MAX_SOURCE_BYTES:
        raise CandidateScanError("empty or oversized source")
    try:
        parsed = ast.parse(source, filename="<ucie-candidate>", mode="exec")
        all_nodes = list(ast.walk(parsed))
    except (SyntaxError, RecursionError, ValueError, MemoryError) as exc:
        raise CandidateScanError("invalid or excessively nested Python source") from exc
    if len(all_nodes) > MAX_AST_NODES:
        raise CandidateScanError("AST complexity limit exceeded")
    scopes = [parsed] + [n for n in all_nodes
                         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    findings = []
    seen = set()
    for scope in scopes:
        statements = list(_scope_nodes(scope))
        if len(statements) > MAX_AST_NODES:
            raise CandidateScanError("scope complexity exceeded")
        iterator_names = {}
        for node in statements:
            if isinstance(node, ast.Assign) and _raw_scandir(node.value):
                for target in node.targets:
                    for name in _assigned_names(target):
                        iterator_names.setdefault(name, []).append(node.lineno)
            elif isinstance(node, ast.AnnAssign) and _raw_scandir(node.value):
                for name in _assigned_names(node.target):
                    iterator_names.setdefault(name, []).append(node.lineno)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for context in node.items:
                    if _raw_scandir(context.context_expr):
                        for name in _assigned_names(context.optional_vars):
                            iterator_names.setdefault(name, []).append(node.lineno)
        if not iterator_names:
            continue
        for node in statements:
            if not isinstance(node, ast.Call):
                continue
            for name, declarations in iterator_names.items():
                if not any(declared_at <= node.lineno for declared_at in declarations):
                    continue
                boundary = _thread_boundary(node, name,
                                            _closures(statements, name))
                if boundary is None:
                    continue
                key = (getattr(scope, "lineno", 0), node.lineno, name,
                       boundary)
                if key in seen:
                    continue
                seen.add(key)
                if len(findings) >= MAX_FINDINGS:
                    raise CandidateScanError("too many candidate findings")
                findings.append({
                    "pattern_code": PATTERN_CODE,
                    "line": node.lineno,
                    "column": node.col_offset,
                    "iterator_binding": name,
                    "thread_boundary": boundary,
                    "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
                    "safe_fix_guidance": (
                        "Avoid sharing raw os.scandir between threads; use a "
                        "single owned lock across next() and close()."
                    ),
                    "public_evidence": PUBLIC_EVIDENCE,
                    "runtime_bug_reproduced": False,
                })
    findings.sort(key=lambda f: (f["line"], f["column"],
                                 f["iterator_binding"], f["thread_boundary"]))
    return {
        "schema": "UCIE_PYTHON_SCANDIR_STATIC_CANDIDATES_V1",
        "source_sha256": hashlib.sha256(source.encode(
            "utf-8", errors="surrogatepass")).hexdigest(),
        "findings": findings,
        "finding_count": len(findings),
        "parser_executed_supplied_code": False,
        "confidence": "HUMAN_REVIEW_REQUIRED",
        "approved_rules": 0,
        "source_files_read": 0,
        "persistent_writes": 0,
        "production_approved": False,
    }
