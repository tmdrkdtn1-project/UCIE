"""Read-only latest hourly Stage12 -> Stage17 operator handoff.

Shows only review proposals first inserted during the *last* successful UCIE
hourly cycle, not the entire historical candidate backlog. Reports candidates,
never proven bugs, learned model weights, QA, approval or a signed Rulepack.
No network, source execution, persistent writes, scheduler or release actions.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import sqlite3
import sys

from .automated_candidate_qa import _checked_handoff
from .public_candidate_learning import _review_path
from .public_discovery import DiscoveryError
from .stage17_review_docket import attest_stage16_aggregate, build_review_docket
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_LATEST_HOURLY_NEW_REVIEW_HANDOFF_V1"
MAX_RECEIPT_BYTES = 8192
MAX_SELECTED = 12
MAX_REVIEWED_ROWS = 1000
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
PR_REF = re.compile(r"(?:pr|fix-pr):([1-9][0-9]*):([a-f0-9]{40})(?::[a-f0-9]{64})?\Z")
COMMIT_REF = re.compile(r"commit:([a-f0-9]{40})\Z")
APPROVED = frozenset((
    "python/cpython", "PowerShell/PowerShell", "git/git",
    "modelcontextprotocol/python-sdk", "actions/runner-images",
))


def _utc(value: object) -> datetime:
    if type(value) is not str or not 1 <= len(value) <= 40:
        raise ValueError("invalid hourly UTC timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid hourly UTC timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise ValueError("hourly UTC timestamp is not UTC")
    return dt


def _no_dupe(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate hourly receipt property")
        obj[key] = value
    return obj


def _read_last_receipt(root: Path) -> dict:
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise ValueError("UCIE runtime absent or unsafe")
    path = runtime / "last_run.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("last UCIE hourly receipt absent or unsafe")
    with path.open("rb") as handle:
        raw = handle.read(MAX_RECEIPT_BYTES + 1)
    if not raw or len(raw) > MAX_RECEIPT_BYTES:
        raise ValueError("oversized or empty UCIE hourly receipt")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupe)
    except (UnicodeError, ValueError) as exc:
        raise ValueError("invalid latest UCIE hourly receipt") from exc
    if type(payload) is not dict:
        raise ValueError("invalid latest UCIE hourly receipt")
    return payload


def _public_ref(source: str, reference: str) -> str | None:
    if source not in APPROVED or type(reference) is not str:
        return None
    pr = PR_REF.fullmatch(reference)
    if pr and source != "git/git":
        return "https://github.com/" + source + "/pull/" + str(int(pr.group(1)))
    commit = COMMIT_REF.fullmatch(reference)
    if commit and source == "git/git":
        return "https://github.com/git/git/commit/" + commit.group(1)
    return None


def _base(status: str, receipt: dict, reported: int) -> dict:
    return {
        "schema": SCHEMA, "status": status,
        "last_cycle_status": receipt["status"],
        "last_cycle_started_utc": receipt["started_utc"],
        "last_cycle_finished_utc": receipt["finished_utc"],
        "new_review_proposals_reported": reported,
        "linked_new_review_proposals": 0,
        "selected_count": 0, "omitted_count": 0,
        "new_review_tasks": [],
        "manual_review_required": True,
        "independent_fix_verified": False,
        "independent_qa_verified": False,
        "owner_signed": False, "approved_rules_added": 0,
        "production_approved": False, "auto_promoted": False,
        "external_api_gets": 0, "persistent_writes": 0,
        "source_executed": False,
    }


def build_latest_hourly_review(receipt: dict, handoff: dict,
                               docket: dict, first_seen: dict) -> dict:
    """Project a validated hourly receipt onto *existing* Stage17 review items.

    first_seen is keyed by Stage12 review fingerprint; its identity has been
    checked by prepare_verification_handoff in the read-only adapter.
    """
    if (type(receipt) is not dict
            or receipt.get("schema") != "UCIE_MINER_CYCLE_V1"
            or receipt.get("verification_pass") != 0
            or receipt.get("production_approved") is not False
            or type(receipt.get("stage12_review_proposals_added")) is not int
            or not 0 <= receipt["stage12_review_proposals_added"] <= MAX_REVIEWED_ROWS):
        raise ValueError("untrusted UCIE hourly review receipt")
    start = _utc(receipt.get("started_utc"))
    finish = _utc(receipt.get("finished_utc"))
    if finish < start or finish - start > timedelta(hours=1):
        raise ValueError("invalid UCIE hourly cycle duration")
    reported = receipt["stage12_review_proposals_added"]
    if receipt.get("status") not in {
            "COLLECTED_UNVERIFIED", "COLLECTED_UNVERIFIED_PARTIAL_NO_GO"}:
        return _base("LATEST_HOURLY_COLLECTION_NOT_COMPLETE_NO_GO", receipt, reported)
    if receipt.get("stage12_review_status") != "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO":
        if reported != 0:
            raise ValueError("reported new reviews without Stage12 execution")
        return _base("LATEST_HOURLY_STAGE12_NOT_UPDATED_NO_GO", receipt, 0)
    complete, tasks = _checked_handoff(handoff)
    if not complete:
        return _base("LATEST_HOURLY_SOURCE_LEDGER_INCOMPLETE_NO_GO", receipt, reported)
    if (type(docket) is not dict
            or docket.get("schema") != "UCIE_STAGE17_CANDIDATE_REVIEW_DOCKET_V1"
            or type(docket.get("items")) is not list
            or docket.get("candidate_count") != len(tasks)
            or len(docket["items"]) != len(tasks)
            or docket.get("auto_promoted") is not False
            or docket.get("production_approved") is not False
            or docket.get("approved_rules_added") != 0
            or docket.get("persistent_writes") != 0):
        raise ValueError("untrusted Stage17 review docket")
    if (type(first_seen) is not dict or len(first_seen) != len(tasks)
            or len(first_seen) > MAX_REVIEWED_ROWS):
        return _base("LATEST_HOURLY_REVIEW_LEDGER_CHANGED_NO_GO", receipt, reported)
    task_by_id = {t["candidate_id_sha256"]: t for t in tasks}
    if len(task_by_id) != len(tasks) or set(first_seen) != set(task_by_id):
        return _base("LATEST_HOURLY_REVIEW_LEDGER_CHANGED_NO_GO", receipt, reported)
    docket_by_id = {}
    for d in docket["items"]:
        if (type(d) is not dict
                or d.get("independent_qa") != "NOT_PERFORMED"
                or d.get("human_approval") is not False
                or d.get("deploy_allowed") is not False
                or type(d.get("required_next_actions")) is not list
                or type(d.get("candidate_id_sha256")) is not str
                or d["candidate_id_sha256"] in docket_by_id):
            raise ValueError("untrusted Stage17 per-candidate review state")
        docket_by_id[d["candidate_id_sha256"]] = d
    if set(docket_by_id) != set(task_by_id):
        raise ValueError("Stage17 review candidate identities differ")
    new_ids = []
    for identity, seen in first_seen.items():
        stamp = _utc(seen)
        if start <= stamp <= finish:
            new_ids.append(identity)
    # Do not guess which records were inserted when the user runs an
    # independent one-shot review concurrently with a scheduled cycle.
    if len(new_ids) != reported:
        return _base("LATEST_HOURLY_REVIEW_COUNT_MISMATCH_NO_GO", receipt, reported)
    result = _base(
        "LATEST_HOURLY_NEW_REVIEWS_READY_NO_GO" if new_ids
        else "LATEST_HOURLY_NO_NEW_REVIEWS", receipt, reported)
    ordered = sorted(new_ids, key=lambda identity: (
        task_by_id[identity]["source"], task_by_id[identity]["reference"],
        task_by_id[identity]["evidence_sha256"]))
    result["linked_new_review_proposals"] = len(ordered)
    result["omitted_count"] = max(0, len(ordered) - MAX_SELECTED)
    for identity in ordered[:MAX_SELECTED]:
        task, d = task_by_id[identity], docket_by_id[identity]
        result["new_review_tasks"].append({
            "candidate_id_sha256": identity,
            "source": task["source"],
            "reference": task["reference"],
            "public_reference_url": _public_ref(task["source"], task["reference"]),
            "evidence_sha256": task["evidence_sha256"],
            "pattern_code": task["pattern_code"],
            "skill_id": task["skill_id"],
            "stage17_review_lane": d["triage"],
            "safe_guidance_for_review": task["safe_guidance_for_review"],
            "regression_plan_for_review": task["regression_plan_for_review"],
            "required_next_actions": d["required_next_actions"],
            "manual_review_required": True,
            "independent_fix_verified": False, "human_approved": False,
            "deploy_allowed": False,
        })
    result["selected_count"] = len(result["new_review_tasks"])
    return result


def inspect_latest_hourly_review(root: Path) -> dict:
    """One read-only command after an existing scheduled cycle; no new timer."""
    root = Path(root)
    if root.name.casefold() != "ucie" or root.is_symlink() or not root.is_dir():
        raise ValueError("dedicated UCIE checkout required")
    receipt = _read_last_receipt(root)
    # A zero-new or skipped run needs no additional ledger scans.
    if (receipt.get("schema") == "UCIE_MINER_CYCLE_V1"
            and receipt.get("stage12_review_proposals_added") == 0
            and receipt.get("status") in {
                "COLLECTED_UNVERIFIED", "COLLECTED_UNVERIFIED_PARTIAL_NO_GO"}
            and receipt.get("stage12_review_status")
                == "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO"):
        return build_latest_hourly_review(receipt, {}, {}, {}) if False else _zero_new(receipt)
    handoff = prepare_verification_handoff(root)
    stage16 = attest_stage16_aggregate(root)
    docket = build_review_docket(handoff, stage16)
    path = _review_path(root)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)) as conn:
        conn.execute("PRAGMA query_only=ON")
        rows = conn.execute("SELECT fingerprint, first_seen_utc FROM review_queue").fetchall()
    if len(rows) > MAX_REVIEWED_ROWS or len({row[0] for row in rows}) != len(rows):
        raise ValueError("invalid bounded UCIE review timestamps")
    return build_latest_hourly_review(receipt, handoff, docket, dict(rows))


def _zero_new(receipt: dict) -> dict:
    if (receipt.get("verification_pass") != 0
            or receipt.get("production_approved") is not False):
        raise ValueError("untrusted zero-new hourly receipt")
    start, finish = _utc(receipt.get("started_utc")), _utc(receipt.get("finished_utc"))
    if finish < start or finish - start > timedelta(hours=1):
        raise ValueError("invalid zero-new hourly duration")
    return _base("LATEST_HOURLY_NO_NEW_REVIEWS", receipt, 0)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    try:
        result = inspect_latest_hourly_review(root)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    except (ValueError, OSError, sqlite3.DatabaseError, DiscoveryError) as exc:
        print(json.dumps({"status": "FAIL_CLOSED",
                          "reason_type": type(exc).__name__,
                          "approved_rules_added": 0,
                          "production_approved": False},
                         sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
