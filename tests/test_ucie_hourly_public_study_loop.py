"""Synthetic acceptance of Stage10->13/15->Stage12 hourly public study loop.

No live HTTP, private project, external code execution or new scheduler.
"""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from test_ucie_stage11_hourly_stage import fixture_batch
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME as REVIEW_MARKER, OPT_IN_TOKEN as REVIEW_TOKEN,
    REVIEW_FILE, optional_hourly_review_learning, update_unverified_review_queue,
    inspect_review_learning,
)
from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_external_history import DB_NAME as HISTORY_DB, _schema as init_history
from ucie_miner.public_fix_evidence import (
    DB_NAME as FIX_DB, OPT_IN_FILE as FIX_MARKER,
    OPT_IN_TOKEN as FIX_TOKEN, _check_schema as init_fix,
)
from ucie_miner.public_hourly_staging import (
    OPT_IN_FILENAME as HOUR_MARKER, OPT_IN_TOKEN as HOUR_TOKEN,
    optional_public_skill_staging,
)
from ucie_miner.skill_profiles import PROFILE

SOURCE = "python/cpython"
SKILL = "python-runtime-safety"
MERGE = "a" * 40
META = "b" * 64
FIX = "c" * 64


class PublicAutomaticStudyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.miner = self.runtime / "public_miner.sqlite3"
        self.knowledge = self.runtime / "knowledge.sqlite3"
        self.miner.write_bytes(b"OPERATING_MINER_UNCHANGED")
        self.knowledge.write_bytes(b"OPERATING_KNOWLEDGE_UNCHANGED")
        self.stage10 = self.runtime / "stage10_unverified_public_candidates.sqlite3"
        self.history = self.runtime / HISTORY_DB
        self.fix = self.runtime / FIX_DB
        self.review = self.runtime / REVIEW_FILE
        self._stage10_setup()

    def _stage10_setup(self):
        batch = fixture_batch(
            root=self.root,
            sources=("python/cpython", "PowerShell/PowerShell", "git/git",
                     "modelcontextprotocol/python-sdk", "actions/runner-images"),
            max_enrich=1, include_git_commits=True, include_docs=False,
            include_advisories=False, backfill_pages=1,
        )
        stage_public_candidates(batch, root=self.root, allow_disk_write=True)

    def _history_setup(self):
        with closing(sqlite3.connect(self.history)) as db:
            db.execute("BEGIN IMMEDIATE")
            init_history(db, new=True)
            db.execute(
                "INSERT INTO upstream_history VALUES (?,?,?,?,?,?,?,?,?)",
                (SOURCE, 159443, MERGE, "2026-10-15T05:32:36Z",
                 "f" * 64, META, SKILL, '["REGRESSION"]',
                 "UNVERIFIED_CANDIDATE_ONLY"),
            )
            db.commit()

    def _fix_setup(self, *, metadata=META, digest=FIX):
        profile = PROFILE[SKILL]
        with closing(sqlite3.connect(self.fix)) as db:
            db.execute("BEGIN IMMEDIATE")
            if not (self.runtime / FIX_DB).stat().st_size:
                init_fix(db, new=True)
            else:
                init_fix(db, new=False)
            db.execute(
                "INSERT INTO fix_evidence VALUES (" + ",".join("?" for _ in range(21)) + ")",
                (SOURCE, 159443, MERGE, metadata, digest, SKILL,
                 '["API_CONTRACT"]', "[]", "[]", 0, 2,
                 "BOUNDED_FIRST_PAGE_ONLY", 0, '["advisory","document"]',
                 profile["safe_call"], profile["recommended_action"],
                 "UNDETERMINED", "UNVERIFIED",
                 "PUBLIC_PATCH_RELEASE_HINTS_UNVERIFIED",
                 "UNVERIFIED_REVIEW_CANDIDATE_ONLY",
                 "2026-10-16T02:00:00+00:00"),
            )
            db.commit()

    def _markers(self, *, review=True, fix=True):
        if review:
            (self.runtime / REVIEW_MARKER).write_text(REVIEW_TOKEN, encoding="ascii")
        if fix:
            (self.runtime / FIX_MARKER).write_text(FIX_TOKEN, encoding="ascii")

    def test_stage10_review_still_runs_without_fix_marker(self):
        self._history_setup()
        self._fix_setup()
        self._markers(fix=False)
        initial = self.miner.read_bytes(), self.knowledge.read_bytes()
        result = optional_hourly_review_learning(self.root)
        self.assertEqual(result["status"], "STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO")
        self.assertEqual(result["stage15_unverified_fix_input_revisions"], 0)
        self.assertEqual(result["new_review_proposals"], 2)
        self.assertEqual(inspect_review_learning(self.root)["by_evidence_origin"].get(
            "stage15_fix_evidence", 0), 0)
        self.assertEqual((self.miner.read_bytes(), self.knowledge.read_bytes()), initial)

    def test_both_markers_append_fix_study_without_changing_old_ledgers(self):
        self._history_setup()
        self._fix_setup()
        self._markers()
        before = {p.name: p.read_bytes() for p in (
            self.miner, self.knowledge, self.stage10, self.history, self.fix)}
        preview = update_unverified_review_queue(self.root)
        self.assertEqual(preview["stage15_unverified_fix_input_revisions"], 1)
        self.assertFalse(self.review.exists())
        first = optional_hourly_review_learning(self.root)
        self.assertEqual(first["stage15_unverified_fix_input_revisions"], 1)
        self.assertEqual(first["new_review_proposals"], 3)
        self.assertFalse(first["model_weights_updated"])
        self.assertEqual(first["approved_rules"], 0)
        inventory = inspect_review_learning(self.root)
        self.assertEqual(inventory["review_proposals"], 3)
        self.assertEqual(inventory["by_evidence_origin"]["stage15_fix_evidence"], 1)
        self.assertEqual(inventory["by_evidence_origin"]["stage10_pr_metadata"], 1)
        self.assertEqual(inventory["by_evidence_origin"]["stage10_git_metadata"], 1)
        with closing(sqlite3.connect(self.review)) as db:
            record = db.execute("""
                SELECT reference,pattern_code,review_state
                FROM review_queue WHERE reference LIKE 'fix-pr:%'
            """).fetchone()
        self.assertTrue(record[0].startswith("fix-pr:159443:"))
        self.assertEqual(record[1], "API_CONTRACT")
        self.assertEqual(record[2], "UNVERIFIED_REVIEW_CANDIDATE_ONLY")
        repeat = optional_hourly_review_learning(self.root)
        self.assertEqual(repeat["new_review_proposals"], 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (
            self.miner, self.knowledge, self.stage10, self.history, self.fix)})

    def test_marker_optout_does_not_delete_learned_review_history(self):
        self._history_setup()
        self._fix_setup()
        self._markers()
        optional_hourly_review_learning(self.root)
        (self.runtime / FIX_MARKER).unlink()
        nxt = optional_hourly_review_learning(self.root)
        self.assertEqual(nxt["stage15_unverified_fix_input_revisions"], 0)
        self.assertEqual(nxt["new_review_proposals"], 0)
        self.assertEqual(inspect_review_learning(self.root)["review_proposals"], 3)
        (self.runtime / REVIEW_MARKER).unlink()
        self.assertEqual(optional_hourly_review_learning(self.root)["status"],
                         "STAGE12_REVIEW_DISABLED")

    def test_unlinked_stage15_does_not_insert_partial_review(self):
        self._history_setup()
        self._fix_setup(metadata="e" * 64)
        self._markers()
        with self.assertRaises(DiscoveryError):
            optional_hourly_review_learning(self.root)
        self.assertFalse(self.review.exists())

    def test_forged_stage15_token_denies_review(self):
        self._history_setup()
        self._fix_setup()
        self._markers()
        (self.runtime / FIX_MARKER).write_text("AUTO_APPROVE", encoding="ascii")
        with self.assertRaises(DiscoveryError):
            optional_hourly_review_learning(self.root)
        self.assertFalse(self.review.exists())

    def test_existing_hourly_lock_orders_fix_ingest_before_study(self):
        self._history_setup()
        self._markers()
        (self.runtime / HOUR_MARKER).write_text(HOUR_TOKEN, encoding="ascii")
        call_order = []

        def fixed_external_staging(root):
            call_order.append("fix_ingest")
            self.assertFalse(self.review.exists())
            self._fix_setup()
            return {
                "status": "STAGE15_STRUCTURED_FIX_EVIDENCE_STAGED_NO_GO",
                "new_unverified_evidence_records": 1,
                "external_gets_upper_bound": 0,
            }

        with patch("ucie_miner.public_fix_evidence.optional_fix_evidence_enrichment",
                   side_effect=fixed_external_staging):
            result = optional_public_skill_staging(self.root, batch_builder=fixture_batch)
        call_order.append("review_ready")
        self.assertEqual(call_order, ["fix_ingest", "review_ready"])
        self.assertEqual(result["stage12_fix_evidence_input_revisions"], 1)
        self.assertEqual(result["stage12_review_proposals_added"], 3)
        self.assertEqual(inspect_review_learning(self.root)["review_proposals"], 3)


if __name__ == "__main__":
    unittest.main()
