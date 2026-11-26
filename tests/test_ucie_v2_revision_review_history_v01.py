"""UCIE original revision decisions recorded but never adopted."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_revision_review_history_v01 as audit
from ucie_miner import ucie_v2_hypothesis_revision_retest_v01 as rev
from ucie_miner import ucie_v2_feedback_registry_v01 as feedback
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5

SHA="a"*64

def study(method):
    return {"study_id":b5.STUDY_ID,"case_id":b5.CASE_ID,
            "anonymous_trial_token":"F01","method":method,
            "cohort":"FIRST_TIME_CODER","first_safe_action_time_ms":900,
            "correct_safe_action":True,"false_version_or_rights_claim":False,
            "evidence_detail_found":False,"origin":b5.SYNTHETIC_ORIGIN}

def example(label,n,*,bad=False):
    truth="RISK" if n<4 else "SAFE"
    return {"case_id":f"{label}_{n}","ground_truth":truth,
            "baseline_prediction":truth,
            "challenger_prediction":("SAFE" if bad and n==1 else truth),
            "origin":"UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY",
            "source_sha256":SHA}


class RevisionHistoryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        b=original.assemble_original_library_assets(
            tuple(study(m) for m in b5.METHODS),())
        cls.h=ledger.append_review_bundle(ledger.new_review_history(),b)
        cls.r=feedback.append_feedback_evidence(
            cls.h,feedback.empty_feedback_registry(cls.h),
            execute_synthetic=True)
        cls.ids=[v["candidate_id"] for v in
                 feedback.prioritize_review_experiments(cls.h,cls.r)["priority_queue"]]
        first={cls.ids[0]:[example("a",i,bad=True) for i in range(8)],
               cls.ids[1]:[example("b",i) for i in range(8)]}
        second={cls.ids[0]:[example("a",i) for i in range(8)],
                cls.ids[1]:[example("b",i) for i in range(8)]}
        cls.report=rev.revise_and_retest_hypotheses(
            cls.h,cls.r,first,second,fixture_sha256=SHA)

    def test_append_and_preserve_both_draft_decisions(self):
        state=audit.append_revision_review(
            self.h,audit.new_revision_history(self.h),self.report)
        self.assertEqual(state["count"],1)
        lessons=audit.review_revision_lessons(self.h,state)
        self.assertEqual(lessons["lessons_count"],2)
        self.assertTrue(all(not x["adopt_as_verified_principle"]
                            for x in lessons["candidate_review_lessons"]))

    def test_same_report_deduplicated(self):
        a=audit.append_revision_review(
            self.h,audit.new_revision_history(self.h),self.report)
        self.assertEqual(a,audit.append_revision_review(self.h,a,self.report))

    def test_original_history_not_changed(self):
        original_history=deepcopy(self.h)
        audit.append_revision_review(
            self.h,audit.new_revision_history(self.h),self.report)
        self.assertEqual(original_history,self.h)

    def test_forged_approval_denied_even_if_outer_hash_recomputed(self):
        changed=deepcopy(self.report)
        changed["automatic_rule_promotion"]=True
        changed["content_sha256"]=audit._digest({
            k:v for k,v in changed.items() if k!="content_sha256"})
        with self.assertRaises(audit.RevisionHistoryError):
            audit.append_revision_review(
                self.h,audit.new_revision_history(self.h),changed)

    def test_wrong_history_replay_denied(self):
        valid=audit.append_revision_review(
            self.h,audit.new_revision_history(self.h),self.report)
        with self.assertRaises(audit.RevisionHistoryError):
            audit.validate_revision_history(ledger.new_review_history(),valid)

    def test_reordered_or_deleted_event_denied(self):
        state=audit.append_revision_review(
            self.h,audit.new_revision_history(self.h),self.report)
        state["events"].pop()
        with self.assertRaises(audit.RevisionHistoryError):
            audit.validate_revision_history(self.h,state)

    def test_forged_candidate_draft_denied(self):
        forged=deepcopy(self.report)
        forged["revision_drafts"][0]["review_option"]="ADOPT_AS_PRODUCTION"
        forged["content_sha256"]=audit._digest({
            k:v for k,v in forged.items() if k!="content_sha256"})
        with self.assertRaises(audit.RevisionHistoryError):
            audit.append_revision_review(
                self.h,audit.new_revision_history(self.h),forged)

    def test_no_persistence_or_training_claim(self):
        state=audit.append_revision_review(
            self.h,audit.new_revision_history(self.h),self.report)
        result=audit.review_revision_lessons(self.h,state)
        self.assertFalse(result["automatic_learning"])
        self.assertFalse(result["automatic_promotion"])
        self.assertFalse(state["persisted"])
        self.assertEqual(len(result["candidate_review_lessons"]),2)
