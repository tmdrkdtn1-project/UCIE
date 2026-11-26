"""Integrated UCIE first-party learning iteration and actual history feedback."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_iterative_learning_cycle_v01 as subject
from ucie_miner import ucie_v2_revision_review_history_v01 as review
from ucie_miner import ucie_v2_feedback_registry_v01 as feedback
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3

SHA = "a"*64


def study(method):
    return {"study_id":b5.STUDY_ID,"case_id":b5.CASE_ID,
            "anonymous_trial_token":"F01","method":method,
            "cohort":"FIRST_TIME_CODER","first_safe_action_time_ms":900,
            "correct_safe_action":True,"false_version_or_rights_claim":False,
            "evidence_detail_found":False,"origin":b5.SYNTHETIC_ORIGIN}


def fixture(prefix,n,broken=False):
    truth = "RISK" if n < 4 else "SAFE"
    return {"case_id":f"{prefix}_{n}","ground_truth":truth,
            "baseline_prediction":truth,
            "challenger_prediction":"SAFE" if broken and n==1 else truth,
            "origin":"UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY",
            "source_sha256":SHA}


class IntegratedCycleTests(TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = original.assemble_original_library_assets(
            tuple(study(m) for m in b5.METHODS), ())
        cls.h = ledger.append_review_bundle(ledger.new_review_history(),bundle)
        cls.f = feedback.append_feedback_evidence(
            cls.h,feedback.empty_feedback_registry(cls.h),
            execute_synthetic=True)
        cls.ids = [x["candidate_id"] for x in
                   feedback.prioritize_review_experiments(cls.h,cls.f)["priority_queue"]]
        cls.before = {
            cls.ids[0]:[fixture("a",i,broken=True) for i in range(8)],
            cls.ids[1]:[fixture("b",i) for i in range(8)]}
        cls.after = {
            cls.ids[0]:[fixture("a",i) for i in range(8)],
            cls.ids[1]:[fixture("b",i) for i in range(8)]}

    def start(self):
        return review.new_revision_history(self.h)

    def cycle(self,prior=None,before=None,after=None,*,sha=SHA,expected=None):
        prev=self.start() if prior is None else prior
        return subject.advance_virtual_library_review_cycle(
            self.h,self.f,prev,
            self.before if before is None else before,
            self.after if after is None else after,
            fixture_sha256=sha,
            expected_revision_head_sha256=(
                prev["content_sha256"] if expected is None else expected),
        )

    def test_one_call_connects_source_test_history_next_drafts(self):
        result=self.cycle()
        self.assertTrue(result["new_revision_event_appended"])
        self.assertEqual(result["next_revision_history"]["count"],1)
        self.assertEqual(len(result["original_skillbook_addenda"]),2)
        self.assertTrue(result["next_generation_draft"][
            "feedback_from_previous_revision_consumed"])
        self.assertNotEqual(result["previous_next_draft_sha256"],
                            result["next_generation_sha256"])

    def test_replay_does_not_duplicate_learning_event(self):
        first=self.cycle()
        repeat=self.cycle(first["next_revision_history"])
        self.assertFalse(repeat["new_revision_event_appended"])
        self.assertTrue(repeat["replayed_existing_observation"])
        self.assertEqual(repeat["next_revision_history"]["count"],1)
        self.assertEqual(repeat["previous_next_draft_sha256"],
                         repeat["next_generation_sha256"])

    def test_second_distinct_retest_advances_another_generation(self):
        first=self.cycle()
        after=deepcopy(self.after)
        after[self.ids[0]][1]["challenger_prediction"]="SAFE"
        second=self.cycle(first["next_revision_history"],after=after)
        self.assertTrue(second["new_revision_event_appended"])
        self.assertEqual(second["next_revision_history"]["count"],2)
        self.assertNotEqual(second["previous_next_draft_sha256"],
                            second["next_generation_sha256"])

    def test_forged_owner_approval_denied(self):
        prior=self.start()
        prior["owner_adoption_approved"]=True
        prior["content_sha256"]=review._digest({
            k:v for k,v in prior.items() if k!="content_sha256"})
        with self.assertRaises(review.RevisionHistoryError):
            self.cycle(prior)

    def test_stale_expected_history_denied(self):
        with self.assertRaises(subject.IterativeLearningError):
            self.cycle(expected="f"*64)

    def test_swapped_ground_truth_denied(self):
        altered=deepcopy(self.after)
        altered[self.ids[0]][0]["ground_truth"]="SAFE"
        with self.assertRaises(ValueError):
            self.cycle(after=altered)

    def test_wrong_fixture_sha_denied(self):
        with self.assertRaises(ValueError):
            self.cycle(sha="f"*64)

    def test_cross_candidate_case_reuse_denied(self):
        altered=deepcopy(self.after)
        altered[self.ids[1]]=deepcopy(altered[self.ids[0]])
        with self.assertRaises(ValueError):
            self.cycle(after=altered)

    def test_old_source_change_hold_survives_gain(self):
        changed=original.assemble_original_library_assets(
            tuple(study(m) for m in b5.METHODS),({
                "source_id":"doc:git/git",
                "previous_pin":b3.PINS["doc:git/git"],
                "candidate_pin":"f"*len(b3.PINS["doc:git/git"]),
            },))
        h=ledger.append_review_bundle(ledger.new_review_history(),changed)
        f=feedback.append_feedback_evidence(
            h,feedback.empty_feedback_registry(h),execute_synthetic=True)
        ids=[x["candidate_id"] for x in
             feedback.prioritize_review_experiments(h,f)["priority_queue"]]
        before={ids[0]:[fixture("a",i,broken=True) for i in range(8)],
                ids[1]:[fixture("b",i) for i in range(8)]}
        after={ids[0]:[fixture("a",i) for i in range(8)],
               ids[1]:[fixture("b",i) for i in range(8)]}
        prior=review.new_revision_history(h)
        result=subject.advance_virtual_library_review_cycle(
            h,f,prior,before,after,fixture_sha256=SHA,
            expected_revision_head_sha256=prior["content_sha256"])
        self.assertTrue(all(x["previous_source_revision_hold_preserved"]
                            for x in result["original_skillbook_addenda"]))
        self.assertTrue(all(x["review_status"]=="HOLD_UNRESOLVED_SOURCE_REVISION"
                            for x in result["original_skillbook_addenda"]))

    def test_original_inputs_remain_unchanged(self):
        h, f, start, before, after = [
            deepcopy(x) for x in (self.h,self.f,self.start(),
                                  self.before,self.after)]
        self.cycle()
        self.assertEqual(h,self.h)
        self.assertEqual(f,self.f)
        self.assertEqual(start,self.start())
        self.assertEqual(before,self.before)
        self.assertEqual(after,self.after)

    def test_deterministic_content_hash_and_addendum_digest(self):
        a,b=self.cycle(),self.cycle()
        self.assertEqual(a,b)
        self.assertEqual(a["content_sha256"],subject._digest({
            k:v for k,v in a.items() if k!="content_sha256"}))
        for item in a["original_skillbook_addenda"]:
            from hashlib import sha256
            self.assertEqual(item["addendum_sha256"],
                sha256(item["original_human_skillbook_addendum"].encode()).hexdigest())

    def test_no_production_side_effect_or_training_claim(self):
        a=self.cycle()
        for field in ("signed_original_skillbook_modified","real_sdk_executed",
                      "real_customer_benefit_verified","rights_approved",
                      "independent_qa_verified","model_training_performed",
                      "automatic_rule_promotion","customer_release_authorized",
                      "jobs_scheduled","source_history_mutated",
                      "feedback_registry_mutated"):
            self.assertIs(a[field],False)
        self.assertEqual(a["network_requests"],0)
        self.assertEqual(a["operating_database_writes"],0)
