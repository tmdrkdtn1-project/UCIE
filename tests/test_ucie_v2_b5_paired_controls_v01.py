"""Bounded B5 paired-control contract, original synthetic-only cases."""
from unittest import TestCase
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as original
from ucie_miner import ucie_v2_b5_paired_controls_v01 as paired


def row(token="F01", method="OFFICIAL_DOCS_ONLY", ms=1200, safe=True, false=False):
    return {"study_id": original.STUDY_ID, "case_id": original.CASE_ID,
            "anonymous_trial_token": token, "method": method,
            "cohort": "FIRST_TIME_CODER" if token.startswith("F") else "TECHNICAL_REVIEWER",
            "first_safe_action_time_ms": ms, "correct_safe_action": safe,
            "false_version_or_rights_claim": false, "evidence_detail_found": False,
            "origin": original.SYNTHETIC_ORIGIN}


class PairedTests(TestCase):
    def test_full_paired_synthetic_only(self):
        rows = (row(ms=1200), row(method="GENERAL_TOOL", ms=800),
                row(method="UCIE_V2_REVIEW_ONLY", ms=600))
        result = paired.assess_synthetic_pairs(rows)
        self.assertEqual(result["paired_synthetic_subjects"], 1)
        self.assertEqual(result["comparison"]["OFFICIAL_DOCS_ONLY"]["synthetic_median_baseline_minus_ucie_ms"], 600)
        self.assertFalse(result["human_evidence_valid"])
        self.assertFalse(result["competitor_advantage_verified"])
        self.assertFalse(result["customer_release_authorized"])

    def test_missing_comparator_holds(self):
        result = paired.assess_synthetic_pairs((row(), row(method="UCIE_V2_REVIEW_ONLY")))
        self.assertEqual(result["status"], "SYNTHETIC_COMPARISON_INCOMPLETE_HOLD")
        self.assertIn("GENERAL_TOOL", result["missing_method_subjects"]["F01"])
        self.assertIsNone(result["comparison"])

    def test_empty_never_claims_complete_human(self):
        result = paired.assess_synthetic_pairs(())
        self.assertEqual(result["paired_synthetic_subjects"], 0)
        self.assertEqual(result["status"], "SYNTHETIC_COMPARISON_EMPTY_HOLD")
        self.assertIsNone(result["comparison"])
        self.assertFalse(result["human_evidence_valid"])

    def test_duplicate_subject_method_fails_closed(self):
        with self.assertRaises(original.B5StudyContractError):
            paired.assess_synthetic_pairs((row(), row()))

    def test_untrusted_real_human_origin_refused(self):
        bad = row()
        bad["origin"] = "REAL_HUMAN"
        with self.assertRaises(original.B5StudyContractError):
            paired.assess_synthetic_pairs((bad,))

    def test_pii_extra_field_refused(self):
        bad = row()
        bad["email"] = "example@example.invalid"
        with self.assertRaises(original.B5StudyContractError):
            paired.assess_synthetic_pairs((bad,))

    def test_false_confidence_in_target_is_explicit(self):
        rows = (row(), row(method="GENERAL_TOOL"),
                row(method="UCIE_V2_REVIEW_ONLY", safe=False, false=True))
        result = paired.assess_synthetic_pairs(rows)
        self.assertEqual(len(result["synthetic_safety_regressions"]), 4)

    def test_inconsistent_cohort_token_denied_by_original_contract(self):
        bad = row()
        bad["cohort"] = "TECHNICAL_REVIEWER"
        with self.assertRaises(original.B5StudyContractError):
            paired.assess_synthetic_pairs((bad,))

    def test_two_subjects_and_three_arms(self):
        values = tuple(row(t, m, 1000 if m == "UCIE_V2_REVIEW_ONLY" else 1500)
                       for t in ("F01", "T01") for m in original.METHODS)
        out = paired.assess_synthetic_pairs(values)
        self.assertEqual(out["paired_synthetic_subjects"], 2)
        self.assertEqual(out["comparison"]["GENERAL_TOOL"]["paired_synthetic_count"], 2)

    def test_unsupplied_competitor_is_not_real_performance_evidence(self):
        values = tuple(row("F01", m, 1 if m == "UCIE_V2_REVIEW_ONLY" else 120000)
                       for m in original.METHODS)
        out = paired.assess_synthetic_pairs(values)
        self.assertFalse(out["competitor_advantage_verified"])
        self.assertFalse(out["human_evidence_valid"])
