"""UCIE P13 first-party AST-only Decimal unbounded-context risk candidate.

Grounded in isolated Windows Python 3.15.0 regression: _pydecimal %
and divmod can exceed a bounded timeout at MAX_PREC, unlike ordinary
precision. Static finding is REVIEW_ONLY, not validated upstream PR fix.

Does not read user files, execute code, import untrusted modules, access
networks, modify runtime databases, schedule tasks, or approve rules.
"""
from __future__ import annotations

import ast
from hashlib import sha256
import json

SCHEMA = "UCIE_P13_DECIMAL_UNBOUNDED_AST_GUARD_V1"
MAX_BYTES = 20000
MAX_NODES = 800
MAX_FINDINGS = 20


class DecimalGuardError(ValueError):
    pass


def _dotted(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    if isinstance(node, ast.Attribute):
        return (*_dotted(node.value), node.attr)
    return ()


def _used_decimal(node: ast.AST, names: set[str]) -> bool:
    return isinstance(node, ast.Name) and node.id in names


def _risk_ops(expression: ast.AST, values: set[str]) -> list[tuple[str, int]]:
    # Bound traversal by the entire validated module node count.
    found = []
    for node in ast.walk(expression):
        if (isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Mod)
                and _used_decimal(node.left, values)):
            found.append(("MODULO", node.lineno))
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "divmod"
                and len(node.args) == 2
                and _used_decimal(node.args[0], values)):
            found.append(("DIVMOD", node.lineno))
        if (isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.FloorDiv)
                and _used_decimal(node.left, values)):
            found.append(("FLOORDIV_CONTROL", node.lineno))
    return found


def inspect_source(source_text: str) -> dict:
    """Detect only explicit first-party _pydecimal context patterns.

    The code never executes input. Dynamic aliases, nested control-flow,
    monkeypatching and unknown Decimal provenance are deliberately ignored.
    """
    if type(source_text) is not str:
        raise DecimalGuardError("UTF-8 Python source required")
    encoded = source_text.encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise DecimalGuardError("untrusted source exceeds bounded limit")
    try:
        tree = ast.parse(source_text, mode="exec")
    except (SyntaxError, RecursionError, ValueError) as exc:
        raise DecimalGuardError("invalid Python source") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_NODES:
        raise DecimalGuardError("untrusted AST node bound exceeded")

    modules: set[str] = set()
    dec_construct: set[str] = set()
    contexts: set[str] = set()
    max_prec: set[str] = set()
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for name in stmt.names:
                if name.name == "_pydecimal":
                    modules.add(name.asname or "_pydecimal")
        elif isinstance(stmt, ast.ImportFrom) and stmt.module == "_pydecimal":
            for alias in stmt.names:
                symbol = alias.asname or alias.name
                if alias.name == "Decimal":
                    dec_construct.add(symbol)
                elif alias.name == "localcontext":
                    contexts.add(symbol)
                elif alias.name == "MAX_PREC":
                    max_prec.add(symbol)

    def _is_member(node: ast.AST, member: str) -> bool:
        parts = _dotted(node)
        return any(parts == (mod, member) for mod in modules)

    def _maxprec(node: ast.AST) -> bool:
        return _is_member(node, "MAX_PREC") or _dotted(node) in {
            (name,) for name in max_prec
        }

    findings: list[dict] = []

    for block in ast.walk(tree):
        if not isinstance(block, (ast.With, ast.AsyncWith)):
            continue
        context_vars = set()
        for part in block.items:
            call = part.context_expr
            if (isinstance(call, ast.Call) and not call.args and not call.keywords
                    and (_is_member(call.func, "localcontext")
                         or _dotted(call.func) in {(n,) for n in contexts})
                    and isinstance(part.optional_vars, ast.Name)):
                context_vars.add(part.optional_vars.id)
        if not context_vars:
            continue

        huge_precision = False
        decimals: set[str] = set()
        for stmt in block.body:
            if (isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1):
                target = stmt.targets[0]
                if (isinstance(target, ast.Attribute)
                        and target.attr == "prec"
                        and isinstance(target.value, ast.Name)
                        and target.value.id in context_vars
                        and _maxprec(stmt.value)):
                    huge_precision = True
                if isinstance(target, ast.Name):
                    # Do not report a stale Decimal binding after reassignment.
                    # This static guard intentionally doesn't infer dynamic types.
                    decimals.discard(target.id)
                    if isinstance(stmt.value, ast.Call):
                        if (_is_member(stmt.value.func, "Decimal")
                                or _dotted(stmt.value.func) in {
                                    (name,) for name in dec_construct
                                }):
                            decimals.add(target.id)
            if not huge_precision or not decimals:
                continue
            if isinstance(stmt, (ast.Assign, ast.Expr, ast.Return, ast.AnnAssign)):
                for op, lineno in _risk_ops(stmt, decimals):
                    if len(findings) < MAX_FINDINGS:
                        findings.append({
                            "line": lineno,
                            "risk": op,
                            "status": "UCIE_FIRST_PARTY_REVIEW_CANDIDATE_NO_GO",
                            "host_regression_scope": "PYTHON_3_15_0_WIN_PYDECIMAL",
                            "source_fix_proven": False,
                        })

    findings.sort(key=lambda x: (x["line"], x["risk"]))
    return {
        "schema": SCHEMA,
        "status": "UCIE_P13_DECIMAL_REVIEW_ONLY",
        "source_sha256": sha256(encoded).hexdigest(),
        "findings": findings,
        "findings_count": len(findings),
        "exact_source_match_required": True,
        "analysis_only": True,
        "production_changes": False,
        "auto_promoted": False,
        "network_requests": 0,
        "database_writes": 0,
    }
