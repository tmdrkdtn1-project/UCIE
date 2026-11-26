"""B5 synthetic-only comparison schema, safety and aggregation regressions."""
from __future__ import annotations

from unittest import TestCase

from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5


def row(*, token="F01", method="OFFICIAL_DOCS_ONLY",
        cohort="FIRST_TIME_CODER", time_ms=3500, safe=True,
        false_claim=False, evidence=False):
    return {
        "study_id": b5.STUDY_ID,
        "case_id": b5.CASE_ID,
        "anonymous_trial_token": token,
        "method": method,
        "cohort": cohort,
        "first_safe_action_time_ms": time_ms,
        "correct_safe_action": safe,
        "false_version_or_rights_claim": false_claim,
        "evidence_detail_found": evidence,
        "origin": b5.SYNTHETIC_ORIGIN,
    }


class V2B5ComparisonContractTests(TestCase):
    def test_study_protocol_is_not_completed_user_study(self):
        p = b5.build_comparison_protocol()
        self.assertEqual(p["schema"], b5.SCHEMA)
        self.assertEqual(p["comparators"], list(b5.METHODS))
        self.assertEqual(p["real_novice_observed"], 0)
        self.assertEqual(p["real_technical_reviewer_observed"], 0)
        self.assertEqual(p["real_prospective_buyers_observed"], 0)
        self.assertIs(p["actual_human_study_completed"], False)
        self.assertIs(p["actual_business_willingness_observed"], False)
        self.assertIn("NO_CUSTOMER_CODE_LOG_TOKEN_PATH_OR_PII", p["study_restrictions"])

    def test_three_methods_metrics_are_synthetic_not_actual(self):
        values = (
            row(),
            row(token="F02", method="UCIE_V2_REVIEW_ONLY",
                time_ms=750, safe=True, evidence=True),
            row(token="T01", method="GENERAL_TOOL",
                cohort="TECHNICAL_REVIEWER", time_ms=2800, safe=False,
                false_claim=True),
        )
        s = b5.summarize_synthetic_comparison(values)
        self.assertEqual(s["total_synthetic_records"], 3)
        self.assertEqual(s["methods"]["OFFICIAL_DOCS_ONLY"]["synthetic_count"], 1)
        self.assertEqual(s["methods"]["UCIE_V2_REVIEW_ONLY"]
                         ["synthetic_first_action_median_ms"], 750)
        self.assertEqual(s["methods"]["GENERAL_TOOL"]["synthetic_false_claim_count"], 1)
        self.assertIs(s["human_comparison_valid"], False)
        self.assertIs(s["real_baseline_or_competitor_tested"], False)
        self.assertIs(s["customer_willingness_measured"], False)

    def test_no_rows_have_none_not_zero_benchmark(self):
        s = b5.summarize_synthetic_comparison(())
        self.assertEqual(s["total_synthetic_records"], 0)
        self.assertIsNone(s["methods"]["OFFICIAL_DOCS_ONLY"]
                          ["synthetic_first_action_median_ms"])
        self.assertIsNone(s["methods"]["GENERAL_TOOL"]
                          ["synthetic_safe_action_fraction"])

    def test_same_pseudonym_can_compare_distinct_methods(self):
        s = b5.summarize_synthetic_comparison((
            row(token="F01", method="OFFICIAL_DOCS_ONLY"),
            row(token="F01", method="UCIE_V2_REVIEW_ONLY"),
        ))
        self.assertEqual(s["total_synthetic_records"], 2)
        self.assertIs(s["human_comparison_valid"], False)

    def test_duplicate_method_subject_rejected(self):
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison((row(), row()))

    def test_free_form_pii_field_rejected(self):
        v = row()
        v["name"] = "unneeded"
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison((v,))

    def test_missing_field_rejected(self):
        v = row()
        del v["origin"]
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison((v,))

    def test_real_human_or_owner_attestation_cannot_be_self_asserted(self):
        for origin in ("OWNER_AUTHORIZED_HUMAN", "REAL_CUSTOMER",
                       "INDEPENDENTLY_VERIFIED", "OPT_IN"):
            v = row()
            v["origin"] = origin
            with self.subTest(origin=origin):
                with self.assertRaises(b5.B5StudyContractError):
                    b5.summarize_synthetic_comparison((v,))

    def test_arbitrary_real_identity_rejected(self):
        for token in ("Han", "first.user@example.com", "F001", "../F01",
                      "F-01", "", "T00 T01", 100, True):
            v = row(token=token)
            with self.subTest(token=str(token)):
                with self.assertRaises(b5.B5StudyContractError):
                    b5.summarize_synthetic_comparison((v,))

    def test_cohort_and_pseudonym_prefix_must_match(self):
        for token, cohort in (("F01", "TECHNICAL_REVIEWER"),
                              ("T01", "FIRST_TIME_CODER")):
            with self.assertRaises(b5.B5StudyContractError):
                b5.summarize_synthetic_comparison((
                    row(token=token, cohort=cohort),))

    def test_buyer_interviews_not_synthetically_substituted(self):
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison((
                row(cohort="PROSPECTIVE_BUYER"),))

    def test_wrong_case_and_study_id_rejected(self):
        v = row()
        v["case_id"] = "private-project"
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison((v,))
        v = row()
        v["study_id"] = "OTHER_STUDY"
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison((v,))

    def test_unknown_comparison_method_rejected(self):
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison((
                row(method="UNREVIEWED_CLAIMED_TOOL"),))

    def test_strict_boolean_and_time_types(self):
        for field, value in (
            ("first_safe_action_time_ms", False),
            ("first_safe_action_time_ms", -1),
            ("first_safe_action_time_ms", 120001),
            ("first_safe_action_time_ms", 5.5),
            ("correct_safe_action", 1),
            ("false_version_or_rights_claim", 0),
            ("evidence_detail_found", "false"),
        ):
            v = row()
            v[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(b5.B5StudyContractError):
                    b5.summarize_synthetic_comparison((v,))

    def test_bounded_row_number_and_tuple_only(self):
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison([row()])
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison(tuple(row() for _ in range(49)))

    def test_non_object_rejected(self):
        with self.assertRaises(b5.B5StudyContractError):
            b5.summarize_synthetic_comparison(("not a row",))

    def test_synthetic_values_cannot_claim_measured_competitive_advantage(self):
        rows = (
            row(token="F01", method="OFFICIAL_DOCS_ONLY",
                time_ms=1900, safe=False),
            row(token="F01", method="UCIE_V2_REVIEW_ONLY",
                time_ms=10, safe=True, evidence=True),
        )
        r = b5.summarize_synthetic_comparison(rows)
        self.assertEqual(r["methods"]["UCIE_V2_REVIEW_ONLY"]
                         ["synthetic_safe_action_fraction"], 1.0)
        self.assertFalse(r["human_comparison_valid"])
        self.assertFalse(r["real_baseline_or_competitor_tested"])
        self.assertFalse(r["automatic_approval_or_training"])
        self.assertEqual(r["network_requests"], 0)
        self.assertEqual(r["operating_database_writes"], 0)


if __name__ == "__main__":
    import unittest
    unittest.main()
