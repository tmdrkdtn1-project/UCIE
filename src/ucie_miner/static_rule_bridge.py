"""Stage 5 static findings -> Stage 6 non-executable regression/Rulepack proposals.

Bounded, in-memory, read-only and fail-closed. All source text and scanner
receipts are untrusted, even when their hashes appear consistent.
Matching pinned public PR metadata is NOT proof of a source-code review.
"""
from __future__ import annotations

import hashlib
import json
import re

from .merge_snapshot import load_merge_snapshot
from .patterns import PatternError
from .regression_plans import TEST_FAMILIES, create_regression_matrix
from .review import load_manifest
from .rule_candidates import GUIDANCE, REQUIRED_GATES

SHA256 = re.compile(r"[0-9a-f]{64}")
SHA40 = re.compile(r"[0-9a-f]{40}")
SOURCE_BINDINGS = {
    "PY_SCANDIR_SHARED_ITERATOR_RACE": ("python/cpython", 153462),
    "PS_FUZZY_GET_COMMAND_DUPLICATES": ("PowerShell/PowerShell", 28042),
    "PS_RESOLVE_PATH_DOT_PREFIX": ("PowerShell/PowerShell", 28087),
}
SCAN_SCHEMAS = {
    "UCIE_PYTHON_SCANDIR_STATIC_CANDIDATES_V1": "python",
    "UCIE_POWERSHELL_STATIC_CANDIDATES_V1": "powershell",
}
PY_FIELDS = {"pattern_code", "line", "column", "iterator_binding",
             "thread_boundary", "confidence", "safe_fix_guidance",
             "public_evidence", "runtime_bug_reproduced"}
PS_FIELDS = {"pattern_code", "line", "column", "confidence",
             "safe_fix_guidance", "public_evidence", "runtime_bug_reproduced"}
PY_BOUNDARIES = {"EXECUTOR_ARGUMENT", "EXECUTOR_KEYWORD",
                 "EXECUTOR_CAPTURED_CLOSURE", "THREAD_ARGUMENT",
                 "THREAD_CAPTURED_CLOSURE"}
SCANNER_GUIDANCE = {
    "PY_SCANDIR_SHARED_ITERATOR_RACE": (
        "Avoid sharing raw os.scandir between threads; use a "
        "single owned lock across next() and close()."),
    "PS_FUZZY_GET_COMMAND_DUPLICATES": (
        "Inspect fuzzy matches for duplicate Name/CommandType/Source "
        "identities before using results"),
    "PS_RESOLVE_PATH_DOT_PREFIX": (
        "Review dot-prefixed relative paths and use an anchored "
        "base-directory conversion if needed"),
}
MAX_FINDINGS = 100


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=True,
        separators=(",", ":")).encode("ascii")).hexdigest()


def _check_receipt(scan):
    required = {"schema", "source_sha256", "findings", "finding_count",
                "parser_executed_supplied_code", "confidence", "approved_rules",
                "source_files_read", "persistent_writes",
                "production_approved"}
    if (not isinstance(scan, dict) or set(scan) != required
            or scan["schema"] not in SCAN_SCHEMAS
            or not isinstance(scan["source_sha256"], str)
            or not SHA256.fullmatch(scan["source_sha256"])
            or not isinstance(scan["findings"], list)
            or len(scan["findings"]) > MAX_FINDINGS
            or type(scan["finding_count"]) is not int
            or scan["finding_count"] != len(scan["findings"])
            or scan["parser_executed_supplied_code"] is not False
            or scan["confidence"] != "HUMAN_REVIEW_REQUIRED"
            or scan["approved_rules"] != 0
            or scan["source_files_read"] != 0
            or scan["persistent_writes"] != 0
            or scan["production_approved"] is not False):
        raise PatternError("unsafe or malformed static-scan metadata")
    language = SCAN_SCHEMAS[scan["schema"]]
    seen = set()
    for item in scan["findings"]:
        if (not isinstance(item, dict)
                or set(item) != (PY_FIELDS if language == "python"
                                  else PS_FIELDS)):
            raise PatternError("invalid static-finding fields")
        code = item["pattern_code"]
        if (code not in SOURCE_BINDINGS
                or (language == "python") != code.startswith("PY_")
                or type(item["line"]) is not int
                or type(item["column"]) is not int
                or not 1 <= item["line"] <= 1_000_000
                or not 0 <= item["column"] <= 1_000_000
                or item["confidence"] != "STATIC_HEURISTIC_REVIEW_REQUIRED"
                or item["runtime_bug_reproduced"] is not False
                or item["safe_fix_guidance"] != SCANNER_GUIDANCE[code]):
            raise PatternError("unapproved pattern, position, or guidance")
        source, pr = SOURCE_BINDINGS[code]
        if item["public_evidence"] != f"https://github.com/{source}/pull/{pr}":
            raise PatternError("noncanonical public evidence URL")
        detail = ""
        if language == "python":
            detail = item["iterator_binding"]
            if (not isinstance(detail, str) or not detail.isidentifier()
                    or len(detail) > 128
                    or item["thread_boundary"] not in PY_BOUNDARIES):
                raise PatternError("invalid Python thread-boundary metadata")
        key = (code, item["line"], item["column"],
               detail, item.get("thread_boundary"))
        if key in seen:
            raise PatternError("duplicate candidate finding")
        seen.add(key)
    return language


