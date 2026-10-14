"""No-network Stage 4 review tests: no user projects, no patch execution."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucie_miner.review import (
    ALLOWED, RESULT_SCHEMA, ReviewError, _verify_live, analyze, load_manifest,
    public_read_only_get, review_and_store,
)


class Stage4ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "runtime").mkdir()
        (self.root / "curated_public").mkdir()
        self.data = json.loads((ROOT / "curated_public" / "pr_review_evidence_v1.json").read_text("utf-8"))
        self.write_manifest()
        self.db_path = self.root / "runtime" / "public_miner.sqlite3"
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("""CREATE TABLE candidates (
              source TEXT NOT NULL, pr_number INTEGER NOT NULL, public_url TEXT NOT NULL,
              merged_at TEXT NOT NULL, evidence_sha256 TEXT NOT NULL, tags_json TEXT NOT NULL,
              observed_at TEXT NOT NULL, status TEXT NOT NULL,
              PRIMARY KEY(source, pr_number))""")
            for e in self.data["entries"]:
                source, n = e["source"], e["pr_number"]
                db.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)",
                           (source, n, f"https://github.com/{source}/pull/{n}", e["merged_at"],
                            hashlib.sha256(str(n).encode()).hexdigest(), "[]",
                            "2026-10-14T00:00:00Z", "UNVERIFIED_CANDIDATE_ONLY"))

    def write_manifest(self):
        p = self.root / "curated_public" / "pr_review_evidence_v1.json"
        p.write_text(json.dumps(self.data, sort_keys=True, ensure_ascii=False), "utf-8")

    def test_known_nine_prs_become_eight_patterns(self):
        result = analyze(self.root)
        self.assertEqual(result["schema"], RESULT_SCHEMA)
        self.assertEqual(result["candidate_pr_count"], 9)
        self.assertEqual(result["unique_mapped_patterns"], 8)
        self.assertEqual(result["groups"]["python/cpython#153462"], [153462, 159365])
        self.assertEqual(result["rules_promoted"], 0)
        self.assertEqual(result["patches_independently_tested"], 0)
        self.assertFalse(result["production_approved"])

    def test_preview_is_strictly_read_only(self):
        start = self.db_path.read_bytes()
        analyze(self.root)
        self.assertEqual(self.db_path.read_bytes(), start)
        self.assertFalse((self.root / "runtime" / "review_candidates.sqlite3").exists())

    def test_review_separate_sqlite_and_staging(self):
        before = self.db_path.read_bytes()
        res = review_and_store(self.root)
        self.assertEqual(res["mapped_unique_patterns"], 8)
        self.assertFalse(res["production_approved"])
        with closing(sqlite3.connect(self.root / "runtime" / "review_candidates.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_candidates").fetchone()[0], 9)
            self.assertEqual(db.execute("SELECT SUM(approval) FROM review_candidates").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_candidates WHERE release_check='NOT_CHECKED'").fetchone()[0], 9)
        self.assertEqual(before, self.db_path.read_bytes())
        receipt = json.loads((self.root / "runtime" / "reviews" / "candidate_review_v1.json").read_text("utf-8"))
        self.assertFalse(receipt["production_approved"])

    def test_rerun_upsert_without_duplicate_review_rows(self):
        review_and_store(self.root)
        review_and_store(self.root)
        with closing(sqlite3.connect(self.root / "runtime" / "review_candidates.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_candidates").fetchone()[0], 9)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_runs").fetchone()[0], 2)

    def test_unmapped_pr_is_never_promoted(self):
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?)",
                       ("python/cpython", 999998, "https://github.com/python/cpython/pull/999998",
                        "2026-10-14T00:00:00Z", "a" * 64, "[]",
                        "2026-10-14T00:00:00Z", "UNVERIFIED_CANDIDATE_ONLY"))
        result = analyze(self.root)
        unknown = [e for e in result["items"] if e["pr_number"] == 999998][0]
        self.assertEqual(unknown["review_state"], "MAPPING_REQUIRED")
        self.assertIsNone(unknown["pattern_id"])
        self.assertFalse(unknown["approval"])

    def test_merge_time_mismatch_never_promoted(self):
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("UPDATE candidates SET merged_at='2026-10-01T00:00:00Z' WHERE pr_number=159365")
        result = analyze(self.root)
        wrong = [e for e in result["items"] if e["pr_number"] == 159365][0]
        self.assertEqual(wrong["review_state"], "MAPPING_REQUIRED")
        self.assertNotIn(159365, result["groups"]["python/cpython#153462"])

    def test_fake_public_project_source_is_rejected(self):
        self.data["entries"][0]["source"] = "some-user/private-project"
        self.write_manifest()
        with self.assertRaises(ReviewError):
            load_manifest(self.root)

    def test_fake_release_path_is_rejected(self):
        self.data["entries"][0]["release_file"] = "../../other_project/secret"
        self.write_manifest()
        with self.assertRaises(ReviewError):
            analyze(self.root)

    def test_unapproved_release_tag_is_rejected(self):
        self.data["entries"][0]["release_tag"] = "v999.999.999"
        self.write_manifest()
        with self.assertRaises(ReviewError):
            analyze(self.root)

    def test_license_mismatch_rejected(self):
        self.data["entries"][0]["license"] = "PSF-2.0"
        self.write_manifest()
        with self.assertRaises(ReviewError):
            analyze(self.root)

    def test_inconsistent_canonical_pattern_rejected(self):
        self.data["entries"][-1]["pattern_id"] = "PY_ANOTHER_FAKE_PATTERN"
        self.write_manifest()
        with self.assertRaises(ReviewError):
            analyze(self.root)

    def test_duplicate_pr_in_evidence_rejected(self):
        self.data["entries"].append(dict(self.data["entries"][0]))
        self.write_manifest()
        with self.assertRaises(ReviewError):
            analyze(self.root)

    def test_duplicate_json_property_rejected(self):
        p = self.root / "curated_public" / "pr_review_evidence_v1.json"
        p.write_text('{"schema":"X","schema":"Y"}',"utf-8")
        with self.assertRaises(ReviewError):
            load_manifest(self.root)

    def test_candidate_db_symlink_denied(self):
        with tempfile.TemporaryDirectory() as outside:
            fake = Path(outside) / "target.sqlite3"
            self.db_path.rename(fake)
            try:
                self.db_path.symlink_to(fake)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not supported")
            with self.assertRaises(ReviewError):
                analyze(self.root)

    def test_review_output_symlink_denied(self):
        d = self.root / "runtime" / "reviews"
        d.mkdir()
        with tempfile.TemporaryDirectory() as outside:
            other = Path(outside) / "foreign.json"
            other.write_text("untouched", encoding="utf-8")
            try:
                (d / "candidate_review_v1.json").symlink_to(other)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not supported")
            with self.assertRaises(ReviewError):
                review_and_store(self.root)
            self.assertEqual(other.read_text("utf-8"), "untouched")

    def test_live_matching_source_and_marker(self):
        requests = []
        def fake_fetch(url):
            requests.append(url)
            if url.startswith("https://api.github.com/"):
                return {"merged": True, "number": 25780,
                        "merged_at": "2025-08-04T23:37:45Z",
                        "html_url": "https://github.com/PowerShell/PowerShell/pull/25780"}
            return "public sample code. A Runspace may not be present in the TLS"
        one = [x for x in analyze(self.root, verify_live=True, fetch=fake_fetch)["items"] if x["pr_number"] == 25780][0]
        self.assertEqual(one["source_check"], "SOURCE_MATCHED")
        self.assertEqual(one["release_check"], "TAG_MARKER_PRESENT")
        self.assertFalse(one["approval"])
        self.assertIn("/v7.5.12/", requests[1])

    def test_live_source_mismatch_fail_closed(self):
        def fake_fetch(url):
            if url.startswith("https://api.github.com/"):
                return {"merged": False}
            raise AssertionError("must not fetch tagged code if PR metadata fails")
        result = analyze(self.root, verify_live=True, fetch=fake_fetch)
        self.assertEqual(result["unique_mapped_patterns"], 0)
        self.assertEqual(result["items"][0]["review_state"], "SOURCE_RECHECK_REQUIRED")

    def test_live_absent_marker_is_not_a_pass(self):
        def fake_fetch(url):
            number = int(url.split("/")[-1]) if "/pulls/" in url else None
            if number:
                for e in self.data["entries"]:
                    if e["pr_number"] == number:
                        return {"merged": True, "number": number, "merged_at": e["merged_at"],
                                "html_url": f"https://github.com/{e['source']}/pull/{number}"}
            return "marker absent"
        result = analyze(self.root, verify_live=True, fetch=fake_fetch)
        self.assertTrue(all(e["release_check"] == "TAG_MARKER_ABSENT" for e in result["items"]))
        self.assertFalse(result["production_approved"])

    def test_live_unavailable_does_not_claim_validation(self):
        def fail(_):
            raise ReviewError("external network is unavailable")
        result = analyze(self.root, verify_live=True, fetch=fail)
        self.assertEqual(result["unique_mapped_patterns"], 0)
        self.assertTrue(all(e["review_state"] == "SOURCE_RECHECK_REQUIRED" for e in result["items"]))
        self.assertFalse(result["production_approved"])

    def test_public_read_rejects_other_projects(self):
        for url in ("https://api.github.com/repos/tmdrkdtn1-project/UCIE/pulls/1",
                    "https://raw.githubusercontent.com/user/private/main/secrets.txt",
                    "http://api.github.com/repos/python/cpython/pulls/1"):
            with self.subTest(url=url), self.assertRaises(ReviewError):
                public_read_only_get(url)

    def test_no_raw_patch_code_recorded(self):
        review_and_store(self.root)
        for p in (self.root / "runtime" / "review_candidates.sqlite3",
                  self.root / "runtime" / "reviews" / "candidate_review_v1.json"):
            b = p.read_bytes()
            self.assertNotIn(b"__import__('os').system", b)
            self.assertNotIn(b"git clone", b)
            self.assertNotIn(b"runspace may not be present", b.lower())


if __name__ == "__main__":
    unittest.main()
