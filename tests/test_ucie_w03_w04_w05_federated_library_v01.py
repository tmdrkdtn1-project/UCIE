"""UCIE W03/W04/W05 federated read-only Library acceptance tests.

Only synthetic TEMP/UCIE ledgers and read-only real D:/UCIE observations.
No live GitHub/public network, no unapproved repositories, no model
training, source code execution, task scheduler, database mutation or
automatic approval/export.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.library_federated_readonly_v01 import (
    SCHEMA, CATALOG_STATUS, PARTIAL_STATUS, FederatedLibraryError,
    search_federated_library, compare_visible_items,
)
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)
from ucie_miner.public_candidate_staging import stage_public_candidates
from test_ucie_stage11_hourly_stage import fixture_batch
from test_ucie_positive_capability_discovery import public_pr, NOW

ROOT = Path(__file__).resolve().parents[1]


class UCIEFederatedLibraryV01Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="UCIE_W03W04W05_FED_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)

    def query(self, **kwargs):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no public GET in Library search")):
            return search_federated_library(self.root, **kwargs)

    def test_01_W01_W02_W03_official_refs_and_recipe_federation(self):
        out = self.query(query="", limit=20, include_legacy=False)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["status"], CATALOG_STATUS)
        self.assertEqual(out["total_matches"], 5)
        self.assertEqual(out["returned_count"], 5)
        self.assertEqual(out["shelf_counts"]["official_document_pointer_count"],4)
        self.assertEqual(out["shelf_counts"]["first_party_recipe_reference_count"],1)
        self.assertEqual(len(out["w03_existing_approved_adapter_plans"]),5)
        self.assertEqual({x["origin_shelf"] for x in out["items"]},{
            "APPROVED_OFFICIAL_DOCUMENT_POINTER",
            "FIRST_PARTY_TEST_RECIPE_REFERENCE",
        })
        self.assertEqual(out["network_requests"],0)
        self.assertEqual(out["operating_database_writes"],0)
        self.assertFalse(out["auto_promoted"])
        self.assertFalse(out["v1_library_accepted"])
        self.assertFalse(out["full_library_implemented"])
        self.assertTrue(all(not x["human_approved"]
                            and not x["export_allowed"]
                            and not x["license_verified"]
                            for x in out["items"]))

    def test_02_source_filter_and_Korean_query_partial_correctly(self):
        only = self.query(query="python", source_id="repo:python/cpython",
                          include_legacy=False)
        self.assertEqual(only["total_matches"],1)
        self.assertEqual(only["items"][0]["kind"],"TEST_RECIPE")
        self.assertEqual(only["items"][0]["source_id"],"doc:python/cpython")
        self.assertEqual(len(only["w03_existing_approved_adapter_plans"]),1)
        ko = self.query(query="파워셸", include_legacy=True)
        self.assertEqual(ko["status"],PARTIAL_STATUS)
        self.assertFalse(ko["total_matches_known"])
        self.assertEqual(ko["legacy_w04_status"],
                         "W04_QUERY_UNSUPPORTED_UNICODE_NO_LEDGER_SEARCH")
        self.assertEqual(ko["returned_count"],1)
        self.assertEqual(ko["items"][0]["source_id"],"doc:PowerShell/PowerShell")

    def test_03_missing_public_ledger_is_partial_not_verified_empty(self):
        out=self.query(query="python",limit=10)
        self.assertEqual(out["status"],PARTIAL_STATUS)
        self.assertEqual(out["legacy_w04_status"],
                         "SOURCE_LINKAGE_INCOMPLETE_NO_GO")
        self.assertIsNone(out["total_matches"])
        self.assertFalse(out["total_matches_known"])
        self.assertEqual(out["shelf_counts"]["first_party_recipe_reference_count"],1)
        self.assertTrue(all(x["origin_shelf"]!="SOURCE_LINKED_PUBLIC_PR_REVIEW"
                            for x in out["items"]))

    def test_04_offline_W05_positive_three_kinds_cannot_claim_real_capabilities(self):
        snapshot={"source_id":"repo:python/cpython","rows":[
            public_pr(100,"Add incremental build cache for compilation"),
            public_pr(101,"Introduce test automation workflow"),
            public_pr(102,"Implement adaptive learning feedback loop"),
            public_pr(103,"Fix regression in build cache"),
        ]}
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("offline W05 must not GET")):
            out=search_federated_library(
                self.root,query="",limit=20,
                positive_snapshot=snapshot,now=NOW,include_legacy=False)
        self.assertEqual(out["status"],CATALOG_STATUS)
        self.assertEqual(out["shelf_counts"]["offline_positive_title_cue_count"],3)
        self.assertEqual(out["w05_public_snapshot_provenance"],
                         "CALLER_SUPPLIED_OFFLINE_PUBLIC_METADATA_UNVERIFIED")
        positive=[x for x in out["items"]
                  if x["origin_shelf"]=="W05_OFFLINE_POSITIVE_TITLE_CUE"]
        self.assertEqual({x["kind"] for x in positive},
                         {"DEVELOPMENT_ENGINE","REUSABLE_SKILL","LEARNING_LOGIC"})
        self.assertTrue(all(x["evidence_level"]==
                            "CALLER_SUPPLIED_MERGED_PR_TITLE_HEURISTIC_UNVERIFIED"
                            and not x["capability_effect_verified"]
                            and not x["human_approved"]
                            and not x["export_allowed"] for x in positive))
        # Caller-controlled PR title must not be retained in Library result.
        self.assertNotIn(snapshot["rows"][0]["title"],json.dumps(out))
        self.assertEqual(out["network_requests"],0)

    def test_05_unapproved_source_drift_and_injection_fail_closed(self):
        bad=[
            {"source_id":"research:GH Archive"},
            {"source_id":"doc:python/cpython"},
            {"source_id":"repo:unapproved/private"},
            {"source_id":"https://github.com/python/cpython"},
            {"query":"python\nprivate"},
            {"limit":True},
            {"limit":21},
            {"offset":-1},
            {"offset":True},
            {"include_legacy":"true"},
        ]
        for kwargs in bad:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises((FederatedLibraryError,ValueError)):
                    self.query(**kwargs)
        for untrusted in (
            {"source_id":"repo:unapproved/private","rows":[]},
            {"source_id":"repo:python/cpython","rows":[
                {**public_pr(102,"Add incremental build cache"),
                 "html_url":"https://unapproved.invalid/steal"}]},
            {"source_id":"repo:python/cpython","rows":[
                public_pr(102,"Add incremental build cache")]*2},
        ):
            with self.subTest(source=untrusted["source_id"]):
                with self.assertRaises(ValueError):
                    self.query(positive_snapshot=untrusted,include_legacy=False)

    def test_06_provenance_comparison_never_rank_or_certify(self):
        out=self.query(query="",limit=10,include_legacy=False)
        a,b=out["items"][:2]
        comp=compare_visible_items(out,a["library_item_id"],b["library_item_id"])
        self.assertEqual(comp["status"],
                         "EVIDENCE_PROVENANCE_COMPARISON_ONLY_NOT_QUALITY_RANKING")
        self.assertFalse(comp["comparison_is_performance_evaluation"])
        self.assertTrue(comp["source_types_are_not_interchangeable"])
        self.assertTrue(all(not x["license_verified"]
                            and not x["capability_effect_verified"]
                            and not x["export_allowed"]
                            for x in comp["items"]))
        with self.assertRaises(FederatedLibraryError):
            compare_visible_items(out,a["library_item_id"],"f"*64)

    def test_07_federated_document_pagination_stable_no_overlap(self):
        complete=self.query(query="",limit=20,include_legacy=False)
        first=self.query(query="",limit=2,offset=0,include_legacy=False)
        second=self.query(query="",limit=2,offset=2,include_legacy=False)
        third=self.query(query="",limit=2,offset=4,include_legacy=False)
        combined=first["items"]+second["items"]+third["items"]
        self.assertEqual([x["library_item_id"] for x in combined],
                         [x["library_item_id"] for x in complete["items"]])
        self.assertEqual(complete["returned_count"],5)
        self.assertEqual(second["total_matches"],5)
        self.assertEqual(third["returned_count"],1)

    def test_08_real_stage10_stage12_source_linked_fixture_search_connected(self):
        from pathlib import Path
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
        result=optional_hourly_review_learning(self.root)
        self.assertEqual(result["new_review_proposals"],2)
        all_rows=self.query(query="",limit=20)
        self.assertEqual(all_rows["status"],CATALOG_STATUS)
        self.assertEqual(all_rows["legacy_w04_matches"],2)
        self.assertEqual(all_rows["total_matches"],7)
        self.assertEqual(all_rows["returned_count"],7)
        actual=[r for r in all_rows["items"]
                if r["origin_shelf"]=="SOURCE_LINKED_PUBLIC_PR_REVIEW"]
        self.assertEqual(len(actual),2)
        self.assertEqual({x["evidence_level"] for x in actual},
                         {"EXISTING_STAGE10_12_15_LINKED_UNVERIFIED_EVIDENCE"})
        self.assertTrue(all(not x["export_allowed"] for x in actual))
        paged=self.query(query="",limit=2,offset=5)
        self.assertEqual([x["library_item_id"] for x in paged["items"]],
                         [x["library_item_id"] for x in actual])

    def test_09_empty_query_is_not_a_license_to_export_or_train(self):
        result=self.query(query="")
        self.assertEqual(result["approved_or_exportable_items"],0)
        self.assertFalse(result["model_weights_changed"])
        self.assertFalse(result["source_allowlist_changed"])
        self.assertFalse(result["customer_release_authorized"])
        self.assertFalse(result["positive_classification_performed_on_real_network"])
        self.assertEqual(result["network_requests"],0)

    @unittest.skipUnless(os.name=="nt","real UCIE Windows only")
    def test_10_live_owner_legacy_ledger_read_only_observation(self):
        if ROOT.resolve()!=Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("exact local UCIE root not available")
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("W04 must not call GitHub")):
            result=search_federated_library(
                ROOT,query="python",limit=6,include_legacy=True)
        self.assertEqual(result["schema"],SCHEMA)
        self.assertEqual(result["network_requests"],0)
        self.assertEqual(result["operating_database_writes"],0)
        self.assertEqual(result["approved_or_exportable_items"],0)
        self.assertFalse(result["v1_library_accepted"])
        print("UCIE_W03W04W05_OWNER_LIBRARY_READONLY="+json.dumps({
            "schema":SCHEMA,
            "status":result["status"],
            "w04_status":result["legacy_w04_status"],
            "known_shelf_matches":result["known_shelf_matches"],
            "legacy_w04_matches":result["legacy_w04_matches"],
            "returned_count":result["returned_count"],
            "total_matches_known":result["total_matches_known"],
            "network_requests":0,
            "db_writes":0,
            "auto_promoted":False,
        },sort_keys=True,ensure_ascii=True))


if __name__=="__main__":
    unittest.main()
