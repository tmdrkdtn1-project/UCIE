"""UCIE stage17 audit capacity and hourly worker receipt bound must agree.

Uses only first-party synthetic results in TemporaryDirectory, no network,
scheduler or operating DB. Owner-host extra test reads exact last_run receipt.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ucie_miner.worker import run_cycle
from ucie_miner.library_audit_v07 import MAX_ROWS as AUDIT_MAX_ROWS

ROOT = Path(__file__).resolve().parents[1]


def synthetic_cycle(count: int, delta: int) -> dict:
    with TemporaryDirectory(prefix="UCIE_WORKER_STAGE17_SYNTH_") as temp:
        root = Path(temp) / "UCIE"
        root.mkdir()

        def collect(_root: Path) -> dict:
            return {
                "schema": "UCIE_MINER_RESULT_V1",
                "status": "COLLECTED_UNVERIFIED",
                "new_candidates": 0,
                "sources_checked": 2,
                "verification_pass": 0,
                "production_approved": False,
                "stage10": {
                    "status": "STAGE10_UNVERIFIED_STAGED_NO_GO",
                    "stage17_quality_status":
                        "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO",
                    "stage17_quality_candidate_count": count,
                    "stage17_quality_candidate_delta": delta,
                },
            }

        def report(repo: Path) -> Path:
            folder = repo / "runtime" / "reports"
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / "synthetic.md"
            target.write_text("UCIE isolated synthetic report only\n",
                              encoding="utf-8")
            return target

        return run_cycle(root, collect=collect, write_report=report,
                         enforce_schedule=False)


class Stage17WorkerReceiptCapacityTests(unittest.TestCase):
    def test_01_source_cap_is_bounded_2000(self):
        self.assertEqual(AUDIT_MAX_ROWS, 2000)

    def test_02_realistic_1313_and_exact_cap_are_accepted(self):
        for count, delta in ((1313, 321), (2000, 2000)):
            with self.subTest(count=count):
                receipt = synthetic_cycle(count, delta)
                self.assertEqual(receipt["status"], "COLLECTED_UNVERIFIED",
                                 receipt)
                self.assertEqual(receipt["stage17_quality_candidate_count"],
                                 count)
                self.assertEqual(receipt["stage17_quality_candidate_delta"],
                                 delta)
                self.assertEqual(receipt["verification_pass"], 0)
                self.assertFalse(receipt["production_approved"])

    def test_03_over_cap_rejected_before_full_hourly_acceptance(self):
        receipt = synthetic_cycle(2001, 0)
        self.assertEqual(receipt["status"], "COLLECTION_FAILED")
        self.assertEqual(receipt["error_type"], "ValueError")
        self.assertEqual(receipt["error_phase"],
                         "COLLECTOR_RESULT_VALIDATION")
        self.assertFalse(receipt["production_approved"])

    def test_04_delta_over_cap_rejected(self):
        for delta in (-2001, 2001):
            with self.subTest(delta=delta):
                receipt = synthetic_cycle(1313, delta)
                self.assertEqual(receipt["status"], "COLLECTION_FAILED")
                self.assertEqual(receipt["error_phase"],
                                 "COLLECTOR_RESULT_VALIDATION")

    def test_05_exact_negative_delta_bound_is_accepted(self):
        receipt = synthetic_cycle(0, -2000)
        self.assertEqual(receipt["status"], "COLLECTED_UNVERIFIED", receipt)

    @unittest.skipUnless(os.name == "nt", "UCIE owner Windows only")
    def test_06_owner_last_run_error_receipt_read_only(self):
        if (ROOT.resolve() != Path("D:/UCIE").resolve()
                or ROOT.is_symlink() or not (ROOT / ".git").is_dir()):
            self.skipTest("exact UCIE owner checkout unavailable")
        target = ROOT / "runtime" / "last_run.json"
        self.assertTrue(target.is_file() and not target.is_symlink())
        self.assertLessEqual(target.stat().st_size, 4096)
        data = json.loads(target.read_text(encoding="utf-8"))
        observed = {
            "schema": "UCIE_STAGE17_WORKER_LAST_RUN_READONLY_V14",
            "last_finished_utc": data.get("finished_utc"),
            "last_status": data.get("status"),
            "error_type": data.get("error_type"),
            "error_phase": data.get("error_phase"),
            "stage10_status": data.get("stage10_status"),
            "stage17_quality_candidate_count":
                data.get("stage17_quality_candidate_count"),
            "network_requests": 0,
            "task_changes": 0,
            "db_writes": 0,
        }
        print("UCIE_STAGE17_WORKER_LAST_RUN=" + json.dumps(
            observed, sort_keys=True, ensure_ascii=True))
        self.assertIn(data.get("status"),
                      ("COLLECTION_FAILED", "COLLECTED_UNVERIFIED",
                       "COLLECTED_UNVERIFIED_PARTIAL_NO_GO"))
        self.assertEqual(observed["db_writes"], 0)


if __name__ == "__main__":
    unittest.main()
