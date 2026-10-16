"""Stage17 fully synthetic live-transport substitution; no real external GET."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_external_history import DB_NAME as HISTORY_DB, _schema as init_history
from ucie_miner.public_fix_evidence import DB_NAME as FIX_DB, _check_schema as init_fix
from ucie_miner.public_official_evidence import DB_NAME as OFFICIAL_DB, _schema as init_official
from ucie_miner.public_evidence_routes import inspect_pr_changes
from ucie_miner.public_pr_coverage_audit import (
    audit_public_pr_evidence_once, public_pr_audit_url, _approved_url,
    fetch_stage17_public,
)
from ucie_miner.skill_profiles import PROFILE

SOURCE = "python/cpython"
SKILL = "python-runtime-safety"
MERGE = "a" * 40
OTHER_MERGE = "f" * 40
HISTORY_SHA = "b" * 64
EVIDENCE_SHA = "c" * 64
PR = 42


def files_fixture(n):
    return [
        {"filename": f"tests/test_behavior_{i}.py", "status": "modified",
         "patch": "- raise RuntimeError('INERT')\n+ raise ValueError('INERT')\n"}
        for i in range(n)
    ]


def metadata_fixture(n, merge=MERGE):
    return {
        "number": PR, "state": "closed", "merge_commit_sha": merge,
        "merged_at": "2026-10-01T10:00:00Z",
        "html_url": f"https://github.com/{SOURCE}/pull/{PR}",
        "base": {"repo": {"full_name": SOURCE}},
        "changed_files": n,
    }


class PublicCoverageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.operating = self.runtime / "public_miner.sqlite3"
        self.operating.write_bytes(b"ORIGINAL_OPERATING_LEDGER")
        self.requests = []
        self.total_files = 1
        self.custom_files = None
        self.merge = MERGE
        self.remaining = 50
        self.duplicate_page_two = False
        self.short_page_two = False
        self._ledgers()

    def _ledgers(self):
        with closing(sqlite3.connect(self.runtime / HISTORY_DB)) as db:
            db.execute("BEGIN IMMEDIATE")
            init_history(db, new=True)
            db.execute("INSERT INTO upstream_history VALUES (?,?,?,?,?,?,?,?,?)", (
                SOURCE, PR, MERGE, "2026-10-01T10:00:00Z", "d" * 64,
                HISTORY_SHA, SKILL, '["REGRESSION"]', "UNVERIFIED_CANDIDATE_ONLY"))
            db.commit()
        features = inspect_pr_changes(SOURCE, PR, files_fixture(1), merge_sha=MERGE)
        with closing(sqlite3.connect(self.runtime / FIX_DB)) as db:
            db.execute("BEGIN IMMEDIATE")
            init_fix(db, new=True)
            profile = PROFILE[SKILL]
            db.execute("INSERT INTO fix_evidence VALUES (" + ",".join("?" * 21) + ")", (
                SOURCE, PR, MERGE, HISTORY_SHA, EVIDENCE_SHA, SKILL,
                json.dumps(features["tags"], separators=(",", ":")),
                json.dumps(features["removed_behavior_signals"], separators=(",", ":")),
                json.dumps(features["added_behavior_signals"], separators=(",", ":")),
                features["test_file_count"], features["patch_file_count"],
                features["coverage"], 1, '["advisory","document"]',
                profile["safe_call"], profile["recommended_action"],
                "UNDETERMINED", "UNVERIFIED", "PUBLIC_PATCH_RELEASE_HINTS_UNVERIFIED",
                "UNVERIFIED_REVIEW_CANDIDATE_ONLY", "2026-10-15T10:00:00+00:00"))
            db.commit()

    def set_first_page_snapshot(self, n):
        features = inspect_pr_changes(SOURCE, PR, files_fixture(n), merge_sha=MERGE)
        with closing(sqlite3.connect(self.runtime / FIX_DB)) as db:
            db.execute("""UPDATE fix_evidence SET
                pattern_tags_json=?,removed_signals_json=?,added_signals_json=?,
                test_file_count=?,patch_file_count=?,patch_coverage=?""", (
                json.dumps(features["tags"], separators=(",", ":")),
                json.dumps(features["removed_behavior_signals"], separators=(",", ":")),
                json.dumps(features["added_behavior_signals"], separators=(",", ":")),
                features["test_file_count"], features["patch_file_count"],
                features["coverage"]))
            db.commit()

    def fetch(self, url):
        self.assertTrue(_approved_url(url))
        self.requests.append(url)
        if url == public_pr_audit_url(SOURCE, PR):
            return metadata_fixture(self.total_files, self.merge), self.remaining
        page = int(url.rsplit("=", 1)[1])
        offset = (page - 1) * 30
        files = self.custom_files if self.custom_files is not None else files_fixture(self.total_files)
        entries = [dict(e) for e in files[offset:offset + 30]]
        if page == 2 and self.duplicate_page_two:
            entries[0]["filename"] = "tests/test_behavior_0.py"
        if page == 2 and self.short_page_two:
            entries.pop()
        return entries, self.remaining

    def test_build_config_backports_expose_real_filenames_without_touching_stage15(self):
        # Shape of the two observed approved CPython 3.14/3.15 backports.
        self.custom_files = [
            {"filename": "Misc/NEWS.d/next/Build/fix-build-tag.rst",
             "status": "added", "patch": "+ news-only"},
            {"filename": "configure", "status": "modified",
             "patch": "- git --git-dir=foo\n+ git --git-dir=foo --work-tree=bar"},
            {"filename": "configure.ac", "status": "modified",
             "patch": "- git --git-dir=foo\n+ git --git-dir=foo --work-tree=bar"},
        ]
        self.total_files = len(self.custom_files)
        # Historical Stage15 ignored these formats. Preserve its pinned
        # snapshot exactly; never reclassify old data as failed provenance.
        self.assertEqual(
            inspect_pr_changes(SOURCE, PR, self.custom_files, merge_sha=MERGE)[
                "changed_supported_file_count"], 0)
        with closing(sqlite3.connect(self.runtime / FIX_DB)) as db:
            features = inspect_pr_changes(SOURCE, PR, self.custom_files, merge_sha=MERGE)
            db.execute("""UPDATE fix_evidence SET pattern_tags_json=?,
                removed_signals_json=?,added_signals_json=?,
                patch_file_count=?,test_file_count=?,patch_coverage=?""", (
                json.dumps(features["tags"], separators=(",", ":")),
                json.dumps(features["removed_behavior_signals"], separators=(",", ":")),
                json.dumps(features["added_behavior_signals"], separators=(",", ":")),
                features["patch_file_count"], features["test_file_count"],
                features["coverage"]))
            db.commit()
        before = {p.name: p.read_bytes() for p in self.runtime.iterdir()}
        result = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(result["status"], "STAGE17_UPSTREAM_LISTING_RECHECKED_UNVERIFIED_NO_GO")
        self.assertTrue(result["stage15_first_page_snapshot_matches"])
        self.assertEqual(result["observed_supported_file_count"], 0)
        self.assertEqual(result["autoconf_source_files_observed"], 1)
        self.assertEqual(result["generated_configure_files_observed"], 1)
        self.assertEqual(result["build_release_note_files_observed"], 1)
        self.assertEqual(result["other_files_observed"], 0)
        self.assertEqual(result["build_file_classification_state"],
                         "FILENAME_ONLY_UNVERIFIED")
        self.assertFalse(result["independent_regression_verified"])
        self.assertFalse(result["production_approved"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.runtime.iterdir()})

    def test_non_root_configure_does_not_become_false_build_source(self):
        self.custom_files = [{
            "filename": "docs/configure.ac", "status": "modified",
            "patch": "+ inert"},
        ]
        result = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(result["autoconf_source_files_observed"], 0)
        self.assertEqual(result["other_files_observed"], 1)

    def test_unrelated_python_code_is_not_mislabeled_build_source(self):
        result = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(result["autoconf_source_files_observed"], 0)
        self.assertEqual(result["generated_configure_files_observed"], 0)
        self.assertEqual(result["build_release_note_files_observed"], 0)
        self.assertEqual(result["other_files_observed"], 1)

    def test_single_file_matches_upstream_identity_and_snapshot_not_verified_fix(self):
        before = {p.name: p.read_bytes() for p in self.runtime.iterdir()}
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["status"], "STAGE17_UPSTREAM_LISTING_RECHECKED_UNVERIFIED_NO_GO")
        self.assertEqual(r["external_gets"], 2)
        self.assertEqual(r["pr_files_inspected"], 1)
        self.assertTrue(r["stage15_first_page_snapshot_matches"])
        self.assertTrue(r["pr_file_listing_complete_at_observation"])
        self.assertFalse(r["upstream_merge_independently_attested"])
        self.assertFalse(r["independent_regression_verified"])
        self.assertFalse(r["official_release_inclusion_proven"])
        self.assertFalse(r["production_approved"])
        self.assertEqual(r["stage14_same_source_inventory"]["present"], False)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.runtime.iterdir()})

    def test_two_pages_31_files_and_first_page_snapshot(self):
        self.total_files = 31
        self.set_first_page_snapshot(30)
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["external_gets"], 3)
        self.assertEqual(r["pr_file_pages_inspected"], 2)
        self.assertEqual(r["pr_files_inspected"], 31)
        self.assertTrue(r["stage15_first_page_snapshot_matches"])
        self.assertTrue(r["pr_file_listing_complete_at_observation"])

    def test_three_pages_90_files_complete(self):
        self.total_files = 90
        self.set_first_page_snapshot(30)
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["external_gets"], 4)
        self.assertTrue(r["pr_file_listing_complete_at_observation"])
        self.assertEqual(r["pr_files_inspected"], 90)

    def test_over_three_pages_91_files_is_partial_not_complete(self):
        self.total_files = 91
        self.set_first_page_snapshot(30)
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["status"], "STAGE17_PAGINATION_INCOMPLETE_NO_GO")
        self.assertEqual(r["external_gets"], 4)
        self.assertEqual(r["pr_files_inspected"], 90)
        self.assertFalse(r["pr_file_listing_complete_at_observation"])

    def test_upstream_merge_conflict_stops_before_patch_fetch(self):
        self.merge = OTHER_MERGE
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["status"], "STAGE17_UPSTREAM_MERGE_MISMATCH_NO_GO")
        self.assertEqual(r["external_gets"], 1)
        self.assertFalse(r["upstream_identity_rechecked"])
        self.assertEqual(len(self.requests), 1)

    def test_upstream_rate_budget_low_pauses_before_pages(self):
        self.remaining = 3
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["status"], "STAGE17_API_RATE_PAUSED_NO_GO")
        self.assertEqual(len(self.requests), 1)

    def test_duplicate_filenames_across_pages_fail_closed(self):
        self.total_files = 31
        self.set_first_page_snapshot(30)
        self.duplicate_page_two = True
        with self.assertRaises(DiscoveryError):
            audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)

    def test_metadata_file_count_disagreement_does_not_claim_complete(self):
        self.total_files = 31
        self.set_first_page_snapshot(30)
        self.short_page_two = True
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["status"], "STAGE17_FILE_COUNT_MISMATCH_NO_GO")
        self.assertFalse(r["pr_file_listing_complete_at_observation"])

    def test_old_first_page_snapshot_drift_does_not_mark_match(self):
        self.total_files = 2
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["status"], "STAGE17_LOCAL_FIRST_PAGE_HINT_MISMATCH_NO_GO")
        self.assertFalse(r["stage15_first_page_snapshot_matches"])

    def test_reject_unknown_source_or_page_without_network(self):
        for args in (("unapproved/private", 7), (SOURCE, 0)):
            with self.assertRaises(DiscoveryError):
                audit_public_pr_evidence_once(self.root, *args, fetch=self.fetch)
        with self.assertRaises(DiscoveryError):
            public_pr_audit_url(SOURCE, PR, page=4)
        self.assertFalse(_approved_url("https://api.github.com/repos/python/cpython/pulls/42/files?per_page=100"))
        self.assertEqual(self.requests, [])

    def test_fetch_hard_denies_unapproved_url_without_network(self):
        with self.assertRaises(DiscoveryError):
            fetch_stage17_public("https://api.github.com/repos/unapproved/private/pulls/4")
        with self.assertRaises(DiscoveryError):
            fetch_stage17_public("https://api.github.com/repos/python/cpython/pulls/42/files?per_page=30&page=4")

    def test_stage14_same_source_evidence_has_no_pr_linkage(self):
        with closing(sqlite3.connect(self.runtime / OFFICIAL_DB)) as db:
            db.execute("BEGIN IMMEDIATE")
            init_official(db, new=True)
            db.execute("INSERT INTO official_revision VALUES (?,?,?,?,?,?)", (
                "release", SOURCE, "12345", "f" * 64,
                "2026-10-01T10:00:00Z", "PUBLIC_METADATA_UNVERIFIED"))
            db.commit()
        r = audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(r["stage14_same_source_inventory"]["counts"]["release"], 1)
        self.assertEqual(r["stage14_linkage_state"], "SAME_SOURCE_ONLY_NO_PR_CAUSAL_LINKAGE")
        self.assertFalse(r["official_release_inclusion_proven"])

    def test_unapproved_stage14_source_rejected_before_network(self):
        with closing(sqlite3.connect(self.runtime / OFFICIAL_DB)) as db:
            db.execute("BEGIN IMMEDIATE")
            init_official(db, new=True)
            db.execute("INSERT INTO official_revision VALUES (?,?,?,?,?,?)", (
                "release", "unapproved/private", "12345", "f" * 64,
                "2026-10-01T10:00:00Z", "PUBLIC_METADATA_UNVERIFIED"))
            db.commit()
        with self.assertRaises(DiscoveryError):
            audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=self.fetch)
        self.assertEqual(self.requests, [])

    def test_untrusted_transport_envelope_fails_closed(self):
        with self.assertRaises(DiscoveryError):
            audit_public_pr_evidence_once(self.root, SOURCE, PR,
                                          fetch=lambda _: (metadata_fixture(1), -1))

    def test_wrong_public_pr_number_fails_closed(self):
        def wrong(url):
            meta = metadata_fixture(1)
            meta["number"] = 99
            return meta, 50
        with self.assertRaises(DiscoveryError):
            audit_public_pr_evidence_once(self.root, SOURCE, PR, fetch=wrong)


if __name__ == "__main__":
    unittest.main()
