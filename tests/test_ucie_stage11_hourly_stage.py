"""Stage 11: connect to existing hourly worker without modifying the task."""
from contextlib import closing, ExitStack
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.public_discovery import DiscoveryError, SOURCES

from ucie_miner.public_hourly_staging import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, STATUS_DISABLED, STATUS_STAGED,
    optional_public_skill_staging,
)
from ucie_miner.public_batch import build_public_batch
from ucie_miner.public_candidate_staging import (
    stage_public_candidates, inspect_staged_candidates, DB_NAME,
)
from ucie_miner.worker import run_cycle
from test_ucie_stage9_batch import NOW, metadata, evidence
from test_ucie_stage10_git_commit_skills import git_commit


def fixture_batch(*, root, sources, max_enrich, include_git_commits,
                  include_docs, include_advisories, backfill_pages):
    assert max_enrich == 1
    assert include_git_commits is True
    assert include_docs is False and include_advisories is False
    assert backfill_pages == 1
    return build_public_batch(
        metadata_fetch=metadata, evidence_fetch=evidence,
        git_commit_fetch=lambda url: [git_commit(42)],
        sources=sources, root=root, max_enrich=max_enrich,
        now=NOW, include_git_commits=include_git_commits,
        include_docs=include_docs, include_advisories=include_advisories,
        backfill_pages=backfill_pages,
    )


def _legacy_success(root):
    return {
        "status": "COLLECTED_UNVERIFIED",
        "new_candidates": 0,
        "sources_checked": 2,
        "verification_pass": 0,
        "production_approved": False,
    }


def _write_report(root):
    reports = root / "runtime" / "reports"
    reports.mkdir(exist_ok=True)
    path = reports / "stage11.txt"
    path.write_text("UCIE test fixture only", encoding="utf-8")
    return path


