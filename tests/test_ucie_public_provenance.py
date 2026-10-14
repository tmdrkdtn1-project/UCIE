"""Synthetic no-network PR metadata checks."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.public_provenance import crosscheck_pr_metadata
from ucie_miner.core import MiningError


class PublicProvenanceTests(unittest.TestCase):
    def detail(self):
        return {"number": 42, "html_url": "https://github.com/python/cpython/pull/42",
                "state": "closed", "merged": True,
                "merged_at": "2026-10-01T00:00:00Z",
                "updated_at": "2026-10-02T00:00:00Z",
                "merge_commit_sha": "a" * 40}

    def item(self):
        return {"number": 42, "merged_at": "2026-10-01T00:00:00Z"}

    def test_matching_public_metadata_is_not_a_license_pass(self):
        result = crosscheck_pr_metadata("python/cpython", self.item(),
                                       fetch=lambda url: self.detail())
        self.assertEqual(result["status"], "PUBLIC_PR_METADATA_CROSSCHECKED")
        self.assertFalse(result["license_verified"])
        self.assertFalse(result["rule_promoted"])

    def test_mismatched_merge_denied(self):
        detail = self.detail()
        detail["merged_at"] = "2026-09-01T00:00:00Z"
        with self.assertRaises(MiningError):
            crosscheck_pr_metadata("python/cpython", self.item(), fetch=lambda _: detail)

    def test_unmerged_denied(self):
        detail = self.detail()
        detail["merged"] = False
        with self.assertRaises(MiningError):
            crosscheck_pr_metadata("python/cpython", self.item(), fetch=lambda _: detail)

    def test_bad_sha_denied(self):
        detail = self.detail()
        detail["merge_commit_sha"] = "not-a-sha"
        with self.assertRaises(MiningError):
            crosscheck_pr_metadata("python/cpython", self.item(), fetch=lambda _: detail)

    def test_unapproved_source_never_fetches(self):
        with self.assertRaises(MiningError):
            crosscheck_pr_metadata("notapproved/code", self.item(),
                                   fetch=lambda _: self.fail("unexpected network"))
