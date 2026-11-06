"""Read-only owner-risk release preflight for UCIE's FIRST public manual rule.

No key generation, signing, distribution, task mutation, or use of unapproved
sources. A passing preflight never stands in for owner risk acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .owner_release import (
    JOBS, MODE, REPO, SCOPE, _local_clean_sha, validate_live_automated_qa,
)
from .policy import PolicyError

SCHEMA = "UCIE_FIRST_RULE_OWNER_RISK_SIGNING_PREFLIGHT_V01"
NO_GO = "NO_GO"
READY = "READY_FOR_EXPLICIT_OWNER_SIGNING_DECISION"
EXPECTED_ROOT = "ucie"


def inspect_owner_release_preflight(root: Path, *, run_id: int | None = None) -> dict:
    """Inspect clean owner main SHA and exact CI run, without signing.

    Only the existing owner_release gates can establish valid GitHub CI:
    push on main, exactly four successful matrix jobs plus required steps.
    """
    report = {
        "schema": SCHEMA,
        "status": NO_GO,
        "repository": REPO,
        "approval_mode": MODE,
        "scope": SCOPE,
        "source_commit_sha": None,
        "ci_run_id": run_id if type(run_id) is int else None,
        "ci_run_url": None,
        "ci_push_main_verified": False,
        "ci_four_jobs_verified": False,
        "clean_owner_main_verified": False,
        "reason_codes": [],
        "owner_explicit_authorization_recorded": False,
        "independent_human_qa_attested": False,
        "legal_license_signoff_attested": False,
        "owner_production_key_read": False,
        "owner_signature_created": False,
        "package_created": False,
        "package_distributed": False,
        "automatic_rule_promotion": False,
        "task_scheduler_mutated": False,
        "operating_database_modified": False,
    }
    if not isinstance(root, Path) or root.is_symlink() or root.name.casefold() != EXPECTED_ROOT:
        report["reason_codes"].append("NOT_EXACT_UCIE_OWNER_ROOT")
        return report
    try:
        sha = _local_clean_sha(root)
    except (PolicyError, OSError, ValueError):
        report["reason_codes"].append("OWNER_MAIN_NOT_CLEAN_OR_UNATTESTED")
        return report
    report["source_commit_sha"] = sha
    report["clean_owner_main_verified"] = True
    if type(run_id) is not int or run_id < 1:
        report["reason_codes"].append("EXACT_MAIN_PUSH_CI_RUN_ID_REQUIRED")
        return report
    try:
        qa = validate_live_automated_qa(run_id)
    except (PolicyError, OSError, ValueError):
        report["reason_codes"].append("MAIN_PUSH_CI_NOT_VERIFIED")
        return report
    if qa.get("head_sha") != sha:
        report["reason_codes"].append("CI_COMMIT_DOES_NOT_MATCH_OWNER_CHECKOUT")
        return report
    if (qa.get("repository") != REPO or qa.get("event") != "push"
            or qa.get("branch") != "main"
            or qa.get("job_names") != sorted(JOBS)
            or qa.get("independent_human_qa") is not False
            or qa.get("legal_license_signoff") is not False):
        report["reason_codes"].append("CI_EVIDENCE_CONTRACT_DRIFT")
        return report
    report.update({
        "status": READY,
        "ci_run_url": qa["run_url"],
        "ci_push_main_verified": True,
        "ci_four_jobs_verified": True,
    })
    # The release still REQUIRES manual signing, exact separate owner
    # acknowledgement of the unreviewed legal/independent QA risks, a real
    # owner-held production key and recipient signature verification.
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only UCIE first-rule owner-risk signing preflight"
    )
    parser.add_argument("--ucie-root", required=True, type=Path)
    parser.add_argument("--run-id", required=False, type=int)
    args = parser.parse_args(argv)
    result = inspect_owner_release_preflight(
        args.ucie_root, run_id=args.run_id
    )
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0 if result["status"] == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
