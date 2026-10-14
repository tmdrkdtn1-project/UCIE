"""Synthetic collector adapter tests; no network requests."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.adapter import inspect_collected_pr
from ucie_miner.core import MiningError


class AdapterTests(unittest.TestCase):
    def test_minimal_collector_record_is_never_promoted(self):
        pr = {"number": 42, "merged_at": "2026-10-01T10:00:00Z"}
        result = inspect_collected_pr("python/cpython", pr,
                                      [{"filename": "Lib/x.py", "patch": "+pass"}])
        self.assertEqual(result["status"], "INCOMPLETE_PROVENANCE")
        self.assertEqual(result["verification_pass"], 0)
        self.assertFalse(result["rule_promoted"])
        self.assertIn("merge_commit_sha", result["missing_fields"])

    def test_unapproved_source_rejected(self):
        with self.assertRaises(MiningError):
            inspect_collected_pr("unapproved/repo", {"number": 2}, [])

    def test_complete_claim_is_still_unverified(self):
        sha = "a" * 40
        pr = {"number": 42, "merged_at": "2026-10-01T10:00:00Z",
              "updated_at": "2026-10-02T10:00:00Z", "merge_commit_sha": sha,
              "license": "MIT",
              "license_url": "https://github.com/python/cpython/blob/" + sha + "/LICENSE"}
        result = inspect_collected_pr("python/cpython", pr,
                                      [{"filename": "Lib/x.py", "patch": "-pass\n+raise ValueError"}])
        self.assertEqual(result["status"], "UNVERIFIED_CANDIDATE_ONLY")
        self.assertFalse(result["metadata_authenticated"])
        self.assertEqual(result["verification_pass"], 0)

    def test_invalid_collector_file_rejected(self):
        with self.assertRaises(MiningError):
            inspect_collected_pr("python/cpython", {"number": 42}, ["bad"])
