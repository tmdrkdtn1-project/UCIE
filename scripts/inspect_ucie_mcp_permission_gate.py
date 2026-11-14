"""UCIE-only *static* MCP startup permission-gate inspection.

Never imports make_server, runs MCP tools, reads credentials, prints
server source, modifies a file, inspects another project or contacts network.

The observed direct-import PermissionError happened before make_server
initialized its local server object. That does not establish runtime failure.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re

TARGET = Path(r"D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py")
EXPECTED_SHA256 = "83b58b68ad0c15a32991e03e82b3c309a5e045da1d4c9a4c8ca3101d8b010d8e"
MAX_FILE_SIZE = 512000
SAFE_ENV_NAME = re.compile(r"UCIE_[A-Z0-9_]{3,75}\Z")
SAFE_ERROR_CODE = re.compile(r"[A-Z][A-Z0-9_]{4,100}\Z")


class InspectionError(ValueError):
    pass


def _function_owner(tree, selected_line):
    functions = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.lineno <= selected_line <= (n.end_lineno or 0)
    ]
    if not functions:
        return None
    return min(functions, key=lambda n: (n.end_lineno or 0)-n.lineno)


def _call_name(expr):
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _call_name(expr.value)
        return f"{base}.{expr.attr}" if base else expr.attr
    return "OTHER"


def _env_keys_in_function(fn):
    keys = set()
    if fn is None:
        return []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name in (
                "os.getenv", "os.environ.get", "environ.get", "getenv"
            ) and node.args:
                first = node.args[0]
                if (isinstance(first, ast.Constant)
                        and type(first.value) is str
                        and SAFE_ENV_NAME.fullmatch(first.value)):
                    keys.add(first.value)
        elif isinstance(node, ast.Subscript):
            target = _call_name(node.value)
            key = node.slice
            if (target in ("os.environ", "environ")
                    and isinstance(key, ast.Constant)
                    and type(key.value) is str
                    and SAFE_ENV_NAME.fullmatch(key.value)):
                keys.add(key.value)
    return sorted(keys)


def _operator_gate_environment_metadata(fn, env):
    """Inspect environment aliases like 'e = os.environ' without values."""
    if fn is None:
        return {"alias_found": False, "keys": {}, "comparison": [],
                "required_literal_hint": "NOT_ESTABLISHED"}

    aliases = set()
    for stmt in fn.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        rhs = stmt.value
        origin = _call_name(rhs)
        if isinstance(rhs, ast.Call):
            call_name = _call_name(rhs.func)
            if call_name in ("os.environ.copy", "environ.copy"):
                origin = "os.environ"
            elif (call_name == "dict" and len(rhs.args) == 1
                  and _call_name(rhs.args[0]) in ("os.environ", "environ")):
                origin = "os.environ"
        if origin not in ("os.environ", "environ"):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        for target in targets:
            if isinstance(target, ast.Name):
                aliases.add(target.id)

    key_names = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        if (isinstance(func, ast.Attribute) and func.attr == "get"
                and isinstance(func.value, ast.Name)
                and func.value.id in aliases
                and isinstance(node.args[0], ast.Constant)
                and type(node.args[0].value) is str):
            key = node.args[0].value
            if SAFE_ENV_NAME.fullmatch(key):
                key_names.add(key)

    comparisons = []
    hints = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        for compare in ast.walk(node.test):
            if not isinstance(compare, ast.Compare):
                continue
            comparisons.extend(type(op).__name__ for op in compare.ops)
            for operand in (compare.left, *compare.comparators):
                if isinstance(operand, ast.Constant):
                    value = operand.value
                    if type(value) is str:
                        hints.add(value if value in ("1", "0", "true",
                                                     "false", "yes", "no")
                                  else "MASKED_TEXT_LITERAL")
                    elif value is None:
                        hints.add("NONE_LITERAL")
                    elif type(value) is bool:
                        hints.add("BOOLEAN_LITERAL")
                    else:
                        hints.add("OTHER_LITERAL")
    # Absence of the alias or matching UCIE key is not proof of no gate:
    # the source may use a more complex mapping or nonstandard names.
    return {
        "alias_found": bool(aliases),
        "alias_names": sorted(aliases)[:4],
        "keys": {name: name in env for name in sorted(key_names)},
        "comparison": sorted(set(comparisons))[:8],
        "required_literal_hint": (
            next(iter(hints)) if len(hints) == 1 else
            ("MULTIPLE_OR_UNKNOWN" if hints else "NOT_ESTABLISHED")
        ),
    }


def _gate_getter_binding_shape(fn):
    """Show the origin *shape* of e and its key; never approval values.

    This works even if e is NOT an os.environ alias and explicitly
    distinguishes unresolved origin from an environment source.
    """
    if fn is None:
        return {
            "e_binding_found": False,
            "e_binding_structure": [],
            "e_get_key_kinds": [],
            "e_get_ucie_keys_only": [],
        }

    def call_shape(expr):
        name = _call_name(expr)
        # Function names from this fixed UCIE-only guard are source structure,
        # but never print unreviewed identifiers that might encode credentials.
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,95}", name):
            return "OTHER_CALL"
        if re.search(r"(?i)(token|password|secret|credential|private|api.key)", name):
            return "SENSITIVE_NAME_MASKED"
        return name

    bindings = []
    for stmt in fn.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        if not any(isinstance(t, ast.Name) and t.id == "e" for t in targets):
            continue
        rhs = stmt.value
        calls = sorted({
            call_shape(node.func) for node in ast.walk(rhs)
            if isinstance(node, ast.Call)
        })[:10]
        bindings.append({
            "rhs_ast_type": type(rhs).__name__,
            "rhs_calls": calls,
            "references_os_environ": any(
                _call_name(node) in ("os.environ", "environ")
                for node in ast.walk(rhs)
                if isinstance(node, (ast.Name, ast.Attribute))
            ),
            "has_conditional": isinstance(rhs, (ast.IfExp, ast.BoolOp)),
        })

    key_kinds = []
    safe_ucie_keys = set()
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "e"
                and node.func.attr == "get"):
            continue
        if not node.args:
            key_kinds.append("NO_POSITIONAL_KEY")
            continue
        key = node.args[0]
        if isinstance(key, ast.Constant) and type(key.value) is str:
            if SAFE_ENV_NAME.fullmatch(key.value):
                key_kinds.append("UCIE_LITERAL_KEY")
                safe_ucie_keys.add(key.value)
            else:
                key_kinds.append("NON_UCIE_LITERAL_KEY_MASKED")
        elif isinstance(key, ast.Name):
            key_kinds.append("NAME_REFERENCE_KEY")
        else:
            key_kinds.append(type(key).__name__.upper() + "_KEY")

    return {
        "e_binding_found": bool(bindings),
        "e_binding_structure": bindings[:4],
        "e_get_key_kinds": sorted(set(key_kinds)),
        "e_get_ucie_keys_only": sorted(safe_ucie_keys),
    }


def analyze(source: str, env=None, error_line: int = 21,
            caller_line: int = 25) -> dict:
    """Return AST structure and environment presence bits only."""
    tree = ast.parse(source, filename="mcp_stdio_server.py")
    gate = _function_owner(tree, error_line)
    caller = _function_owner(tree, caller_line)
    factories = [
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
        and n.name == "make_server"
    ]
    if len(factories) != 1:
        raise InspectionError("UCIE make_server shape differs; stop")
    factory = factories[0]

    initial_calls = []
    for stmt in factory.body:
        if stmt.lineno > 30:
            break
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            initial_calls.append(_call_name(stmt.value.func))
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            if isinstance(stmt.value, ast.Call):
                initial_calls.append("assignment:" + _call_name(stmt.value.func))

    raised = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue
        call = node.exc
        if (not isinstance(call, ast.Call)
                or _call_name(call.func) != "PermissionError"):
            continue
        owner = _function_owner(tree, node.lineno)
        entry = {
            "line": node.lineno,
            "function": owner.name if owner else None,
        }
        if call.args and isinstance(call.args[0], ast.Constant):
            literal = call.args[0].value
            if type(literal) is str and SAFE_ERROR_CODE.fullmatch(literal):
                entry["symbolic_error_code"] = literal
        raised.append(entry)

    # Expose structure only, never literal arguments, file paths, secrets,
    # auth tokens, or source expressions. This distinguishes an unconditional
    # operator HOLD from a branch that an authorized launcher may satisfy.
    gate_statements = ([type(stmt).__name__ for stmt in gate.body[:16]]
                       if gate is not None else [])
    guard_calls = sorted({
        _call_name(node.func)
        for node in ast.walk(gate) if isinstance(node, ast.Call)
    })[:20] if gate is not None else []
    has_branch = (any(isinstance(node, (ast.If, ast.IfExp, ast.Match,
                    ast.Try, ast.For, ast.While, ast.With))
                    for node in ast.walk(gate)) if gate else False)
    has_early_return = (any(isinstance(node, ast.Return)
                            for node in ast.walk(gate)) if gate else False)
    direct_raise_only = (gate is not None and len(gate.body) == 1
                         and isinstance(gate.body[0], ast.Raise))

    env_keys = set(_env_keys_in_function(gate))
    env_keys.update(_env_keys_in_function(factory))
    if env is None:
        env = os.environ
    operator_gate = _operator_gate_environment_metadata(gate, env)
    getter_origin = _gate_getter_binding_shape(gate)
    return {
        "status": "UCIE_MCP_EARLY_PERMISSION_GATE_STATIC_OBSERVED",
        "guard_line": error_line,
        "guard_function": gate.name if gate else None,
        "guard_function_differs_from_factory": (
            gate is not None and gate is not factory
        ),
        "caller_line": caller_line,
        "caller_function": caller.name if caller else None,
        "factory_initial_calls": initial_calls[:8],
        "guard_top_level_statement_types": gate_statements,
        "guard_callable_names_only": guard_calls,
        "guard_has_condition_or_control_flow": has_branch,
        "guard_has_return": has_early_return,
        "guard_is_single_unconditional_raise": direct_raise_only,
        "permission_raise_sites": raised[:8],
        "ucie_env_key_presence_only": {
            name: name in env for name in sorted(env_keys)
        },
        "operator_gate_environment_alias_detected": operator_gate["alias_found"],
        "operator_gate_environment_alias_names": operator_gate["alias_names"],
        "operator_gate_ucie_variable_presence_only": operator_gate["keys"],
        "operator_gate_comparison_operator_types": operator_gate["comparison"],
        "operator_gate_comparison_literal_hint": operator_gate["required_literal_hint"],
        "operator_gate_e_binding_found": getter_origin["e_binding_found"],
        "operator_gate_e_binding_structure": getter_origin["e_binding_structure"],
        "operator_gate_e_get_key_kinds": getter_origin["e_get_key_kinds"],
        "operator_gate_e_get_ucie_keys_only": getter_origin["e_get_ucie_keys_only"],
        "executed_make_server": False,
        "read_credentials_or_secret_values": False,
        "server_restarted": False,
        "tunnel_modified": False,
    }


def main() -> int:
    try:
        if not TARGET.is_file() or TARGET.is_symlink():
            raise InspectionError("exact UCIE MCP server file unavailable")
        raw = TARGET.read_bytes()
        if not raw or len(raw) > MAX_FILE_SIZE or b"\x00" in raw:
            raise InspectionError("unsupported UCIE MCP source format")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != EXPECTED_SHA256:
            raise InspectionError("server source changed; do not infer old guard")
        result = analyze(raw.decode("utf-8"))
        result["server_sha256_matches_last_owner_observation"] = True
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 0
    except (InspectionError, SyntaxError, UnicodeError, OSError) as exc:
        print(json.dumps({
            "status": "UCIE_MCP_GATE_STATIC_INSPECTION_NOT_PROVEN",
            "reason": type(exc).__name__,
            "server_restarted": False,
            "tunnel_modified": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
