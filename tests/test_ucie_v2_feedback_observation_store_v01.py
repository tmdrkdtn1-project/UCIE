"""UCIE-only detached review persistence and evidence-delta contracts."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest import TestCase

from ucie_miner import ucie_v2_feedback_observation_store_v01 as target
from ucie_miner import ucie_v2_feedback_registry_v01 as registry
from ucie_miner import ucie_v2_library_revision_ledger_v01 as history
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5


def record(method):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 900,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


class FeedbackObservationStoreTests(TestCase):
    @classmethod
    def setUpClass(cls):
        bundle=original.assemble_original_library_assets(
            tuple(record(m) for m in b5.METHODS), ())
        cls.h=history.append_review_bundle(history.new_review_history(), bundle)
        cls.empty=registry.empty_feedback_registry(cls.h)
        cls.preview=registry.append_feedback_evidence(cls.h, cls.empty)
        cls.executed=registry.append_feedback_evidence(
            cls.h, cls.empty, execute_synthetic=True)

    def make_root(self, temporary):
        root=Path(temporary)/target.FOLDER
        root.mkdir()
        (root/target.MARKER).write_text(target.MARKER_VALUE,encoding="utf-8")
        return root

    def test_empty_to_preview_counts_receipt_not_customer_gain(self):
        x=target.compare_review_observations(self.h,self.empty,self.preview)
        self.assertEqual(x["new_distinct_review_receipts"],1)
        self.assertFalse(x["real_user_improvement_measured"])

    def test_equal_receipts_no_learning_increment(self):
        x=target.compare_review_observations(self.h,self.executed,self.executed)
        self.assertEqual(x["new_distinct_review_receipts"],0)
        self.assertTrue(x["unchanged"])

    def test_nonappend_history_denied(self):
        with self.assertRaises(target.FeedbackStoreError):
            target.compare_review_observations(self.h,self.executed,self.preview)

    def test_hash_is_deterministic(self):
        x=target.compare_review_observations(self.h,self.empty,self.executed)
        self.assertEqual(x,target.compare_review_observations(
            self.h,self.empty,self.executed))
        self.assertEqual(x["content_sha256"],target._digest({
            k:v for k,v in x.items() if k!="content_sha256"}))

    def test_absent_marker_denies_write(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/target.FOLDER
            root.mkdir()
            with self.assertRaises(target.FeedbackStoreError):
                target.save_feedback_receipt(self.h,self.preview,root,
                                             approve_write=True)

    def test_preview_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.make_root(t)
            result=target.save_feedback_receipt(self.h,self.preview,root)
            self.assertEqual(result["status"],"PREVIEW_ONLY_NO_WRITE")
            self.assertEqual(list(root.glob("feedback_*.json")),[])

    def test_create_and_verified_load_and_idempotent(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.make_root(t)
            one=target.save_feedback_receipt(self.h,self.executed,root,
                                             approve_write=True)
            self.assertTrue(one["wrote"])
            found=target.read_feedback_receipt(self.h,root,one["receipt_sha256"])
            self.assertEqual(found["registry"],self.executed)
            two=target.save_feedback_receipt(self.h,self.executed,root,
                                             approve_write=True)
            self.assertEqual(two["status"],"ALREADY_STORED_IMMUTABLE")
            self.assertFalse(two["wrote"])

    def test_wrong_history_denied_for_load(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.make_root(t)
            result=target.save_feedback_receipt(self.h,self.preview,root,
                                                approve_write=True)
            with self.assertRaises((history.ReviewHistoryError,
                                    registry.FeedbackRegistryError,
                                    target.FeedbackStoreError)):
                target.read_feedback_receipt(history.new_review_history(),
                                             root,result["receipt_sha256"])

    def test_existing_file_tamper_denied(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.make_root(t)
            result=target.save_feedback_receipt(self.h,self.preview,root,
                                                approve_write=True)
            path=root/("feedback_"+result["receipt_sha256"]+".json")
            path.write_text("{}",encoding="utf-8")
            with self.assertRaises(target.FeedbackStoreError):
                target.read_feedback_receipt(self.h,root,result["receipt_sha256"])

    def test_symlinked_root_denied(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.make_root(t)
            alias=Path(t)/"alias"
            try:
                alias.symlink_to(root,target_is_directory=True)
            except (OSError,NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaises(target.FeedbackStoreError):
                target.save_feedback_receipt(self.h,self.preview,alias,
                                             approve_write=True)

    def test_oversized_or_injected_registry_denied(self):
        bad=deepcopy(self.preview)
        bad["user_notes"]="private"
        with tempfile.TemporaryDirectory() as t:
            root=self.make_root(t)
            with self.assertRaises(registry.FeedbackRegistryError):
                target.save_feedback_receipt(self.h,bad,root,approve_write=True)

    def test_invalid_write_flag_denied(self):
        with tempfile.TemporaryDirectory() as t:
            root=self.make_root(t)
            with self.assertRaises(target.FeedbackStoreError):
                target.save_feedback_receipt(self.h,self.preview,root,
                                             approve_write="true")

    def test_no_operating_db_or_auto_acceptance(self):
        x=target.compare_review_observations(self.h,self.empty,self.executed)
        for name in ("new_external_evidence_observed",
                     "real_user_improvement_measured",
                     "reproducible_customer_benefit_verified",
                     "technical_adoption_authorized",
                     "automatic_learning_or_training",
                     "automatic_job_dispatch"):
            self.assertFalse(x[name])
        self.assertEqual(x["operating_database_writes"],0)