def preview_static_rule_candidates(root, scan, *, existing_rulepack=None):
    """Pin candidates to Stage 4 public PR identities without DB operations.

    The optional existing rulepack must be a non-approved Stage 6 pack from
    a separate trusted Knowledge preview. In either mode source authenticity,
    true runtime behavior and authorization remain UNVERIFIED.
    """
    _check_receipt(scan)
    manifest = load_manifest(root)
    snapshot = load_merge_snapshot(root, manifest)
    refs = {(x["source"], x["pr_number"]): x
            for x in manifest["entries"]}
    pins = {(x["source"], x["pr_number"]): x
            for x in snapshot["entries"]}
    attached = {}
    if existing_rulepack is not None:
        matrix = create_regression_matrix(existing_rulepack)
        for case in matrix["cases"]:
            attached[(case["source"], case["rule_code"])] = case
    proposals = []
    for item in scan["findings"]:
        code = item["pattern_code"]
        source, pr = SOURCE_BINDINGS[code]
        key = (source, pr)
        if (key not in refs or key not in pins
                or refs[key]["pattern_id"] != code
                or refs[key]["canonical_pr_number"] != pr):
            raise PatternError("approved public pattern identity not pinned")
        pin = pins[key]
        if (not isinstance(pin.get("merge_commit_sha"), str)
                or not SHA40.fullmatch(pin["merge_commit_sha"])
                or pin["public_url"] != item["public_evidence"]):
            raise PatternError("invalid pinned public merge identity")
        original = None
        if existing_rulepack is not None:
            original = attached.get((source, code))
            if (original is None
                    or original["case_id"] != f"{source}#{pr}:{code}"
                    or original["independent_reviewer_signoff"] != "NOT_RECEIVED"
                    or original["actual_test_result"] != "NOT_EXECUTED"):
                raise PatternError("Stage 6 candidate evidence does not match")
        test_fixture, expected, platform = TEST_FAMILIES[code]
        guidance, regression_description = GUIDANCE[code]
        locator = {"scan_sha256": scan["source_sha256"],
                   "pattern_code": code, "line": item["line"],
                   "column": item["column"],
                   "binding": item.get("iterator_binding"),
                   "boundary": item.get("thread_boundary"),
                   "pinned_merge_sha": pin["merge_commit_sha"]}
        proposals.append({
            "candidate_id_sha256": _digest(locator),
            "pattern_code": code, "source": source,
            "canonical_pr_number": pr,
            "public_evidence": pin["public_url"],
            "pinned_merge_commit_sha": pin["merge_commit_sha"],
            "scan_source_sha256": scan["source_sha256"],
            "source_line": item["line"], "source_column": item["column"],
            "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
            "stage6_rulepack_candidate": {
                "rule_code": code, "safe_fix_guidance": guidance,
                "regression_test_plan": regression_description,
                "status": "UNVERIFIED_CANDIDATE_ONLY",
                "evidence_fingerprint": (
                    original["evidence_fingerprint"] if original else None),
                "required_gates": {
                    gate: "NOT_VERIFIED" for gate in REQUIRED_GATES},
                "executable_command": None,
            },
            "stage6_regression_case": {
                "case_id": f"{source}#{pr}:{code}",
                "fixture_design": test_fixture,
                "expected_invariant": expected,
                "platform": platform,
                "actual_test_result": "NOT_EXECUTED",
                "independent_reviewer_signoff": "NOT_RECEIVED",
                "executable_script": None,
            },
        })
    proposals.sort(key=lambda p: (
        p["source_line"], p["source_column"], p["pattern_code"],
        p["candidate_id_sha256"]))
    return {
        "schema": "UCIE_STATIC_RULEPACK_CANDIDATE_PREVIEW_V1",
        "status": ("STRUCTURALLY_LINKED_UNVERIFIED" if existing_rulepack is not None
                   else "PUBLIC_PR_PINNED_CANDIDATES_UNVERIFIED"),
        "scan_source_sha256": scan["source_sha256"],
        "source_digest_is_authoritative": False,
        "finding_count": len(proposals),
        "proposals": proposals,
        "review_digest_sha256": _digest(proposals),
        "miner_knowledge_binding": ("STRUCTURAL_ONLY" if existing_rulepack is not None
                                    else "NOT_CHECKED"),
        "upstream_fix_reproduced": False,
        "independent_regression_passed": False,
        "rulepack_signed": False,
        "auto_promoted": False,
        "deploy_allowed": False,
        "persistent_writes": 0,
        "production_approved": False,
    }