class Stage11ExistingTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.marker = self.runtime / OPT_IN_FILENAME
        self.operating = self.runtime / "public_miner.sqlite3"
        self.knowledge = self.runtime / "knowledge.sqlite3"
        with closing(sqlite3.connect(self.operating)) as conn:
            conn.execute("""CREATE TABLE candidates(
                source TEXT, pr_number INTEGER, status TEXT
            )""")
            conn.commit()
        self.knowledge.write_bytes(b"DO_NOT_REWRITE_KNOWLEDGE_DB")

    def optin(self):
        self.marker.write_text(OPT_IN_TOKEN + "\n", encoding="utf-8")

    def test_absent_marker_preserves_legacy_mode_and_zero_public_requests(self):
        def never_called(**kwargs):
            raise AssertionError("hourly Stage 10 should stay DISABLED")
        status = optional_public_skill_staging(self.root, batch_builder=never_called)
        self.assertEqual(status["status"], STATUS_DISABLED)
        self.assertFalse(status["operator_opted_in"])
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_single_existing_worker_lock_and_opt_in_append_only_stage(self):
        self.optin()
        seen = []
        def legacy_and_new(root):
            seen.append("legacy")
            base = _legacy_success(root)
            status = optional_public_skill_staging(
                root, batch_builder=fixture_batch,
                stage_candidate_batch=stage_public_candidates)
            seen.append(status)
            return base
        initial = self.operating.read_bytes(), self.knowledge.read_bytes()
        receipt = run_cycle(
            self.root, collect=legacy_and_new,
            write_report=_write_report)
        self.assertEqual(receipt["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(seen[0], "legacy")
        self.assertEqual(seen[1]["status"], STATUS_STAGED)
        self.assertEqual(seen[1]["metadata_source_count"], 5)
        self.assertEqual(seen[1]["public_gets_upper_bound"], 8)
        self.assertEqual(seen[1]["approved_rules_added"], 0)
        self.assertEqual(inspect_staged_candidates(
            self.root)["candidate_revisions"], 1)
        self.assertEqual((self.operating.read_bytes(),
                          self.knowledge.read_bytes()), initial)
        self.assertFalse(receipt["production_approved"])

    def test_second_run_reuses_staging_without_duplicate_or_promotion(self):
        self.optin()
        first = optional_public_skill_staging(
            self.root, batch_builder=fixture_batch)
        again = optional_public_skill_staging(
            self.root, batch_builder=fixture_batch)
        self.assertEqual(first["candidate_pr_rows_added"], 1)
        self.assertEqual(again["candidate_pr_rows_added"], 0)
        self.assertEqual(again["candidate_pr_revisions_added"], 0)
        self.assertEqual(again["candidate_git_rows_added"], 0)
        self.assertFalse(again["production_approved"])

    def test_each_failed_stage_reports_exact_safe_phase_without_network(self):
        self.optin()
        batch = {
            "sources_fetched": list(SOURCES),
            "overall_gets_upper_bound": 8,
            "enriched_count": 0,
            "production_approved": False,
        }
        staged = {
            "status": "UNVERIFIED_CANDIDATES_STAGED_NO_GO",
            "mode": "OPT_IN_SEPARATE_DISK",
            "approved_rules_added": 0,
            "production_approved": False,
        }
        external = {
            "STAGE13_HISTORY": (
                "ucie_miner.public_external_history.optional_external_history_backfill",
                {"status": "STAGE13_EXTERNAL_HISTORY_DISABLED"},
            ),
            "STAGE14_OFFICIAL": (
                "ucie_miner.public_official_evidence.optional_official_evidence_cycle",
                {"status": "STAGE14_OFFICIAL_DISABLED"},
            ),
            "STAGE15_FIX_EVIDENCE": (
                "ucie_miner.public_fix_evidence.optional_fix_evidence_enrichment",
                {"status": "STAGE15_FIX_EVIDENCE_DISABLED"},
            ),
            "STAGE12_REVIEW": (
                "ucie_miner.public_candidate_learning.optional_hourly_review_learning",
                {"status": "STAGE12_REVIEW_DISABLED"},
            ),
            "STAGE16_SAFE_QA": (
                "ucie_miner.public_safe_qa_cycle.optional_pinned_public_qa",
                {"status": "STAGE16_SAFE_QA_DISABLED",
                 "approved_rules_added": 0,
                 "production_approved": False,
                 "public_gets_upper_bound": 0},
            ),
        }
        failures = (
            "STAGE10_BATCH",
            "STAGE10_STAGING",
            *external,
        )
        for failed_phase in failures:
            with self.subTest(phase=failed_phase), ExitStack() as stack:
                for phase, (target, healthy) in external.items():
                    if phase == failed_phase:
                        stack.enter_context(patch(
                            target, side_effect=DiscoveryError(
                                "SYNTHETIC_SECRET_NEVER_STORE")))
                    else:
                        stack.enter_context(patch(
                            target, return_value=healthy))

                def fake_batch(**kwargs):
                    if failed_phase == "STAGE10_BATCH":
                        raise DiscoveryError("SYNTHETIC_SECRET_NEVER_STORE")
                    return batch

                def fake_stager(*args, **kwargs):
                    if failed_phase == "STAGE10_STAGING":
                        raise DiscoveryError("SYNTHETIC_SECRET_NEVER_STORE")
                    return staged

                with self.assertRaises(DiscoveryError) as caught:
                    optional_public_skill_staging(
                        self.root, batch_builder=fake_batch,
                        stage_candidate_batch=fake_stager)
                self.assertEqual(type(caught.exception).__name__, "DiscoveryError")
                self.assertEqual(
                    getattr(caught.exception, "ucie_stage10_phase", None),
                    failed_phase)
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_invalid_batch_is_attributed_without_weakening_fail_closed(self):
        self.optin()
        with self.assertRaises(ValueError) as caught:
            optional_public_skill_staging(
                self.root,
                batch_builder=lambda **kwargs: {
                    "sources_fetched": ["UNAPPROVED_PRIVATE_SOURCE"],
                    "overall_gets_upper_bound": 8,
                    "enriched_count": 0,
                    "production_approved": False,
                })
        self.assertEqual(
            getattr(caught.exception, "ucie_stage10_phase", None),
            "STAGE10_BATCH")
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_disabling_after_opt_in_does_not_delete_staged_data(self):
        self.optin()
        optional_public_skill_staging(self.root, batch_builder=fixture_batch)
        self.marker.unlink()
        stopped = optional_public_skill_staging(
            self.root, batch_builder=lambda **k: self.fail("unexpected API"))
        self.assertEqual(stopped["status"], STATUS_DISABLED)
        self.assertEqual(inspect_staged_candidates(
            self.root)["candidate_revisions"], 1)

    def test_invalid_marker_fails_before_public_network_or_disk_write(self):
        self.marker.write_text("UCIE_PRODUCTION_AUTOPROMOTION", encoding="utf-8")
        with self.assertRaises(ValueError):
            optional_public_skill_staging(
                self.root, batch_builder=lambda **k: self.fail("network"))
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_reject_marker_symlink(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / "foreign.txt"
            target.write_text(OPT_IN_TOKEN, encoding="utf-8")
            try:
                self.marker.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unsupported")
            with self.assertRaises(ValueError):
                optional_public_skill_staging(
                    self.root, batch_builder=lambda **k: self.fail("network"))
            self.assertFalse((self.runtime / DB_NAME).exists())

    def test_refuse_forged_stager_approval(self):
        self.optin()
        def unsafe_stager(*a, **k):
            return {
                "status": "UNVERIFIED_CANDIDATES_STAGED_NO_GO",
                "mode": "OPT_IN_SEPARATE_DISK",
                "approved_rules_added": 1, "production_approved": False,
            }
        with self.assertRaises(ValueError):
            optional_public_skill_staging(
                self.root, batch_builder=fixture_batch,
                stage_candidate_batch=unsafe_stager)

    def test_failure_in_optional_stage_cannot_invalidate_legacy_miner(self):
        self.optin()
        def collect(root):
            legacy = _legacy_success(root)
            try:
                optional_public_skill_staging(
                    root, batch_builder=lambda **k: (_ for _ in ()).throw(
                        RuntimeError("fake API unavailable")))
            except RuntimeError:
                pass
            return legacy
        receipt = run_cycle(self.root, collect=collect,
                            write_report=_write_report)
        self.assertEqual(receipt["status"], "COLLECTED_UNVERIFIED")
        self.assertFalse((self.runtime / DB_NAME).exists())


if __name__ == "__main__":
    unittest.main()
