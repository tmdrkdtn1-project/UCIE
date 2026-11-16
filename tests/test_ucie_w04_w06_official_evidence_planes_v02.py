"""UCIE W04/W06 read-only official evidence integration acceptance tests.

No live GitHub API, no task scheduler or production ledger mutation;
Stage14 tests use only isolated TemporaryDirectory/UCIE fixtures.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner.library_federated_official_v02 import (
    SCHEMA, FederatedOfficialError, _plain_text,
    search_with_official_evidence, compare_catalog_to_official,
)
from ucie_miner.library_shelves import (
    LibraryShelfError, search_official_metadata_shelf,
)
from ucie_miner.public_official_evidence import (
    _schema as stage14_schema, DB_NAME as OFFICIAL_DB,
)
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)
from ucie_miner.public_candidate_staging import stage_public_candidates
from test_ucie_stage11_hourly_stage import fixture_batch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "python/cpython"
ROWS = (
    ("document", SOURCE, "pinned-doc-url", "a"*64,
     "2026-10-27T05:00:00+00:00", "PUBLIC_METADATA_UNVERIFIED"),
    ("release", SOURCE, "1234567", "b"*64,
     "2026-10-26T05:00:00+00:00", "PUBLIC_METADATA_UNVERIFIED"),
    ("advisory", SOURCE, "GHSA-2345-6789-cfgh", "c"*64,
     "2026-10-25T05:00:00+00:00", "PUBLIC_METADATA_UNVERIFIED"),
)


class W04W06OfficialPlaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix="UCIE_W04W06_OFFICIAL_SYNTH_")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"UCIE"
        (self.root/"runtime").mkdir(parents=True)
        self.db=self.root/"runtime"/OFFICIAL_DB

    def _populate(self):
        with closing(sqlite3.connect(self.db)) as conn:
            stage14_schema(conn,new=True)
            conn.executemany(
                "INSERT INTO official_revision VALUES(?,?,?,?,?,?)", ROWS)
            conn.commit()

    def _query(self, **kwargs):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no public GET during read-only search")):
            return search_with_official_evidence(self.root,**kwargs)

    def test_01_absent_W06_remains_partial_unknown_not_zero_claim(self):
        output=self._query(query="python",limit=5)
        self.assertEqual(output["schema"],SCHEMA)
        self.assertEqual(output["status"],
                         "FEDERATED_PARTIAL_EVIDENCE_PLANES_NO_GO")
        self.assertFalse(output["official_window"]["total_matches_known"])
        self.assertIsNone(output["official_window"]["total_matches"])
        self.assertEqual(output["official_window"]["items"],[])
        self.assertFalse(self.db.exists())
        self.assertFalse(output["cross_plane_result_totals_combined"])
        self.assertFalse(output["v1_library_accepted"])
        self.assertFalse(output["customer_release_authorized"])

    def test_02_W06_stable_pagination_three_distinct_evidence_kinds(self):
        self._populate()
        before=self.db.read_bytes()
        entire=self._query(query="python",limit=10)
        one=self._query(query="python",limit=1,official_offset=0)
        two=self._query(query="python",limit=1,official_offset=1)
        three=self._query(query="python",limit=1,official_offset=2)
        fourth=self._query(query="python",limit=1,official_offset=3)
        all_items=entire["official_window"]["items"]
        self.assertEqual([i["metadata_inventory_id"]
                          for i in one["official_window"]["items"]+
                                   two["official_window"]["items"]+
                                   three["official_window"]["items"]],
                         [i["metadata_inventory_id"] for i in all_items])
        self.assertEqual(len(all_items),3)
        self.assertEqual(fourth["official_window"]["returned_count"],0)
        self.assertEqual(entire["official_window"]["total_matches"],3)
        self.assertEqual({i["kind"] for i in all_items},{
            "OFFICIAL_ADVISORY_EVIDENCE",
            "OFFICIAL_RELEASE_EVIDENCE",
            "OFFICIAL_DOCUMENT_EVIDENCE",
        })
        self.assertEqual(entire["status"],
                         "FEDERATED_PARTIAL_EVIDENCE_PLANES_NO_GO")
        self.assertTrue(entire["official_window"]["total_matches_known"])
        self.assertEqual(before,self.db.read_bytes())
        self.assertTrue(all(
            i["evidence_level"]=="STAGE14_METADATA_HASH_ONLY_NOT_CONTENT_OR_VERSION_CERTIFICATION"
            and i["lifecycle"]=="PUBLIC_METADATA_UNVERIFIED"
            and not i["content_bytes_independently_verified"]
            and not i["source_revision_validated"]
            and not i["license_verified"]
            and not i["effect_measured"]
            and not i["export_allowed"]
            for i in all_items))

    def test_03_exact_source_and_kind_filters_stay_within_approved_repos(self):
        self._populate()
        document=self._query(query="python",source_id="repo:python/cpython",
                             official_kind="document",limit=10)
        self.assertEqual(document["official_window"]["total_matches"],1)
        self.assertEqual(document["official_window"]["items"][0]["source_id"],
                         "doc:python/cpython")
        self.assertEqual(document["official_window"]["items"][0]["reference_scope"],
                         "PINNED_OFFICIAL_DOCUMENT_CURRENT_URL")
        none=self._query(query="python",source_id="repo:git/git",
                         official_kind="advisory")
        self.assertEqual(none["official_window"]["total_matches"],0)
        self.assertEqual(none["official_window"]["returned_count"],0)

    def test_04_comparison_does_not_assert_same_fix_or_capability_benefit(self):
        self._populate()
        out=self._query(query="python",limit=10,include_w04=False)
        candidate=out["candidate_window"]["items"][0]
        official=out["official_window"]["items"][0]
        compared=compare_catalog_to_official(
            out,candidate_id=candidate["library_item_id"],
            official_id=official["metadata_inventory_id"])
        self.assertEqual(compared["status"],
                         "CROSS_PLANE_EVIDENCE_PROVENANCE_ONLY_NO_GO")
        self.assertFalse(compared["same_underlying_fix_or_causal_link_verified"])
        self.assertFalse(compared["performance_benefit_measured"])
        self.assertFalse(compared["source_license_verified"])
        self.assertFalse(compared["export_allowed"])
        with self.assertRaises(FederatedOfficialError):
            compare_catalog_to_official(
                out,candidate_id=candidate["library_item_id"],
                official_id="f"*64)

    def test_05_invalid_source_offset_kind_query_and_document_tamper_denied(self):
        self._populate()
        for bad in (
            {"source_id":"repo:unapproved/stranger"},
            {"source_id":"research:GH Archive"},
            {"source_id":"doc:python/cpython"},
            {"official_kind":"private"},
            {"limit":True},
            {"limit":21},
            {"offset":-1},
            {"official_offset":True},
            {"official_offset":20001},
            {"query":"python\nprompt injection"},
            {"include_w04":"yes"},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises((FederatedOfficialError,ValueError)):
                    self._query(**bad)
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("UPDATE official_revision SET upstream_reference='../../secret' "
                         "WHERE evidence_kind='document'")
            conn.commit()
        with self.assertRaises((FederatedOfficialError,LibraryShelfError)):
            self._query(query="python",official_kind="document")

    def test_06_source_linked_W04_and_Stage14_both_visible_when_complete(self):
        self._populate()
        batch=fixture_batch(
            root=self.root,
            sources=("python/cpython","PowerShell/PowerShell",
                     "git/git","modelcontextprotocol/python-sdk",
                     "actions/runner-images"),
            max_enrich=1,include_git_commits=True,
            include_docs=False,include_advisories=False,
            backfill_pages=1)
        stage_public_candidates(batch,root=self.root,allow_disk_write=True)
        (self.root/"runtime"/OPT_IN_FILENAME).write_text(
            OPT_IN_TOKEN,encoding="ascii")
        review=optional_hourly_review_learning(self.root)
        self.assertEqual(review["new_review_proposals"],2)
        out=self._query(query="",limit=20)
        self.assertEqual(out["status"],
                         "FEDERATED_TWO_EVIDENCE_PLANES_UNVERIFIED_NO_GO")
        self.assertEqual(out["candidate_window"]["legacy_w04_matches"],2)
        self.assertEqual(out["official_window"]["total_matches"],3)
        self.assertFalse(out["cross_plane_duplicate_or_revision_equivalence_certified"])
        self.assertFalse(out["cross_plane_result_totals_combined"])
        self.assertEqual(out["network_requests"],0)
        self.assertEqual(out["operating_database_writes"],0)
        self.assertFalse(out["auto_promoted"])

    def test_07_human_readable_screen_distinguishes_evidence_planes(self):
        self._populate()
        report=self._query(query="python",limit=5)
        txt=_plain_text(report)
        self.assertIn("UCIE Virtual Library",txt)
        self.assertIn("CANDIDATE",txt)
        self.assertIn("OFFICIAL",txt)
        self.assertIn("GET=0 | DB-WRITES=0",txt)
        self.assertIn("HASH METADATA ONLY / NOT VERIFIED",txt)
        self.assertNotIn("APPROVED FOR RELEASE",txt)

    @unittest.skipUnless(os.name=="nt","exact owner Windows only")
    def test_08_owner_W06_readonly_observation_no_public_GET(self):
        if ROOT.resolve()!=Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("exact UCIE owner checkout not available")
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("real W06 test must not use network")):
            report=search_with_official_evidence(
                ROOT,query="python",limit=6)
        self.assertEqual(report["schema"],SCHEMA)
        self.assertEqual(report["network_requests"],0)
        self.assertEqual(report["operating_database_writes"],0)
        self.assertFalse(report["auto_promoted"])
        self.assertFalse(report["v1_library_accepted"])
        out={
            "schema":SCHEMA,
            "status":report["status"],
            "w04_catalog_status":report["candidate_window"]["status"],
            "w04_linked_matches":report["candidate_window"]["legacy_w04_matches"],
            "w06_status":report["official_window"]["status"],
            "w06_matches":report["official_window"]["total_matches"],
            "w06_page_items":report["official_window"]["returned_count"],
            "network_requests":0,"operating_database_writes":0,
            "auto_promoted":False,
        }
        print("UCIE_W04_W06_OWNER_READONLY="+json.dumps(
            out,sort_keys=True,ensure_ascii=True))


if __name__=="__main__":
    unittest.main()
