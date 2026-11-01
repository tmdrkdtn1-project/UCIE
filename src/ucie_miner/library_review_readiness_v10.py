"""UCIE V1.0: offline review-ready audit from source + real observation receipts.

Builds on the V0.7 immutable source audit and V1.0 observation replay, plus
UCIE-owned safety regression fixtures. It records REAL program guard results,
not invented independent upstream fix results or rule approvals.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

from .library_audit_v07 import audit_existing_public_library
from .library_observation_receipts_v10 import replay_observations
from .library_safety_regression_v10 import run_owner_guard_regressions

SCHEMA = "UCIE_PUBLIC_EVIDENCE_REPRODUCIBILITY_READINESS_V10"
HEX = re.compile(r"[0-9a-f]{64}\Z")
MAX_CANDIDATES = 1000
MAX_OBSERVATIONS = 100


class ReadinessError(ValueError):
    pass


def _hash(value: dict) -> str:
    return sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                             separators=(",", ":")).encode("ascii")).hexdigest()


def assemble_readiness(*, audit: dict, observations: dict,
                       guard: dict, top: int = 20) -> dict:
    if (type(top) is not int or not 1 <= top <= 20
            or type(audit) is not dict or audit.get("schema") !=
            "UCIE_PUBLIC_SOURCE_LINKED_AUDIT_V07"
            or audit.get("source_linkage_checked") is not True
            or audit.get("auto_promoted") is not False
            or audit.get("approved_candidates") != 0
            or audit.get("exportable_rules") != 0
            or type(audit.get("candidates")) is not list
            or len(audit["candidates"]) > MAX_CANDIDATES
            or type(observations) is not dict or observations.get("schema") !=
            "UCIE_PUBLIC_OBSERVATION_REPLAY_V10"
            or observations.get("source_linkage_valid") is not True
            or observations.get("production_approved") is not False
            or type(observations.get("observations")) is not list
            or len(observations["observations"]) > MAX_OBSERVATIONS
            or observations.get("source_linked_candidates") !=
            audit.get("source_linked_candidates")
            or type(guard) is not dict or guard.get("schema") !=
            "UCIE_OWNED_OFFLINE_GUARD_REGRESSION_V10"
            or guard.get("status") !=
            "UCIE_GUARD_FIXTURE_PASS_NOT_UPSTREAM_FIX_VERIFIED"
            or guard.get("upstream_fix_verified") is not False
            or guard.get("independent_upstream_regressions_passed") != 0):
        raise ReadinessError("incomplete or approval-forged report inputs")
    by_id = {}
    for row in audit["candidates"]:
        identity = row.get("item_id")
        if (type(identity) is not str or HEX.fullmatch(identity) is None
                or identity in by_id or row.get("owner_approved") is not False
                or row.get("independently_verified") is not False
                or type(row.get("review_guide")) is not dict
                or row["review_guide"].get("generated_executable_rule") is not False):
            raise ReadinessError("invalid source-linked review candidate")
        by_id[identity] = row
    counts = {}
    observed_details = {}
    for observation in observations["observations"]:
        identity = observation.get("item_id")
        row = by_id.get(identity)
        if (not row or observation.get("source_id") != row["source_id"]
                or observation.get("independently_verified_fix") is not False
                or observation.get("owner_approved") is not False
                or observation.get("metadata_status") not in {
                    "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
                    "PUBLIC_COMMIT_IDENTITY_MATCHED_NOT_FIX_VERIFIED",
                    "PUBLIC_REVISION_MISMATCH_NO_GO",
                    "PUBLIC_METADATA_UNAVAILABLE_NO_GO",
                    "UNSUPPORTED_PUBLIC_IDENTITY_NO_GO"}):
            raise ReadinessError("source claim mismatch or verified status forgery")
        counts[identity] = counts.get(identity, 0) + 1
        observed_details.setdefault(identity, []).append(
            observation["metadata_status"])
    if sum(counts.values()) != len(observations["observations"]):
        raise ReadinessError("ambiguous observation counts")
    # Fix proof ALWAYS requires independent separately pinned safe tests and
    # legal review; even a real merge SHA match cannot promote the candidate.
    candidates = sorted(audit["candidates"], key=lambda row: (
        -counts.get(row["item_id"], 0),
        -row["claim_count"], row["source_id"], row["item_id"]))
    queue = []
    for row in candidates[:top]:
        question = row["review_guide"]
        queue.append({
            "item_id": row["item_id"],
            "source_id": row["source_id"],
            "purpose_code": row["purpose_code"],
            "unverified_public_observation_count": counts.get(row["item_id"], 0),
            "observed_metadata_statuses": observed_details.get(row["item_id"], []),
            "submitted_unverified_claims": row["claim_count"],
            "next_safe_review_action": question["required_next_check"],
            "fixed_ucie_review_question": question["question"],
            "required_independent_regression_recipe": "NOT_PROVIDED",
            "required_official_release_inclusion": "NOT_VERIFIED",
            "required_license_review": "NOT_VERIFIED",
            "rule_source_code_generated": False,
            "ready_for_owner_signoff": False,
        })
    result = {
        "schema": SCHEMA,
        "status": "OBSERVATION_AND_GUARD_PREPARED_UPSTREAM_FIX_NOT_VERIFIED",
        "source_candidate_count": len(by_id),
        "observation_receipts_replayed": len(observations["observations"]),
        "candidate_count_with_source_observations": len(counts),
        "guard_fixture_tests_run": guard["tested_fixture_count"],
        "guard_fixture_tests_passed": guard["passed_fixture_count"],
        "guard_fixture_results_sha256": guard["report_sha256"],
        "review_queue": queue,
        "independent_upstream_fix_regression_pass": 0,
        "version_applicability_pass": 0,
        "legal_license_signoff": 0,
        "signed_candidate_rule_count": 0,
        "production_rule_count": 0,
        "auto_promotion": False,
        "cross_project_access": False,
        "external_upstream_code_executed": False,
        "operating_database_writes": 0,
        "scheduler_changes": 0,
    }
    result["report_sha256"] = _hash(result)
    return result


def audit_owner_review_readiness(root: Path, *, top: int = 20,
                                 audit_reader=None,
                                 observation_reader=None,
                                 guard_runner=None) -> dict:
    # All reads constrained to current UCIE-only paths by their existing
    # validators; any source-drift between two reads aborts on inconsistency.
    audit = (audit_existing_public_library if audit_reader is None
             else audit_reader)(root)
    observations = (replay_observations if observation_reader is None
                    else observation_reader)(root)
    guard = (run_owner_guard_regressions if guard_runner is None
             else guard_runner)()
    return assemble_readiness(
        audit=audit, observations=observations, guard=guard, top=top)


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="UCIE source observation and local guard readiness, not rule verification")
    p.add_argument("--top", type=int, default=10)
    args = p.parse_args()
    try:
        result = audit_owner_review_readiness(
            Path(__file__).resolve().parents[2], top=args.top)
    except (ReadinessError, ValueError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "READINESS_NO_GO",
                          "error_type": type(exc).__name__}))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
