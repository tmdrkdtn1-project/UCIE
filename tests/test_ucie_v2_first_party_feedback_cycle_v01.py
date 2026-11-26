"""UCIE V2 real first-party synthetic feedback: lineage and negative gates."""
from copy import deepcopy
from unittest import TestCase, mock

from ucie_miner import ucie_v2_first_party_feedback_cycle_v01 as subject
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as originals
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3


def row(method):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 900,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


def signal(source):
    return {"source_id": source, "previous_pin": b3.PINS[source],
            "candidate_pin": "f"*len(b3.PINS[source])}


class FirstPartyFeedbackCycleTests(TestCase):
    @classmethod
    def setUpClass(cls):
        records = tuple(row(m) for m in b5.METHODS)
        cls.clean = originals.assemble_original_library_assets(records, ())
        cls.changed = originals.assemble_original_library_assets(
            records, (signal("doc:python/cpython"),))
        cls.incomplete = originals.assemble_original_library_assets(
            (row(b5.METHODS[0]),), ())

    def history(self, *bundles):
        history = ledger.new_review_history()
        for x in bundles:
            history = ledger.append_review_bundle(history, x)
        return history

    def test_empty_history_never_invents_experiments(self):
        x = subject.execute_first_party_feedback_cycle(self.history())
        self.assertEqual(x["feedback_count"], 0)
        self.assertEqual(x["executed_ucie_synthetic_fixture_count"], 0)

    def test_actual_three_first_party_fixtures_per_cycle(self):
        x = subject.execute_first_party_feedback_cycle(self.history(self.clean))
        self.assertEqual(x["feedback_count"], 2)
        self.assertEqual(x["executed_ucie_synthetic_fixture_count"], 3)
        self.assertTrue(all(r["verdict"] ==
             "REVIEW_ONLY_SYNTHETIC_CONTROLS_MATCH" for r in x["feedback_results"]))
        self.assertFalse(x["real_upstream_sdk_executed"])

    def test_preview_runs_no_ucie_fixtures(self):
        with mock.patch.object(subject, "run_bounded_transfer",
                               side_effect=AssertionError("should not run")):
            x = subject.execute_first_party_feedback_cycle(
                self.history(self.clean), execute_synthetic=False)
        self.assertEqual(x["executed_ucie_synthetic_fixture_count"], 0)
        self.assertTrue(all(r["verdict"] == "HOLD_SYNTHETIC_TEST_NOT_RUN"
                            for r in x["feedback_results"]))

    def test_prior_source_hold_persists_after_synthetic_match(self):
        x = subject.execute_first_party_feedback_cycle(
            self.history(self.changed, self.clean))
        self.assertEqual(x["review_lifecycle"],
                         "SOURCE_REVISION_HOLD_NOT_CLEARED_BY_SYNTHETIC_REPLAY")
        self.assertTrue(all(r["verdict"] == "HOLD_UNRESOLVED_SOURCE_REVISION"
                            for r in x["feedback_results"]))
        self.assertTrue(all(not r["historical_source_hold_cleared"]
                            for r in x["feedback_results"]))
        self.assertEqual(x["unresolved_source_changes"], ["doc:python/cpython"])

    def test_incomplete_pair_stays_hold(self):
        x = subject.execute_first_party_feedback_cycle(
            self.history(self.incomplete))
        self.assertTrue(all(r["verdict"] == "HOLD_INCOMPLETE_SYNTHETIC_PAIR"
                            for r in x["feedback_results"]))

    def test_observed_negative_is_not_approved_positive(self):
        x = subject.execute_first_party_feedback_cycle(self.history(self.clean))
        self.assertTrue(all(r["rejected_original_privacy_overgeneralization_preserved"]
                            for r in x["feedback_results"]))
        self.assertFalse(any(r["candidate_approved"] for r in x["feedback_results"]))

    def test_original_history_unmodified(self):
        h = self.history(self.changed, self.clean)
        before = deepcopy(h)
        subject.execute_first_party_feedback_cycle(h)
        self.assertEqual(h, before)

    def test_deterministic_content_hash(self):
        h = self.history(self.clean)
        a = subject.execute_first_party_feedback_cycle(h)
        b = subject.execute_first_party_feedback_cycle(h)
        self.assertEqual(a, b)
        self.assertEqual(a["content_sha256"],
                         subject._digest({k:v for k,v in a.items()
                                          if k != "content_sha256"}))

    def test_forged_source_denied_by_history(self):
        h = self.history(self.clean)
        h["events"][0]["bundle"]["chapter"]["source_lineage"][0][
            "source_id"] = "repo:unapproved/outside"
        with self.assertRaises(ledger.ReviewHistoryError):
            subject.execute_first_party_feedback_cycle(h)

    def test_forged_candidate_hash_denied(self):
        from ucie_miner import ucie_v2_hypothesis_reassessment_v01 as reassess
        h = self.history(self.clean)
        fake = reassess.reassess_library_hypotheses(h)
        fake["original_falsifiable_candidates"][0]["candidate_sha256"] = "f"*64
        fake["content_sha256"] = reassess._hash({
            k:v for k,v in fake.items() if k != "content_sha256"
        })
        with mock.patch.object(subject, "reassess_library_hypotheses",
                               return_value=fake):
            with self.assertRaises(subject.LearningFeedbackError):
                subject.execute_first_party_feedback_cycle(h)

    def test_missing_candidate_arm_denied(self):
        from ucie_miner import ucie_v2_hypothesis_reassessment_v01 as reassess
        h = self.history(self.clean)
        fake = reassess.reassess_library_hypotheses(h)
        fake["original_falsifiable_candidates"].pop()
        fake["generated_candidates_count"] = 1
        fake["content_sha256"] = reassess._hash({
            k:v for k,v in fake.items() if k != "content_sha256"
        })
        with mock.patch.object(subject, "reassess_library_hypotheses",
                               return_value=fake):
            with self.assertRaises(subject.LearningFeedbackError):
                subject.execute_first_party_feedback_cycle(h)

    def test_forged_sdk_execution_claim_denied(self):
        h = self.history(self.clean)
        actual = subject.run_bounded_transfer(subject.build_hypothesis())
        fake = deepcopy(actual)
        fake["real_upstream_sdk_rerun"] = True
        with mock.patch.object(subject, "run_bounded_transfer", return_value=fake):
            with self.assertRaises(subject.LearningFeedbackError):
                subject.execute_first_party_feedback_cycle(h)

    def test_invalid_synthetic_flag_denied(self):
        with self.assertRaises(subject.LearningFeedbackError):
            subject.execute_first_party_feedback_cycle(
                self.history(self.clean), execute_synthetic="yes")

    def test_no_operating_db_training_or_customer_release(self):
        x = subject.execute_first_party_feedback_cycle(self.history(self.clean))
        for key in ("source_revision_authenticated", "independent_qa_verified",
                    "real_user_study", "customer_release_authorized",
                    "automatic_model_training", "automatic_rule_promotion",
                    "history_mutated", "history_written"):
            self.assertIs(x[key], False)
        self.assertEqual(x["operating_database_writes"], 0)
        self.assertEqual(x["network_requests"], 0)
