"""UCIE Stage 6-8: structural inspection of untrusted external regression claims.

This module does NOT execute a command, checkout external code, fetch a URL,
read a log, trust a runner, attest a reviewer, or certify a fix. The existence
of a before/after result claim never makes a rule safe for production.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re

from .patterns import PatternError

HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
VERSION = re.compile(r"[0-9]{1,2}[.][0-9]{1,2}(?:[.][0-9]{1,3})?")
CLAIM_FIELDS = frozenset({
    "schema", "case_id", "source", "rule_code", "evidence_fingerprint",
    "merge_commit_sha", "runtime_product", "runtime_version", "platform",
    "fixture_sha256", "pre_fix", "post_fix", "recorded_utc",
    "independent_attestation",
})
OBS_FIELDS = frozenset({"revision_sha", "result", "observation_sha256"})
CASE_FIELDS = frozenset({
    "case_id", "source", "rule_code", "evidence_fingerprint",
    "fixture_design", "expected_invariant", "target_environment",
    "negative_case", "independent_test_script", "actual_test_result",
    "independent_reviewer_signoff",
})
MAX_CLAIMS = 40


def _digest(value):
    try:
        raw = json.dumps(value, sort_keys=True, ensure_ascii=True,
                         separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError, OverflowError) as exc:
        raise PatternError("malformed external receipt") from exc
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _timestamp(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PatternError("UTC timestamp required")
    try:
        stamp = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PatternError("invalid UTC timestamp") from exc
    if stamp.utcoffset().total_seconds() != 0 or stamp > datetime.now(timezone.utc):
        raise PatternError("invalid or future claim date")
    return value


def inspect_regression_claims(plan: object, pinned: object,
                              external_claims: object = None) -> dict:
    """Return nonauthoritative receipt matches; never claim test PASS."""
    if (not isinstance(plan, dict)
            or plan.get("schema") != "UCIE_SYNTHETIC_REGRESSION_PLAN_V1"
            or plan.get("upstream_code_executed") is not False
            or plan.get("regressions_independently_reproduced") != 0
            or plan.get("rulepack_signed") is not False
            or plan.get("production_approved") is not False
            or plan.get("persistent_writes") != 0
            or not isinstance(plan.get("cases"), list)
            or type(plan.get("candidate_count")) is not int
            or plan["candidate_count"] != len(plan["cases"])
            or len(plan["cases"]) > MAX_CLAIMS):
        raise PatternError("invalid unsigned regression plan")
    if (not isinstance(pinned, dict)
            or pinned.get("schema") != "UCIE_PUBLIC_PR_MERGE_SNAPSHOT_V1"
            or not isinstance(pinned.get("entries"), list)
            or not 1 <= len(pinned["entries"]) <= MAX_CLAIMS):
        raise PatternError("invalid merge snapshot for regression inspection")
    pinned_by_key = {}
    for item in pinned["entries"]:
        if (not isinstance(item, dict)
                or set(item) != {"source", "pr_number", "public_url",
                                    "merged_at", "base_branch", "merge_commit_sha"}):
            raise PatternError("unexpected pinned PR metadata")
        source, number, commit = (item["source"], item["pr_number"],
                                   item["merge_commit_sha"])
        if (source not in ("python/cpython", "PowerShell/PowerShell")
                or type(number) is not int or number < 1
                or not isinstance(commit, str) or not HEX40.fullmatch(commit)
                or item["public_url"] != f"https://github.com/{source}/pull/{number}"
                or (source, number) in pinned_by_key):
            raise PatternError("invalid pinned PR identity")
        pinned_by_key[(source, number)] = commit

    plans = {}
    for case in plan["cases"]:
        if (not isinstance(case, dict) or set(case) != CASE_FIELDS
                or not isinstance(case["case_id"], str)
                or not isinstance(case["source"], str)
                or not isinstance(case["rule_code"], str)
                or not isinstance(case["evidence_fingerprint"], str)
                or not HEX64.fullmatch(case["evidence_fingerprint"])
                or case["case_id"] in plans
                or case["independent_test_script"] is not None
                or case["actual_test_result"] != "NOT_EXECUTED"
                or case["independent_reviewer_signoff"] != "NOT_RECEIVED"
                or case["target_environment"] not in ("Any", "Windows")):
            raise PatternError("modified or invalid regression plan")
        plans[case["case_id"]] = case

    claims = [] if external_claims is None else external_claims
    if not isinstance(claims, list) or len(claims) > MAX_CLAIMS:
        raise PatternError("unbounded regression claims")
    seen = set()
    comparisons = []
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != CLAIM_FIELDS:
            raise PatternError("unexpected external claim fields")
        case_id = claim["case_id"]
        if not isinstance(case_id, str) or case_id not in plans or case_id in seen:
            raise PatternError("unknown/duplicate regression case")
        case = plans[case_id]
        source = case["source"]
        try:
            canonical = int(case_id.split("#", 1)[1].split(":", 1)[0])
        except (ValueError, IndexError, TypeError) as exc:
            raise PatternError("bad pinned canonical regression ID") from exc
        if (case_id != f"{source}#{canonical}:{case['rule_code']}"
                or (source, canonical) not in pinned_by_key):
            raise PatternError("nonpinned regression identity")
        target_sha = pinned_by_key[(source, canonical)]
        runtime = "CPython" if source == "python/cpython" else "PowerShell"
        platform = claim["platform"]
        if (claim["schema"] != "UCIE_EXTERNAL_REGRESSION_CLAIM_V1"
                or claim["source"] != source
                or claim["rule_code"] != case["rule_code"]
                or claim["evidence_fingerprint"] != case["evidence_fingerprint"]
                or claim["merge_commit_sha"] != target_sha
                or claim["runtime_product"] != runtime
                or not isinstance(claim["runtime_version"], str)
                or not VERSION.fullmatch(claim["runtime_version"])
                or platform not in ("Windows", "Linux")
                or (case["target_environment"] == "Windows"
                    and platform != "Windows")
                or (runtime == "PowerShell" and platform != "Windows")
                or not isinstance(claim["fixture_sha256"], str)
                or not HEX64.fullmatch(claim["fixture_sha256"])
                or claim["independent_attestation"] is not None):
            raise PatternError("forged or unverified regression evidence")
        _timestamp(claim["recorded_utc"])
        before, after = claim["pre_fix"], claim["post_fix"]
        if (not isinstance(before, dict) or not isinstance(after, dict)
                or set(before) != OBS_FIELDS or set(after) != OBS_FIELDS):
            raise PatternError("malformed before/after claims")
        for item in (before, after):
            if (not isinstance(item["revision_sha"], str)
                    or not HEX40.fullmatch(item["revision_sha"])
                    or not isinstance(item["observation_sha256"], str)
                    or not HEX64.fullmatch(item["observation_sha256"])):
                raise PatternError("invalid claimed revision/observation SHA")
        if (before["result"] != "FAILURE_OBSERVED_CLAIM"
                or after["result"] != "SUCCESS_OBSERVED_CLAIM"
                or after["revision_sha"] != target_sha
                or before["revision_sha"] == target_sha
                or before["observation_sha256"] == after["observation_sha256"]):
            raise PatternError("incomplete or contradictory regression delta")
        seen.add(case_id)
        comparisons.append({
            "case_id": case_id,
            "external_claim_sha256": _digest(claim),
            "claim_consistency": "STRUCTURAL_ONLY",
            "reproduction_verified": False,
            "independent_attestation_verified": False,
            "version_applicability": "UNDETERMINED",
        })
    comparisons.sort(key=lambda item: item["case_id"])
    return {
        "schema": "UCIE_EXTERNAL_REGRESSION_REVIEW_V1",
        "status": ("UNTRUSTED_CLAIMS_PRESENT" if comparisons
                   else "AWAITING_EXTERNAL_CLAIMS"),
        "planned_cases": len(plans),
        "claimed_cases": len(comparisons),
        "missing_claims": len(plans) - len(comparisons),
        "comparisons": comparisons,
        "claim_set_sha256": _digest(comparisons),
        "runtime_executions_by_ucie": 0,
        "reproduced_fixes_verified": 0,
        "independent_attestations_verified": 0,
        "fixed_release_versions_verified": 0,
        "rulepack_signed": False,
        "production_approved": False,
        "persistent_writes": 0,
    }
