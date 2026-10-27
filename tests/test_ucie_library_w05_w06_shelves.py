"""Focused UCIE W05/W06 real Library shelf tests; offline and dedicated UCIE temp only."""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.library_shelves import (
    SCHEMA, LibraryShelfError, search_positive_capability_shelf,
    search_official_metadata_shelf, main,
)
from ucie_miner.library_search import search_linked_public_candidates
from ucie_miner.public_official_evidence import _schema as stage14_schema
from ucie_miner.public_discovery import DiscoveryError
from test_ucie_positive_capability_discovery import (
    handoff_two_evidence_revisions, public_pr, NOW,
)

SOURCE = "python/cpython"
DOC_URL = "https://docs.python.org/3/library/os.html"


class PositiveLibraryShelfTests(unittest.TestCase):
    def test_engine_skill_and_learning_logic_are_genuine_searchable_shelves(self):
        rows = [
            public_pr(101, "Introduce incremental build cache"),
            public_pr(102, "Introduce test automation"),
            public_pr(103, "Introduce adaptive learning feedback loop"),
            public_pr(104, "Fix regression in build cache"),
        ]
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("shelf must not use API")):
            all_results = search_positive_capability_shelf(
                rows, source_id="repo:python/cpython", now=NOW)
            engines = search_positive_capability_shelf(
                rows, source_id="repo:python/cpython", now=NOW,
                kind="DEVELOPMENT_ENGINE")
        self.assertEqual(all_results["schema"], SCHEMA)
        self.assertEqual(all_results["total_matches"], 3)
        self.assertEqual(engines["total_matches"], 1)
        self.assertEqual(
            {x["kind"] for x in all_results["items"]},
            {"DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC"})
        self.assertTrue(all(x["lifecycle"] == "UNVERIFIED_CANDIDATE_ONLY"
                            and x["actual_capability_verified"] is False
                            and x["human_approved"] is False
                            and x["export_allowed"] is False
                            for x in all_results["items"]))
        self.assertEqual(all_results["network_requests"], 0)
        self.assertEqual(all_results["database_writes"], 0)
        self.assertFalse(all_results["full_library_implemented"])
        self.assertNotIn(rows[0]["title"], json.dumps(all_results))

    def test_unapproved_source_wrong_kind_and_page_limit_rejected(self):
        rows = [public_pr(101, "Introduce incremental build cache")]
        for args in (
            {"source_id": "research:GH Archive"},
            {"source_id": "repo:unknown/private"},
            {"source_id": "repo:python/cpython", "kind": "PREVENTION_RULE"},
            {"source_id": "repo:python/cpython", "limit": 300},
        ):
            with self.subTest(args=args):
                with self.assertRaises((DiscoveryError, LibraryShelfError)):
                    search_positive_capability_shelf(rows, now=NOW, **args)

    def test_default_cli_is_inert_and_never_gets(self):
        import sys
        with patch("sys.argv", ["library_shelves", "--shelf", "positive",
                                "--source-id", "repo:python/cpython"]):
            with patch("ucie_miner.library_shelves.public_feed_get",
                       side_effect=AssertionError("must not GET")):
                with patch("builtins.print") as output:
                    self.assertEqual(main(), 0)
        result = json.loads(output.call_args.args[0])
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["items"], [])

    def test_one_explicit_positive_get_produces_library_results(self):
        called = []
        def synthetic_get(url):
            called.append(url)
            return [public_pr(101, "Introduce incremental build cache",
                              merged_at="2026-10-20T12:00:00Z")]
        # CLI clock is current and mocked public merged date remains in past.
        with patch("sys.argv", ["library_shelves", "--shelf", "positive",
                                "--source-id", "repo:python/cpython", "--live"]):
            with patch("ucie_miner.library_shelves.public_feed_get", synthetic_get):
                with patch("builtins.print") as output:
                    self.assertEqual(main(), 0)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0],
                         "https://api.github.com/repos/python/cpython/"
                         "pulls?state=closed&sort=updated&direction=desc&per_page=20")
        result = json.loads(output.call_args.args[0])
        self.assertEqual(result["total_matches"], 1)
        self.assertEqual(result["network_requests"], 1)
        self.assertFalse(result["items"][0]["export_allowed"])


class OfficialReadOnlyShelfTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir()
        self.db = self.root / "runtime" / "stage14_official_public_sources.sqlite3"

    def build_stage14(self):
        with closing(sqlite3.connect(self.db)) as conn:
            stage14_schema(conn, new=True)
            conn.executemany(
                "INSERT INTO official_revision VALUES (?,?,?,?,?,?)", [
                    ("document", SOURCE, "pinned-doc-url", "a" * 64,
                     "2026-10-27T05:00:00+00:00", "PUBLIC_METADATA_UNVERIFIED"),
                    ("release", SOURCE, "1234567", "b" * 64,
                     "2026-10-26T05:00:00+00:00", "PUBLIC_METADATA_UNVERIFIED"),
                    ("advisory", SOURCE, "GHSA-2345-6789-cfgh", "c" * 64,
                     "2026-10-25T05:00:00+00:00", "PUBLIC_METADATA_UNVERIFIED"),
                ])
            conn.commit()

    def test_missing_ledger_is_explicit_no_go_and_uncreated(self):
        result = search_official_metadata_shelf(self.root)
        self.assertEqual(result["status"], "STAGE14_OFFICIAL_LEDGER_ABSENT_NO_GO")
        self.assertFalse(self.db.exists())

    def test_three_official_kinds_read_without_database_mutation(self):
        self.build_stage14()
        before = self.db.read_bytes()
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("official shelf never GETs")):
            result = search_official_metadata_shelf(self.root)
            docs = search_official_metadata_shelf(
                self.root, source_id="doc:python/cpython")
            releases = search_official_metadata_shelf(
                self.root, source_id="repo:python/cpython", kind="release")
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual(result["total_matches"], 3)
        self.assertEqual(result["returned_count"], 3)
        self.assertEqual(result["database_writes"], 0)
        self.assertEqual(result["network_requests"], 0)
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(docs["total_matches"], 1)
        self.assertEqual(docs["items"][0]["public_url"], DOC_URL)
        self.assertEqual(releases["total_matches"], 1)
        self.assertEqual(releases["items"][0]["reference_scope"],
                         "PUBLIC_REPOSITORY_RELEASE_INDEX_NOT_EXACT_RELEASE")
        self.assertTrue(all(item["lifecycle"] == "PUBLIC_METADATA_UNVERIFIED"
                            and not item["export_allowed"]
                            for item in result["items"]))

    def test_research_source_and_non_doc_filter_fail_closed(self):
        for params in (
            {"source_id": "research:GH Archive"},
            {"source_id": "doc:python/cpython", "kind": "release"},
            {"kind": "private"},
            {"limit": True},
            {"limit": 30},
        ):
            with self.subTest(params=params):
                with self.assertRaises(LibraryShelfError):
                    search_official_metadata_shelf(self.root, **params)

    def test_hostile_official_row_must_not_gain_library_identity(self):
        self.build_stage14()
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute(
                "UPDATE official_revision SET upstream_reference='../../foo' "
                "WHERE evidence_kind='document'")
            conn.commit()
        with self.assertRaises(LibraryShelfError):
            search_official_metadata_shelf(self.root)

    def test_legacy_unclassified_pr_is_not_promoted_to_reusable_skill(self):
        result = search_linked_public_candidates(handoff_two_evidence_revisions())
        self.assertEqual(result["total_matches"], 2)
        self.assertEqual({i["kind"] for i in result["items"]},
                         {"PUBLIC_TECHNICAL_EVIDENCE"})
        self.assertEqual(result["approved_or_exportable_items"], 0)


if __name__ == "__main__":
    unittest.main()
