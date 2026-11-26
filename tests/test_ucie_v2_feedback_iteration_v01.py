"""UCIE feedback iteration lifecycle, dedupe and forged receipt gates."""
from copy import deepcopy
from unittest import TestCase, mock

from ucie_miner import ucie_v2_feedback_iteration_v01 as iteration
from ucie_miner import ucie_v2_first_party_feedback_cycle_v01 as cycle
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3


def row(method):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 900,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


class FeedbackIterationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        records = tuple(row(m) for m in b5.METHODS)
        cls.clean = original.assemble_original_library_assets(records, ())
        cls.changed = original.assemble_original_library_assets(records, ({
            "source_id": "doc:git/git", "previous_pin": b3.PINS["doc:git/git"],
            "candidate_pin": "f" * len(b3.PINS["doc:git/git"]),
        },))
        cls.incomplete = original.assemble_original_library_assets(
            (row(b5.METHODS[0]),), ())

    def history(self, *bundles):
        h = ledger.new_review_history()
        for bundle in bundles:
            h = ledger.append_review_bundle(h, bundle)
        return h

    def test_empty_no_fake_evidence(self):
        x = iteration.compose_feedback_iteration(self.history())
        self.assertEqual(x["disposition"], "NO_HYPOTHESIS_FROM_EMPTY_HISTORY")
        self.assertEqual(x["real_first_party_synthetic_cases_run"], 0)

    def test_real_three_ucie_fixtures_only_review(self):
        x = iteration.compose_feedback_iteration(self.history(self.clean))
        self.assertEqual(x["real_first_party_synthetic_cases_run"], 3)
        self.assertEqual(x["disposition"],
                         "FIRST_PARTY_SYNTHETIC_REVIEW_CANDIDATES_ONLY")
        self.assertFalse(x["new_approved_technical_evidence"])
        self.assertEqual(len(x["review_candidate_ids"]), 2)

    def test_preview_runs_no_fixtures(self):
        with mock.patch.object(iteration, "execute_first_party_feedback_cycle",
                               wraps=cycle.execute_first_party_feedback_cycle) as wrapped:
            x = iteration.compose_feedback_iteration(
                self.history(self.clean), preview_only=True)
        self.assertEqual(x["disposition"], "PREVIEW_ONLY_NO_TEST_EXECUTION")
        self.assertEqual(x["real_first_party_synthetic_cases_run"], 0)
        self.assertEqual(wrapped.call_args.kwargs["execute_synthetic"], False)

    def test_old_source_hold_outweighs_later_clean(self):
        x = iteration.compose_feedback_iteration(
            self.history(self.changed, self.clean))
        self.assertEqual(x["disposition"], "HOLD_SOURCE_REVISION_UNRESOLVED")
        self.assertTrue(x["source_change_hold_active"])
        self.assertIn("REVIEW_AFFECTED_ONLY_RETESTS", x["proposed_next_review_steps"])

    def test_latest_incomplete_holds(self):
        x = iteration.compose_feedback_iteration(
            self.history(self.clean,self.incomplete))
        self.assertEqual(x["disposition"], "HOLD_PAIRED_SYNTHETIC_INCOMPLETE")

    def test_same_history_identical_experiment_no_new_evidence(self):
        h = self.history(self.clean)
        old = cycle.execute_first_party_feedback_cycle(h)
        x = iteration.compose_feedback_iteration(h, prior_cycle=old)
        self.assertTrue(x["duplicate_observation"])
        self.assertEqual(x["disposition"],
                         "NO_NEW_EVIDENCE_DUPLICATE_SYNTHETIC_CYCLE")

    def test_different_history_replay_denied(self):
        old = cycle.execute_first_party_feedback_cycle(self.history(self.clean))
        with self.assertRaises(iteration.FeedbackIterationError):
            iteration.compose_feedback_iteration(
                self.history(self.clean,self.changed), prior_cycle=old)

    def test_fake_approval_even_rehashed_denied(self):
        h = self.history(self.clean)
        fake = cycle.execute_first_party_feedback_cycle(h)
        fake["customer_release_authorized"] = True
        fake["content_sha256"] = iteration._sha({
            k:v for k,v in fake.items() if k != "content_sha256"
        })
        with self.assertRaises(iteration.FeedbackIterationError):
            iteration.compose_feedback_iteration(h, prior_cycle=fake)

    def test_fake_candidate_id_even_rehashed_denied(self):
        h = self.history(self.clean)
        fake = cycle.execute_first_party_feedback_cycle(h)
        fake["feedback_results"][0]["candidate_id"] = "forged"
        fake["content_sha256"] = iteration._sha({
            k:v for k,v in fake.items() if k != "content_sha256"
        })
        with self.assertRaises(iteration.FeedbackIterationError):
            iteration.compose_feedback_iteration(h, prior_cycle=fake)

    def test_deterministic_reports_and_original_untouched(self):
        h = self.history(self.clean)
        old = deepcopy(h)
        a = iteration.compose_feedback_iteration(h)
        b = iteration.compose_feedback_iteration(h)
        self.assertEqual(a,b)
        self.assertEqual(h,old)

    def test_bad_preview_flag_denied(self):
        with self.assertRaises(iteration.FeedbackIterationError):
            iteration.compose_feedback_iteration(
                self.history(self.clean), preview_only="not bool")

    def test_no_real_upstream_or_side_effects(self):
        x = iteration.compose_feedback_iteration(self.history(self.clean))
        for key in ("new_approved_technical_evidence","independent_qa_verified",
                    "rights_approved","customer_release_authorized"):
            self.assertFalse(x[key])
        self.assertTrue(x["no_automatic_model_training"])
        self.assertTrue(x["no_automatic_rule_promotion"])
        self.assertEqual(x["operating_database_writes"],0)
        self.assertEqual(x["network_requests"],0)
