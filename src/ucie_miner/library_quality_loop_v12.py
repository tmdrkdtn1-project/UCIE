"""UCIE V1.2: opt-in deterministic source-linked hourly library quality snapshots.

Uses the SAME existing hourly UCIE scheduler and OS-held worker lock, only
when BOTH already-present Stage10 opt-in and this new Stage17 exact opt-in
are present. No new Windows task, no HTTP, new repositories, user files,
LLM training, rule execution/approval, or program code self-modification.

This tracks increasing/receding source-linked candidates and review
receipt conflicts, not 'fix effectiveness' or automatic knowledge promotion.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from .library_audit_v07 import audit_existing_public_library, STATUS as AUDIT_OK
from .library_review_records_v05 import _root

OPT_IN_FILENAME = "stage17_quality_opt_in.txt"
OPT_IN_TOKEN = "UCIE_STAGE17_HOURLY_LIBRARY_QUALITY_OPT_IN_V1"
SCHEMA = "UCIE_HOURLY_PUBLIC_LIBRARY_QUALITY_V12"
DISABLED = "STAGE17_QUALITY_DISABLED"
OBSERVED = "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO"
REVIEW = "STAGE17_QUALITY_REVIEW_REQUIRED_NO_GO"
MAX_SNAPSHOT = 2300
STAGE12 = ("STAGE12_REVIEW_DISABLED", "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO")
STAGE16 = (
    "STAGE16_SAFE_QA_DISABLED",
    "STAGE16_SAFE_QA_RATE_PAUSED_NO_GO",
    "STAGE16_SAFE_QA_ALREADY_ATTEMPTED_NO_GO",
    "STAGE16_SAFE_QA_24H_BUDGET_PAUSED_NO_GO",
    "STAGE16_SAFE_QA_OBSERVED_REVIEW_REQUIRED",
    "STAGE16_SAFE_QA_LEDGER_INCOMPLETE_NO_GO",
    "STAGE16_SAFE_QA_FAILED_NO_GO",
)


class QualityError(ValueError):
    pass


def _canonical(value: dict) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")).encode("ascii")


def _digest(value: dict) -> str:
    return sha256(_canonical(value)).hexdigest()


def _location(root: Path, *, create: bool) -> tuple[Path, Path]:
    root = _root(root)
    runtime = root / "runtime"
    folder = runtime / "quality_v12"
    dest = folder / "latest.json"
    if (runtime.is_symlink() or not runtime.is_dir()
            or folder.is_symlink()
            or folder.exists() and not folder.is_dir()
            or dest.is_symlink()):
        raise QualityError("unsafe UCIE-only quality snapshot location")
    if create:
        folder.mkdir(exist_ok=True)
    return folder, dest


def _snapshot(record: object) -> dict:
    if type(record) is not dict or set(record) != {
        "schema", "status", "finished_utc", "source_candidate_count",
        "candidate_delta", "latest_source_audit_sha256",
        "previous_quality_sha256", "stage12_status", "stage16_status",
        "claim_receipts", "conflict_groups", "orphaned_claims",
        "source_sha_conflicts", "approved_rule_count", "auto_promoted",
        "executed_external_code", "code_changes", "database_changes",
        "scheduled_task_changes", "snapshot_sha256",
    }:
        raise QualityError("unexpected hourly quality receipt schema")
    if (record.get("schema") != SCHEMA
            or record.get("status") not in (OBSERVED, REVIEW)
            or type(record.get("source_candidate_count")) is not int
            or not 0 <= record["source_candidate_count"] <= 1000
            or type(record.get("candidate_delta")) is not int
            or not -1000 <= record["candidate_delta"] <= 1000
            or type(record.get("latest_source_audit_sha256")) is not str
            or len(record["latest_source_audit_sha256"]) != 64
            or any(c not in "0123456789abcdef"
                   for c in record["latest_source_audit_sha256"])
            or record.get("stage12_status") not in STAGE12
            or record.get("stage16_status") not in STAGE16
            or any(type(record.get(f)) is not int or
                   not 0 <= record[f] <= 1000
                   for f in ("claim_receipts","conflict_groups",
                             "orphaned_claims","source_sha_conflicts"))
            or record.get("approved_rule_count") != 0
            or record.get("auto_promoted") is not False
            or record.get("executed_external_code") is not False
            or record.get("code_changes") != 0
            or record.get("database_changes") != 0
            or record.get("scheduled_task_changes") != 0):
        raise QualityError("forged or invalid quality receipt")
    previous = record.get("previous_quality_sha256")
    if previous is not None and (
            type(previous) is not str or len(previous) != 64
            or any(c not in "0123456789abcdef" for c in previous)):
        raise QualityError("invalid previous quality digest")
    stamp = record.get("finished_utc")
    if type(stamp) is not str:
        raise QualityError("missing quality UTC timestamp")
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QualityError("invalid quality timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise QualityError("non-UTC quality timestamp")
    if (type(record.get("snapshot_sha256")) is not str or
            record["snapshot_sha256"] != _digest(
                {k:v for k,v in record.items() if k != "snapshot_sha256"})):
        raise QualityError("quality snapshot integrity mismatch")
    return record


def _prior(dest: Path) -> dict | None:
    if not dest.exists():
        return None
    if (dest.is_symlink() or not dest.is_file()
            or dest.stat().st_size > MAX_SNAPSHOT):
        raise QualityError("unsafe previous quality snapshot")
    try:
        value = json.loads(dest.read_bytes().decode("ascii"))
    except (ValueError, UnicodeError, OSError) as exc:
        raise QualityError("corrupted prior quality snapshot") from exc
    return _snapshot(value)


def optional_hourly_library_quality(
        root: Path, *, stage12_status: str, stage16_status: str,
        auditor=None, clock=None) -> dict:
    """One bounded opt-in QA pass within the original hourly collector lock."""
    root = _root(root)
    runtime = root / "runtime"
    marker = runtime / OPT_IN_FILENAME
    if marker.is_symlink():
        raise QualityError("unsafe quality opt-in marker")
    if not marker.exists():
        return {"status": DISABLED, "operator_opted_in": False,
                "approved_rules_added": 0, "production_approved": False,
                "quality_snapshot_written": False}
    if (not marker.is_file() or marker.stat().st_size > 100
            or marker.read_text("utf-8").strip() != OPT_IN_TOKEN):
        raise QualityError("invalid Stage17 marker")
    if stage12_status not in STAGE12 or stage16_status not in STAGE16:
        raise QualityError("unrecognized hourly review or QA status")
    read = audit_existing_public_library if auditor is None else auditor
    audit = read(root)
    if (type(audit) is not dict
            or audit.get("schema") != "UCIE_PUBLIC_SOURCE_LINKED_AUDIT_V07"
            or audit.get("auto_promoted") is not False
            or audit.get("approved_candidates") != 0
            or audit.get("exportable_rules") != 0
            or audit.get("operating_database_writes") != 0
            or type(audit.get("source_linked_candidates")) is not int
            or not 0 <= audit["source_linked_candidates"] <= 1000
            or audit.get("status") not in (
                "AUDIT_REVIEW_REQUIRED_NO_GO",
                "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
                "RECEIPT_SOURCE_BINDING_CONFLICT_NO_GO")):
        raise QualityError("invalid bounded linked public audit result")
    current = audit["source_linked_candidates"]
    folder, dest = _location(root, create=False)
    previous = _prior(dest)
    if previous and (
            datetime.fromisoformat(previous["finished_utc"]) >
            (datetime.now(timezone.utc) if clock is None else clock)):
        raise QualityError("previous quality receipt in future")
    delta = 0 if previous is None else current - previous["source_candidate_count"]
    if not -1000 <= delta <= 1000:
        raise QualityError("unbounded source candidate change")
    now = datetime.now(timezone.utc) if clock is None else clock
    if not isinstance(now, datetime) or now.tzinfo is None or (
            now.utcoffset() != timedelta(0)):
        raise QualityError("quality snapshot UTC clock required")
    # No claims of independent validation: all source candidates stay
    # UNVERIFIED. Purely count and alarm on internal corpus inconsistencies.
    anomaly = (audit["status"] != AUDIT_OK or delta < 0
               or any(audit.get(k, 0) != 0 for k in (
                   "conflicting_claim_groups", "orphaned_claim_count",
                   "source_sha_conflicts")))
    data = {
        "schema": SCHEMA, "status": REVIEW if anomaly else OBSERVED,
        "finished_utc": now.replace(microsecond=0).isoformat(),
        "source_candidate_count": current,
        "candidate_delta": delta,
        "latest_source_audit_sha256": _digest({
            "status": audit["status"],
            "candidates": sorted(
                r["item_id"] for r in audit.get("candidates", [])),
            "counts": {k: audit[k] for k in (
                "source_linked_candidates", "claim_receipts_integrity_checked",
                "conflicting_claim_groups", "orphaned_claim_count",
                "source_sha_conflicts")},
        }),
        "previous_quality_sha256": None if previous is None
        else previous["snapshot_sha256"],
        "stage12_status": stage12_status, "stage16_status": stage16_status,
        "claim_receipts": audit["claim_receipts_integrity_checked"],
        "conflict_groups": audit["conflicting_claim_groups"],
        "orphaned_claims": audit["orphaned_claim_count"],
        "source_sha_conflicts": audit["source_sha_conflicts"],
        "approved_rule_count": 0, "auto_promoted": False,
        "executed_external_code": False, "code_changes": 0,
        "database_changes": 0, "scheduled_task_changes": 0,
    }
    data["snapshot_sha256"] = _digest(data)
    raw = _canonical(data) + b"\n"
    if len(raw) > MAX_SNAPSHOT:
        raise QualityError("quality snapshot too large")
    _location(root, create=True)
    stage = None
    try:
        fd, temp = tempfile.mkstemp(prefix=".ucie_quality_",
                                    suffix=".tmp", dir=folder)
        stage = Path(temp)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        if dest.is_symlink():
            raise QualityError("snapshot target became unsafe")
        os.replace(stage, dest)
        stage = None
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)
    return {
        "status": data["status"], "operator_opted_in": True,
        "quality_snapshot_written": True,
        "public_unverified_candidates": current,
        "candidate_delta": delta,
        "approved_rules_added": 0, "production_approved": False,
        "snapshot_sha256": data["snapshot_sha256"],
    }


def read_quality_snapshot(root: Path) -> dict:
    _, dest = _location(root, create=False)
    record = _prior(dest)
    if record is None:
        return {"schema": SCHEMA, "status": "STAGE17_QUALITY_SNAPSHOT_ABSENT",
                "automatic_rules_approved": 0, "source_quality_verified": False}
    return record


def main() -> int:
    p = __import__("argparse").ArgumentParser(
        description="UCIE read-only hourly quality observation, no auto learning")
    p.add_argument("--inspect", action="store_true", required=True)
    args = p.parse_args()
    try:
        data = read_quality_snapshot(Path(__file__).resolve().parents[2])
    except (QualityError, ValueError, OSError):
        print(json.dumps({"schema": SCHEMA, "status": "QUALITY_SNAPSHOT_NO_GO"}))
        return 2
    print(json.dumps(data, sort_keys=True, ensure_ascii=True))
    return 0 if data["status"] in (OBSERVED, REVIEW) else 2


if __name__ == "__main__":
    raise SystemExit(main())
