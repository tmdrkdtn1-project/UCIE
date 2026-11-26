"""Per-candidate UCIE synthetic review ranking: avoid shared metric leakage."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_candidate_evidence_priority_v01 as ranking
from ucie_miner import ucie_v2_feedback_registry_v01 as feedback
from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as originals
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3

SHA = "a" * 64


def study(method):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 900,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


def fixture(key, truth, base, new):
    return {"case_id": key, "ground_truth": truth,
            "baseline_prediction": base, "challenger_prediction": new,
            "origin": ranking.ORIGIN, "source_sha256": SHA}


class CandidateEvidencePriorityTests(TestCase):
    @classmethod
    def setUpClass(cls):
        original = originals.assemble_original_library_assets(
            tuple(study(x) for x in b5.METHODS), ())
        cls.h = ledger.append_review_bundle(ledger.new_review_history(), original)
        cls.registry = feedback.append_feedback_evidence(
            cls.h, feedback.empty_feedback_registry(cls.h),
            execute_synthetic=True)
        cls.ids = [x["candidate_id"] for x in feedback.prioritize_review_experiments(
            cls.h, cls.registry)["priority_queue"]]

    def cases(self, prefix, *, regression=False):
        rows = []
        for n in range(8):
            truth = "RISK" if n < 4 else "SAFE"
            base = truth if n != 0 else ("SAFE" if truth == "RISK" else "RISK")
            new = truth
            if regression and n == 1:
                new = "SAFE"
            rows.append(fixture(f"{prefix}_{n}", truth, base, new))
        return rows

    def evaluate(self, mapping=None):
        return ranking.prioritize_candidate_evidence(
            self.h, self.registry,
            {self.ids[0]: self.cases("x"),
             self.ids[1]: self.cases("y", regression=True)}
            if mapping is None else mapping,
            fixture_sha256=SHA)

    def test_per_candidate_regression_is_top_priority(self):
        result = self.evaluate()
        self.assertEqual(result["ranked_candidates"][0]["priority"], 1)
        self.assertEqual(result["ranked_candidates"][0]["paired_regressed"], 1)
        self.assertEqual(result["ranked_candidates"][0]["verdict"],
                         "REVISE_SYNTHETIC_REGRESSION")
        self.assertEqual(result["total_synthetic_cases"], 16)

    def test_other_candidate_can_remain_review_only(self):
        r = self.evaluate()
        other = next(x for x in r["ranked_candidates"] if x["priority"] == 3)
        self.assertEqual(other["verdict"], "REVIEW_SYNTHETIC_GAIN_NOT_PROVEN")
        self.assertFalse(other["rule_approved"])

    def test_missing_candidate_is_explicit_hold(self):
        r = self.evaluate({self.ids[0]: self.cases("a")})
        absent = next(x for x in r["ranked_candidates"] if x["paired_case_count"] == 0)
        self.assertEqual(absent["verdict"], "HOLD_INADEQUATE_SYNTHETIC_CONTROLS")

    def test_zero_cases_not_a_success(self):
        r = self.evaluate({})
        self.assertTrue(all(x["priority"] == 2 for x in r["ranked_candidates"]))
        self.assertTrue(all(x["false_positive_rate_delta"] is None
                            for x in r["ranked_candidates"]))

    def test_imbalanced_controls_hold(self):
        rows = [fixture(f"a{n}", "RISK", "RISK", "RISK") for n in range(8)]
        r = self.evaluate({self.ids[0]: rows})
        inspected = next(x for x in r["ranked_candidates"]
                         if x["candidate_id"] == self.ids[0])
        self.assertEqual(inspected["verdict"],
                         "HOLD_INADEQUATE_SYNTHETIC_CONTROLS")

    def test_cross_candidate_case_reuse_denied(self):
        sample = self.cases("duplicate")
        with self.assertRaises(ranking.CandidatePriorityError):
            self.evaluate({self.ids[0]: sample, self.ids[1]: sample})

    def test_unknown_candidate_denied(self):
        with self.assertRaises(ranking.CandidatePriorityError):
            self.evaluate({"forged": self.cases("a")})

    def test_private_extra_field_denied(self):
        row = self.cases("a")
        row[0]["email"] = "private@example.invalid"
        with self.assertRaises(ValueError):
            self.evaluate({self.ids[0]: row})

    def test_source_pin_mismatch_denied(self):
        row = self.cases("a")
        row[0]["source_sha256"] = "b"*64
        with self.assertRaises(ValueError):
            self.evaluate({self.ids[0]: row})

    def test_excessive_total_cases_denied(self):
        excessive = self.cases("a") * 17
        with self.assertRaises(ranking.CandidatePriorityError):
            self.evaluate({self.ids[0]: excessive})

    def test_deterministic_and_no_input_mutation(self):
        inputs = {self.ids[0]: self.cases("a"), self.ids[1]: self.cases("b")}
        before = deepcopy(inputs)
        a = self.evaluate(inputs)
        self.assertEqual(a, self.evaluate(inputs))
        self.assertEqual(inputs, before)
        self.assertEqual(a["content_sha256"],
                         ranking._digest({k:v for k,v in a.items()
                                          if k != "content_sha256"}))

    def test_no_user_or_approval_claim(self):
        r = self.evaluate()
        for key in ("fixture_source_authenticated",
                    "real_user_improvement_verified",
                    "independent_qa_verified", "rights_approved",
                    "automatic_promotion", "tests_scheduled"):
            self.assertFalse(r[key])
        self.assertEqual(r["network_requests"], 0)
        self.assertEqual(r["operating_database_writes"], 0)

    def test_historical_source_change_stays_hold(self):
        changed = originals.assemble_original_library_assets(
            tuple(study(x) for x in b5.METHODS), ({
                "source_id": "doc:git/git", "previous_pin": b3.PINS["doc:git/git"],
                "candidate_pin": "f"*len(b3.PINS["doc:git/git"]),
            },))
        h = ledger.append_review_bundle(
            ledger.new_review_history(), changed)
        reg = feedback.append_feedback_evidence(
            h, feedback.empty_feedback_registry(h), execute_synthetic=True)
        ids = [x["candidate_id"] for x in feedback.prioritize_review_experiments(
            h,reg)["priority_queue"]]
        result = ranking.prioritize_candidate_evidence(
            h, reg, {ids[0]: self.cases("a"), ids[1]: self.cases("b")},
            fixture_sha256=SHA)
        self.assertTrue(all(x["verdict"] == "HOLD_UNRESOLVED_UPSTREAM"
                            for x in result["ranked_candidates"]))
