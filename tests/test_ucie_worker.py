"""Synthetic offline checks for local worker locking, safe receipts, and failure handling."""
from __future__ import annotations

import json
import urllib.error
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.worker import _single_instance, _runtime, run_cycle
from ucie_miner.public_discovery import DiscoveryError, classify_stage10_discovery_error


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

    def test_stage10_discovery_failure_safe_categories(self):
        # Fully offline exception objects, NEVER a real network call.
        cases = (
            (urllib.error.HTTPError("https://invalid.example/", 429,
                                    "secret remote content", {}, None),
             "UPSTREAM_HTTP_429"),
            (urllib.error.HTTPError("https://invalid.example/", 403,
                                    "private forbidden details", {}, None),
             "UPSTREAM_HTTP_403"),
            (urllib.error.HTTPError("https://invalid.example/", 503,
                                    "secret upstream", {}, None),
             "UPSTREAM_HTTP_OTHER"),
            (urllib.error.URLError("secret token in URL"),
             "UPSTREAM_NETWORK_FAILURE"),
            (OSError("private local path"),
             "UPSTREAM_IO_OR_TIMEOUT"),
            (json.JSONDecodeError("sensitive content", "}", 0),
             "PUBLIC_JSON_INVALID"),
        )
        for upstream, expected in cases:
            try:
                with self.subTest(category=expected):
                    try:
                        raise DiscoveryError("approved public feed unavailable") from upstream
                    except DiscoveryError as exc:
                        self.assertEqual(classify_stage10_discovery_error(exc), expected)
            finally:
                # HTTPError is a response-like object in Python 3.15;
                # close even synthetic objects to avoid ResourceWarning.
                if isinstance(upstream, urllib.error.HTTPError):
                    upstream.close()
        self.assertEqual(classify_stage10_discovery_error(
            DiscoveryError("a hostile payload: do not store")),
            "DISCOVERY_VALIDATION_OR_RESPONSE_REJECTED")
        self.assertEqual(classify_stage10_discovery_error(
            ValueError("private token")), "OTHER_FAILURE")

    def test_stage10_failure_category_receipt_is_bounded_without_messages(self):
        def optional_stage_failure(root):
            result = valid_collection(root)
            result["stage10"] = {
                "status": "STAGE10_HOURLY_FAILED_NO_GO",
                "error_type": "DiscoveryError",
                "error_category": "UPSTREAM_HTTP_429",
                "error_phase": "STAGE14_OFFICIAL",
            }
            return result
        result = run_cycle(
            self.repo, collect=optional_stage_failure, write_report=local_report)
        self.assertEqual(result["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(result["stage10_status"], "STAGE10_HOURLY_FAILED_NO_GO")
        self.assertEqual(result["stage10_error_type"], "DiscoveryError")
        self.assertEqual(result["stage10_error_category"], "UPSTREAM_HTTP_429")
        self.assertEqual(result["stage10_error_phase"], "STAGE14_OFFICIAL")
        receipt = (self.repo / "runtime" / "last_run.json").read_text("utf-8")
        self.assertNotIn("secret", receipt)
        self.assertEqual(
            json.loads((self.repo / "runtime" / "run_history.jsonl")
                       .read_text("utf-8").strip()),
            result)

    def test_stage10_failure_rejects_untrusted_category_fail_closed(self):
        def invalid_category(root):
            result = valid_collection(root)
            result["stage10"] = {
                "status": "STAGE10_HOURLY_FAILED_NO_GO",
                "error_type": "DiscoveryError",
                "error_category": "UPSTREAM_HTTP_429; secret_token",
            }
            return result
        out = run_cycle(
            self.repo, collect=invalid_category, write_report=local_report)
        self.assertEqual(out["status"], "COLLECTION_FAILED")
        receipt = (self.repo / "runtime" / "last_run.json").read_text("utf-8")
        self.assertNotIn("secret_token", receipt)
        self.assertNotIn("stage10_error_category", receipt)

    def test_stage10_phase_code_must_be_static_allowlisted(self):
        def forged_phase(root):
            result = valid_collection(root)
            result["stage10"] = {
                "status": "STAGE10_HOURLY_FAILED_NO_GO",
                "error_type": "DiscoveryError",
                "error_category": "DISCOVERY_VALIDATION_OR_RESPONSE_REJECTED",
                "error_phase": "STAGE15_FIX_EVIDENCE:SECRET_PATH",
            }
            return result
        result = run_cycle(
            self.repo, collect=forged_phase, write_report=local_report)
        self.assertEqual(result["status"], "COLLECTION_FAILED")
        receipt = (self.repo / "runtime" / "last_run.json").read_text("utf-8")
        self.assertNotIn("SECRET_PATH", receipt)
        self.assertNotIn("stage10_error_phase", receipt)

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
