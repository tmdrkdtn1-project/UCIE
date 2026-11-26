"""Source-locked UCIE synthetic effectiveness + regression tests."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_effectiveness_evaluation_v01 as subject
from ucie_miner import ucie_v2_feedback_registry_v01 as reviews
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5

SHA = "a"*64


def row(method):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 900,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


def sample(name, truth, base, new):
    return {"case_id": name, "ground_truth": truth,
            "baseline_prediction": base, "challenger_prediction": new,
            "origin": subject.ORIGIN, "source_sha256": SHA}


class EffectivenessTests(TestCase):
    @classmethod
    def setUpClass(cls):
        bundle = original.assemble_original_library_assets(
            tuple(row(x) for x in b5.METHODS), ())
        cls.history = ledger.append_review_bundle(ledger.new_review_history(), bundle)
        cls.registry = reviews.append_feedback_evidence(
            cls.history, reviews.empty_feedback_registry(cls.history))
        cls.data = (
            sample("a", "RISK", "SAFE", "RISK"),
            sample("b", "RISK", "RISK", "RISK"),
            sample("c", "SAFE", "RISK", "SAFE"),
            sample("d", "SAFE", "SAFE", "RISK"),
        )

    def compute(self, data=None):
        return subject.evaluate_bounded_improvement(
            self.history, self.registry, self.data if data is None else data,
            source_sha256=SHA)

    def test_confusion_matrix_and_denominators(self):
        x = self.compute()
        self.assertEqual(x["baseline"]["confusion"], {
            "tp":1, "fp":1, "fn":1, "tn":1})
        self.assertEqual(x["challenger"]["confusion"], {
            "tp":2, "fp":1, "fn":0, "tn":1})
        self.assertEqual(x["challenger"]["detection_rate"]["value"],1.0)
        self.assertEqual(x["challenger"]["false_positive_rate"]["value"],0.5)

    def test_paired_improvements_and_regressions(self):
        x = self.compute()
        self.assertEqual(x["paired_improved_cases"],2)
        self.assertEqual(x["paired_regressed_cases"],1)
        self.assertEqual(x["paired_regression_rate"]["value"],0.25)
        self.assertEqual(x["status"],"REVIEW_REGRESSION_OBSERVED")

    def test_missing_dataset_is_hold_not_success(self):
        x = self.compute(())
        self.assertEqual(x["status"],"HOLD_NO_SYNTHETIC_CASES")
        self.assertIsNone(x["baseline"]["accuracy"]["value"])

    def test_no_negative_control_is_hold(self):
        x = self.compute((sample("a","RISK","RISK","RISK"),))
        self.assertEqual(x["status"],"HOLD_NO_POSITIVE_OR_NEGATIVE_CONTROL")
        self.assertIsNone(x["challenger"]["false_positive_rate"]["value"])

    def test_same_inputs_deterministic_and_unchanged(self):
        x = self.compute()
        self.assertEqual(x,self.compute(reversed(self.data) if False else self.data))
        self.assertEqual(x["content_sha256"],subject.digest({
            k:v for k,v in x.items() if k!="content_sha256"}))

    def test_duplicates_rejected(self):
        with self.assertRaises(subject.EvaluationError):
            self.compute((self.data[0],self.data[0]))

    def test_unsupported_source_digest_rejected(self):
        bad=deepcopy(self.data[0])
        bad["source_sha256"]="f"*64
        with self.assertRaises(subject.EvaluationError):
            self.compute((bad,))

    def test_private_or_extra_fields_denied(self):
        bad=deepcopy(self.data[0])
        bad["private_email"]="nobody@example.invalid"
        with self.assertRaises(subject.EvaluationError):
            self.compute((bad,))

    def test_unknown_labels_denied(self):
        bad=deepcopy(self.data[0])
        bad["ground_truth"]="UNKNOWN"
        with self.assertRaises(subject.EvaluationError):
            self.compute((bad,))

    def test_bool_labels_denied(self):
        bad=deepcopy(self.data[0])
        bad["challenger_prediction"]=True
        with self.assertRaises(subject.EvaluationError):
            self.compute((bad,))

    def test_data_immutability(self):
        prior=deepcopy(self.data)
        self.compute()
        self.assertEqual(self.data,prior)

    def test_different_history_cannot_reuse_registry(self):
        with self.assertRaises(reviews.FeedbackRegistryError):
            subject.evaluate_bounded_improvement(
                ledger.new_review_history(),self.registry,self.data,
                source_sha256=SHA)

    def test_no_real_world_claims_or_mutations(self):
        x=self.compute()
        for key in ("real_world_effectiveness_verified",
                    "independent_qa_verified",
                    "fixture_source_authentication_proven",
                    "automatic_adoption","automatic_training",
                    "customer_release_authorized"):
            self.assertFalse(x[key])
        self.assertEqual(x["real_user_outcomes_collected"],0)
        self.assertEqual(x["operating_database_writes"],0)
