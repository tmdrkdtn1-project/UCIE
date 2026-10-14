"""Network-free, synthetic public-only miner tests."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.core import PUBLIC_SOURCES, MiningError, _api_url, _classify_changes, mine_once, report, fetch_public_json


class PublicMinerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    @staticmethod
    def fake_get(url):
        if "pulls?state=closed" in url:
            return [{"number": 42, "title": "Fix exception regression", "merged_at": "2026-10-01T10:00:00Z"},
                    {"number": 41, "title": "Add feature", "merged_at": "2026-10-01T10:00:00Z"}]
        if "pulls/42/files?" in url:
            return [{"filename": "Lib/test_async.py", "patch": "@@ -1 +1 @@\n-raise OldError\n+except RuntimeError:\n"}]
        raise AssertionError("Unexpected outbound API URL: " + url)

    def test_allowlisted_routes(self):
        self.assertEqual(_api_url(PUBLIC_SOURCES[0], "pulls/42/files?per_page=30"),
                         "https://api.github.com/repos/python/cpython/pulls/42/files?per_page=30")

    def test_fetch_denies_unapproved_endpoint_before_network(self):
        for url in (
            "https://api.github.com/repos/python/cpython/contents/private",
            "https://api.github.com/repos/python/cpython/pulls/42/files?per_page=999",
            "https://api.github.com/repos/python/cpython/pulls/42/commits",
            "https://api.github.com/repos/not-approved/test/pulls/4",
        ):
            with self.subTest(url=url), self.assertRaises(MiningError):
                fetch_public_json(url)

    def test_other_project_source_is_denied(self):
        with self.assertRaises(MiningError):
            _api_url("somebody/unknown-project", "pulls?state=closed&sort=updated&direction=desc&per_page=20")

    def test_unsafe_endpoint_denied(self):
        with self.assertRaises(MiningError):
            _api_url(PUBLIC_SOURCES[0], "contents/secrets")

    @staticmethod
    def fake_get_with_origin(url):
        if url.endswith("/pulls/42"):
            return {"number": 42, "html_url": "https://github.com/python/cpython/pull/42",
                    "state": "closed", "merged": True,
                    "merged_at": "2026-10-01T10:00:00Z",
                    "updated_at": "2026-10-02T10:00:00Z",
                    "merge_commit_sha": "a" * 40}
        return PublicMinerTests.fake_get(url)

    def test_crosscheck_origin_in_collector(self):
        result = mine_once(self.root, fetch=self.fake_get_with_origin,
                           sources=(PUBLIC_SOURCES[0],), crosscheck_origin=True)
        self.assertEqual(result["public_pr_crosschecked"], 1)
        self.assertEqual(result["verification_pass"], 0)

    def test_origin_mismatch_fails_closed(self):
        def mismatch(url):
            if url.endswith("/pulls/42"):
                return {"number": 42, "html_url": "https://github.com/python/cpython/pull/42",
                        "state": "closed", "merged": False,
                        "merged_at": "2026-10-01T10:00:00Z",
                        "updated_at": "2026-10-02T10:00:00Z",
                        "merge_commit_sha": "a" * 40}
            return self.fake_get(url)
        with self.assertRaises(MiningError):
            mine_once(self.root, fetch=mismatch,
                      sources=(PUBLIC_SOURCES[0],), crosscheck_origin=True)

    def test_mine_once(self):
        r = mine_once(self.root, fetch=self.fake_get, sources=(PUBLIC_SOURCES[0],))
        self.assertEqual(r["new_candidates"], 1)
        self.assertEqual(r["verification_pass"], 0)
        db = sqlite3.connect(str(self.root / "runtime" / "public_miner.sqlite3"))
        source, url, status, tags = db.execute("SELECT source,public_url,status,tags_json FROM candidates").fetchone()
        self.assertEqual(source, PUBLIC_SOURCES[0])
        self.assertIn("/pull/42", url)
        self.assertEqual(status, "UNVERIFIED_CANDIDATE_ONLY")
        self.assertIn("TEST_CHANGE", tags)
        db.close()

    def test_deduplication(self):
        mine_once(self.root, fetch=self.fake_get, sources=(PUBLIC_SOURCES[0],))
        r = mine_once(self.root, fetch=self.fake_get, sources=(PUBLIC_SOURCES[0],))
        self.assertEqual(r["new_candidates"], 0)

    def test_no_raw_title_or_patch_in_db(self):
        mine_once(self.root, fetch=self.fake_get, sources=(PUBLIC_SOURCES[0],))
        raw = (self.root / "runtime" / "public_miner.sqlite3").read_bytes()
        self.assertNotIn(b"Fix exception regression", raw)
        self.assertNotIn(b"raise OldError", raw)

    def test_report_is_local_and_unverified(self):
        mine_once(self.root, fetch=self.fake_get, sources=(PUBLIC_SOURCES[0],))
        path = report(self.root)
        self.assertTrue(path.is_relative_to(self.root / "runtime"))
        body = path.read_text(encoding="utf-8")
        self.assertIn("UNVERIFIED_CANDIDATE_ONLY", body)
        self.assertIn("Promoted knowledge rules: 0", body)

    def test_classification_never_executes(self):
        digest, tags = _classify_changes([
            {"filename": "mod.py", "patch": "+__import__('os').system('exit 1')\n"}])
        self.assertEqual(len(digest), 64)
        self.assertIn("PYTHON_CHANGE", tags)

    def test_files_overflow_rejected(self):
        with self.assertRaises(MiningError):
            _classify_changes([{"filename": "m.py", "patch": ""}] * 31)

    def test_invalid_cap(self):
        with self.assertRaises(MiningError):
            mine_once(self.root, fetch=self.fake_get, sources=(PUBLIC_SOURCES[0],), max_new_per_source=999)

if __name__ == "__main__":
    unittest.main()
