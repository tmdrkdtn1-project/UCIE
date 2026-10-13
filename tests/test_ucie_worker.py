"""Synthetic offline checks for local worker locking, safe receipts, and failure handling."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.worker import _single_instance, _runtime, run_cycle


def valid_collection(root: Path) -> dict:
    return {
        "status": "COLLECTED_UNVERIFIED",
        "new_candidates": 2,
        "sources_checked": 1,
        "verification_pass": 0,
        "production_approved": False,
    }


def local_report(root: Path) -> Path:
    dest = root / "runtime" / "reports"
    dest.mkdir(exist_ok=True)
    path = dest / "sample.md"
    path.write_text("# UNVERIFIED candidates only\n", encoding="utf-8")
    return path


class MinerWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)

    def test_success_writes_local_receipt(self):
        result = run_cycle(self.repo, collect=valid_collection, write_report=local_report)
        self.assertEqual(result["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(result["new_candidates"], 2)
        self.assertFalse(result["production_approved"])
        last = json.loads((self.repo / "runtime" / "last_run.json").read_text("utf-8"))
        self.assertEqual(last, result)
        history = (self.repo / "runtime" / "run_history.jsonl").read_text("utf-8").splitlines()
        self.assertEqual(len(history), 1)

    def test_failure_stores_error_type_not_sensitive_exception(self):
        def unsafe_error(root):
            raise RuntimeError("github_pat_SENSITIVE_DO_NOT_RECORD")
        result = run_cycle(self.repo, collect=unsafe_error, write_report=local_report)
        self.assertEqual(result["status"], "COLLECTION_FAILED")
        record = (self.repo / "runtime" / "last_run.json").read_text("utf-8")
        self.assertNotIn("SENSITIVE_DO_NOT_RECORD", record)
        self.assertIn('"error_type": "RuntimeError"', record)

    def test_reject_verification_claim(self):
        def fake_verified(root):
            result = valid_collection(root)
            result["verification_pass"] = 9
            return result
        result = run_cycle(self.repo, collect=fake_verified, write_report=local_report)
        self.assertEqual(result["status"], "COLLECTION_FAILED")

    def test_reject_external_report_path(self):
        with tempfile.TemporaryDirectory() as other:
            external = Path(other) / "external.md"
            external.write_text("NOPE")
            result = run_cycle(self.repo, collect=valid_collection, write_report=lambda _: external)
        self.assertEqual(result["status"], "COLLECTION_FAILED")

    def test_single_instance_lock(self):
        runtime = _runtime(self.repo)
        with _single_instance(runtime) as first:
            self.assertTrue(first)
            result = run_cycle(self.repo, collect=valid_collection, write_report=local_report)
            self.assertEqual(result["status"], "SKIPPED_ALREADY_RUNNING")
        # OS released its lock and the next run can proceed
        result = run_cycle(self.repo, collect=valid_collection, write_report=local_report)
        self.assertEqual(result["status"], "COLLECTED_UNVERIFIED")

    def test_local_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            try:
                (self.repo / "runtime").symlink_to(Path(outside), target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest("test system cannot create symlink")
            with self.assertRaises(ValueError):
                _runtime(self.repo)

if __name__ == "__main__":
    unittest.main()
