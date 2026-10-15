"""Stage 12 public-only, unsigned, opt-in review learning integration."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from test_ucie_stage11_hourly_stage import fixture_batch
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, REVIEW_FILE, REVIEW_STATUS,
    inspect_review_learning, optional_hourly_review_learning,
    update_unverified_review_queue,
)
from ucie_miner.public_discovery import DiscoveryError


class Stage12CandidateLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.marker = self.runtime / OPT_IN_FILENAME
        self.stage10 = self.runtime / "stage10_unverified_public_candidates.sqlite3"
        self.knowledge = self.runtime / "knowledge.sqlite3"
        self.miner = self.runtime / "public_miner.sqlite3"
        self.knowledge.write_bytes(b"KEEP_EXISTING_KNOWLEDGE_UNCHANGED")
        with closing(sqlite3.connect(self.miner)) as conn:
            conn.execute("""CREATE TABLE candidates
                            (source TEXT, pr_number INTEGER, status TEXT)""")
            conn.commit()
        batch = fixture_batch(
            root=self.root,
            sources=("python/cpython", "PowerShell/PowerShell", "git/git",
                     "modelcontextprotocol/python-sdk", "actions/runner-images"),
            max_enrich=1, include_git_commits=True, include_docs=False,
            include_advisories=False, backfill_pages=1)
        stage_public_candidates(batch, root=self.root, allow_disk_write=True)

    def enable(self):
        self.marker.write_text(OPT_IN_TOKEN, encoding="ascii")

    def test_default_no_learning_db_and_only_a_preview(self):
        initial = self.miner.read_bytes(), self.knowledge.read_bytes(), self.stage10.read_bytes()
        preview = update_unverified_review_queue(self.root)
        self.assertEqual(preview["status"], "STAGE12_REVIEW_PREVIEW_ONLY")
        self.assertEqual(preview["candidate_proposals"], 1)
        self.assertEqual(preview["persistent_writes"], 0)
        self.assertEqual(optional_hourly_review_learning(self.root)["status"],
                         "STAGE12_REVIEW_DISABLED")
        self.assertFalse((self.runtime / REVIEW_FILE).exists())
        self.assertEqual(
            (self.miner.read_bytes(), self.knowledge.read_bytes(),
             self.stage10.read_bytes()), initial)

    def test_explicit_learning_marker_creates_only_separate_review_candidates(self):
        self.enable()
        before = self.miner.read_bytes(), self.knowledge.read_bytes(), self.stage10.read_bytes()
        output = optional_hourly_review_learning(self.root)
        self.assertEqual(output["status"], "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO")
        self.assertEqual(output["source_revisions"], 1)
        self.assertEqual(output["new_review_proposals"], 1)
        self.assertEqual(output["total_review_proposals"], 1)
        self.assertEqual(output["approved_rules"], 0)
        self.assertFalse(output["model_weights_updated"])
        inventory = inspect_review_learning(self.root)
        self.assertEqual(inventory["review_proposals"], 1)
        self.assertEqual(sum(inventory["by_skill"].values()), 1)
        with closing(sqlite3.connect(self.runtime / REVIEW_FILE)) as db:
            vals = db.execute("""
                SELECT pattern_code, safe_guidance, regression_plan, review_state
                FROM review_queue
            """).fetchone()
        self.assertIn(vals[0], (
            "SECURITY", "CRASH", "REGRESSION", "COMPATIBILITY", "TESTING",
            "UNCLASSIFIED"))
        self.assertTrue(vals[1])
        self.assertTrue(vals[2])
        self.assertEqual(vals[3], REVIEW_STATUS)
        self.assertEqual(
            (self.miner.read_bytes(), self.knowledge.read_bytes(),
             self.stage10.read_bytes()), before)

    def test_repeat_cycle_is_idempotent_and_optout_is_reversible(self):
        self.enable()
        first = optional_hourly_review_learning(self.root)
        second = optional_hourly_review_learning(self.root)
        self.assertEqual(first["new_review_proposals"], 1)
        self.assertEqual(second["new_review_proposals"], 0)
        self.assertEqual(second["unchanged_review_proposals"], 1)
        self.marker.unlink()
        self.assertEqual(optional_hourly_review_learning(self.root)["status"],
                         "STAGE12_REVIEW_DISABLED")
        self.assertEqual(inspect_review_learning(self.root)["review_proposals"], 1)

    def test_new_revision_appends_new_review_candidate_only(self):
        self.enable()
        optional_hourly_review_learning(self.root)
        with closing(sqlite3.connect(self.stage10)) as conn:
            row = conn.execute("""SELECT source, pr_number, merge_sha,
                skill_id, tags_json, missing_json, first_seen_utc, review_state
                FROM public_candidate_stage""").fetchone()
            conn.execute("""INSERT INTO public_candidate_stage
                (source,pr_number,merge_sha,evidence_sha,
                 skill_id,tags_json,missing_json,first_seen_utc,review_state)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (row[0], row[1], row[2], "f"*64,
                 row[3], row[4], row[5], row[6], row[7]))
            conn.commit()
        update = optional_hourly_review_learning(self.root)
        self.assertEqual(update["new_review_proposals"], 1)
        self.assertEqual(update["total_review_proposals"], 2)
        self.assertEqual(update["approved_rules"], 0)

    def test_git_sha_keeps_distinct_commit_identity(self):
        self.enable()
        with closing(sqlite3.connect(self.stage10)) as conn:
            conn.execute("""INSERT INTO public_git_commit_stage
                (git_commit_sha,message_sha256,tags_json,first_seen_utc,review_state)
                VALUES (?,?,?,?,?)""",
                ("a"*40, "b"*64, '["REGRESSION"]',
                 "2026-10-15T08:00:00+00:00", "UNVERIFIED_CANDIDATE_ONLY"))
            conn.commit()
        data = optional_hourly_review_learning(self.root)
        self.assertEqual(data["total_review_proposals"], 2)
        info = inspect_review_learning(self.root)
        self.assertEqual(info["by_skill"]["git-workflow-prevention"], 1)

    def test_stage10_tampered_tags_are_denied_without_learning(self):
        self.enable()
        with closing(sqlite3.connect(self.stage10)) as conn:
            conn.execute("UPDATE public_candidate_stage SET tags_json = ?",
                         ('["UNTRUSTED_REMOTE_CODE"]',))
            conn.commit()
        with self.assertRaises(DiscoveryError):
            optional_hourly_review_learning(self.root)
        self.assertFalse((self.runtime / REVIEW_FILE).exists())

    def test_bad_marker_denies_writes(self):
        self.marker.write_text("UCIE_AUTO_APPROVE_ALL", encoding="ascii")
        with self.assertRaises(DiscoveryError):
            optional_hourly_review_learning(self.root)
        self.assertFalse((self.runtime / REVIEW_FILE).exists())

    def test_review_schema_tampering_fails_closed(self):
        self.enable()
        optional_hourly_review_learning(self.root)
        with closing(sqlite3.connect(self.runtime / REVIEW_FILE)) as conn:
            conn.execute("CREATE TABLE unrelated(data TEXT)")
            conn.commit()
        with self.assertRaises(DiscoveryError):
            optional_hourly_review_learning(self.root)

    def test_review_marker_symlink_denied(self):
        with tempfile.TemporaryDirectory() as out:
            target = Path(out) / "bad.txt"
            target.write_text(OPT_IN_TOKEN, encoding="ascii")
            try:
                self.marker.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unsupported")
            with self.assertRaises(DiscoveryError):
                optional_hourly_review_learning(self.root)


if __name__ == "__main__":
    unittest.main()
