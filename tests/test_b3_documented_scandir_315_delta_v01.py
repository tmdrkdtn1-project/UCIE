"""UCIE B3 documented upstream delta: actual docs != customer-runtime proof."""
import unittest

from ucie_miner.b3_documented_scandir_315_delta_v01 import (
    DocumentedDeltaError, GIT_CASE, PYTHON_CASE,
    evaluate_documented_scandir_delta,
)


class DocumentedScandirDeltaTests(unittest.TestCase):
    def test_exact_documented_python_315_changed_callsite_holds(self):
        x = evaluate_documented_scandir_delta(
            PYTHON_CASE, proposed_runtime="3.15", uses_negative_one=True)
        self.assertEqual(x["affected_source_ids"], ["doc:python/cpython"])
        self.assertEqual(x["recommendation"],
                         "REVIEW_NEGATIVE_FD_CALLSITE_BEFORE_UPGRADE")
        self.assertTrue(x["retest_candidate"])
        self.assertFalse(x["retest_executed"])
        self.assertFalse(x["documentation_content_sha256_attested"])
        self.assertFalse(x["customer_runtime_version_verified"])
        self.assertFalse(x["rights_approved"])

    def test_git_does_not_retest_for_unrelated_python_doc_delta(self):
        git = evaluate_documented_scandir_delta(
            GIT_CASE, proposed_runtime="3.15", uses_negative_one=True)
        self.assertEqual(git["affected_source_ids"], [])
        self.assertFalse(git["retest_candidate"])
        self.assertEqual(git["recommendation"], "NO_RETEST_FROM_THIS_DELTA")

    def test_unknown_callsite_not_promoted(self):
        x = evaluate_documented_scandir_delta(
            PYTHON_CASE, proposed_runtime="3.15")
        self.assertEqual(x["recommendation"], "CHECK_CALLSITE_FIRST_NO_EXECUTION")
        self.assertEqual(x["callsite_analysis_status"], "UNKNOWN_NO_PROOF")
        self.assertFalse(x["retest_candidate"])

    def test_declared_safe_callsite_not_affected_code_claim(self):
        x = evaluate_documented_scandir_delta(
            PYTHON_CASE, proposed_runtime="3.15", uses_negative_one=False)
        self.assertFalse(x["retest_candidate"])
        self.assertEqual(x["recommendation"],
                         "NO_NEGATIVE_FD_RISK_DECLARED_OR_VERSION_UNKNOWN")
        self.assertEqual(x["callsite_analysis_status"],
                         "DECLARED_NOT_INDEPENDENTLY_VERIFIED")

    def test_other_version_and_missing_version_never_claim_runtime_pass(self):
        for version in ("3.14", None):
            with self.subTest(version=version):
                x = evaluate_documented_scandir_delta(
                    PYTHON_CASE, proposed_runtime=version,
                    uses_negative_one=True)
                self.assertFalse(x["retest_candidate"])
                self.assertFalse(x["customer_runtime_version_verified"])

    def test_invalid_cases_versions_and_untrusted_types_fail_closed(self):
        for kwargs in (
            {"case_id": "UCIE-SKILLBOOK-OTHER"},
            {"case_id": PYTHON_CASE, "proposed_runtime": "3.16"},
            {"case_id": PYTHON_CASE, "proposed_runtime": "3.15.0+arbitrary"},
            {"case_id": PYTHON_CASE, "proposed_runtime": 3.15},
            {"case_id": PYTHON_CASE, "uses_negative_one": "true"},
            {"case_id": PYTHON_CASE, "uses_negative_one": 1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(
                DocumentedDeltaError):
                evaluate_documented_scandir_delta(**kwargs)

    def test_exact_receipt_deterministic_and_separate_rights(self):
        a = evaluate_documented_scandir_delta(
            PYTHON_CASE, proposed_runtime="3.15", uses_negative_one=True)
        b = evaluate_documented_scandir_delta(
            PYTHON_CASE, proposed_runtime="3.15", uses_negative_one=True)
        self.assertEqual(a, b)
        self.assertEqual(len(a["proposal_sha256"]), 64)
        self.assertEqual(a["retest_status"], "NOT_RUN")
        self.assertEqual(a["network_fetches_at_runtime"], 0)
        self.assertEqual(a["operating_database_writes"], 0)
        self.assertFalse(a["owner_approved"])


if __name__ == "__main__":
    unittest.main()
