"""Entrypoint restricted to the standalone D:/UCIE checkout on Windows.

No project access, no GitHub credentials, no global scheduler installation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if os.name == "nt":
    expected = Path("D:/UCIE").resolve()
    if ROOT.resolve() != expected or ROOT.is_symlink():
        print(json.dumps({"status": "FAIL_CLOSED", "reason": "UCIE checkout is not D:/UCIE"}))
        raise SystemExit(2)

sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.worker import run_cycle
from ucie_miner.core import mine_once
from ucie_miner.public_discovery import (
    classify_stage10_discovery_error, STAGE10_FAILURE_PHASES,
)


def main() -> int:
    stage10 = None

    def collect(root):
        nonlocal stage10
        # The existing two-source miner remains first and authoritative.
        # Both collectors share run_cycle's existing OS-held single-instance lock.
        legacy = mine_once(root, crosscheck_origin=True)
        try:
            from ucie_miner.public_hourly_staging import optional_public_skill_staging
            stage10 = optional_public_skill_staging(root)
        except Exception as exc:
            failure_phase = getattr(exc, "ucie_stage10_phase", "STAGE10_SETUP")
            if type(failure_phase) is not str or failure_phase not in STAGE10_FAILURE_PHASES:
                failure_phase = "STAGE10_SETUP"
            # Never roll back or falsely mark a successful legacy collection
            # as failed. But return a nonzero task result so Stage 10 failures
            # are visible to the owner; never log untrusted error strings.
            stage10 = {
                "status": "STAGE10_HOURLY_FAILED_NO_GO",
                "error_type": type(exc).__name__,
                "error_category": classify_stage10_discovery_error(exc),
                "error_phase": failure_phase,
                "approved_rules_added": 0,
                "production_approved": False,
            }
        # The worker must persist this opt-in stage's outcome alongside
        # the legacy receipt; otherwise a task exit 2 has no stored cause.
        # The worker stores only its pinned status and sanitized error TYPE.
        legacy["stage10"] = {
            "status": stage10["status"],
            **({k: stage10[k] for k in ("error_type", "error_category", "error_phase")}
               if stage10["status"] == "STAGE10_HOURLY_FAILED_NO_GO" else {}),
            **({k: stage10[k] for k in (
                "stage13_history_status", "stage13_failure_source",
                "stage13_failure_category", "stage12_review_status",
                "stage12_review_proposals_added",
                "stage15_fix_evidence_status", "stage15_failure_source",
                "stage15_failure_category",
                "stage16_safe_qa_status",
                "stage16_safe_qa_templates",
                "stage16_safe_qa_gets_upper_bound",
            ) if k in stage10}
               if stage10["status"] in (
                   "STAGE10_UNVERIFIED_STAGED_NO_GO",
                   "STAGE10_HOURLY_PARTIAL_NO_GO") else {}),
        }
        return legacy

    try:
        result = run_cycle(ROOT, collect=collect, enforce_schedule=True)
        if result.get("status") == "COLLECTED_UNVERIFIED" and stage10 is not None:
            result["stage10"] = stage10
    except Exception as exc:
        result = {"status": "FAIL_CLOSED", "error_type": type(exc).__name__}
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    if result.get("stage10", {}).get("status") in (
            "STAGE10_HOURLY_FAILED_NO_GO", "STAGE10_HOURLY_PARTIAL_NO_GO"):
        return 2
    return 0 if result["status"] == "COLLECTED_UNVERIFIED" else (
        3 if result["status"] == "SKIPPED_ALREADY_RUNNING" else (0 if result["status"] == "SKIPPED_NOT_DUE" else 2)
    )


if __name__ == "__main__":
    raise SystemExit(main())
