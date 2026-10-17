"""Stage 6 reproducible regression *plans* for fixed Stage 4 error families.

This module never downloads, compiles, imports, or executes upstream fixes.
Every case is synthetic test guidance; results remain NOT_EXECUTED.
"""
from __future__ import annotations

import hashlib
import json
import re

from .patterns import PatternError
from .rule_candidates import GUIDANCE

HEX64 = re.compile(r"[0-9a-f]{64}")
TEST_FAMILIES = {
    "PS_SSH_PATH_WITHOUT_RUNSPACE": (
        "Synthetic path construction without Runspace",
        "No unexpected exception when a Runspace is absent", "Windows"),
    "PS_FUZZY_GET_COMMAND_DUPLICATES": (
        "Overlapping exact and fuzzy command names",
        "Returned command identities are not unintentionally duplicated", "Windows"),
    "PS_RESOLVE_PATH_DOT_PREFIX": (
        "Dot-prefixed relative path with synthetic fixture tree",
        "Relative path semantics remain stable", "Windows"),
    "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO": (
        "Inert explicit Python -X options and an isolated feature-enabled runtime",
        "A supported interpreter reports remote debugging disabled with the hyphenated option, not with the misspelled underscored option", "Any"),
    "PY_SCANDIR_SHARED_ITERATOR_RACE": (
        "Synthetic parallel iterator ownership and close calls",
        "Iterator state is not corrupted by overlapping lifecycle events", "Any"),
    "PY_QSBR_THREADSTATE_SLOT_LEAK": (
        "Repeated synthetic thread-state lifecycle",
        "Allocated slot count returns to the documented baseline", "Any"),
    "PY_COMPREHENSION_COMPILER_ERROR_CLEANUP": (
        "Malformed synthetic comprehension parse and cleanup",
        "Parser/compiler failure retains exception state without leaked fixtures", "Any"),
    "PY_AST_REPR_FIELDS_LOOKUP": (
        "Synthetic AST with absent and renamed fields",
        "Representation handles documented missing-field behavior", "Any"),
    "PY_WEAKREF_FREE_THREADED_RACE": (
        "Synthetic concurrent weakref lifetime interleavings",
        "Weakref access and finalization preserve documented invariants", "Any"),
}


def create_regression_matrix(candidate_pack: object) -> dict:
    if (not isinstance(candidate_pack, dict)
            or candidate_pack.get("schema") != "UCIE_RULEPACK_PREVIEW_V1"
            or candidate_pack.get("signed") is not False
            or candidate_pack.get("published") is not False
            or candidate_pack.get("approval") is not False
            or candidate_pack.get("auto_promoted") is not False
            or candidate_pack.get("regressions_executed") != 0
            or not isinstance(candidate_pack.get("proposals"), list)):
        raise PatternError("invalid rulepack preview input")
    proposals = candidate_pack["proposals"]
    if len(proposals) > 40:
        raise PatternError("excessive candidate count")
    valid_digest = hashlib.sha256(json.dumps(
        proposals, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    if candidate_pack.get("digest_sha256") != valid_digest:
        raise PatternError("rulepack proposal fingerprint mismatch")
    cases, seen = [], set()
    fields = {"source", "canonical_pr_number", "evidence_fingerprint",
              "rule_code", "safe_fix_guidance", "regression_test_plan",
              "executable_command", "status", "required_gates"}
    for item in proposals:
        if not isinstance(item, dict) or set(item) != fields:
            raise PatternError("invalid regression source schema")
        rule = item["rule_code"]
        source, number = item["source"], item["canonical_pr_number"]
        if (rule not in TEST_FAMILIES
                or not isinstance(source, str)
                or source not in ("python/cpython", "PowerShell/PowerShell")
                or (rule.startswith("PY_") and source != "python/cpython")
                or (rule.startswith("PS_") and source != "PowerShell/PowerShell"
                    and not (rule == "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO"
                             and source == "python/cpython"))
                or type(number) is not int or number < 1
                or (source, number) in seen
                or not isinstance(item["evidence_fingerprint"], str)
                or not HEX64.fullmatch(item["evidence_fingerprint"])
                or item["status"] != "UNVERIFIED_CANDIDATE_ONLY"
                or item["executable_command"] is not None
                or item["safe_fix_guidance"] != GUIDANCE[rule][0]
                or item["regression_test_plan"] != GUIDANCE[rule][1]
                or not isinstance(item["required_gates"], dict)
                or set(item["required_gates"]) != {
                    "source_authenticated", "license_verified",
                    "security_review_passed", "independent_regression_passed",
                    "human_approved"}
                or any(s != "NOT_VERIFIED"
                       for s in item["required_gates"].values())):
            raise PatternError("unverified or forged regression candidate")
        seen.add((source, number))
        setup, expected, platform = TEST_FAMILIES[rule]
        cases.append({
            "case_id": f"{source}#{number}:{rule}",
            "source": source, "rule_code": rule,
            "evidence_fingerprint": item["evidence_fingerprint"],
            "fixture_design": setup,
            "expected_invariant": expected,
            "target_environment": platform,
            "negative_case": "An intentionally invalid or racing input",
            "independent_test_script": None,
            "actual_test_result": "NOT_EXECUTED",
            "independent_reviewer_signoff": "NOT_RECEIVED",
        })
    return {
        "schema": "UCIE_SYNTHETIC_REGRESSION_PLAN_V1",
        "candidate_count": len(cases), "cases": cases,
        "upstream_code_executed": False,
        "regressions_independently_reproduced": 0,
        "rulepack_signed": False,
        "production_approved": False,
        "persistent_writes": 0,
    }
