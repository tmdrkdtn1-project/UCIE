#!/usr/bin/env python3
"""UCIE-only daily committed-HEAD recovery ref. Never auto-commit or touch services."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sys

from scripts.ucie_acg_snapshot_guard_v01 import SnapshotDenied, checkpoint, inspect, recover_preview

REPO = "tmdrkdtn1-project/UCIE"
PROJECT = "UCIE"
KST = timezone(timedelta(hours=9), "KST")
DATE = re.compile(r"[0-9]{8}\Z")


def daily(root: str | Path, *, write: bool = False, now: datetime | None = None) -> dict:
    instant = now or datetime.now(KST)
    if instant.tzinfo is None:
        raise SnapshotDenied("OFFSET_AWARE_CLOCK_REQUIRED")
    day = instant.astimezone(KST).strftime("%Y%m%d")
    if not DATE.fullmatch(day):
        raise SnapshotDenied("DATE_INVALID")
    checkpoint_id = f"daily_{day}"
    state = inspect(root, REPO, PROJECT)
    if not state["worktree_clean"]:
        return {**state, "status": "HOLD_DIRTY_NO_GIT_REF_CREATED",
                "checkpoint_id": checkpoint_id, "scheduled_time_kst": "05:00",
                "reason": "UNCOMMITTED_OR_UNTRACKED_CHANGES_NOT_CAPTURED"}
    try:
        old = recover_preview(root, REPO, PROJECT, checkpoint_id)
    except SnapshotDenied:
        old = None
    if old is not None:
        if old["checkpoint_sha"] != state["head_sha"]:
            return {**state, "status": "HOLD_DAILY_REF_EXISTS_DIFFERENT_SHA",
                    "checkpoint_id": checkpoint_id, "existing_sha": old["checkpoint_sha"],
                    "scheduled_time_kst": "05:00"}
        return {**state, "status": "ALREADY_CAPTURED_SAME_HEAD",
                "checkpoint_id": checkpoint_id, "checkpoint_ref": old["checkpoint_ref"],
                "scheduled_time_kst": "05:00"}
    result = checkpoint(root, REPO, PROJECT, checkpoint_id, state["head_sha"],
                        approve_write=write)
    return {**result, "checkpoint_id": checkpoint_id, "scheduled_time_kst": "05:00",
            "local_time_kst": instant.astimezone(KST).isoformat(),
            "automatic_commit": False, "automatic_remote_push": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--run", action="store_true",
                        help="Create local ref only after owner-approved task install")
    args = parser.parse_args(argv)
    try:
        report = daily(args.repo_root, write=args.run)
        ok = report["status"] in (
            "PREVIEW_ONLY_NO_WRITE",
            "LOCAL_COMMITTED_HEAD_REF_CREATED_NOT_CI_VERIFIED",
            "ALREADY_CAPTURED_SAME_HEAD",
        )
    except (SnapshotDenied, OSError, ValueError) as exc:
        report, ok = {"status": "DENIED_OR_UNKNOWN", "reason": str(exc)}, False
    print(json.dumps(report, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
