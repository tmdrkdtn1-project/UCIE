"""UCIE-only 05:00 KST cut-off report PREVIEW from the legacy public miner.

This module never sends messages, writes reports, modifies SQLite, starts a
collector, scans user projects, authorizes rules or makes network calls.
A verified cut-off calculation is NOT proof of 09:00 delivery.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sqlite3

KST = timezone(timedelta(hours=9))
UTC = timezone.utc
ALLOWED_LEGACY = frozenset({"python/cpython", "PowerShell/PowerShell"})
SCHEMA = "UCIE_PUBLIC_MINER_DAILY_0500_CUTOFF_PREVIEW_V01"


class DailyCutoffError(ValueError):
    """Unavailable or unsafe UCIE-only snapshot."""


def cutoff_window(day: date) -> tuple[str, str]:
    if type(day) is not date:
        raise DailyCutoffError("invalid report day")
    try:
        cutoff = datetime(day.year, day.month, day.day, 5, tzinfo=KST)
        previous = cutoff - timedelta(days=1)
        return (previous.astimezone(UTC).isoformat(timespec="seconds"),
                cutoff.astimezone(UTC).isoformat(timespec="seconds"))
    except (ValueError, OverflowError) as exc:
        raise DailyCutoffError("invalid report window") from exc


def inspect_snapshot(repo_root: Path, day: date) -> dict:
    if not isinstance(repo_root, Path) or repo_root.is_symlink():
        raise DailyCutoffError("invalid UCIE checkout")
    root = repo_root.resolve()
    if root.name.casefold() != "ucie" or not (root / ".git").is_dir():
        raise DailyCutoffError("UCIE checkout not verified")
    runtime = root / "runtime"
    target = runtime / "public_miner.sqlite3"
    if (runtime.is_symlink() or target.is_symlink() or
            not runtime.is_dir() or not target.is_file()):
        raise DailyCutoffError("UCIE runtime DB unavailable")
    start_utc, cutoff_utc = cutoff_window(day)
    # SQLite URI mode=ro and query_only are both enforced. No _db() creator.
    connection = None
    try:
        connection = sqlite3.connect(
            "file:" + target.as_posix() + "?mode=ro",
            uri=True, timeout=2.0)
        connection.execute("PRAGMA query_only=ON")
        rows = connection.execute(
            "SELECT source, COUNT(*) FROM candidates "
            "WHERE observed_at < ? GROUP BY source ORDER BY source",
            (cutoff_utc,)).fetchall()
        added = connection.execute(
            "SELECT COUNT(*) FROM candidates "
            "WHERE observed_at >= ? AND observed_at < ?",
            (start_utc, cutoff_utc)).fetchone()[0]
        cycles = connection.execute(
            "SELECT COUNT(*) FROM runs "
            "WHERE at_utc >= ? AND at_utc < ?",
            (start_utc, cutoff_utc)).fetchone()[0]
        last = connection.execute(
            "SELECT at_utc, status FROM runs WHERE at_utc < ? "
            "ORDER BY at_utc DESC LIMIT 1", (cutoff_utc,)).fetchone()
        bad = connection.execute(
            "SELECT COUNT(*) FROM candidates WHERE status != "
            "'UNVERIFIED_CANDIDATE_ONLY' AND observed_at < ?",
            (cutoff_utc,)).fetchone()[0]
        if bad:
            raise DailyCutoffError("unverified status contract drift")
        sources = {}
        for name, count in rows:
            if type(name) is not str or name not in ALLOWED_LEGACY:
                raise DailyCutoffError("unexpected public source")
            if type(count) is not int or count < 0:
                raise DailyCutoffError("invalid candidate count")
            sources[name] = count
        if type(added) is not int or type(cycles) is not int:
            raise DailyCutoffError("invalid snapshot totals")
        return {
            "schema": SCHEMA,
            "status": "CUTOFF_PREVIEW_NO_DELIVERY_PROOF",
            "report_day_kst": day.isoformat(),
            "window_start_utc_inclusive": start_utc,
            "window_end_utc_exclusive": cutoff_utc,
            "scheduled_delivery_hour_kst": "09:00",
            "candidates_all_time_as_of_cutoff": sum(sources.values()),
            "new_candidates_in_window": added,
            "cycle_runs_in_window": cycles,
            "legacy_source_counts": sources,
            "last_run_at_or_before_cutoff_utc": last[0] if last else None,
            "last_run_status_unverified": last[1] if last else None,
            "status_if_no_changes": "REPORT_STILL_REQUIRED",
            "report_sent": False,
            "delivery_receipt_verified": False,
            "owner_operating_database_writes": 0,
            "scheduled_task_changed": False,
            "rule_auto_promotion": False,
            "release_approved": False,
        }
    except (sqlite3.Error, OSError) as exc:
        raise DailyCutoffError("read-only snapshot unavailable") from exc
    finally:
        if connection is not None:
            connection.close()
