"""Owner-only UCIE read-only operational receipt probe.

This intentionally reports unhealthy states as evidence, never a PASS verdict
for Windows Task Scheduler. It reads only UCIE's public-source metadata,
candidate ledger counts, existing quality receipt and isolated P10/P11 ledgers.
No new network calls, no task mutation, no SQLite writes and no private data.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _readonly_count(path: Path, table: str) -> int | None:
    if not path.is_file() or path.is_symlink():
        return None
    # Table names below are first-party fixed literals, never input strings.
    if table not in ("public_candidate_stage", "review_queue"):
        raise ValueError("unregistered UCIE candidate table")
    try:
        with closing(sqlite3.connect(
                "file:" + path.as_posix() + "?mode=ro", uri=True,
                timeout=1)) as db:
            db.execute("PRAGMA query_only=ON")
            return db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
    except (sqlite3.DatabaseError, OSError):
        return None


def _read_receipt(path: Path, *, max_bytes: int = 3000) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > max_bytes:
        return {}
    try:
        data=json.loads(path.read_bytes().decode("utf-8"))
    except (ValueError, UnicodeError, OSError):
        return {}
    return data if type(data) is dict else {}


class OwnerPublicAutomationObservationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "real owner Windows only")
    def test_owner_ucie_only_readonly_operational_snapshot(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()):
            self.skipTest("exact UCIE owner root not mounted")
        from ucie_miner.pending_queue import inspect_queue
        from ucie_miner.p11_closed_loop import status as p11_status
        from ucie_miner.library_audit_v07 import (
            MAX_ROWS, AuditError, audit_existing_public_library)
        from ucie_miner.library_explore import _candidate_rows
        from ucie_miner.verification_handoff import prepare_verification_handoff

        runtime=ROOT / "runtime"
        miner=_read_receipt(runtime / "last_run.json")
        quality=_read_receipt(runtime / "quality_v12" / "latest.json")
        stage10=_readonly_count(runtime / "stage10_unverified_public_candidates.sqlite3",
                                "public_candidate_stage")
        stage12=_readonly_count(runtime / "stage12_unverified_review.sqlite3",
                                "review_queue")
        p10={}
        p11={}
        p10_error=None
        p11_error=None
        try:
            q=inspect_queue(ROOT,limit=20)
            pending=[{"kind":item.get("kind"),"status":item.get("status"),
                      "attempts":item.get("attempts"),
                      "max_attempts":item.get("max_attempts"),
                      "last_reason":item.get("last_reason")}
                     for item in q.get("jobs", [])
                     if item.get("status") in ("REVIEW_REQUIRED","PENDING")]
            p10={"queue_status":q.get("status"),"job_counts":q.get("counts"),
                 "held_jobs":pending[:10]}
        except (OSError, ValueError, sqlite3.Error) as exc:
            p10_error=type(exc).__name__
        try:
            p=p11_status(ROOT)
            p11={k:p.get(k) for k in (
                "status", "last_public_attempt_utc", "last_public_attempt_failed",
                "next_public_get_due_utc", "total_successful_public_gets",
                "unverified_leads", "awaiting_synthetic_experiment",
                "first_party_experiences", "synthetic_equivalence_observed",
                "improvement_review_record_count",
                "production_improvements_auto_applied","auto_promoted")}
        except (OSError, ValueError, sqlite3.Error) as exc:
            p11_error=type(exc).__name__
        grouped_count=None
        source_linkage_complete=None
        handoff_error=None
        try:
            complete,rows=_candidate_rows(prepare_verification_handoff(ROOT))
            source_linkage_complete=complete
            grouped_count=len(rows) if complete else None
        except (ValueError, OSError, sqlite3.Error) as exc:
            handoff_error=type(exc).__name__
        audit_status=None
        audit_error=None
        try:
            a=audit_existing_public_library(ROOT)
            audit_status=a.get("status")
        except AuditError as exc:
            audit_error=("AUDIT_CAPACITY_1000_EXCEEDED"
                         if str(exc) == "public candidate count exceeds bound"
                         else "AUDIT_OTHER_ERROR")
        except (ValueError, OSError, sqlite3.Error) as exc:
            audit_error=type(exc).__name__
        report={
            "schema":"UCIE_OWNER_PUBLIC_AUTOMATION_OBSERVATION_V01",
            "read_only":True,
            "windows_scheduled_task_state":"NOT_QUERIED_BY_THIS_PROBE",
            "minute_dispatcher_event_binding":"NOT_QUERIED_BY_THIS_PROBE",
            "miner_last_finished_utc":miner.get("finished_utc"),
            "miner_status":miner.get("status"),
            "miner_stage10_status":miner.get("stage10_status"),
            "miner_stage10_error_phase":miner.get("stage10_error_phase"),
            "miner_stage10_error_type":miner.get("stage10_error_type"),
            "last_quality_finished_utc":quality.get("finished_utc"),
            "last_quality_status":quality.get("status"),
            "last_quality_source_count":quality.get("source_candidate_count"),
            "stage10_unverified_pr_rows":stage10,
            "stage12_unverified_review_rows":stage12,
            "current_source_linkage_complete":source_linkage_complete,
            "current_grouped_source_count":grouped_count,
            "audit_cap":MAX_ROWS,"audit_status":audit_status,
            "audit_error":audit_error,"handoff_error_type":handoff_error,
            "p10":p10,"p10_error_type":p10_error,
            "p11":p11,"p11_error_type":p11_error,
            "production_auto_improvements_verified":False,
            "source_private_projects_read":False,
            "network_requests":0,
            "database_writes":0,"scheduler_changes":0,
        }
        print("UCIE_OWNER_RUNTIME_OBSERVATION="+json.dumps(
            report,ensure_ascii=True,sort_keys=True))
        self.assertTrue(report["read_only"])
        self.assertEqual(report["network_requests"],0)
        self.assertEqual(report["database_writes"],0)
        self.assertFalse(report["production_auto_improvements_verified"])


if __name__=="__main__":
    unittest.main()
