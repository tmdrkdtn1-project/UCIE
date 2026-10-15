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
            # Never roll back or falsely mark a successful legacy collection
            # as failed. But return a nonzero task result so Stage 10 failures
            # are visible to the owner; never log untrusted error strings.
            stage10 = {
                "status": "STAGE10_HOURLY_FAILED_NO_GO",
                "error_type": type(exc).__name__,
                "approved_rules_added": 0,
                "production_approved": False,
            }
        return legacy

    try:
        result = run_cycle(ROOT, collect=collect, enforce_schedule=True)
        if result.get("status") == "COLLECTED_UNVERIFIED" and stage10 is not None:
            result["stage10"] = stage10
    except Exception as exc:
        result = {"status": "FAIL_CLOSED", "error_type": type(exc).__name__}
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    if result.get("stage10", {}).get("status") == "STAGE10_HOURLY_FAILED_NO_GO":
        return 2
    return 0 if result["status"] == "COLLECTED_UNVERIFIED" else (
        3 if result["status"] == "SKIPPED_ALREADY_RUNNING" else (0 if result["status"] == "SKIPPED_NOT_DUE" else 2)
    )


if __name__ == "__main__":
    raise SystemExit(main())
