"""UCIE V2 review registry: real bounded controls, replay, decision, priorities."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_feedback_registry_v01 as subject
from ucie_miner import ucie_v2_library_revision_ledger_v01 as hist
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3
from ucie_miner import ucie_v2_first_party_feedback_cycle_v01 as cycle
from ucie_miner import ucie_v2_feedback_iteration_v01 as iteration


def row(method):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 900,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


class FeedbackRegistryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        records = tuple(row(method) for method in b5.METHODS)
        cls.clean = original.assemble_original_library_assets(records, ())
        cls.changed = original.assemble_original_library_assets(records, ({
            "source_id": "doc:git/git", "previous_pin": b3.PINS["doc:git/git"],
            "candidate_pin": "f"*len(b3.PINS["doc:git/git"]),
        },))
        cls.incomplete = original.assemble_original_library_assets(
            (row(b5.METHODS[0]),), ())

    def h(self, *bundles):
        result = hist.new_review_history()
        for bundle in bundles:
            result = hist.append_review_bundle(result, bundle)
        return result

    def test_empty_history_no_candidate_or_test(self):
        h = self.h()
        a = subject.append_feedback_evidence(h, subject.empty_feedback_registry(h))
        self.assertEqual(a["event_count"], 1)
        self.assertEqual(subject.prioritize_review_experiments(h,a)["candidate_count"],0)

    def test_preview_retains_no_synthetic_execution(self):
        h = self.h(self.clean)
        r = subject.append_feedback_evidence(h, subject.empty_feedback_registry(h))
        self.assertEqual([x["decision"] for x in
                          r["events"][0]["evidence"]["candidate_reviews"]],
                         ["HOLD_PREVIEW_NOT_TESTED"]*2)

    def test_opt_in_real_ucie_control_and_priority(self):
        h = self.h(self.clean)
        r = subject.append_feedback_evidence(
            h, subject.empty_feedback_registry(h), execute_synthetic=True)
        decisions = [x["decision"] for x in
                     r["events"][0]["evidence"]["candidate_reviews"]]
        self.assertEqual(decisions, [
            "REVISE_REVIEW_ONLY_OUTPUT_GUARD",
            "REVIEW_CANDIDATE_SYNTHETIC_NOT_INDEPENDENT",
        ])
        queue = subject.prioritize_review_experiments(h,r)
        self.assertEqual(queue["candidate_count"],2)
        self.assertFalse(queue["tests_scheduled"])

    def test_prior_source_hold_is_never_cleared(self):
        h = self.h(self.changed,self.clean)
        r = subject.append_feedback_evidence(
            h, subject.empty_feedback_registry(h), execute_synthetic=True)
        self.assertEqual([x["decision"] for x in
                          r["events"][0]["evidence"]["candidate_reviews"]],
                         ["HOLD_SOURCE_REVISION"]*2)
        self.assertEqual(subject.prioritize_review_experiments(h,r)[
            "priority_queue"][0]["priority"],1)

    def test_incomplete_pair_still_holds(self):
        h = self.h(self.incomplete)
        r = subject.append_feedback_evidence(
            h, subject.empty_feedback_registry(h), execute_synthetic=True)
        self.assertEqual([x["decision"] for x in
                          r["events"][0]["evidence"]["candidate_reviews"]],
                         ["HOLD_INCOMPLETE_PAIRED_EVIDENCE"]*2)

    def test_dedupe_same_observation(self):
        h = self.h(self.clean)
        a = subject.append_feedback_evidence(
            h, subject.empty_feedback_registry(h), execute_synthetic=True)
        b = subject.append_feedback_evidence(h,a,execute_synthetic=True)
        self.assertEqual(a,b)

    def test_cross_history_replay_denied(self):
        h1 = self.h(self.clean)
        h2 = self.h(self.changed)
        prior = subject.append_feedback_evidence(h1,subject.empty_feedback_registry(h1))
        with self.assertRaises(subject.FeedbackRegistryError):
            subject.validate_feedback_registry(h2,prior)

    def test_tampered_hash_chain_denied(self):
        h = self.h(self.clean)
        r = subject.append_feedback_evidence(h,subject.empty_feedback_registry(h))
        r["events"][0]["event_hash"] = "f"*64
        with self.assertRaises(subject.FeedbackRegistryError):
            subject.validate_feedback_registry(h,r)

    def test_forged_approval_denied_even_rehashed(self):
        h = self.h(self.clean)
        r = subject.append_feedback_evidence(h,subject.empty_feedback_registry(h))
        r["events"][0]["evidence"]["candidate_reviews"][0]["approved_as_rule"] = True
        evidence = r["events"][0]["evidence"]
        r["events"][0]["fingerprint"] = subject._sha(evidence)
        r["events"][0]["event_hash"] = subject._sha({
            k:v for k,v in r["events"][0].items() if k != "event_hash"
        })
        r["head_hash"] = r["events"][0]["event_hash"]
        r["content_sha256"] = subject._sha({
            k:v for k,v in r.items() if k != "content_sha256"
        })
        with self.assertRaises(subject.FeedbackRegistryError):
            subject.validate_feedback_registry(h,r)

    def test_fake_fixture_result_denied(self):
        h = self.h(self.clean)
        observed = cycle.execute_first_party_feedback_cycle(h)
        observed["feedback_results"][0]["controls_observed"] = ["CONTRACT_MATCH"]*3
        observed["content_sha256"] = cycle._digest({
            k:v for k,v in observed.items() if k != "content_sha256"
        })
        report = iteration.compose_feedback_iteration(h)
        with self.assertRaises(subject.FeedbackRegistryError):
            subject.append_feedback_evidence(
                h, subject.empty_feedback_registry(h),
                cycle=observed, iteration=report)

    def test_wrong_iteration_sha_denied(self):
        h = self.h(self.clean)
        observed = cycle.execute_first_party_feedback_cycle(h)
        report = iteration.compose_feedback_iteration(h)
        report["feedback_cycle_sha256"] = "a"*64
        report["content_sha256"] = iteration._sha({
            k:v for k,v in report.items() if k != "content_sha256"
        })
        with self.assertRaises(subject.FeedbackRegistryError):
            subject.append_feedback_evidence(
                h,subject.empty_feedback_registry(h),cycle=observed,iteration=report)

    def test_history_unmodified(self):
        h = self.h(self.clean)
        before = deepcopy(h)
        subject.append_feedback_evidence(
            h, subject.empty_feedback_registry(h), execute_synthetic=True)
        self.assertEqual(before,h)

    def test_no_operating_or_customer_mutations(self):
        h = self.h(self.clean)
        registry = subject.append_feedback_evidence(
            h,subject.empty_feedback_registry(h))
        plan = subject.prioritize_review_experiments(h,registry)
        for field in ("source_revision_authenticated", "tests_scheduled",
                      "owner_approval_granted", "automatic_promotion",
                      "customer_release_authorized"):
            self.assertFalse(plan[field])
        self.assertEqual(plan["network_requests"],0)
        self.assertEqual(plan["operating_database_writes"],0)
