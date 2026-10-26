"""Stage 15: synthetic public patch/release evidence, no remote execution."""
from contextlib import closing
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_external_history import _schema as init_history
from ucie_miner.public_evidence_routes import PublicEvidenceError
from ucie_miner.public_fix_evidence import (
    DB_NAME, OPT_IN_FILE, OPT_IN_TOKEN, EVIDENCE_STATE,
    inspect_fix_evidence, optional_fix_evidence_enrichment,
)

SOURCE = "python/cpython"
SOURCE_TWO = "modelcontextprotocol/python-sdk"
SHA = "a" * 40
SHA_TWO = "c" * 40


def patch_fixture(source, number):
    return [{
        "filename": "tests/test_behavior.py",
        "status": "modified",
        "patch": ("- raise RuntimeError('INERT_UPSTREAM_ERROR')\n"
                  "+ raise ValueError('INERT_UPSTREAM_ERROR')\n"
                  "+ with Lock(): pass\n"),
    }]


def release_fixture():
    return [{
        "tag_name": "v3.15.0", "draft": False, "prerelease": False,
        "published_at": "2026-10-01T10:00:00Z",
        "body": "INERT_REMOTE_CODE_DO_NOT_STORE",
    }]


class _FixedStage15UTC(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 26, tzinfo=timezone.utc).astimezone(tz or timezone.utc)


