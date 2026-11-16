"""W07 signed manual reference x W08 first-party QA: no release claims.

Uses only UCIE TEST-owned temporary signing keys/Serial4, synthetic
Stage10/12 source-linked ledgers and exact owner D:/UCIE read-only data.
No live API, production signing, imported third-party code, user files,
P11 queue rearm, task modification, rule promotion or distribution.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import w07_w08_independent_readiness_v01 as qa
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME,OPT_IN_TOKEN,optional_hourly_review_learning
)
from ucie_miner.public_candidate_staging import stage_public_candidates
from test_ucie_stage11_hourly_stage import fixture_batch
from ucie_public.mixed_release import RULE_ORDER

ROOT=Path(__file__).resolve().parents[1]
REPOS=("python/cpython","PowerShell/PowerShell","git/git",
       "modelcontextprotocol/python-sdk","actions/runner-images")


class W07W08IndependentReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix="UCIE_W07_W08_QA_SYNTH_")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"UCIE"
        (self.root/"runtime").mkdir(parents=True)

    def _linked(self):
        batch=fixture_batch(
            root=self.root,sources=REPOS,max_enrich=1,
            include_git_commits=True,include_docs=False,
            include_advisories=False,backfill_pages=1)
        stage_public_candidates(batch,root=self.root,allow_disk_write=True)
        (self.root/"runtime"/OPT_IN_FILENAME).write_text(
            OPT_IN_TOKEN,encoding="ascii")
        out=optional_hourly_review_learning(self.root)
        self.assertEqual(out["new_review_proposals"],2)

    @staticmethod
    def _synthetic_verifier_output():
        # A contract fake, NOT a real crypto verification; existing
        # first-party W07 CI independently tests genuine signatures.
        return {
            "schema":qa.SIGNED_SCHEMA,
            "status":"EXISTING_OWNER_SIGNED_RULEPACKS_VERIFIED_READ_ONLY",
            "network_requests":0,"database_writes":0,
            "new_release_approved":False,"v1_library_accepted":False,
            "private_signing_key_accessed":False,
            "new_signatures_created":0,
            "unsigned_candidate_records_imported":0,
            "source_pack_sha256s":{"serial4":"a"*64},
            "signed_rule_count":len(RULE_ORDER),
            "items":[{
                "rule_id":code,
                "pack_serial":4,
                "source_package_sha256":"a"*64,
                "item_id":sha256((code+":"+"a"*64).encode("ascii")).hexdigest(),
                "verification":"OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME",
                "approval_basis":"OWNER_RISK_ACCEPTED_CI_ONLY",
                "independent_qa_approved":False,
                "license_signoff":False,
                "new_package_export_allowed":False,
                "unattended_execution_allowed":False,
            } for code in RULE_ORDER],
        }

    def _review(self,**kw):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("W07/W08 QA may not GET")):
            return qa.independent_review_board(self.root,**kw)

    def test_01_heldout_oracle_checks_positive_negative_and_duplicate_keys(self):
        result=qa._heldout_exact_key_oracle()
        self.assertEqual(result["synthetic_record_count"],8)
        self.assertEqual(result["heldout_query_count"],9)
        self.assertEqual(result["negative_query_count"],3)
        self.assertTrue(result["duplicate_exact_key_cases_included"])
        self.assertEqual(result["mismatched_expected_results"],0)
        self.assertEqual(len(result["casebook_sha256"]),64)
        self.assertFalse(result["independent_human_qa_approved"])

    def test_02_missing_stage12_is_partial_not_verified(self):
        out=self._review(queries=8,repeats=1)
        self.assertEqual(out["schema"],qa.SCHEMA)
        self.assertEqual(out["status"],qa.PARTIAL)
        self.assertFalse(out["real_metadata_benchmark"]["source_linkage_present"])
        self.assertIsNone(out["real_metadata_benchmark"]["metadata_rows"])
        self.assertEqual(
            out["existing_w07_signed_manual_rule_references"]["status"],
            "EXACT_SIGNED_PACKS_NOT_SUPPLIED_NO_GO")
        self.assertFalse(out["customer_release_authorized"])
        self.assertFalse(out["qa_handoff_digest_is_authorization"])

    def test_03_real_source_linked_first_party_benchmark_still_no_release(self):
        self._linked()
        out=self._review(queries=8,repeats=2)
        self.assertEqual(out["status"],qa.PARTIAL)
        r=out["real_metadata_benchmark"]
        self.assertTrue(r["source_linkage_present"])
        self.assertEqual(r["metadata_rows"],2)
        self.assertEqual(r["reference_operations"],16)
        self.assertEqual(r["index_build_and_lookup_operations"],10)
        self.assertEqual(r["reduction_in_operation_count"],6)
        self.assertEqual(r["exact_result_mismatches"],0)
        self.assertFalse(r["upstream_candidate_benefit_measured"])
        self.assertFalse(out["independent_human_qa_approved"])
        self.assertFalse(out["license_and_rights_signoff"])
        self.assertEqual(out["unverified_rule_candidates_approved"],0)
        self.assertEqual(out["network_requests"],0)
        self.assertEqual(out["operating_database_writes"],0)

    def test_04_pinned_signed_verifier_contract_is_still_not_qa_signoff(self):
        self._linked()
        # Fake is only a strict verifier-contract negative authority test.
        with patch.object(qa,"inspect_signed_library",
                          return_value=self._synthetic_verifier_output()):
            out=self._review(
                queries=8,repeats=2,
                serial4_pack=self.root/"synthetic-only.zip",
                owner_public_trust=self.root/"synthetic-only.pem")
        self.assertEqual(out["status"],qa.CLOSED)
        signed=out["existing_w07_signed_manual_rule_references"]
        self.assertTrue(signed["original_crypto_reverified"])
        self.assertEqual(signed["verified_manual_rule_references"],4)
        self.assertEqual(len(set(signed["rule_ids"])),4)
        self.assertTrue(all(len(x)==64
                            for x in signed["source_pack_sha256s"].values()))
        self.assertFalse(out["independent_human_qa_approved"])
        self.assertFalse(out["license_and_rights_signoff"])
        self.assertFalse(out["explicit_owner_new_release_approval"])
        self.assertFalse(out["new_production_rulepack_signed"])
        self.assertFalse(out["new_generic_package_export_allowed"])
        self.assertFalse(out["automatic_rule_application_allowed"])
        self.assertFalse(out["customer_release_authorized"])
        self.assertEqual(len(out["remaining_release_gates"]),5)

    def test_05_tampered_existing_signed_package_is_rejected_by_real_verifier(self):
        self._linked()
        build=self.root/"build"
        build.mkdir(exist_ok=True)
        pack=build/"untrusted-serial4.zip"
        trust=build/"untrusted-owner-public.pem"
        pack.write_bytes(b"UNTRUSTED_NOT_A_RULEPACK")
        trust.write_bytes(b"UNTRUSTED_NOT_A_PUBLIC_KEY")
        with self.assertRaises((qa.SignedLibraryError,qa.ReadinessError)):
            self._review(queries=8,repeats=1,
                         serial4_pack=pack,
                         owner_public_trust=trust)
        with self.assertRaises(qa.ReadinessError):
            self._review(queries=8,repeats=1,
                         serial4_pack=pack)
        forged=self._synthetic_verifier_output()
        forged["items"][0]["independent_qa_approved"]=True
        with patch.object(qa,"inspect_signed_library",return_value=forged):
            with self.assertRaises(qa.ReadinessError):
                self._review(queries=8,repeats=1,
                             serial4_pack=pack,owner_public_trust=trust)
        other=self._synthetic_verifier_output()
        other["items"][0]["source_package_sha256"]="b"*64
        with patch.object(qa,"inspect_signed_library",return_value=other):
            with self.assertRaises(qa.ReadinessError):
                self._review(queries=8,repeats=1,
                             serial4_pack=pack,owner_public_trust=trust)

    def test_06_wrong_result_reference_is_not_passed_by_heldout_oracle(self):
        # A candidate index that silently drops duplicate keys must fail
        # independently of any self-reported production benchmark receipt.
        original=qa.indexed_search
        def corrupt(index,query):
            ids, steps=original(index,query)
            if len(ids)>1:
                ids=ids[:1]
            return ids,steps
        with patch.object(qa,"indexed_search",corrupt):
            with self.assertRaisesRegex(
                    qa.ReadinessError,"held-out exact-key index regression"):
                self._review(queries=8,repeats=1)

    def test_07_forged_benchmark_metrics_auto_approval_and_scope_rejected(self):
        self._linked()
        honest=qa.evaluation_board(self.root,queries=8,repeats=1)
        for forged in (
            {**honest,"auto_promoted":True},
            {**honest,"w05_candidate_benefit_measured":True},
            {**honest,"w05_hypothesis_count":1},
            {**honest,"first_party_catalog_benchmark":{
                **honest["first_party_catalog_benchmark"],
                "operation_reduction":999999}},
            {**honest,"first_party_catalog_benchmark":{
                **honest["first_party_catalog_benchmark"],
                "time_guaranteed_faster":True}},
        ):
            with self.subTest(fields=tuple(forged)):
                with patch.object(qa,"evaluation_board",return_value=forged):
                    with self.assertRaises(qa.ReadinessError):
                        self._review(queries=8,repeats=1)

    def test_08_bad_root_booleans_missing_paths_and_out_of_bounds_denied(self):
        for kw in (
            {"queries":True},
            {"repeats":True},
            {"queries":7},
            {"queries":97},
            {"repeats":6},
            {"serial5_pack":self.root/"nonexistent.zip"},
            {"owner_public_trust":self.root/"nonexistent-trust.pem"},
        ):
            with self.subTest(kw=kw):
                with self.assertRaises(qa.ReadinessError):
                    self._review(**kw)
        with self.assertRaises(qa.ReadinessError):
            qa.independent_review_board(Path(self.tmp.name))

    @unittest.skipUnless(os.name=="nt","exact owner Windows only")
    def test_09_real_UCIE_owner_readonly_no_signing_or_network(self):
        if ROOT.resolve()!=Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("exact owner checkout unavailable")
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("no public GET")):
            out=qa.independent_review_board(
                ROOT,queries=32,repeats=3)
        r=out["real_metadata_benchmark"]
        self.assertTrue(r["source_linkage_present"])
        self.assertEqual(r["exact_result_mismatches"],0)
        self.assertFalse(out["customer_release_authorized"])
        self.assertFalse(out["auto_promoted"])
        self.assertFalse(out["new_production_rulepack_signed"])
        self.assertEqual(out["network_requests"],0)
        self.assertEqual(out["operating_database_writes"],0)
        print("UCIE_W07_W08_OWNER_READONLY="+json.dumps({
            "schema":qa.SCHEMA,"status":out["status"],
            "heldout_queries":out["first_party_independent_oracle"]["heldout_query_count"],
            "heldout_mismatches":
                out["first_party_independent_oracle"]["mismatched_expected_results"],
            "metadata_rows":r["metadata_rows"],
            "reference_operations":r["reference_operations"],
            "indexed_operations":r["index_build_and_lookup_operations"],
            "exact_result_mismatches":r["exact_result_mismatches"],
            "W07_signed_pack_supplied":False,
            "independent_human_qa_approved":False,
            "license_signoff":False,"customer_release_authorized":False,
            "network_requests":0,"db_writes":0,
        },sort_keys=True))


if __name__=="__main__":
    unittest.main()
