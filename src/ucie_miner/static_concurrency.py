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
        # Only literal constants are simplified. Never eval() conditions,
        # resolve symbols, import modules or execute the supplied source.
        if (isinstance(node, ast.If) and isinstance(node.test, ast.Constant)
                and type(node.test.value) in (bool, int)
                and node.test.value in (0, 1)):
            chosen = node.body if node.test.value else node.orelse
            pending.extend(reversed(chosen))
            continue
        pending.extend(reversed(list(ast.iter_child_nodes(node))))


def _scandir_function(expr, aliases):
    return (
        (isinstance(expr, ast.Attribute)
         and isinstance(expr.value, ast.Name)
         and expr.value.id == "os" and expr.attr == "scandir")
        or (isinstance(expr, ast.Name) and expr.id in aliases)
    )


def _raw_scandir(expr, aliases):
    return isinstance(expr, ast.Call) and _scandir_function(expr.func, aliases)


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
            if any(_name_used(statement, name)
                   for statement in _scope_nodes(node)):
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
    # Collect only scopes reachable under strictly literal if-branches.
    # A function declared solely inside `if False` must not be scanned.
    scopes = [parsed]
    inherited = {}
    findings = []
    seen = set()
    for scope in scopes:
        statements = list(_scope_nodes(scope))
        if len(statements) > MAX_AST_NODES:
            raise CandidateScanError("scope complexity exceeded")
        scopes.extend(n for n in statements
                      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        # Read lexical events in order rather than pre-scanning aliases across
        # the entire scope. An alias created later must NOT retroactively
        # turn an earlier call into a candidate.
        ordered = sorted(
            statements,
            key=lambda n: (getattr(n, "lineno", 0),
                           getattr(n, "col_offset", 0),
                           int(isinstance(n, ast.Call))),
        )
        state = dict(inherited.pop(id(scope), {}))
        closure_cache = {}
        for node in ordered:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inherited[id(node)] = {name: kind for name, kind in
                                       state.items() if kind == "scandir_fn"}
                continue
            if isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module == "os":
                    for imported in node.names:
                        name = imported.asname or imported.name
                        state[name] = ("scandir_fn" if imported.name == "scandir"
                                       else "other")
                else:
                    for imported in node.names:
                        state[imported.asname or imported.name] = "other"
                continue
            if isinstance(node, ast.Import):
                for imported in node.names:
                    state[imported.asname or imported.name.split(".")[0]] = "other"
                continue
            assigned = {}
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                if isinstance(node, ast.Assign):
                    names = set().union(*(_assigned_names(x) for x in node.targets))
                else:
                    names = _assigned_names(node.target)
                value = node.value
                if _scandir_function(value, {k for k, v in state.items()
                                              if v == "scandir_fn"}):
                    kind = "scandir_fn"
                elif _raw_scandir(value, {k for k, v in state.items()
                                           if v == "scandir_fn"}):
                    kind = "raw"
                elif isinstance(value, ast.Name) and state.get(value.id) == "raw":
                    kind = "raw"  # single-scope iterator variable alias
                else:
                    kind = "other"
                assigned = {name: kind for name in names}
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                assigned = {name: "other" for name in _assigned_names(node.target)}
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for context in node.items:
                    raw = _raw_scandir(context.context_expr,
                                       {k for k,v in state.items()
                                        if v == "scandir_fn"})
                    for name in _assigned_names(context.optional_vars):
                        assigned[name] = "raw" if raw else "other"
            elif isinstance(node, ast.Delete):
                for target in node.targets:
                    assigned.update({name: "other"
                                     for name in _assigned_names(target)})
            state.update(assigned)
            if not isinstance(node, ast.Call):
                continue
            for name, kind in list(state.items()):
                if kind != "raw":
                    continue
                closures = closure_cache.setdefault(
                    name, _closures(statements, name))
                boundary = _thread_boundary(node, name, closures)
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
