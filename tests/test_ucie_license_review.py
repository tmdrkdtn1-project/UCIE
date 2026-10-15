"""Synthetic-only pinned upstream license-document marker audit tests."""
from pathlib import Path
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.license_review import inspect_pinned_licenses
from ucie_miner.review import ReviewError


class PinnedLicenseReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "curated_public").mkdir()
        original = (ROOT / "curated_public" / "pr_review_evidence_v1.json")
        (self.root / "curated_public" / original.name).write_bytes(
            original.read_bytes())

    def test_offline_by_default(self):
        called = []
        receipt = inspect_pinned_licenses(
            self.root, fetch=lambda url: called.append(url))
        self.assertEqual(called, [])
        self.assertTrue(receipt["items"])
        self.assertTrue(all(row["marker_status"] == "NOT_CHECKED"
                            for row in receipt["items"]))
        self.assertFalse(receipt["license_approved"])
        self.assertEqual(receipt["persistent_writes"], 0)

    def test_synthetic_marker_never_proves_license(self):
        urls = []
        def fake(url):
            urls.append(url)
            if "/python/cpython/" in url:
                return "PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2"
            return "MIT License"
        receipt = inspect_pinned_licenses(
            self.root, verify_live=True, fetch=fake)
        self.assertEqual(len(urls), receipt["count"])
        self.assertTrue(all(row["marker_status"] ==
                            "SYNTHETIC_TAG_MARKER_PRESENT"
                            for row in receipt["items"]))
        self.assertFalse(receipt["live_checked"])
        self.assertTrue(all(not row["legal_approval"]
                            for row in receipt["items"]))
        self.assertTrue(all(not row["independent_commit_license_reviewed"]
                            for row in receipt["items"]))
        self.assertTrue(all(url.startswith("https://raw.githubusercontent.com/")
                            for url in urls))
        self.assertTrue(all(row["body_sha256"] for row in receipt["items"]))

    def test_missing_marker_is_not_pass(self):
        receipt = inspect_pinned_licenses(
            self.root, verify_live=True, fetch=lambda _: "invalid license")
        self.assertTrue(all(row["marker_status"] == "MARKER_ABSENT"
                            for row in receipt["items"]))

    def test_oversized_body_denied(self):
        receipt = inspect_pinned_licenses(
            self.root, verify_live=True, fetch=lambda _: "X" * 500001)
        self.assertTrue(all(row["marker_status"] == "UNAVAILABLE_OR_OVERSIZED"
                            for row in receipt["items"]))

    def test_unavailable_does_not_claim_verified(self):
        def unavailable(_):
            raise OSError("fixture only")
        receipt = inspect_pinned_licenses(
            self.root, verify_live=True, fetch=unavailable)
        self.assertTrue(all(row["marker_status"] == "UNAVAILABLE_OR_OVERSIZED"
                            for row in receipt["items"]))

    def test_bad_type_denied(self):
        with self.assertRaises(ReviewError):
            inspect_pinned_licenses(self.root, verify_live="yes")


if __name__ == "__main__":
    unittest.main()
