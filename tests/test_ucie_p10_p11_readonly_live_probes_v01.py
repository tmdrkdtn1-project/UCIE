"""UCIE-only owner P10/P11 blocker snapshot; explicitly read-only.

Run ONLY as a reviewed one-file unittest via the existing UCIE admin bridge.
Never run a worker, dispatch tick, queue rearm, public GET or Task mutation.
The output records present-day handler contract observations, not historic cause.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
from time import perf_counter
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "UCIE_P10_P11_CURRENT_DEPENDENCY_READONLY_V01"


def _queue_summary(root: Path) -> dict:
    from ucie_miner.pending_queue import inspect_queue
    queue = inspect_queue(root, limit=20)
    return {
        "status": queue.get("status"),
        "counts": queue.get("counts"),
        "held": [
            {
                "kind": job.get("kind"),
                "status": job.get("status"),
                "attempts": job.get("attempts"),
                "max_attempts": job.get("max_attempts"),
                "last_reason": job.get("last_reason"),
            }
            for job in queue.get("jobs", [])
            if job.get("status") == "REVIEW_REQUIRED"
        ],
    }


def _p11_summary(root: Path) -> dict:
    from ucie_miner.p11_closed_loop import status
    result = status(root)
    return {key: result.get(key) for key in (
        "status", "sources", "next_source_id", "quiet_collection_backoff",
        "effective_interval_minutes", "last_public_attempt_utc",
        "last_public_attempt_failed", "last_failed_public_attempt_category",
        "next_public_get_due_utc",
        "total_successful_public_gets", "unverified_leads",
        "awaiting_synthetic_experiment", "first_party_experiences",
        "improvement_review_record_count", "production_improvements_auto_applied",
        "auto_promoted",
    )}


def _observe_handler(label: str, handler) -> dict:
    start = perf_counter()
    try:
        result = handler()
        record = {
            "path": label,
            "call_completed": True,
            "schema": result.get("schema") if type(result) is dict else None,
            "status": result.get("status") if type(result) is dict else None,
            "network_requests_reported": (
                result.get("network_requests") if type(result) is dict else None
            ),
            "operating_database_writes_reported": (
                result.get("operating_database_writes") if type(result) is dict else None
            ),
        }
        if label == "PUBLIC_METADATA_REVIEW":
            record["linked_candidate_count"] = result.get("source_linked_count")
            record["grouped_matches"] = result.get("total_matches")
        elif label == "UCIE_REPORT_PREPARATION":
            record["v1_accepted"] = result.get("v1_accepted")
            record["package_released"] = result.get("package_released")
    except Exception as exc:
        record = {
            "path": label,
            "call_completed": False,
            "error_type": type(exc).__name__,
        }
    record["elapsed_ms"] = round((perf_counter() - start) * 1000, 3)
    return record


class UCIEOwnerReadOnlyBlockerProbes(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "owner Windows only")
    def test_current_p10_handlers_and_p11_ledger_do_not_rearm(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()
                or not (ROOT / "runtime").is_dir()):
            self.skipTest("exact dedicated UCIE owner checkout unavailable")

        from ucie_miner.library_search import search_existing_public_library
        from ucie_miner.product_v1 import integrated_product_preview

        queue_before = _queue_summary(ROOT)
        p11_before = _p11_summary(ROOT)
        with patch.object(socket.socket, "connect",
                          side_effect=RuntimeError("UCIE_NETWORK_BLOCKED")), patch(
                "socket.create_connection",
                side_effect=RuntimeError("UCIE_NETWORK_BLOCKED")):
            checks = [
                _observe_handler(
                    "PUBLIC_METADATA_REVIEW",
                    lambda: search_existing_public_library(
                        ROOT, query="", limit=1, group_revisions=True)),
                _observe_handler(
                    "UCIE_REPORT_PREPARATION",
                    lambda: integrated_product_preview(
                        ROOT, query="", limit=1)),
            ]

        queue_after = _queue_summary(ROOT)
        p11_after = _p11_summary(ROOT)
        unchanged = queue_before == queue_after and p11_before == p11_after
        report = {
            "schema": SCHEMA,
            "status": "P10_P11_READONLY_DEPENDENCY_OBSERVED_NO_REARM",
            "checks": checks,
            "queue": queue_after,
            "p11": p11_after,
            "queue_and_p11_state_unchanged": unchanged,
            "scheduler_inspected": False,
            "historical_failure_root_cause_proven": False,
            "public_fetch_attempted": False,
            "worker_dispatched": False,
            "queue_rearmed": False,
            "scheduler_changed": False,
            "model_or_training_invoked": False,
        }
        print("UCIE_P10_P11_LIVE_PROBE=" + json.dumps(
            report, sort_keys=True, ensure_ascii=True))
        self.assertTrue(unchanged)
        self.assertEqual(len(checks), 2)
        self.assertFalse(report["queue_rearmed"])


if __name__ == "__main__":
    unittest.main()
