"""Static, narrow audit of UCIE's OWN pinned scandir recipe only.

No customer files, arbitrary paths, imported third-party source or runtime scans.
An AST observation does not establish native runtime or independent QA.
"""
from __future__ import annotations

import ast
from hashlib import sha256
import inspect
import json
import textwrap

from .b3_documented_scandir_315_delta_v01 import (
    PYTHON_CASE, evaluate_documented_scandir_delta,
)
from .skillbook_scandir_recipe_v01 import bounded_regular_file_names

SCHEMA = "UCIE_B3_FIRST_PARTY_SCANDIR_CALLSITE_AUDIT_V01"


class CallsiteAuditError(ValueError):
    pass


def audit_trusted_scandir_recipe() -> dict:
    """Observe only the installed UCIE first-party function's direct AST call.

    Any source unavailable / aliases / unknown call argument -> HOLD rather
    than 'not affected'. No arbitrary code or paths accepted.
    """
    if (bounded_regular_file_names.__module__
            != "ucie_miner.skillbook_scandir_recipe_v01"):
        raise CallsiteAuditError("TRUSTED_FUNCTION_IDENTITY_DRIFT")
    try:
        source = textwrap.dedent(inspect.getsource(bounded_regular_file_names))
        tree = ast.parse(source)
    except (OSError, TypeError, IndentationError, SyntaxError) as exc:
        raise CallsiteAuditError("TRUSTED_CALLSITE_SOURCE_NOT_INSPECTABLE") from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise CallsiteAuditError("UNEXPECTED_FUNCTION_SHAPE")
    func = tree.body[0]
    if func.name != "bounded_regular_file_names":
        raise CallsiteAuditError("TRUSTED_FUNCTION_NAME_DRIFT")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "scandir"]
    inspected = (len(calls) == 1
                 and isinstance(calls[0].func.value, ast.Name)
                 and calls[0].func.value.id == "os"
                 and len(calls[0].args) == 1
                 and not calls[0].keywords)
    safe_explicit_argument = (
        inspected and isinstance(calls[0].args[0], ast.Name)
        and calls[0].args[0].id == "directory"
    )
    # No claim on unrelated customer call sites; this is one UCIE function.
    delta = evaluate_documented_scandir_delta(
        PYTHON_CASE, proposed_runtime="3.15",
        uses_negative_one=False if safe_explicit_argument else None)
    if (delta["retest_candidate"] is not False
            or delta["customer_runtime_version_verified"] is not False):
        raise CallsiteAuditError("B3_TRUTH_GATE_DRIFT")
    report = {
        "schema": SCHEMA,
        "case_id": PYTHON_CASE,
        "capsule_id": delta["capsule_id"],
        "function_module": bounded_regular_file_names.__module__,
        "function_name": func.name,
        "source_sha256": sha256(source.encode("utf-8")).hexdigest(),
        "direct_os_scandir_calls": len(calls),
        "expected_direct_call_shape": inspected,
        "explicit_directory_argument": bool(safe_explicit_argument),
        "negative_fd_risk_for_this_static_callsite": (
            "NOT_INDICATED_BY_DIRECT_AST" if safe_explicit_argument
            else "UNKNOWN_HOLD"),
        "other_callers_and_customer_code": "NOT_INSPECTED",
        "native_python315_behavior": "SEPARATE_CI_TEST",
        "actual_runtime_compatibility": "NOT_VERIFIED",
        "automatic_fix_applied": False,
        "retest_executed_here": False,
        "independent_qa": "NOT_VERIFIED",
        "rights_approved": False,
        "release_approved": False,
    }
    report["receipt_sha256"] = sha256(json.dumps(
        report, sort_keys=True, ensure_ascii=True,
        separators=(",", ":")).encode("ascii")).hexdigest()
    return report
