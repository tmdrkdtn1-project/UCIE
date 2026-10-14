"""Stage 7 read-only reviewer docket for static findings and claimed regressions.

Produces a review agenda, NOT an approval, cryptographic signature, source
authentication, tested-fix certification, or executable Rulepack.
"""
from __future__ import annotations

import hashlib
import json
import re

from .patterns import PatternError
from .static_rule_bridge import SOURCE_BINDINGS, _digest as digest

HEX64 = re.compile(r"[0-9a-f]{64}")


def _is_sha(v):
    return isinstance(v, str) and HEX64.fullmatch(v) is not None


def prepare_independent_review_docket(static_preview, external_review):
    """Compare bounded, candidate-only receipts; always deny operational GO."""
    preview_keys = {
        "schema", "status", "scan_source_sha256",
        "source_digest_is_authoritative", "finding_count", "proposals",
        "review_digest_sha256", "miner_knowledge_binding",
        "upstream_fix_reproduced", "independent_regression_passed",
        "rulepack_signed", "auto_promoted", "deploy_allowed",
        "persistent_writes", "production_approved",
    }
    if (not isinstance(static_preview, dict)
            or set(static_preview) != preview_keys
            or static_preview["schema"] != "UCIE_STATIC_RULEPACK_CANDIDATE_PREVIEW_V1"
            or static_preview["status"] not in (
                "PUBLIC_PR_PINNED_CANDIDATES_UNVERIFIED",
                "STRUCTURALLY_LINKED_UNVERIFIED")
            or not _is_sha(static_preview["scan_source_sha256"])
            or static_preview["source_digest_is_authoritative"] is not False
            or type(static_preview["finding_count"]) is not int
            or not isinstance(static_preview["proposals"], list)
            or not 0 <= len(static_preview["proposals"]) <= 100
            or static_preview["finding_count"] != len(static_preview["proposals"])
            or static_preview["review_digest_sha256"] != digest(static_preview["proposals"])
            or static_preview["miner_knowledge_binding"] not in (
                "NOT_CHECKED", "STRUCTURAL_ONLY")
            or static_preview["upstream_fix_reproduced"] is not False
            or static_preview["independent_regression_passed"] is not False
            or static_preview["rulepack_signed"] is not False
            or static_preview["auto_promoted"] is not False
            or static_preview["deploy_allowed"] is not False
            or static_preview["persistent_writes"] != 0
            or static_preview["production_approved"] is not False):
        raise PatternError("untrusted, altered or approved static candidate")
    if (static_preview["status"] == "STRUCTURALLY_LINKED_UNVERIFIED"
            and static_preview["miner_knowledge_binding"] != "STRUCTURAL_ONLY"):
        raise PatternError("static Knowledge link is inconsistent")

    review_keys = {
        "schema", "status", "planned_cases", "claimed_cases",
        "missing_claims", "comparisons", "claim_set_sha256",
        "runtime_executions_by_ucie", "reproduced_fixes_verified",
        "independent_attestations_verified", "fixed_release_versions_verified",
        "rulepack_signed", "production_approved", "persistent_writes",
    }
    if (not isinstance(external_review, dict)
            or set(external_review) != review_keys
            or external_review["schema"] != "UCIE_EXTERNAL_REGRESSION_REVIEW_V1"
            or external_review["status"] not in (
                "AWAITING_EXTERNAL_CLAIMS", "UNTRUSTED_CLAIMS_PRESENT")
            or type(external_review["planned_cases"]) is not int
            or not 0 <= external_review["planned_cases"] <= 40
            or type(external_review["claimed_cases"]) is not int
            or not isinstance(external_review["comparisons"], list)
            or external_review["claimed_cases"] != len(external_review["comparisons"])
            or type(external_review["missing_claims"]) is not int
            or external_review["missing_claims"] !=
                external_review["planned_cases"] - external_review["claimed_cases"]
            or external_review["claim_set_sha256"] != digest(external_review["comparisons"])
            or external_review["runtime_executions_by_ucie"] != 0
            or external_review["reproduced_fixes_verified"] != 0
            or external_review["independent_attestations_verified"] != 0
            or external_review["fixed_release_versions_verified"] != 0
            or external_review["rulepack_signed"] is not False
            or external_review["production_approved"] is not False
            or external_review["persistent_writes"] != 0):
        raise PatternError("untrusted or forged external regression review")
    if (external_review["status"] == "AWAITING_EXTERNAL_CLAIMS"
            and external_review["claimed_cases"] != 0):
        raise PatternError("claim status/count mismatch")
    if (external_review["status"] == "UNTRUSTED_CLAIMS_PRESENT"
            and external_review["claimed_cases"] == 0):
        raise PatternError("claim status/count mismatch")

    comparisons = {}
    cmp_fields = {"case_id", "external_claim_sha256", "claim_consistency",
                  "reproduction_verified", "independent_attestation_verified",
                  "version_applicability"}
    for row in external_review["comparisons"]:
        if (not isinstance(row, dict) or set(row) != cmp_fields
                or not isinstance(row["case_id"], str)
                or not _is_sha(row["external_claim_sha256"])
                or row["case_id"] in comparisons
                or row["claim_consistency"] != "STRUCTURAL_ONLY"
                or row["reproduction_verified"] is not False
                or row["independent_attestation_verified"] is not False
                or row["version_applicability"] != "UNDETERMINED"):
            raise PatternError("invalid external review claim")
        comparisons[row["case_id"]] = row

    queue = []
    proposal_fields = {"candidate_id_sha256", "pattern_code", "source",
                       "canonical_pr_number", "public_evidence",
                       "pinned_merge_commit_sha", "scan_source_sha256",
                       "source_line", "source_column", "confidence",
                       "stage6_rulepack_candidate", "stage6_regression_case"}
    for entry in static_preview["proposals"]:
        if not isinstance(entry, dict) or set(entry) != proposal_fields:
            raise PatternError("invalid candidate identity")
        code, source, number = (
            entry["pattern_code"], entry["source"],
            entry["canonical_pr_number"])
        if (not isinstance(code, str) or code not in SOURCE_BINDINGS
                or SOURCE_BINDINGS[code] != (source, number)
                or not _is_sha(entry["candidate_id_sha256"])
                or entry["scan_source_sha256"] != static_preview["scan_source_sha256"]
                or type(entry["source_line"]) is not int
                or type(entry["source_column"]) is not int
                or entry["confidence"] != "STATIC_HEURISTIC_REVIEW_REQUIRED"
                or entry["public_evidence"] !=
                    f"https://github.com/{source}/pull/{number}"):
            raise PatternError("invalid static proposal link")
        plan = entry["stage6_regression_case"]
        rule = entry["stage6_rulepack_candidate"]
        if (not isinstance(plan, dict) or not isinstance(rule, dict)
                or plan.get("case_id") != f"{source}#{number}:{code}"
                or plan.get("actual_test_result") != "NOT_EXECUTED"
                or plan.get("independent_reviewer_signoff") != "NOT_RECEIVED"
                or plan.get("executable_script") is not None
                or rule.get("rule_code") != code
                or rule.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
                or rule.get("executable_command") is not None
                or not isinstance(rule.get("required_gates"), dict)
                or not rule["required_gates"]
                or any(state != "NOT_VERIFIED"
                       for state in rule["required_gates"].values())):
            raise PatternError("unsigned regression/rule guidance required")
        claim = comparisons.get(plan["case_id"])
        queue.append({
            "candidate_id_sha256": entry["candidate_id_sha256"],
            "source": source,
            "canonical_pr_number": number,
            "pattern_code": code,
            "case_id": plan["case_id"],
            "review_action": "INDEPENDENT_BEHAVIORAL_REPRODUCTION_REQUIRED",
            "claimed_external_regression_sha256": (
                claim["external_claim_sha256"] if claim else None),
            "claim_consistency": ("STRUCTURAL_ONLY_UNTRUSTED" if claim
                                  else "NO_EXTERNAL_CLAIM"),
            "source_digest_authenticated": False,
            "reviewer_identity_authenticated": False,
            "regression_independently_verified": False,
            "signed": False,
            "ready_to_deploy": False,
        })
    queue.sort(key=lambda x: (x["case_id"], x["candidate_id_sha256"]))
    docket_fp = hashlib.sha256(json.dumps(
        {"items": queue, "external_review_sha": external_review["claim_set_sha256"]},
        sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    return {
        "schema": "UCIE_STAGE7_INDEPENDENT_REVIEW_DOCKET_V1",
        "status": "REVIEW_PENDING_NO_GO",
        "candidate_findings": len(queue),
        "claimed_reviewed_cases": sum(
            x["claimed_external_regression_sha256"] is not None for x in queue),
        "review_queue": queue,
        "docket_sha256": docket_fp,
        "docket_sha256_is_signature": False,
        "independent_approvals_verified": 0,
        "rulepacks_signed": 0,
        "auto_promotions": 0,
        "persistent_writes": 0,
        "deploy_allowed": False,
        "production_approved": False,
    }
