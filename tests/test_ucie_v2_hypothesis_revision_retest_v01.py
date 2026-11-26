"""UCIE V2 source-pinned hypothesis revision paired retest with lifecycle HOLD."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_hypothesis_revision_retest_v01 as subject
from ucie_miner import ucie_v2_feedback_registry_v01 as feedback
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3

SHA="a"*64


def study(method):
    return {"study_id":b5.STUDY_ID,"case_id":b5.CASE_ID,
            "anonymous_trial_token":"F01","method":method,
            "cohort":"FIRST_TIME_CODER","first_safe_action_time_ms":900,
            "correct_safe_action":True,"false_version_or_rights_claim":False,
            "evidence_detail_found":False,"origin":b5.SYNTHETIC_ORIGIN}


def fixture(name,truth,base,new):
    return {"case_id":name,"ground_truth":truth,
            "baseline_prediction":base,"challenger_prediction":new,
            "origin":"UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY",
            "source_sha256":SHA}


class RevisionRetestTests(TestCase):
    @classmethod
    def setUpClass(cls):
        bundle=original.assemble_original_library_assets(
            tuple(study(x) for x in b5.METHODS),())
        cls.history=ledger.append_review_bundle(ledger.new_review_history(),bundle)
        cls.registry=feedback.append_feedback_evidence(
            cls.history,feedback.empty_feedback_registry(cls.history),
            execute_synthetic=True)
        cls.ids=[x["candidate_id"] for x in feedback.prioritize_review_experiments(
            cls.history,cls.registry)["priority_queue"]]

    def cases(self,prefix,*,regression=False,fix=False):
        rows=[]
        for n in range(8):
            truth="RISK" if n<4 else "SAFE"
            base="SAFE" if n in (0,4) else truth
            new=truth if n!=1 else ("SAFE" if regression and not fix else truth)
            rows.append(fixture(f"{prefix}_{n}",truth,base,new))
        return rows

    def inputs(self):
        before={self.ids[0]:self.cases("a",regression=True),
                self.ids[1]:self.cases("b")}
        after={self.ids[0]:self.cases("a",regression=True,fix=True),
               self.ids[1]:self.cases("b")}
        return before,after

    def calculate(self,before=None,after=None):
        first,second=self.inputs()
        return subject.revise_and_retest_hypotheses(
            self.history,self.registry,first if before is None else before,
            second if after is None else after,fixture_sha256=SHA)

    def test_fixed_regression_creates_review_only_revision(self):
        report=self.calculate()
        self.assertEqual(report["draft_count"],2)
        a=next(x for x in report["revision_drafts"]
               if x["candidate_id"]==self.ids[0])
        self.assertEqual(a["review_option"],"REVISE_DRAFT")
        self.assertTrue(a["observed_synthetic_gain"])
        self.assertFalse(a["original_skillbook_replaced"])

    def test_unchanged_challenger_kept_review_only(self):
        report=self.calculate()
        b=next(x for x in report["revision_drafts"]
               if x["candidate_id"]==self.ids[1])
        self.assertEqual(b["review_option"],"RETAIN_REVIEW_ONLY")

    def test_regression_added_rejected(self):
        first,second=self.inputs()
        second[self.ids[1]][2]["challenger_prediction"]="SAFE"
        out=self.calculate(first,second)
        decision=next(x for x in out["revision_drafts"]
                      if x["candidate_id"]==self.ids[1])
        self.assertEqual(decision["review_option"],
                         "REJECT_SYNTHETIC_CHALLENGER")

    def test_missing_control_is_hold(self):
        first,second=self.inputs()
        first[self.ids[1]]=first[self.ids[1]][:2]
        second[self.ids[1]]=second[self.ids[1]][:2]
        out=self.calculate(first,second)
        decision=next(x for x in out["revision_drafts"]
                      if x["candidate_id"]==self.ids[1])
        self.assertEqual(decision["review_option"],"HOLD")

    def test_changed_ground_truth_denied(self):
        first,second=self.inputs()
        second[self.ids[0]][0]["ground_truth"]="SAFE"
        with self.assertRaises(subject.RevisionCycleError):
            self.calculate(first,second)

    def test_changed_baseline_denied(self):
        first,second=self.inputs()
        second[self.ids[0]][0]["baseline_prediction"]="RISK"
        with self.assertRaises(subject.RevisionCycleError):
            self.calculate(first,second)

    def test_changed_case_id_denied(self):
        first,second=self.inputs()
        second[self.ids[0]][0]["case_id"]="other"
        with self.assertRaises(subject.RevisionCycleError):
            self.calculate(first,second)

    def test_missing_candidate_arm_denied(self):
        first,second=self.inputs()
        second.pop(self.ids[1])
        with self.assertRaises(subject.RevisionCycleError):
            self.calculate(first,second)

    def test_cross_candidate_test_leak_denied(self):
        first,second=self.inputs()
        second[self.ids[1]]=deepcopy(second[self.ids[0]])
        with self.assertRaises(ValueError):
            self.calculate(first,second)

    def test_source_pin_forgery_denied(self):
        first,second=self.inputs()
        second[self.ids[0]][0]["source_sha256"]="b"*64
        with self.assertRaises(ValueError):
            self.calculate(first,second)

    def test_content_deterministic(self):
        report=self.calculate()
        self.assertEqual(report,self.calculate())
        self.assertEqual(report["content_sha256"],subject._hash({
            k:v for k,v in report.items() if k!="content_sha256"}))

    def test_no_history_mutation_or_rule_adoption(self):
        first,second=self.inputs()
        original_first=deepcopy(first)
        original_second=deepcopy(second)
        report=self.calculate(first,second)
        self.assertEqual(first,original_first)
        self.assertEqual(second,original_second)
        self.assertFalse(report["automatic_rule_promotion"])
        self.assertFalse(report["customer_release_authorized"])
        self.assertEqual(report["operating_database_writes"],0)

    def test_prior_source_change_remains_hold(self):
        changed=original.assemble_original_library_assets(
            tuple(study(x) for x in b5.METHODS),({
                "source_id":"doc:git/git","previous_pin":b3.PINS["doc:git/git"],
                "candidate_pin":"f"*len(b3.PINS["doc:git/git"]),
            },))
        h=ledger.append_review_bundle(ledger.new_review_history(),changed)
        reg=feedback.append_feedback_evidence(
            h,feedback.empty_feedback_registry(h),execute_synthetic=True)
        ids=[x["candidate_id"] for x in feedback.prioritize_review_experiments(
            h,reg)["priority_queue"]]
        first={ids[0]:self.cases("a",regression=True),
               ids[1]:self.cases("b")}
        second={ids[0]:self.cases("a",fix=True),ids[1]:self.cases("b")}
        report=subject.revise_and_retest_hypotheses(
            h,reg,first,second,fixture_sha256=SHA)
        self.assertTrue(all(r["review_option"]=="HOLD"
                            for r in report["revision_drafts"]))
