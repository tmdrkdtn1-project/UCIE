"""UCIE V1.1: complete candidate review packet, never upstream-fix approval.

Combine the currently validated source audit, V1.0 observation receipts,
UCIE-owned offline guard regression results and an optional release ancestry
observation. Outputs an inert checklist; no external code execution or writes.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

from .library_audit_v07 import audit_existing_public_library
from .library_observation_receipts_v10 import replay_observations
from .library_safety_regression_v10 import run_owner_guard_regressions
from .public_discovery import SOURCES, SOURCE_SKILL
from .skill_profiles import PROFILE

SCHEMA = "UCIE_SOURCE_PINNED_REVIEW_BUNDLE_V11"
HEX = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
GUARD_IDS = frozenset((
    "NON_ALLOWLIST_REPO_API_REJECTED",
    "LOOPBACK_PUBLIC_URL_REJECTED",
    "THIRD_PARTY_CLAIM_REJECTED",
    "DUPLICATE_QUERY_REJECTED",
    "FORGED_APPROVAL_REJECTED",
    "UNVERIFIED_SNAPSHOT_ACCEPTS_ONLY_UNVERIFIED",
))
REQUIREMENTS = (
    ("EXACT_UPSTREAM_FIX_REPRODUCTION", "NOT_PERFORMED",
     "Prepare an independently reviewed UCIE-authored before/after test for the pinned upstream change; never execute PR instructions."),
    ("OFFICIAL_RELEASE_ANCESTRY", "NOT_PROVEN_IN_OFFLINE_PACKET",
     "Explicitly compare an approved repository's published release tag with the pinned source commit."),
    ("TARGET_RUNTIME_REGRESSION", "NOT_PERFORMED",
     "Run the approved harmless reproduction independently on supported actual target tool versions."),
    ("VERSION_MATRIX", "NOT_VERIFIED",
     "Check release notes, runtime behavior, supported versions and any backports."),
    ("LICENSE", "NOT_APPROVED",
     "Review exact license and redistribution constraints independently."),
    ("SECURITY", "NOT_APPROVED",
     "Review security consequences and regression risks without running untrusted input."),
    ("OWNER_SIGNOFF", "NOT_APPROVED",
     "Require explicit independent human signoff before rule promotion or export."),
)


class ReviewBundleError(ValueError):
    pass


def assemble_review_bundle(audit: dict, observations: dict, guard: dict, *,
                           item_id: str, release_result: dict | None = None) -> dict:
    if type(item_id) is not str or HEX.fullmatch(item_id) is None:
        raise ReviewBundleError("exact public source-linked item required")
    if (type(audit) is not dict or audit.get("schema") !=
            "UCIE_PUBLIC_SOURCE_LINKED_AUDIT_V07"
            or audit.get("source_linkage_checked") is not True
            or audit.get("approved_candidates") != 0
            or audit.get("exportable_rules") != 0
            or type(audit.get("candidates")) is not list
            or type(observations) is not dict
            or observations.get("schema") != "UCIE_PUBLIC_OBSERVATION_REPLAY_V10"
            or observations.get("source_linkage_valid") is not True
            or observations.get("production_approved") is not False
            or observations.get("source_linked_candidates") !=
            audit.get("source_linked_candidates")
            or type(guard) is not dict
            or guard.get("status") != "UCIE_GUARD_FIXTURE_PASS_NOT_UPSTREAM_FIX_VERIFIED"
            or guard.get("upstream_fix_verified") is not False
            or guard.get("independent_upstream_regressions_passed") != 0
            or type(guard.get("cases")) is not list
            or len(guard["cases"]) != len(GUARD_IDS)
            or {x.get("case") for x in guard["cases"]} != GUARD_IDS
            or any(x.get("passed") is not True for x in guard["cases"])):
        raise ReviewBundleError("incomplete or forged public evidence inputs")
    selected = [row for row in audit["candidates"]
                if row.get("item_id") == item_id]
    if len(selected) != 1:
        raise ReviewBundleError("unknown or duplicate public source item")
    row = selected[0]
    sid = row["source_id"]
    repo = sid.removeprefix("repo:")
    profile = PROFILE.get(SOURCE_SKILL.get(repo))
    if (repo not in SOURCES or profile is None
            or profile["domain"] != row["domain"]
            or row.get("independently_verified") is not False
            or row.get("owner_approved") is not False
            or row.get("review_guide", {}).get("generated_executable_rule") is not False):
        raise ReviewBundleError("unapproved source or profile mismatch")
    linked = []
    for obs in observations["observations"]:
        if obs["item_id"] != item_id:
            continue
        if (obs.get("source_id") != sid
                or obs.get("independently_verified_fix") is not False
                or obs.get("owner_approved") is not False
                or type(obs.get("receipt_id")) is not str
                or HEX.fullmatch(obs["receipt_id"]) is None):
            raise ReviewBundleError("untrusted observation")
        linked.append({
            "receipt_id": obs["receipt_id"],
            "metadata_status": obs["metadata_status"],
            "identity_matched": obs["identity_matched"],
            "source_revision_sha": obs["revision_hint"],
            "upstream_fix_verified": False,
        })
    release_summary = None
    if release_result is not None:
        if (type(release_result) is not dict
                or release_result.get("schema") !=
                "UCIE_PUBLIC_RELEASE_ANCESTRY_OBSERVATION_V11"
                or release_result.get("item_id") != item_id
                or release_result.get("source_id") != sid
                or type(release_result.get("source_commit_sha")) is not str
                or HEX40.fullmatch(release_result["source_commit_sha"]) is None
                or release_result.get("rule_approved") is not False
                or release_result.get("runtime_version_fix_verified") is not False
                or release_result.get("auto_promoted") is not False
                or release_result.get("result_sha256") != sha256(json.dumps(
                    {k: v for k, v in release_result.items()
                     if k != "result_sha256"}, sort_keys=True, ensure_ascii=True,
                    separators=(",", ":")).encode("ascii")).hexdigest()
                or not any(
                    entry["identity_matched"] is True
                    and entry["source_revision_sha"] ==
                    release_result["source_commit_sha"] for entry in linked)):
            raise ReviewBundleError("unbound release observation or forged approval")
        # A separate release observation is displayed only, never promoted.
        release_summary = {
            "release_tag": release_result["release_tag_claimed"],
            "status": release_result["status"],
            "tag_contains_commit_observed": release_result["tag_contains_exact_source_commit"],
            "fix_verified": False,
        }
    result = {
        "schema": SCHEMA,
        "status": "UPSTREAM_FIX_AND_RELEASE_REVIEW_REQUIRED_NO_GO",
        "item_id": item_id, "source_id": sid,
        "public_candidate_count": len(audit["candidates"]),
        "observation_count": len(linked),
        "observation_receipts": linked,
        "ucie_owned_guard_tests_passed": len(GUARD_IDS),
        "ucie_owned_guard_case_ids": sorted(GUARD_IDS),
        "source_domain": row["domain"],
        "fixed_ucie_review_question": profile["review_question"],
        "safe_review_guidance": profile["safe_call"],
        "release_observation": release_summary,
        "independent_upstream_test_recipe": None,
        "requirements": [{
            "gate": gate, "status": status, "human_next_action": action,
            "automatic_approval": False,
        } for gate, status, action in REQUIREMENTS],
        "independent_upstream_regression_passes": 0,
        "verified_runtime_versions": [],
        "license_signoffs": 0, "owner_signoffs": 0,
        "source_code_generated": False,
        "approved_rule_count": 0,
        "exportable_rule_count": 0,
        "auto_promotion": False,
        "upstream_code_executed": False,
        "operating_db_writes": 0,
    }
    result["bundle_sha256"] = sha256(json.dumps(
        result, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")).encode("ascii")).hexdigest()
    return result


def review_current_candidate(root: Path, *, item_id: str,
                             audit_reader=None, replay_reader=None,
                             guard_runner=None, release_result=None) -> dict:
    audit = (audit_existing_public_library if audit_reader is None
             else audit_reader)(root)
    observations = (replay_observations if replay_reader is None
                    else replay_reader)(root)
    guard = (run_owner_guard_regressions if guard_runner is None
             else guard_runner)()
    return assemble_review_bundle(audit, observations, guard,
                                  item_id=item_id, release_result=release_result)


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="UCIE pinned source review only, no upstream fix PASS")
    p.add_argument("--item-id", required=True)
    args = p.parse_args()
    try:
        report = review_current_candidate(
            Path(__file__).resolve().parents[2], item_id=args.item_id)
    except (ReviewBundleError, ValueError, OSError):
        print(json.dumps({"schema": SCHEMA, "status": "REVIEW_BUNDLE_NO_GO"}))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
