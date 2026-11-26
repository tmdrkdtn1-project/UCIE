"""Next revision generator must consume actual past review decisions."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_next_hypothesis_feedback_v01 as subject
from ucie_miner import ucie_v2_revision_review_history_v01 as review
from ucie_miner import ucie_v2_hypothesis_revision_retest_v01 as retest
from ucie_miner import ucie_v2_feedback_registry_v01 as feedback
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3

SHA="a"*64

def study(method):
    return {"study_id":b5.STUDY_ID, "case_id":b5.CASE_ID,
            "anonymous_trial_token":"F01", "method":method,
            "cohort":"FIRST_TIME_CODER", "first_safe_action_time_ms":900,
            "correct_safe_action":True, "false_version_or_rights_claim":False,
            "evidence_detail_found":False, "origin":b5.SYNTHETIC_ORIGIN}

def fixture(label,index,*,broken=False):
    truth="RISK" if index<4 else "SAFE"
    return {"case_id":f"{label}_{index}","ground_truth":truth,
            "baseline_prediction":truth,
            "challenger_prediction":("SAFE" if broken and index==1 else truth),
            "origin":"UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY",
            "source_sha256":SHA}


class NextFeedbackTests(TestCase):
    @classmethod
    def setUpClass(cls):
        bundle=original.assemble_original_library_assets(
            tuple(study(m) for m in b5.METHODS),())
        cls.h=ledger.append_review_bundle(ledger.new_review_history(),bundle)
        cls.f=feedback.append_feedback_evidence(
            cls.h,feedback.empty_feedback_registry(cls.h),execute_synthetic=True)
        cls.ids=[x["candidate_id"] for x in feedback.prioritize_review_experiments(
            cls.h,cls.f)["priority_queue"]]
        before={cls.ids[0]:[fixture("a",i,broken=True) for i in range(8)],
                cls.ids[1]:[fixture("b",i) for i in range(8)]}
        after={cls.ids[0]:[fixture("a",i) for i in range(8)],
               cls.ids[1]:[fixture("b",i) for i in range(8)]}
        cls.report=retest.revise_and_retest_hypotheses(
            cls.h,cls.f,before,after,fixture_sha256=SHA)

    def history(self):
        return review.append_revision_review(
            self.h,review.new_revision_history(self.h),self.report)

    def test_actual_revision_lessons_change_next_candidate(self):
        empty=subject.next_hypotheses_from_revisions(
            self.h,review.new_revision_history(self.h))
        nxt=subject.next_hypotheses_from_revisions(self.h,self.history())
        self.assertNotEqual(empty["content_sha256"],nxt["content_sha256"])
        self.assertEqual(nxt["next_candidate_count"],2)
        self.assertTrue(nxt["feedback_from_previous_revision_consumed"])
        selected=next(x for x in nxt["next_candidates"]
                      if x["candidate_id"]==self.ids[0])
        self.assertEqual(selected["next_review_status"],
                         "NEXT_REVISION_DRAFT_REQUIRES_INDEPENDENT_REVIEW")
        self.assertEqual(selected["revision_iteration"],1)

    def test_retain_one_hypothesis_but_revise_other(self):
        nxt=subject.next_hypotheses_from_revisions(self.h,self.history())
        other=next(x for x in nxt["next_candidates"]
                   if x["candidate_id"]==self.ids[1])
        self.assertEqual(other["next_review_status"],
                         "RETAIN_DRAFT_AWAIT_INDEPENDENT_EVIDENCE")

    def test_rejected_challenger_constraint_survives_later_revision(self):
        older=deepcopy(self.report)
        for item in older["revision_drafts"]:
            if item["candidate_id"]==self.ids[0]:
                item["review_option"]="REJECT_SYNTHETIC_CHALLENGER"
                item["observed_synthetic_gain"]=False
                item["observed_synthetic_nonworsening"]=False
                item["revision_sha256"]=review._digest({
                    k:v for k,v in item.items() if k not in (
                        "revision_id","revision_sha256","original_skillbook_replaced",
                        "engine_contract_activated","rule_approved",
                        "independent_qa_verified","real_customer_effect_verified",
                        "automatic_learning_or_training")})
                item["revision_id"]="UCIE-VLIB-REV-"+item["revision_sha256"][:24]
        older["content_sha256"]=review._digest({
            k:v for k,v in older.items() if k!="content_sha256"})
        history=review.append_revision_review(
            self.h,review.new_revision_history(self.h),older)
        history=review.append_revision_review(self.h,history,self.report)
        nxt=subject.next_hypotheses_from_revisions(self.h,history)
        chosen=next(x for x in nxt["next_candidates"]
                    if x["candidate_id"]==self.ids[0])
        self.assertTrue(chosen["earlier_rejected_challenger_seen"])
        self.assertEqual(chosen["revision_iteration"],2)

    def test_unrelated_source_history_rejected(self):
        with self.assertRaises(review.RevisionHistoryError):
            subject.next_hypotheses_from_revisions(
                ledger.new_review_history(),self.history())

    def test_untrusted_approval_denied(self):
        forged=self.history()
        forged["owner_adoption_approved"]=True
        forged["content_sha256"]=review._digest({
            k:v for k,v in forged.items() if k!="content_sha256"})
        with self.assertRaises(review.RevisionHistoryError):
            subject.next_hypotheses_from_revisions(self.h,forged)

    def test_wrong_candidate_provenance_even_rehashed_denied(self):
        forged=deepcopy(self.report)
        item=forged["revision_drafts"][0]
        item["parent_candidate_sha256"]="f"*64
        item["revision_sha256"]=review._digest({
            k:v for k,v in item.items() if k not in (
                "revision_id","revision_sha256","original_skillbook_replaced",
                "engine_contract_activated","rule_approved","independent_qa_verified",
                "real_customer_effect_verified","automatic_learning_or_training")})
        item["revision_id"]="UCIE-VLIB-REV-"+item["revision_sha256"][:24]
        forged["content_sha256"]=review._digest({
            k:v for k,v in forged.items() if k!="content_sha256"})
        reviews=review.append_revision_review(
            self.h,review.new_revision_history(self.h),forged)
        with self.assertRaises(subject.NextHypothesisError):
            subject.next_hypotheses_from_revisions(self.h,reviews)

    def test_invalid_release_fails_closed(self):
        forged=self.history()
        forged["events"][0]["report"]["customer_release_authorized"]=True
        with self.assertRaises(review.RevisionHistoryError):
            subject.next_hypotheses_from_revisions(self.h,forged)

    def test_deterministic_and_nonmutating(self):
        originals=deepcopy(self.h)
        history=self.history()
        before=deepcopy(history)
        first=subject.next_hypotheses_from_revisions(self.h,history)
        self.assertEqual(first,subject.next_hypotheses_from_revisions(self.h,history))
        self.assertEqual(originals,self.h)
        self.assertEqual(before,history)
        self.assertEqual(first["content_sha256"],subject._digest({
            k:v for k,v in first.items() if k!="content_sha256"}))

    def test_no_automatic_adoption(self):
        x=subject.next_hypotheses_from_revisions(self.h,self.history())
        self.assertFalse(x["automatic_model_training"])
        self.assertFalse(x["automatic_rule_promotion"])
        self.assertTrue(all(not c["customer_release_authorized"]
                            for c in x["next_candidates"]))

    def test_original_privacy_counterexample_stays_binding(self):
        x=subject.next_hypotheses_from_revisions(self.h,self.history())
        self.assertTrue(all(
            "ALL_BOUNDED_METADATA_PROCESSES_HIDE_SOURCE_NAMES" in
            c["reusable_negative_constraints"] for c in x["next_candidates"]))
