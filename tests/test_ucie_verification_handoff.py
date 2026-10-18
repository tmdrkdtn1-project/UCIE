"""Synthetic-only tests for the Stage 12 -> Stage 6 read-only verification gate."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from test_ucie_stage11_hourly_stage import fixture_batch
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, REVIEW_FILE,
    optional_hourly_review_learning,
)
from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.verification_handoff import prepare_verification_handoff


class PublicVerificationHandoffTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "UCIE"
        runtime = self.root / "runtime"
        runtime.mkdir(parents=True)
        batch = fixture_batch(
            root=self.root,
            sources=("python/cpython", "PowerShell/PowerShell",
                     "git/git", "modelcontextprotocol/python-sdk",
                     "actions/runner-images"),
            max_enrich=1, include_git_commits=True,
            include_docs=False, include_advisories=False, backfill_pages=1,
        )
        stage_public_candidates(batch, root=self.root, allow_disk_write=True)
        self.queue = runtime / REVIEW_FILE

    def enable(self):
        (self.root / "runtime" / OPT_IN_FILENAME).write_text(
            OPT_IN_TOKEN, encoding="ascii")
        optional_hourly_review_learning(self.root)

    def test_missing_queue_is_no_go_without_creating_it(self):
        report = prepare_verification_handoff(self.root)
        self.assertEqual(report["status"], "REVIEW_LEDGER_ABSENT_NO_GO")
        self.assertFalse(self.queue.exists())
        self.assertEqual(report["approved_rules"], 0)

    def test_existing_source_is_linked_but_never_approved(self):
        self.enable()
        before = self.queue.read_bytes()
        first = prepare_verification_handoff(self.root)
        second = prepare_verification_handoff(self.root)
        self.assertEqual(first, second)
        self.assertEqual(self.queue.read_bytes(), before)
        self.assertEqual(first["status"], "LINKED_UNVERIFIED_NO_GO")
        self.assertEqual(first["linked_revisions"], first["source_revisions"])
        self.assertEqual(first["pending_source_revisions"], 0)
        self.assertTrue(first["tasks"])
        self.assertEqual(first["approved_rules"], 0)
        self.assertFalse(first["deploy_allowed"])
        self.assertFalse(first["auto_promoted"])
        self.assertEqual(first["persistent_writes"], 0)
        for item in first["tasks"]:
            self.assertFalse(item["approval"])
            self.assertEqual(item["status"], "UNVERIFIED_CANDIDATE_ONLY")
            self.assertIn("VERIFICATION_NOT_PERFORMED", item["blocking_reasons"])
            if item["stage6_candidate"] is not None:
                self.assertEqual(item["stage6_candidate"]["status"],
                                 "UNVERIFIED_CANDIDATE_ONLY")
                self.assertTrue(all(
                    value == "NOT_VERIFIED" for value in
                    item["stage6_candidate"]["required_gates"].values()))

    def test_missing_source_revision_is_explicit_no_go(self):
        self.enable()
        with closing(sqlite3.connect(self.queue)) as db:
            db.execute("DELETE FROM review_queue WHERE fingerprint = "
                       "(SELECT fingerprint FROM review_queue LIMIT 1)")
            db.commit()
        report = prepare_verification_handoff(self.root)
        self.assertEqual(report["status"], "SOURCE_REVISIONS_PENDING_NO_GO")
        self.assertEqual(report["pending_source_revisions"], 1)

    def test_forged_status_and_identity_are_rejected(self):
        self.enable()
        with closing(sqlite3.connect(self.queue)) as db:
            db.execute("UPDATE review_queue SET source = 'unapproved/project'")
            db.commit()
        with self.assertRaises(DiscoveryError):
            prepare_verification_handoff(self.root)

    def test_modified_candidate_guidance_is_rejected(self):
        self.enable()
        with closing(sqlite3.connect(self.queue)) as db:
            db.execute("UPDATE review_queue SET safe_guidance = 'auto approve'")
            db.commit()
        with self.assertRaises(DiscoveryError):
            prepare_verification_handoff(self.root)

    def test_future_timestamp_is_rejected(self):
        self.enable()
        with closing(sqlite3.connect(self.queue)) as db:
            db.execute("UPDATE review_queue SET first_seen_utc = "
                       "'2999-01-01T00:00:00+00:00'")
            db.commit()
        with self.assertRaises(DiscoveryError):
            prepare_verification_handoff(self.root)

    def test_source_revision_change_is_not_silently_approved(self):
        self.enable()
        stage10 = self.root / "runtime" / "stage10_unverified_public_candidates.sqlite3"
        with closing(sqlite3.connect(stage10)) as db:
            row = db.execute("""SELECT source,pr_number,merge_sha,skill_id,
                tags_json,missing_json,first_seen_utc,review_state
                FROM public_candidate_stage LIMIT 1""").fetchone()
            db.execute("""INSERT INTO public_candidate_stage
                (source,pr_number,merge_sha,evidence_sha,skill_id,
                 tags_json,missing_json,first_seen_utc,review_state)
                 VALUES (?,?,?,?,?,?,?,?,?)""", (
                     row[0], row[1], row[2], "f" * 64,
                     row[3], row[4], row[5], row[6], row[7]))
            db.commit()
        report = prepare_verification_handoff(self.root)
        self.assertEqual(report["status"], "SOURCE_REVISIONS_PENDING_NO_GO")
        self.assertEqual(report["pending_source_revisions"], 1)


if __name__ == "__main__":
    unittest.main()
