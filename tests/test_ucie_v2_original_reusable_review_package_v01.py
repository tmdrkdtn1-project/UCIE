"""UCIE original reusable package from connected feedback: no release drift."""
from copy import deepcopy
from hashlib import sha256
from unittest import TestCase

from ucie_miner import ucie_v2_original_reusable_review_package_v01 as subject
from ucie_miner import ucie_v2_revision_review_history_v01 as revisions
from ucie_miner import ucie_v2_feedback_registry_v01 as feedback
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3

SHA = "a"*64


def study(m):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": m,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 900,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


def case(prefix, n, bad=False):
    truth = "RISK" if n<4 else "SAFE"
    return {"case_id": f"{prefix}_{n}", "ground_truth": truth,
            "baseline_prediction": truth,
            "challenger_prediction": "SAFE" if bad and n==1 else truth,
            "origin": "UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY",
            "source_sha256": SHA}


class ReusablePackageTests(TestCase):
    @classmethod
    def setUpClass(cls):
        b = original.assemble_original_library_assets(
            tuple(study(m) for m in b5.METHODS), ())
        cls.h = ledger.append_review_bundle(ledger.new_review_history(), b)
        cls.f = feedback.append_feedback_evidence(
            cls.h, feedback.empty_feedback_registry(cls.h),
            execute_synthetic=True)
        cls.r = revisions.new_revision_history(cls.h)
        ids = [x["candidate_id"] for x in
               feedback.prioritize_review_experiments(cls.h, cls.f)["priority_queue"]]
        cls.before = {
            ids[0]: [case("a", n, True) for n in range(8)],
            ids[1]: [case("b", n) for n in range(8)]}
        cls.after = {
            ids[0]: [case("a", n) for n in range(8)],
            ids[1]: [case("b", n) for n in range(8)]}

    def run_package(self, history=None, feedback_registry=None, revision=None,
                    before=None, after=None, fixture=SHA, expected=None):
        r=self.r if revision is None else revision
        return subject.build_original_review_packages(
            self.h if history is None else history,
            self.f if feedback_registry is None else feedback_registry,
            r, self.before if before is None else before,
            self.after if after is None else after,
            fixture_sha256=fixture,
            expected_revision_head_sha256=r["content_sha256"] if expected is None
                                          else expected)

    def test_produces_two_real_original_contracts(self):
        x=self.run_package()
        self.assertEqual(x["package_count"],2)
        for p in x["review_packages"]:
            self.assertIn("UCIE 가상도서관",p["human_skillbook_text"])
            self.assertFalse(p["engine_test_contract"]["runtime_execution_enabled"])
            self.assertEqual(p["human_text_sha256"],
                sha256(p["human_skillbook_text"].encode()).hexdigest())
            self.assertEqual(len(p["engine_test_contract"]["expected_synthetic_controls"]),3)

    def test_provenance_and_determinism(self):
        a=self.run_package()
        b=self.run_package()
        self.assertEqual(a,b)
        self.assertEqual(a["content_sha256"],subject._hash({
            k:v for k,v in a.items() if k != "content_sha256"}))

    def test_duplicate_cycle_does_not_forge_extra_approved_versions(self):
        a=self.run_package()
        self.assertEqual(a["package_count"],2)
        self.assertFalse(a["customer_distribution_authorized"])

    def test_wrong_source_identity_denied(self):
        with self.assertRaises((ValueError, subject.ReviewPackageError)):
            self.run_package(history=ledger.new_review_history())

    def test_stale_review_head_denied(self):
        with self.assertRaises(ValueError):
            self.run_package(expected="f"*64)

    def test_changed_baseline_denied(self):
        after=deepcopy(self.after)
        key=next(iter(after))
        after[key][0]["baseline_prediction"]="SAFE"
        with self.assertRaises(ValueError):
            self.run_package(after=after)

    def test_unapproved_customer_data_denied(self):
        after=deepcopy(self.after)
        key=next(iter(after))
        after[key][0]["private_customer_data"]="secret"
        with self.assertRaises(ValueError):
            self.run_package(after=after)

    def test_source_change_preserves_hold(self):
        changed=original.assemble_original_library_assets(
            tuple(study(m) for m in b5.METHODS),({
                "source_id": "doc:git/git",
                "previous_pin": b3.PINS["doc:git/git"],
                "candidate_pin": "f"*len(b3.PINS["doc:git/git"]),
            },))
        h=ledger.append_review_bundle(ledger.new_review_history(),changed)
        f=feedback.append_feedback_evidence(
            h,feedback.empty_feedback_registry(h),execute_synthetic=True)
        ids=[x["candidate_id"] for x in
             feedback.prioritize_review_experiments(h,f)["priority_queue"]]
        before={ids[0]:[case("a",n,True) for n in range(8)],
                ids[1]:[case("b",n) for n in range(8)]}
        after={ids[0]:[case("a",n) for n in range(8)],
               ids[1]:[case("b",n) for n in range(8)]}
        r=subject.build_original_review_packages(
            h,f,revisions.new_revision_history(h),before,after,
            fixture_sha256=SHA,
            expected_revision_head_sha256=revisions.new_revision_history(h)[
                "content_sha256"])
        self.assertTrue(all(p["prior_source_hold_preserved"]
                            for p in r["review_packages"]))

    def test_no_signed_skillbook_or_release_claim(self):
        r=self.run_package()
        for p in r["review_packages"]:
            for key in ("independent_qa_verified", "rights_approved",
                        "customer_export_authorized", "signed", "installed",
                        "model_trained"):
                self.assertFalse(p[key])
        self.assertFalse(r["automatic_rule_promotion"])
        self.assertEqual(r["operating_database_writes"],0)

    def test_input_objects_unchanged(self):
        h,f,r,b,a=[deepcopy(x) for x in (
            self.h,self.f,self.r,self.before,self.after)]
        self.run_package()
        self.assertEqual((h,f,r,b,a),
                         (self.h,self.f,self.r,self.before,self.after))