class FixEvidenceTests(unittest.TestCase):
    def setUp(self):
        # The real collector rotates by UTC hour. Pin synthetic fixture
        # selection to a reproducible even hour; never depend on CI wall time.
        self.enterContext(patch("ucie_miner.public_fix_evidence.datetime",
                                _FixedStage15UTC))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.marker = self.runtime / OPT_IN_FILE
        self.miner = self.runtime / "public_miner.sqlite3"
        self.knowledge = self.runtime / "knowledge.sqlite3"
        self.miner.write_bytes(b"operational miner unchanged")
        self.knowledge.write_bytes(b"operational Knowledge unchanged")
        self.external = self.runtime / "stage13_external_public_history.sqlite3"
        with closing(sqlite3.connect(self.external)) as db:
            db.execute("BEGIN IMMEDIATE")
            init_history(db, new=True)
            db.execute("""INSERT INTO upstream_history VALUES
                (?,?,?,?,?,?,?,?,?)""", (
                SOURCE, 12345, SHA, "2026-10-01T10:00:00Z",
                "1" * 64, "2" * 64, "python-runtime-safety",
                '["REGRESSION"]', "UNVERIFIED_CANDIDATE_ONLY",
            ))
            db.execute("""INSERT INTO upstream_history VALUES
                (?,?,?,?,?,?,?,?,?)""", (
                SOURCE_TWO, 67890, SHA_TWO, "2026-09-30T10:00:00Z",
                "3" * 64, "4" * 64, "mcp-api-compatibility",
                '["COMPATIBILITY"]', "UNVERIFIED_CANDIDATE_ONLY",
            ))
            db.commit()
        self.urls = []

    def activate(self):
        self.marker.write_text(OPT_IN_TOKEN, encoding="ascii")

    def fetch(self, url):
        self.urls.append(url)
        if "/files?per_page=30" in url:
            if "/python/cpython/" in url:
                return patch_fixture(SOURCE, 12345)
            return patch_fixture(SOURCE_TWO, 67890)
        if "/releases?per_page=10" in url:
            return release_fixture()
        self.fail("unexpected public endpoint")

    def test_off_by_default_never_reads_external_api(self):
        result = optional_fix_evidence_enrichment(
            self.root, fetch=lambda _: self.fail("external HTTP must be off"))
        self.assertEqual(result["status"], "STAGE15_FIX_EVIDENCE_DISABLED")
        self.assertFalse((self.runtime / DB_NAME).exists())
        self.assertEqual(inspect_fix_evidence(self.root)["evidence_records"], 0)

    def test_two_real_patch_release_receipts_become_unverified_structured_evidence(self):
        self.activate()
        before = self.miner.read_bytes(), self.knowledge.read_bytes()
        result = optional_fix_evidence_enrichment(self.root, fetch=self.fetch)
        self.assertEqual(result["status"], "STAGE15_STRUCTURED_FIX_EVIDENCE_STAGED_NO_GO")
        self.assertEqual(result["public_prs_enriched"], 2)
        self.assertEqual(result["external_gets_upper_bound"], 4)
        self.assertEqual(result["new_unverified_evidence_records"], 2)
        self.assertEqual(len(self.urls), 4)
        inventory = inspect_fix_evidence(self.root)
        self.assertEqual(inventory["evidence_records"], 2)
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as db:
            rows = db.execute("""
                SELECT pattern_tags_json,removed_signals_json,added_signals_json,
                test_file_count,patch_file_count,published_release_count,
                missing_evidence_json,safe_guidance,regression_plan,
                affected_versions_state,license_state,evidence_state,review_state
                FROM fix_evidence
            """).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(x[3] == 1 and x[4] == 1 and x[5] == 1 for x in rows))
        self.assertTrue(all(json.loads(x[6]) == ["advisory", "document"] for x in rows))
        self.assertTrue(all(x[9] == "UNDETERMINED" and x[10] == "UNVERIFIED"
                            and x[11] == EVIDENCE_STATE
                            and x[12] == "UNVERIFIED_REVIEW_CANDIDATE_ONLY"
                            for x in rows))
        self.assertIn("EXCEPTION_HANDLING", str(rows))
        self.assertIn("GENERIC_EXCEPTION", str(rows))
        self.assertIn("THREAD_SERIALIZATION", str(rows))
        self.assertNotIn("INERT_REMOTE_CODE", str(rows))
        self.assertNotIn("INERT_UPSTREAM_ERROR", str(rows))
        self.assertEqual((self.miner.read_bytes(), self.knowledge.read_bytes()), before)
        self.assertEqual(result["approved_rules"], 0)
        self.assertFalse(result["model_weights_updated"])

    def test_repeat_cycle_skips_reenrichment_and_network(self):
        self.activate()
        first = optional_fix_evidence_enrichment(self.root, fetch=self.fetch)
        self.assertEqual(first["new_unverified_evidence_records"], 2)
        second = optional_fix_evidence_enrichment(
            self.root, fetch=lambda _: self.fail("duplicate network request"))
        self.assertEqual(second["public_prs_enriched"], 0)
        self.assertEqual(second["new_unverified_evidence_records"], 0)
        self.assertEqual(inspect_fix_evidence(self.root)["evidence_records"], 2)

    def test_new_historical_evidence_revision_is_new_review_only(self):
        self.activate()
        optional_fix_evidence_enrichment(self.root, fetch=self.fetch)
        with closing(sqlite3.connect(self.external)) as db:
            db.execute("""INSERT INTO upstream_history VALUES
                (?,?,?,?,?,?,?,?,?)""", (
                SOURCE, 12345, SHA, "2026-10-01T10:00:00Z",
                "1" * 64, "f" * 64, "python-runtime-safety",
                '["REGRESSION"]', "UNVERIFIED_CANDIDATE_ONLY",
            ))
            db.commit()
        repeat = optional_fix_evidence_enrichment(self.root, fetch=self.fetch)
        self.assertEqual(repeat["new_unverified_evidence_records"], 1)
        self.assertEqual(inspect_fix_evidence(self.root)["evidence_records"], 3)

    def test_public_patch_missing_does_not_falsely_create_review_record(self):
        self.activate()
        def no_patch(url):
            if "/files?" in url:
                raise PublicEvidenceError("remote error details must stay inert")
            return release_fixture()
        result = optional_fix_evidence_enrichment(
            self.root, fetch=no_patch, max_candidates=1)
        self.assertEqual(
            result["status"], "STAGE15_PUBLIC_EVIDENCE_REJECTED_PARTIAL_NO_GO")
        self.assertEqual(result["failure_source"], SOURCE)
        self.assertEqual(result["failure_category"],
                         "PUBLIC_PATCH_OR_RELEASE_REJECTED")
        self.assertEqual(result["new_unverified_evidence_records"], 0)
        self.assertEqual(result["public_prs_attempted"], 1)
        self.assertEqual(result["external_gets_upper_bound"], 2)
        self.assertNotIn("remote error details", str(result))
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_invalid_remote_path_fails_closed(self):
        self.activate()
        def bad_path(url):
            if "/files?" in url:
                return [{
                    "filename": "../malicious.py",
                    "status": "modified", "patch": "+exec('UPSTREAM')",
                }]
            return release_fixture()
        result = optional_fix_evidence_enrichment(
            self.root, fetch=bad_path, max_candidates=1)
        self.assertEqual(
            result["status"], "STAGE15_PUBLIC_EVIDENCE_REJECTED_PARTIAL_NO_GO")
        self.assertEqual(result["failure_source"], SOURCE)
        self.assertEqual(result["new_unverified_evidence_records"], 0)
        self.assertFalse((self.runtime / DB_NAME).exists())

    def test_stage15_missing_release_rejects_two_bounded_leads_without_writing(self):
        self.activate()
        before = self.miner.read_bytes(), self.knowledge.read_bytes()
        requested = []
        def missing_release(url):
            requested.append(url)
            if "/files?" in url:
                return patch_fixture(SOURCE, 12345)
            raise PublicEvidenceError("INERT_UNTRUSTED_UPSTREAM_TOKEN")
        result = optional_fix_evidence_enrichment(
            self.root, fetch=missing_release)
        self.assertEqual(result["status"],
                         "STAGE15_PUBLIC_EVIDENCE_REJECTED_PARTIAL_NO_GO")
        self.assertEqual(result["public_prs_attempted"], 2)
        self.assertEqual(result["public_prs_enriched"], 0)
        self.assertEqual(len(requested), 4)
        self.assertEqual(result["external_gets_upper_bound"], 4)
        self.assertEqual(result["failure_source"], SOURCE)
        self.assertEqual(result["failure_category"],
                         "PUBLIC_PATCH_OR_RELEASE_REJECTED")
        self.assertNotIn("INERT_UNTRUSTED_UPSTREAM_TOKEN", str(result))
        self.assertFalse((self.runtime / DB_NAME).exists())
        self.assertEqual((self.miner.read_bytes(), self.knowledge.read_bytes()),
                         before)
        self.assertFalse(result["production_approved"])

    def test_no_license_version_or_independent_regression_promotion(self):
        self.activate()
        optional_fix_evidence_enrichment(self.root, fetch=self.fetch)
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as db:
            modes = db.execute("""
                SELECT DISTINCT affected_versions_state, license_state,
                    evidence_state,review_state FROM fix_evidence
            """).fetchall()
        self.assertEqual(modes, [(
            "UNDETERMINED", "UNVERIFIED", EVIDENCE_STATE,
            "UNVERIFIED_REVIEW_CANDIDATE_ONLY"
        )])
        self.assertEqual(inspect_fix_evidence(self.root)["approved_rules"], 0)

    def test_disabled_again_preserves_existing_and_performs_no_gets(self):
        self.activate()
        optional_fix_evidence_enrichment(self.root, fetch=self.fetch)
        self.marker.unlink()
        result = optional_fix_evidence_enrichment(
            self.root, fetch=lambda _: self.fail("network after opt out"))
        self.assertEqual(result["status"], "STAGE15_FIX_EVIDENCE_DISABLED")
        self.assertEqual(inspect_fix_evidence(self.root)["evidence_records"], 2)

    def test_invalid_opt_in_and_foreign_sqlite_rejected(self):
        self.marker.write_text("RUN_EXTERNAL_CODE_AUTO_APPLY", encoding="ascii")
        with self.assertRaises(DiscoveryError):
            optional_fix_evidence_enrichment(
                self.root, fetch=lambda _: self.fail("network"))
        self.activate()
        with closing(sqlite3.connect(self.runtime / DB_NAME)) as db:
            db.execute("CREATE TABLE foreign_schema(data TEXT)")
            db.commit()
        with self.assertRaises(DiscoveryError):
            optional_fix_evidence_enrichment(
                self.root, fetch=lambda _: self.fail("network"))

    def test_stage13_source_tampering_denied_before_network(self):
        self.activate()
        with closing(sqlite3.connect(self.external)) as db:
            db.execute("UPDATE upstream_history SET source='unapproved/private'")
            db.commit()
        with self.assertRaises(DiscoveryError):
            optional_fix_evidence_enrichment(
                self.root, fetch=lambda _: self.fail("network"))

    def test_max_candidates_bounded(self):
        self.activate()
        with self.assertRaises(DiscoveryError):
            optional_fix_evidence_enrichment(self.root, fetch=self.fetch,
                                             max_candidates=100)
        self.assertEqual(self.urls, [])


if __name__ == "__main__":
    unittest.main()
