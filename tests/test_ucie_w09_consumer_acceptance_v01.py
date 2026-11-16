"""UCIE W09 original signed manual handoff and standalone DRAFT consumer QA.

Synthetic TEMP/UCIE source-linked fixtures and isolated Python processes;
owner Windows only READ-ONLY. Never approve, export, sign, apply or collect.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import w09_consumer_acceptance_v01 as w09
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME,OPT_IN_TOKEN,optional_hourly_review_learning,
)
from ucie_miner.public_candidate_staging import stage_public_candidates
from test_ucie_stage11_hourly_stage import fixture_batch

ROOT=Path(__file__).resolve().parents[1]
REPOS=("python/cpython","PowerShell/PowerShell","git/git",
       "modelcontextprotocol/python-sdk","actions/runner-images")


class W09ConsumerAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="UCIE_W09_ACCEPTANCE_SYNTH_")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"UCIE"
        (self.root/"runtime").mkdir(parents=True)
        (self.root/"runtime"/"UCIE_W09_CONSUMER_SYNTH_ONLY.marker").write_text(
            "UCIE_W09_CONSUMER_SYNTHETIC_ONLY_V01",encoding="ascii")

    def _linked(self):
        batch=fixture_batch(
            root=self.root,sources=REPOS,max_enrich=1,
            include_git_commits=True,include_docs=False,
            include_advisories=False,backfill_pages=1)
        stage_public_candidates(batch,root=self.root,allow_disk_write=True)
        (self.root/"runtime"/OPT_IN_FILENAME).write_text(
            OPT_IN_TOKEN,encoding="ascii")
        r=optional_hourly_review_learning(self.root)
        self.assertEqual(r["new_review_proposals"],2)

    def _review(self,**kw):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("W09 must never contact GitHub")):
            return w09.inspect_w09_consumer_acceptance(self.root,**kw)

    def test_01_no_packs_runs_real_independent_draft_and_stays_no_go(self):
        r=self._review(queries=8,repeats=1)
        self.assertEqual(r["schema"],w09.SCHEMA)
        self.assertEqual(r["status"],w09.NO_SIGNED)
        draft=r["portable_first_party_draft_independent_QA"]
        self.assertEqual(draft["status"],
                         "FIRST_PARTY_ISOLATED_CONSUMER_QA_PASS_NOT_RELEASED")
        self.assertTrue(draft["independent_python_process_executed"])
        self.assertTrue(draft["standalone_zip_without_ucie_install_executed"])
        self.assertEqual(draft["standalone_parity_cases"],3)
        self.assertTrue(draft["no_upstream_public_source_executed"])
        self.assertFalse(draft["portable_distribution_rights_approved"])
        self.assertFalse(r["owner_signed_original_supplied"])
        self.assertFalse(r["manual_selection_present"])
        self.assertIsNone(r["signed_rule_manual_consumer"])
        self.assertFalse(r["review_digest_is_release_authorization"])
        self.assertFalse(r["customer_release_authorized"])
        self.assertFalse(r["new_package_created_or_exported"])
        self.assertEqual(r["network_requests"],0)
        self.assertEqual(r["operating_database_writes"],0)

    def test_02_linked_W04_metadata_is_used_only_as_unapproved_trial_input(self):
        self._linked()
        r=self._review(queries=8,repeats=2)
        draft=r["portable_first_party_draft_independent_QA"]
        # Of two W04-linked metadata records only one is a PR URL:
        # git/git commit evidence is intentionally unsupported by the
        # existing PR-only portable consumer.
        self.assertEqual(draft["public_unverified_metadata_records_tested"],1)
        self.assertEqual(r["w08_first_party_real_metadata_rows"],2)
        self.assertEqual(r["w08_heldout_query_count"],9)
        self.assertEqual(r["w08_heldout_mismatched_results"],0)
        self.assertEqual(len(r["remaining_release_gates"]),5)
        self.assertEqual(r["unsigned_candidates_promoted"],0)
        self.assertFalse(r["automatic_rule_execution"])
        self.assertFalse(r["owner_new_release_approved"])
        self.assertFalse(r["customer_release_authorized"])

    def test_03_unknown_root_or_signature_and_selection_drift_denied(self):
        for kw in (
            {"serial4_pack":self.root/"does-not-exist.zip"},
            {"owner_public_trust":self.root/"does-not-exist.pem"},
            {"serial5_pack":self.root/"does-not-exist.zip"},
            {"select_item_id":"a"*64},
            {"select_item_id":"a"*63},
            {"select_item_id":"../../other"},
            {"queries":True},
            {"queries":7},
            {"repeats":0},
            {"repeats":True},
        ):
            with self.subTest(kw=kw):
                with self.assertRaises(w09.W09AcceptanceError):
                    self._review(**kw)
        bad=self.root.parent/"UCIE_UNRELATED"
        bad.mkdir()
        with self.assertRaises(w09.W09AcceptanceError):
            w09.inspect_w09_consumer_acceptance(bad,queries=8,repeats=1)
        marker=self.root/"runtime"/"UCIE_W09_CONSUMER_SYNTH_ONLY.marker"
        marker.write_text("FORGED_MARKER",encoding="ascii")
        with self.assertRaises(w09.W09AcceptanceError):
            self._review(queries=8,repeats=1)

    def test_04_portable_false_release_or_external_code_claim_fails_closed(self):
        actual=w09.check_portable_engine_qa(self.root)
        for name,value in (
            ("package_released",True),
            ("owner_release_approved",True),
            ("independent_external_qa_attested",True),
            ("exact_result_parity_verified",False),
            ("network_requests",1),
            ("upstream_public_code_included_or_executed",True),
            ("standalone_zip_exact_parity_cases",0),
            ("first_party_source_sha256","f"*65),
        ):
            with self.subTest(name=name):
                forged={**actual,name:value}
                with patch.object(w09,"check_portable_engine_qa",return_value=forged):
                    with self.assertRaises(w09.W09AcceptanceError):
                        self._review(queries=8,repeats=1)

    def test_05_old_signed_original_tamper_stops_before_handoff(self):
        pack=self.root/"runtime"/"corrupt-signed.zip"
        trust=self.root/"runtime"/"corrupt-public-trust.pem"
        pack.write_bytes(b"NOT_A_SIGNED_UCIE_PACK")
        trust.write_bytes(b"NOT_A_PUBLIC_KEY")
        with self.assertRaises((w09.ReadinessError,w09.SignedLibraryError)):
            self._review(serial4_pack=pack,owner_public_trust=trust,
                         select_item_id="a"*64,queries=8,repeats=1)

    def test_06_manual_consumer_receipt_requires_pack_and_reference_sha(self):
        digest="a"*64
        rule="PS_RESOLVE_PATH_DOT_PREFIX"
        item=sha256((rule+":"+digest).encode("ascii")).hexdigest()
        ref={
            "selected_library_item_id":item,
            "source_package_sha256":digest,
            "parent_serial4_sha256":digest,
            "existing_w09_descriptor_sha256":"b"*64,
            "rule_id":rule,"pack_serial":4,
        }
        observed={
            "schema":w09.MANUAL_SCHEMA,"status":w09.MANUAL_STATUS,
            "original_signature_trust_and_expiry_reverified_in_consumer":True,
            "selected_library_item_id":item,"source_pack_sha256":digest,
            "parent_serial4_sha256":digest,
            "w09_descriptor_sha256":"b"*64,
            "handoff_reference_sha256":w09._hash(ref),
            "rule_id":rule,"pack_serial":4,"owner_risk_only":True,
            "consumer_action":"INSPECT_EXISTING_SIGNED_RULE_IDENTITY_ONLY",
            "actual_rule_scan_executed":False,
            "runtime_version_applicability_verified":False,
            "independent_qa_approved":False,"legal_license_signoff":False,
            "new_generic_package_export_allowed":False,
            "automatic_rule_application_allowed":False,
            "pack_bytes_copied":False,
            "external_project_files_read":False,
            "network_requests":0,"operating_database_writes":0,
            "new_signature_created":False,"package_released":False,
            "v1_accepted":False,
        }
        signed={"source_pack_sha256s":{"serial4":digest},"rule_ids":[rule]}
        got=w09._consumer_receipt(ref,observed,signed)
        self.assertEqual(got["selected_library_item_id"],item)
        self.assertFalse(got["new_package_export_allowed"])
        self.assertFalse(got["independent_rule_quality_QA_approved"])
        for modified in (
            {"handoff_reference_sha256":"c"*64},
            {"independent_qa_approved":True},
            {"actual_rule_scan_executed":True},
            {"new_generic_package_export_allowed":True},
            {"source_pack_sha256":"d"*64},
        ):
            with self.subTest(modified=modified):
                with self.assertRaises(w09.W09AcceptanceError):
                    w09._consumer_receipt(ref,{**observed,**modified},signed)
        with self.assertRaises(w09.W09AcceptanceError):
            w09._consumer_receipt(
                {**ref,"source_package_sha256":"f"*64},observed,signed)

    def test_07_bogus_w07_approved_claim_is_refused_not_released(self):
        honest=w09.independent_review_board(self.root,queries=8,repeats=1)
        with patch.object(w09,"independent_review_board",
                          return_value={**honest,"independent_human_qa_approved":True}):
            with self.assertRaises(w09.W09AcceptanceError):
                self._review(queries=8,repeats=1)
        with patch.object(w09,"independent_review_board",
                          return_value={**honest,"customer_release_authorized":True}):
            with self.assertRaises(w09.W09AcceptanceError):
                self._review(queries=8,repeats=1)

    def test_08_review_digest_is_stable_and_not_authorization(self):
        first=self._review(queries=8,repeats=1)
        second=self._review(queries=8,repeats=1)
        self.assertEqual(first["review_digest_sha256"],
                         second["review_digest_sha256"])
        self.assertEqual(len(first["review_digest_sha256"]),64)
        self.assertFalse(first["review_digest_is_release_authorization"])
        self.assertEqual(first["status"],w09.NO_SIGNED)

    def test_09_genuine_synthetic_serial4_independent_consumer_if_fixture_available(self):
        # GitHub's complete source checkout includes this pre-existing
        # first-party test fixture; the owner Windows bounded test bridge
        # may intentionally expose a smaller source subset. Never fake a
        # successful crypto-positive test when it is unavailable.
        try:
            from test_ucie_w07_w09_signed_library import W07W09SignedLibraryTests
            from ucie_miner.signed_rule_library import inspect_signed_library
        except ImportError:
            self.skipTest("original first-party cryptographic test fixture unavailable")
        signer=W07W09SignedLibraryTests(
            "test_genuine_cryptographic_serial4_produces_only_signed_rule_shelf")
        signer.setUp()
        self.addCleanup(signer.doCleanups)
        signer._publish_serial4()
        self.root=signer.root
        (self.root/"runtime").mkdir(exist_ok=True)
        (self.root/"runtime"/"UCIE_W09_CONSUMER_SYNTH_ONLY.marker").write_text(
            "UCIE_W09_CONSUMER_SYNTHETIC_ONLY_V01",encoding="ascii")
        self._linked()
        existing=inspect_signed_library(
            self.root,serial4_pack=signer.serial4,
            owner_public_trust=signer.trust)
        self.assertEqual(existing["signed_rule_count"],4)
        chosen=existing["items"][0]["item_id"]
        result=self._review(
            serial4_pack=signer.serial4,
            owner_public_trust=signer.trust,
            select_item_id=chosen,queries=8,repeats=1)
        self.assertEqual(result["status"],w09.REVERIFIED)
        self.assertTrue(result["owner_signed_original_supplied"])
        real=result["signed_rule_manual_consumer"]
        self.assertTrue(real["consumer_subprocess_reverified_signature"])
        self.assertEqual(real["selected_library_item_id"],chosen)
        self.assertFalse(real["new_package_export_allowed"])
        self.assertFalse(result["independent_human_qa_approved"])
        self.assertFalse(result["customer_release_authorized"])
        self.assertEqual(result["network_requests"],0)
        self.assertEqual(result["operating_database_writes"],0)
        # A pack modified after the previous successful consumer check
        # cannot be accepted based on the old handoff receipt.
        signer.serial4.write_bytes(b"TAMPERED_AFTER_W09_CONSUME")
        with self.assertRaises((w09.ReadinessError,w09.SignedLibraryError)):
            self._review(
                serial4_pack=signer.serial4,
                owner_public_trust=signer.trust,
                select_item_id=chosen,queries=8,repeats=1)

    @unittest.skipUnless(os.name=="nt","exact UCIE owner Windows only")
    def test_10_real_owner_independent_portable_qa_and_P11_nonimpact(self):
        if ROOT.resolve()!=Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("exact UCIE owner not available")
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("W09 owner cannot use web")):
            out=w09.inspect_w09_consumer_acceptance(
                ROOT,queries=32,repeats=3)
        self.assertEqual(out["status"],w09.NO_SIGNED)
        self.assertTrue(out["portable_first_party_draft_independent_QA"][
            "independent_python_process_executed"])
        self.assertEqual(out["w08_first_party_real_metadata_rows"],1335)
        self.assertEqual(out["w08_heldout_mismatched_results"],0)
        self.assertEqual(out["network_requests"],0)
        self.assertEqual(out["operating_database_writes"],0)
        self.assertFalse(out["customer_release_authorized"])
        print("UCIE_W09_OWNER_READONLY="+json.dumps({
            "schema":w09.SCHEMA,"status":out["status"],
            "real_public_metadata_rows":out["w08_first_party_real_metadata_rows"],
            "independent_portable_QA":out[
                "portable_first_party_draft_independent_QA"]["status"],
            "standalone_parity_cases":out[
                "portable_first_party_draft_independent_QA"]["standalone_parity_cases"],
            "original_signed_owner_package_provided":out["owner_signed_original_supplied"],
            "original_manual_consumer_run":out["signed_rule_manual_consumer"] is not None,
            "QA_release_approved":out["customer_release_authorized"],
            "network_requests":0,"operating_db_writes":0,
        },sort_keys=True))


if __name__=="__main__":
    unittest.main()
