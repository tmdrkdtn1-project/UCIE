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
    relocated = (__name__ == "__main__"
                 and sys.argv[1:] == ["--owner-relocated-runtime"])
    if __name__ == "__main__" and sys.argv[1:] not in (
            [], ["--owner-relocated-runtime"],
            ["--owner-base-shared-core"],
            ["--owner-base-shared-core-bootstrap-once"]):
        print(json.dumps({"status": "FAIL_CLOSED",
                          "reason": "UCIE_UNKNOWN_LAUNCH_ARGUMENTS"}))
        raise SystemExit(2)
    if relocated:
        from ucie_owner_root_gate_v01 import (
            OwnerRootError, require_owner_runtime_root,
        )
        try:
            require_owner_runtime_root(ROOT, relocated=True, platform=os.name)
        except OwnerRootError:
            print(json.dumps({"status": "FAIL_CLOSED",
                              "reason": "UCIE_OWNER_RUNTIME_ROOT_NOT_APPROVED"}))
            raise SystemExit(2)
    elif ROOT.resolve() != expected or ROOT.is_symlink():
        print(json.dumps({"status": "FAIL_CLOSED",
                          "reason": "UCIE checkout is not D:/UCIE"}))
        raise SystemExit(2)

sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.worker import run_cycle
from ucie_miner.core import mine_once


def _collect_owner_base_shared_core(
        root: Path, *, reviewed_bootstrap_once: bool = False) -> dict:
    """The only new live-capable entry, requiring an EXPLICIT owner CLI flag.

    Never stage Stage10/P11 on this pilot. BASE's existing parse and
    provenance code uses the exact same fetch_public_json transport. No
    extra quota probe, no retry, no more than three public requests.
    """
    from ucie_miner.core import fetch_public_json, MiningError
    from ucie_miner.shared_core_quota import SharedCoreQuota

    quota = SharedCoreQuota(root)
    before = quota.inspect()
    if reviewed_bootstrap_once and before["phase"] != "ABSENT":
        raise MiningError("first CORE bootstrap already consumed")
    bootstrap = reviewed_bootstrap_once and before["phase"] == "ABSENT"
    attempts = 0

    def budgeted_fetch(url: str):
        nonlocal attempts
        if attempts >= 3:
            raise MiningError("BASE shared CORE three-request owner cap")
        first = bootstrap and attempts == 0
        attempts += 1
        return fetch_public_json(
            url, core_quota=quota, reviewed_first_get=first)

    outcome = mine_once(
        root, fetch=budgeted_fetch, sources=("python/cpython",),
        max_new_per_source=1, crosscheck_origin=True, read_workers=1)
    outcome["owner_pilot_gets_attempted"] = attempts
    outcome["shared_core_quota_phase"] = quota.inspect()["phase"]
    return outcome
from ucie_miner.public_discovery import (
    classify_stage10_discovery_error, STAGE10_FAILURE_PHASES,
)


def main() -> int:
    pilot = sys.argv[1:] in (
        ["--owner-base-shared-core"],
        ["--owner-base-shared-core-bootstrap-once"],
    )
    reviewed_bootstrap_once = sys.argv[1:] == [
        "--owner-base-shared-core-bootstrap-once"]
    stage10 = None

    def collect(root):
        nonlocal stage10
        if pilot:
            return _collect_owner_base_shared_core(
                root, reviewed_bootstrap_once=reviewed_bootstrap_once)
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
                "stage17_quality_status",
                "stage17_quality_candidate_count",
                "stage17_quality_candidate_delta",
            ) if k in stage10}
               if stage10["status"] in (
                   "STAGE10_UNVERIFIED_STAGED_NO_GO",
                   "STAGE10_HOURLY_PARTIAL_NO_GO") else {}),
        }
        return legacy

    try:
        result = run_cycle(
            ROOT, collect=collect, enforce_schedule=True,
            owner_base_core_hourly=pilot)
        if result.get("status") in (
                "COLLECTED_UNVERIFIED", "COLLECTED_UNVERIFIED_PARTIAL_NO_GO") and stage10 is not None:
            result["stage10"] = stage10
    except Exception as exc:
        result = {"status": "FAIL_CLOSED", "error_type": type(exc).__name__}
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    if result.get("stage10", {}).get("status") in (
            "STAGE10_HOURLY_FAILED_NO_GO", "STAGE10_HOURLY_PARTIAL_NO_GO"):
        return 2
    # An upstream quota/permission hold is a successful SAFE SKIP, not a
    # successful collection. Keep OS task scheduled; never retry the GET.
    return 0 if result["status"] in (
        "COLLECTED_UNVERIFIED",
        "SKIPPED_NOT_DUE",
        "SKIPPED_PUBLIC_RATE_PAUSED_NO_GET",
        "SKIPPED_PUBLIC_RATE_OWNER_REVIEW_NO_GET",
    ) else (3 if result["status"] == "SKIPPED_ALREADY_RUNNING" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
