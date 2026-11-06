"""UCIE-only on-demand READ-ONLY inventory of distinct public miner ledgers.

No connection to other projects, no public HTTP, no scheduled-task mutation,
no training/approval, and no SQLite database creation/migration/writes.
A current TaskScheduler success is NOT inferred from local SQLite/receipts.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
import argparse
import json
import os
from pathlib import Path
import sqlite3

from .core import PUBLIC_SOURCES
from .library_hourly_proof_v12 import HourlyProofError, inspect_hourly_public_library
from .public_candidate_staging import inspect_staged_candidates
from .public_candidate_learning import inspect_review_learning
from .public_discovery import DiscoveryError

SCHEMA = "UCIE_PUBLIC_COLLECTION_INVENTORY_READONLY_V01"
NO_GO = "COLLECTION_INVENTORY_INCOMPLETE_NO_GO"
OBSERVED = "COLLECTION_LEDGER_COUNTS_OBSERVED_SCHEDULER_UNATTESTED"
LEGACY_DB = "public_miner.sqlite3"
LEGACY_CANDIDATE_COLUMNS = (
    "source", "pr_number", "public_url", "merged_at", "evidence_sha256",
    "tags_json", "observed_at", "status",
)
LEGACY_RUN_COLUMNS = (
    "run_id", "at_utc", "sources_count", "added_candidates", "status",
)


class CollectionInventoryError(ValueError):
    """UCIE-only root or ledger validation failed; never use fake zeros."""


def _ucie_runtime(root: Path) -> Path:
    base = Path(root)
    if (base.name.casefold() != "ucie" or not base.is_dir()
            or base.is_symlink()):
        raise CollectionInventoryError("UCIE dedicated root required")
    runtime = base / "runtime"
    if (not runtime.is_dir() or runtime.is_symlink()
            or not runtime.resolve().is_relative_to(base.resolve())):
        raise CollectionInventoryError("UCIE runtime not trusted")
    return runtime


def _safe_file(runtime: Path, name: str) -> Path:
    file = runtime / name
    if file.is_symlink() or (file.exists() and not file.is_file()):
        raise CollectionInventoryError("ledger file is not a regular file")
    return file


def _utc_time(stamp: object) -> str:
    if type(stamp) is not str or len(stamp) > 45:
        raise CollectionInventoryError("invalid run UTC timestamp")
    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CollectionInventoryError("invalid run UTC timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise CollectionInventoryError("run timestamp not UTC")
    return dt.isoformat(timespec="seconds")


def _legacy_counts(runtime: Path) -> dict:
    path = _safe_file(runtime, LEGACY_DB)
    if not path.exists():
        return {
            "status": "LEGACY_MINER_DATABASE_ABSENT_NO_GO",
            "candidates": None, "runs": None,
            "by_source": None, "invalid_status_rows": None,
            "last_run_utc": None, "latest_added_candidates": None,
        }
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                     uri=True, timeout=3)) as conn:
            conn.execute("PRAGMA query_only=ON")
            conn.execute("PRAGMA trusted_schema=OFF")
            if conn.execute("PRAGMA quick_check(1)").fetchone() != ("ok",):
                raise CollectionInventoryError("legacy SQLite integrity failed")
            names = set(conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall())
            if not {("candidates",), ("runs",)} <= names:
                raise CollectionInventoryError("legacy expected tables missing")
            for table, expected in (
                    ("candidates", LEGACY_CANDIDATE_COLUMNS),
                    ("runs", LEGACY_RUN_COLUMNS)):
                columns = tuple(row[1] for row in conn.execute(
                    "PRAGMA table_info(" + table + ")"))
                if columns != expected:
                    raise CollectionInventoryError("legacy schema drift")
            candidates = conn.execute(
                "SELECT COUNT(*) FROM candidates").fetchone()[0]
            runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            invalid = conn.execute("""
                SELECT COUNT(*) FROM candidates
                WHERE status != 'UNVERIFIED_CANDIDATE_ONLY'
            """).fetchone()[0]
            group = conn.execute("""
                SELECT source, COUNT(*) FROM candidates
                GROUP BY source ORDER BY source
            """).fetchall()
            latest = conn.execute("""
                SELECT at_utc, added_candidates, status
                FROM runs ORDER BY run_id DESC LIMIT 1
            """).fetchone()
    except sqlite3.Error as exc:
        raise CollectionInventoryError("legacy SQLite read failed") from exc
    if (type(candidates) is not int or type(runs) is not int
            or type(invalid) is not int or min(candidates, runs, invalid) < 0
            or invalid or sum(count for _, count in group) != candidates
            or any(source not in PUBLIC_SOURCES or type(count) is not int
                   or count < 0 for source, count in group)):
        raise CollectionInventoryError("legacy counts/status invalid")
    last = None
    added = None
    if latest is not None:
        last = _utc_time(latest[0])
        added = latest[1]
        if (type(added) is not int or not 0 <= added <= candidates
                or latest[2] not in (
                    "COLLECTED_UNVERIFIED", "COLLECTION_FAILED",
                    "COLLECTED_UNVERIFIED_PARTIAL_NO_GO")):
            raise CollectionInventoryError("untrusted latest legacy run")
    if (runs == 0) != (latest is None):
        raise CollectionInventoryError("legacy run count inconsistent")
    return {
        "status": "LEGACY_UNVERIFIED_COUNT_READ_ONLY",
        "candidates": candidates, "runs": runs,
        "by_source": dict(group), "invalid_status_rows": invalid,
        "last_run_utc": last, "latest_added_candidates": added,
    }


def collection_inventory(root: Path, *, now: datetime | None = None,
                         legacy_reader=None, stage10_reader=None,
                         stage12_reader=None, hourly_reader=None) -> dict:
    """On-demand single snapshot; never sum overlapping ledgers.

    Allows dependency-injected readers for synthetic offline tests only.
    Live code uses only the existing UCIE read-only inspectors.
    """
    runtime = _ucie_runtime(root)
    stamp = datetime.now(timezone.utc) if now is None else now
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise CollectionInventoryError("UTC report timestamp required")
    issues = []
    try:
        legacy = (_legacy_counts if legacy_reader is None else legacy_reader)(runtime)
        if legacy.get("status") != "LEGACY_UNVERIFIED_COUNT_READ_ONLY":
            issues.append("LEGACY_LEDGER_NOT_AVAILABLE")
    except (CollectionInventoryError, sqlite3.Error, OSError):
        legacy = {
            "status": "LEGACY_LEDGER_INVALID_NO_GO", "candidates": None,
            "runs": None, "by_source": None, "invalid_status_rows": None,
            "last_run_utc": None, "latest_added_candidates": None,
        }
        issues.append("LEGACY_LEDGER_INVALID")
    try:
        stage10 = (inspect_staged_candidates if stage10_reader is None
                   else stage10_reader)(root)
        if stage10.get("status") not in (
                "UNVERIFIED_CANDIDATE_STAGING_INSPECTED_NO_GO",
                "STAGING_FILE_ABSENT"):
            raise CollectionInventoryError("Stage10 inspect failed")
        if any(type(stage10.get(key)) is not int or stage10[key] < 0
               for key in ("candidate_revisions", "git_commit_revisions")):
            raise CollectionInventoryError("Stage10 invalid counters")
        stage10 = {
            "status": stage10["status"],
            "candidate_revisions": stage10["candidate_revisions"],
            "git_commit_revisions": stage10["git_commit_revisions"],
        }
    except (CollectionInventoryError, DiscoveryError, sqlite3.Error, OSError,
            ValueError, KeyError, TypeError):
        stage10 = {"status": "STAGE10_LEDGER_INVALID_NO_GO",
                   "candidate_revisions": None, "git_commit_revisions": None}
        issues.append("STAGE10_LEDGER_INVALID")
    try:
        stage12 = (inspect_review_learning if stage12_reader is None
                   else stage12_reader)(root)
        if stage12.get("status") not in (
                "STAGE12_UNVERIFIED_REVIEW_INSPECTED_NO_GO",
                "STAGE12_REVIEW_LEDGER_ABSENT"):
            raise CollectionInventoryError("Stage12 inspect failed")
        if (type(stage12.get("review_proposals")) is not int
                or stage12["review_proposals"] < 0):
            raise CollectionInventoryError("Stage12 invalid count")
        stage12 = {"status": stage12["status"],
                   "review_proposals": stage12["review_proposals"]}
    except (CollectionInventoryError, DiscoveryError, sqlite3.Error, OSError,
            ValueError, KeyError, TypeError):
        stage12 = {"status": "STAGE12_LEDGER_INVALID_NO_GO",
                   "review_proposals": None}
        issues.append("STAGE12_LEDGER_INVALID")
    try:
        hourly = (inspect_hourly_public_library if hourly_reader is None
                  else hourly_reader)(root, now=stamp)
        if hourly.get("schema") != "UCIE_HOURLY_PUBLIC_LIBRARY_PROOF_V12":
            raise CollectionInventoryError("untrusted hourly receipt schema")
        freshness_status = hourly["status"]
        if freshness_status not in (
                "TWO_FRESH_CYCLE_RECEIPTS_OBSERVED_SCHEDULER_NOT_ATTESTED",
                "HOURLY_CYCLE_ACTIVITY_NOT_PROVEN_NO_GO"):
            raise CollectionInventoryError("untrusted activity state")
        last_utc = _utc_time(hourly["latest_finished_utc"])
        recent = {
            "status": freshness_status,
            "last_finished_utc": last_utc,
            "last_finished_age_minutes": hourly["last_completed_age_minutes"],
            "latest_new_unverified_candidates":
                hourly["latest_new_unverified_candidates"],
            "two_successful_collection_receipts":
                hourly["two_successful_collection_receipts"],
        }
        if freshness_status != "TWO_FRESH_CYCLE_RECEIPTS_OBSERVED_SCHEDULER_NOT_ATTESTED":
            issues.append("HOURLY_RECENT_ACTIVITY_UNPROVEN")
    except (HourlyProofError, CollectionInventoryError, OSError, ValueError,
            KeyError, TypeError):
        recent = {"status": "HOURLY_RECEIPTS_UNAVAILABLE_NO_GO",
                  "last_finished_utc": None,
                  "last_finished_age_minutes": None,
                  "latest_new_unverified_candidates": None,
                  "two_successful_collection_receipts": False}
        issues.append("HOURLY_RECEIPTS_UNAVAILABLE")
    return {
        "schema": SCHEMA,
        "status": OBSERVED if not issues else NO_GO,
        "captured_utc": stamp.isoformat(timespec="seconds"),
        "legacy_miner": legacy,
        "stage10_public_candidate_staging": stage10,
        "stage12_unverified_review": stage12,
        "recent_hourly_activity": recent,
        "current_windows_task_scheduler_events_verified": False,
        "windows_task_proof_owner_command": r"D:\UCIE\scripts\task_status.ps1 -Evidence",
        "totals_from_distinct_ledgers_are_not_additive": True,
        "w04_search_matches_are_not_total_candidate_counts": True,
        "source_code_or_project_data_scanned": False,
        "public_network_requests": 0,
        "operating_database_writes": 0,
        "scheduler_changed": False,
        "approved_rules_inferred": 0,
        "issues": issues,
    }


def render_report_markdown(report: dict) -> str:
    if type(report) is not dict or report.get("schema") != SCHEMA:
        raise CollectionInventoryError("unknown report data")
    legacy, stage10, stage12, hourly = (
        report["legacy_miner"], report["stage10_public_candidate_staging"],
        report["stage12_unverified_review"], report["recent_hourly_activity"])
    def display(value):
        return "확인 불가" if value is None else str(value)
    lines = [
        "# UCIE 자동 수집 현황 (읽기 전용)",
        "",
        "- UTC 집계: " + report["captured_utc"],
        "- 판정: " + report["status"],
        "- 기본 공개 PR 후보: " + display(legacy["candidates"]) + "건",
        "- 기본 수집 실행: " + display(legacy["runs"]) + "회",
        "- 기본 마이너 마지막 기록: " + display(legacy["last_run_utc"]),
        "- Stage10 미검증 PR 개정: " + display(stage10["candidate_revisions"]) + "건",
        "- Stage10 공개 커밋 개정: " + display(stage10["git_commit_revisions"]) + "건",
        "- Stage12 별도 검토 제안: " + display(stage12["review_proposals"]) + "건",
        "- 최근 시간당 실행 상태: " + hourly["status"],
        "- 최근 시간당 완료 UTC: " + display(hourly["last_finished_utc"]),
        "- Windows TaskScheduler 실이벤트 검증: 별도 확인 필요",
        "",
        "주의: 서로 다른 원장의 건수는 중복될 수 있으므로 합산하지 않습니다.",
        "조회 결과가 0건인 것과 파일이 없거나 검증되지 않은 것은 구분합니다.",
        "자동 규칙 승인·모델 학습·다른 프로젝트 조회·운영 DB 쓰기는 실행하지 않았습니다.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE public miner count snapshot, read only")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if (os.name == "nt" and root.resolve() != Path("D:/UCIE").resolve()):
        print(json.dumps({"schema": SCHEMA, "status": NO_GO,
                          "reason": "UCIE_OWNER_ROOT_REQUIRED"}))
        return 3
    try:
        report = collection_inventory(root)
    except (CollectionInventoryError, OSError):
        print(json.dumps({"schema": SCHEMA, "status": NO_GO,
                          "reason": "ROOT_OR_RUNTIME_UNAVAILABLE"}))
        return 3
    if args.format == "markdown":
        print(render_report_markdown(report), end="")
    else:
        print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0 if report["status"] == OBSERVED else 2


if __name__ == "__main__":
    raise SystemExit(main())
