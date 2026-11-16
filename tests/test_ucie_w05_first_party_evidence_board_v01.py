"""UCIE W05 title cue vs P8 first-party exact-key benchmark boundary QA.

Synthetic Stage10/12 review ledgers in TEMP/UCIE only; actual D:/UCIE
is observed read-only. No external GET, source execution or model train.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner.capability_evidence_trial_board_v01 import (
    SCHEMA, CapabilityTrialBoardError, evaluation_board, REQUIREMENTS,
)
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)
from ucie_miner.public_candidate_staging import stage_public_candidates
from test_ucie_stage11_hourly_stage import fixture_batch
from test_ucie_positive_capability_discovery import public_pr, NOW

ROOT=Path(__file__).resolve().parents[1]


class UCIEW05FirstPartyTrialBoardTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix="UCIE_W05_TRIAL_BOARD_SYNTH_")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"UCIE"
        (self.root/"runtime").mkdir(parents=True)

    def _data(self):
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

    def _board(self,**kwargs):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("W05 board never contacts GitHub")):
            return evaluation_board(self.root,**kwargs)

    def test_01_missing_real_catalog_reports_no_go_not_a_measured_gain(self):
        r=self._board(queries=8,repeats=1)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["status"],"P8_SOURCE_LINKAGE_INCOMPLETE_NO_GO")
        self.assertEqual(r["first_party_catalog_benchmark"]["operation_reduction"],None)
        self.assertEqual(r["w05_hypothesis_count"],0)
        self.assertEqual(r["w05_candidates_loaded_from"],
                         "NONE_NOT_A_ZERO_CAPABILITY_CLAIM")
        self.assertFalse(r["w05_candidate_benefit_measured"])
        self.assertFalse(r["customer_release_authorized"])

    def test_02_real_existing_metadata_equivalence_benchmarks_ucie_only(self):
        self._data()
        r=self._board(queries=8,repeats=2)
        self.assertEqual(r["status"],
                         "FIRST_PARTY_EXACT_KEY_BENCHMARK_REVIEW_ONLY")
        b=r["first_party_catalog_benchmark"]
        self.assertEqual(b["scope"],
                         "UCIE_OWNED_EXACT_KEY_INDEX_VS_LINEAR_ON_LINKED_METADATA")
        self.assertEqual(b["mismatched_query_results"],0)
        self.assertEqual(b["real_public_metadata_rows"],2)
        self.assertEqual(b["baseline_scan_operations"],16)
        self.assertEqual(b["candidate_index_build_and_lookup_operations"],10)
        self.assertEqual(b["operation_reduction"],6)
        self.assertFalse(b["time_guaranteed_faster"])
        self.assertFalse(b["external_upstream_candidate_tested"])
        self.assertFalse(b["production_index_applied"])
        self.assertEqual(r["network_requests"],0)
        self.assertEqual(r["operating_database_writes"],0)
        self.assertFalse(r["auto_promoted"])
        self.assertFalse(r["w05_candidate_benefit_measured"])

    def test_03_offline_positive_title_cues_not_candidate_performance(self):
        self._data()
        sample={"source_id":"repo:python/cpython","rows":[
            public_pr(100,"Add incremental build cache for compilation"),
            public_pr(101,"Introduce test automation workflow"),
            public_pr(102,"Implement adaptive learning feedback loop"),
            public_pr(103,"Fix a resource leak in build cache"),
        ]}
        r=self._board(positive_snapshot=sample,now=NOW,queries=8,repeats=1)
        self.assertEqual(r["w05_hypothesis_count"],3)
        self.assertEqual({x["kind"] for x in r["w05_unverified_hypotheses"]},
                         {"DEVELOPMENT_ENGINE","REUSABLE_SKILL","LEARNING_LOGIC"})
        self.assertEqual(r["w05_candidates_loaded_from"],
                         "IN_MEMORY_OFFLINE_UNVERIFIED")
        self.assertFalse(r["w05_candidate_benefit_measured"])
        self.assertEqual(len(r["w05_required_real_candidate_gates"]),6)
        self.assertEqual(r["first_party_catalog_benchmark"]["mismatched_query_results"],0)
        self.assertFalse(r["v1_accepted"])
        self.assertFalse(r["model_weights_changed"])
        self.assertNotIn(sample["rows"][0]["title"],json.dumps(r))

    def test_04_unapproved_public_repo_or_untrusted_url_does_not_get(self):
        for candidate in (
            {"source_id":"research:GH Archive","rows":[]},
            {"source_id":"doc:python/cpython","rows":[]},
            {"source_id":"repo:unknown/other","rows":[]},
            {"source_id":"repo:python/cpython","rows":[
                {**public_pr(120,"Introduce test automation"),
                 "html_url":"https://unauthorized.example/private"}]},
            {"source_id":"repo:python/cpython","rows":[
                public_pr(100,"Introduce test automation")]*2},
        ):
            with self.subTest(source=candidate["source_id"]):
                with self.assertRaises(ValueError):
                    self._board(positive_snapshot=candidate,
                                now=NOW,queries=8,repeats=1)

    def test_05_limits_and_ucie_root_hardened(self):
        with self.assertRaises(CapabilityTrialBoardError):
            self._board(queries=True)
        with self.assertRaises(CapabilityTrialBoardError):
            self._board(queries=7)
        with self.assertRaises(CapabilityTrialBoardError):
            self._board(repeats=6)
        with self.assertRaises(CapabilityTrialBoardError):
            evaluation_board(Path("/tmp/OTHER"),queries=8)
        self.assertEqual(len(REQUIREMENTS),6)

    def test_06_untrusted_positive_cue_cannot_forge_benefit_through_p8(self):
        self._data()
        forged={
            "schema":"UCIE_P8_EXPERIENCE_TO_REAL_CATALOG_BRIDGE_V1",
            "status":"REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED",
            "network_requests":0,"operating_database_writes":0,
            "production_index_applied":False,"v1_accepted":False,
            "real_public_catalog_items":2,
            "mismatched_query_results":0,
            "full_w04_substring_search_benchmarked":True,
            "upstream_code_executed":False,
            "automatic_learning_or_promotion":False,
            "approved_or_exportable_items":0,
        }
        with patch(
            "ucie_miner.capability_evidence_trial_board_v01."
            "benchmark_existing_ucie_public_catalog",return_value=forged
        ):
            with self.assertRaises(CapabilityTrialBoardError):
                self._board(queries=8,repeats=1)

    @unittest.skipUnless(os.name=="nt","exact UCIE owner Windows only")
    def test_07_real_owner_catalog_benchmark_stays_readonly(self):
        if ROOT.resolve()!=Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("exact D:/UCIE checkout unavailable")
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no network from owner benchmark")):
            r=evaluation_board(ROOT,queries=32,repeats=3)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["network_requests"],0)
        self.assertEqual(r["operating_database_writes"],0)
        self.assertFalse(r["w05_candidate_benefit_measured"])
        self.assertFalse(r["auto_promoted"])
        b=r["first_party_catalog_benchmark"]
        print("UCIE_W05_P8_OWNER_READONLY="+json.dumps({
            "schema":SCHEMA,
            "status":r["status"],
            "first_party_benchmark_scope":b["scope"],
            "real_public_metadata_rows":b["real_public_metadata_rows"],
            "mismatched_query_results":b.get("mismatched_query_results"),
            "baseline_scan_operations":b.get("baseline_scan_operations"),
            "index_build_and_lookup_operations":
                b.get("candidate_index_build_and_lookup_operations"),
            "operation_reduction":b.get("operation_reduction"),
            "upstream_candidate_benefit_measured":False,
            "operating_database_writes":0,"network_requests":0,
            "auto_promoted":False,
        },sort_keys=True,ensure_ascii=True))


if __name__=="__main__":
    unittest.main()
