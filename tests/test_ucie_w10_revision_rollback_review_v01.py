"""UCIE W10 source-pinned, rollback-NO-GO quality review acceptance.

Temporary UCIE test roots and independent read-only actual D:/UCIE.
No modified operating source, no Git checkout, no branch/deploy,
no model training, external code execution, P11 rearm or network GET.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import w10_revision_rollback_review_v01 as w10
from ucie_miner import experience_evolution as evo
from ucie_miner.capability_experience import run_capability_cycle
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning)
from test_ucie_stage11_hourly_stage import fixture_batch

ROOT=Path(__file__).resolve().parents[1]
REPOS=("python/cpython","PowerShell/PowerShell","git/git",
       "modelcontextprotocol/python-sdk","actions/runner-images")


class UCIEW10RevisionRollbackReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix="UCIE_W10_READONLY_SYNTH_")
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
        result=optional_hourly_review_learning(self.root)
        self.assertEqual(result["new_review_proposals"],2)

    def _first_party_p8(self):
        self._linked()
        result=evo.run_evolution_cycle(self.root,record=True)
        self.assertTrue(result["new_event_written"])

    def _first_party_w05(self):
        pr={
            "number":123456,
            "title":"Add test automation helpers",
            "merged_at":"2026-10-10T12:00:00Z",
            "merge_commit_sha":"a"*40,
            "html_url":"https://github.com/python/cpython/pull/123456",
            "base":{"repo":{"full_name":"python/cpython"}},
        }
        out=run_capability_cycle(
            self.root,source_rows=[pr],source_id="repo:python/cpython",
            record=True,now=datetime(2026,10,29,tzinfo=timezone.utc))
        self.assertTrue(out["new_event_written"])

    def _review(self,**kw):
        settings={"queries":8,"repeats":1}
        settings.update(kw)
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("W10 read-only must never GET")):
            return w10.review_w10_revision_and_rollback(self.root,**settings)

    def test_01_no_existing_revision_proposals_no_go_no_rollback(self):
        out=self._review()
        self.assertEqual(out["schema"],w10.SCHEMA)
        self.assertEqual(out["status"],w10.STATUS_EMPTY)
        self.assertEqual(out["proposal_window_total"],0)
        self.assertEqual(out["proposals"],[])
        self.assertIsNone(out["selected_proposal"])
        self.assertIsNone(out["rollback_readiness"][
            "protected_current_baseline_source_sha256"])
        self.assertFalse(out["runtime_rollback_executed"])
        self.assertFalse(out["customer_release_authorized"])
        self.assertFalse(out["review_sha256_is_owner_approval"])
        self.assertEqual(out["network_requests"],0)
        self.assertEqual(out["operating_database_writes"],0)

    def test_02_real_P8_review_queue_source_pin_but_no_replacement(self):
        self._first_party_p8()
        out=self._review()
        self.assertEqual(out["status"],w10.STATUS_PENDING)
        self.assertEqual(out["proposal_window_total"],1)
        self.assertEqual(len(out["proposals"]),1)
        row=out["proposals"][0]
        self.assertEqual(row["target_ucie_component"],w10.TARGET_INDEX)
        self.assertEqual(row["source_shelf"],"UCIE_SYNTHETIC_EXPERIENCE")
        self.assertEqual(row["old_code_source_pin"]["source_file"],
                         "library_exact_index.py")
        self.assertEqual(len(row["old_code_source_pin"][
            "current_checked_out_source_sha256"]),64)
        self.assertFalse(row["candidate_code_and_sha_pinned"])
        self.assertFalse(row["reversible_bytes_or_snapshot_attested"])
        self.assertFalse(out["rollback_readiness"]["rollback_restore_exercised"])
        self.assertFalse(out["actual_revision_applied"])
        self.assertEqual(out["w08_reference_heldout_mismatches"],0)

    def test_03_select_exact_P8_proposal_pinned_to_owner_W09_digest(self):
        self._first_party_p8()
        first=self._review()
        selected=first["proposals"][0]["proposal_id"]
        pinned=self._review(
            select_proposal_id=selected,
            expected_w09_review_digest=first["w09_owner_review_digest_sha256"])
        self.assertEqual(pinned["status"],w10.STATUS_SELECTED)
        self.assertEqual(pinned["selected_proposal"]["proposal_id"],selected)
        self.assertEqual(pinned["rollback_readiness"][
            "protected_current_baseline_source_sha256"],
            pinned["selected_proposal"]["old_code_source_pin"][
                "current_checked_out_source_sha256"])
        self.assertFalse(pinned["rollback_readiness"][
            "actual_prechange_recoverable_bytes_attested"])
        self.assertFalse(pinned["rollback_readiness"][
            "candidate_behavior_equivalence_tested"])
        self.assertFalse(pinned["rollback_readiness"][
            "post_rollback_W09_consumer_reverified"])
        self.assertFalse(pinned["new_source_or_owner_signing_key_accessed"])
        self.assertFalse(pinned["customer_release_authorized"])

    def test_04_current_W09_digest_change_and_unknown_proposal_fail_closed(self):
        self._first_party_p8()
        with self.assertRaises(w10.W10ReviewError):
            self._review(expected_w09_review_digest="f"*64)
        with self.assertRaises(w10.W10ReviewError):
            self._review(select_proposal_id="f"*64)
        with self.assertRaises(w10.W10ReviewError):
            self._review(select_proposal_id="../other")

    def test_05_source_target_spoof_and_false_approval_in_P9_blocked(self):
        self._first_party_p8()
        genuine=w10.integrated_product_preview(self.root,limit=10)
        for altered in (
            lambda p:p["library_revision_review_queue"].update({"auto_promoted":True}),
            lambda p:p["library_revision_review_queue"]["items"][0].update(
                {"production_improvement_verified":True}),
            lambda p:p["library_revision_review_queue"]["items"][0].update(
                {"proposal_id":"0"*64}),
            lambda p:p["library_revision_review_queue"]["items"][0].update(
                {"target_ucie_component":"other_project:injected"}),
            lambda p:p.update({"package_released":True}),
        ):
            # Snapshot clone prevents any fake flag from leaking to subsequent tests.
            from copy import deepcopy
            fake=deepcopy(genuine)
            altered(fake)
            with patch.object(w10,"integrated_product_preview",return_value=fake):
                with self.assertRaises(w10.W10ReviewError):
                    self._review()

    def test_06_W09_false_approval_or_changed_digest_denied(self):
        honest=w10.inspect_w09_consumer_acceptance(
            self.root,queries=8,repeats=1)
        for change in (
            {"customer_release_authorized":True},
            {"auto_promoted":True},
            {"network_requests":1},
            {"w08_heldout_mismatched_results":1},
            {"owner_signed_original_supplied":True},
            {"new_package_created_or_exported":True},
            {"review_digest_sha256":"corrupt"},
        ):
            with self.subTest(change=change):
                with patch.object(w10,"inspect_w09_consumer_acceptance",
                                  return_value={**honest,**change}):
                    with self.assertRaises(w10.W10ReviewError):
                        self._review()

    def test_07_W05_existing_synthetic_recipe_review_never_upstream_adoption(self):
        self._first_party_w05()
        out=self._review()
        self.assertEqual(out["proposal_window_total"],1)
        row=out["proposals"][0]
        self.assertEqual(row["source_shelf"],
                         "UCIE_CANDIDATE_TRIAL_EXPERIENCE")
        self.assertTrue(row["target_ucie_component"].startswith(
            w10.TARGET_RECIPE))
        self.assertEqual(row["old_code_source_pin"]["source_file"],
                         "capability_trials.py")
        self.assertFalse(row["candidate_regression_evaluated"])
        self.assertFalse(row["owner_deploy_approved"])
        self.assertFalse(out["runtime_rollback_executed"])
        self.assertFalse(out["auto_promoted"])

    def test_08_invalid_input_and_boundary_rejection(self):
        for kw in (
            {"limit":True}, {"limit":0}, {"limit":21},
            {"queries":True}, {"queries":7},
            {"repeats":True}, {"repeats":0},
            {"expected_w09_review_digest":"invalid"},
        ):
            with self.subTest(kw=kw):
                with self.assertRaises(w10.W10ReviewError):
                    self._review(**kw)
        for target in (
            "other_project/repo.py",
            "ucie_miner.capability_trials:../../private",
            "ucie_miner.library_exact_index:EDIT_OTHER",
        ):
            with self.subTest(target=target):
                with self.assertRaises(w10.W10ReviewError):
                    w10._target_source(target)

    def test_09_source_and_rollback_digest_stable_without_side_effects(self):
        self._first_party_p8()
        before={}
        for path in (self.root/"runtime").iterdir():
            if path.is_file():
                before[path.name]=path.read_bytes()
        a=self._review()
        b=self._review()
        self.assertEqual(a["review_sha256"],b["review_sha256"])
        self.assertEqual(
            {name:(self.root/"runtime"/name).read_bytes() for name in before},
            before)
        self.assertFalse(a["review_sha256_is_owner_approval"])
        self.assertFalse(a["git_branch_or_commit_modified"])
        self.assertFalse(a["operating_code_modified"])
        self.assertFalse(a["runtime_rollback_executed"])
        self.assertEqual(a["network_requests"],0)
        self.assertEqual(a["operating_database_writes"],0)

    @unittest.skipUnless(os.name=="nt","actual UCIE owner Windows only")
    def test_10_real_owner_readonly_W10_and_nonimpact_P11(self):
        if ROOT.resolve()!=Path("D:/UCIE").resolve() or ROOT.is_symlink():
            self.skipTest("exact D:/UCIE owner checkout unavailable")
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("real W10 must not GET")):
            out=w10.review_w10_revision_and_rollback(
                ROOT,queries=32,repeats=3,limit=10)
        self.assertEqual(out["schema"],w10.SCHEMA)
        self.assertEqual(out["w08_reference_heldout_query_cases"],9)
        self.assertEqual(out["w08_reference_heldout_mismatches"],0)
        self.assertEqual(out["w08_first_party_real_metadata_rows"],1335)
        self.assertFalse(out["runtime_rollback_executed"])
        self.assertFalse(out["customer_release_authorized"])
        self.assertFalse(out["auto_promoted"])
        self.assertEqual(out["network_requests"],0)
        self.assertEqual(out["operating_database_writes"],0)
        print("UCIE_W10_OWNER_READONLY="+json.dumps({
            "schema":w10.SCHEMA,
            "status":out["status"],
            "w09_review_digest":out["w09_owner_review_digest_sha256"][:12],
            "revision_queue_items":out["proposal_window_total"],
            "returned":out["proposal_window_returned"],
            "targets":[{"component":row["target_ucie_component"],
                        "state":row["status"],
                        "proposal_id_prefix":row["proposal_id"][:12],
                        "baseline_source_sha_prefix":
                            row["old_code_source_pin"][
                                "current_checked_out_source_sha256"][:12]}
                       for row in out["proposals"]],
            "truncated":out["proposal_window_truncated"],
            "heldout_reference_mismatches":out["w08_reference_heldout_mismatches"],
            "rollback_restore_exercised":False,
            "owner_release":False,
            "network_requests":0,
            "db_writes":0,
        },sort_keys=True))


if __name__=="__main__":
    unittest.main()
