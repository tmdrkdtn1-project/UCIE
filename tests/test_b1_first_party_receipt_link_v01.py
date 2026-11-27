"""Real first-party synthetic observation receipt, strict source/rights limits."""
import unittest
from unittest.mock import patch

from ucie_miner.b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from ucie_miner.b1_first_party_receipt_link_v01 import (
    FirstPartyReceiptError, run_scoped_receipt, render_receipt_guidance,
)


class FirstPartyReceiptTests(unittest.TestCase):
    def setUp(self):
        self.caps = build_pinned_b1_capsules()
        self.assertEqual(len(self.caps), 2)

    def test_two_pinned_cases_run_actual_bounded_synthetics(self):
        for cap in self.caps:
            with self.subTest(source=cap["source_id"]):
                receipt = run_scoped_receipt(cap["case_id"], cap["source_tag"])
                self.assertEqual(receipt["capsule_id"], cap["capsule_id"])
                self.assertEqual(receipt["capsule_sha256"], cap["content_sha256"])
                self.assertEqual(receipt["observed_scandir_count"], 2)
                self.assertEqual(receipt["observed_git_record_count"], 2)
                self.assertTrue(receipt["trial_executed"])
                self.assertFalse(receipt["case_specific_runtime_trial"])
                self.assertFalse(receipt["actual_runtime_version_verified"])
                self.assertIsNone(receipt["tested_python_or_git_version"])
                self.assertFalse(receipt["independent_qa_verified"])
                self.assertFalse(receipt["rights_approved"])
                self.assertFalse(receipt["release_approved"])
                self.assertEqual(receipt["network_requests"], 0)
                self.assertEqual(receipt["customer_project_reads"], 0)
                self.assertEqual(receipt["operating_database_writes"], 0)
                self.assertIn("자체 예제에서는 확인", render_receipt_guidance(receipt))

    def test_mismatch_stays_hold_without_claiming_runtime_support(self):
        cap = self.caps[0]
        r = run_scoped_receipt(cap["case_id"], "declared-v99")
        self.assertEqual(r["source_revision_decision"], "SOURCE_REVISION_MISMATCH_HOLD")
        self.assertEqual(r["runtime_applicability"], "UNKNOWN_NO_PROOF")
        self.assertFalse(r["b3_retests_executed"])
        # Renderer intentionally requires exact-tag view; mismatched claim is blocked.
        with self.assertRaisesRegex(FirstPartyReceiptError, "JOURNEY_DRIFT"):
            render_receipt_guidance(r)

    def test_unsupported_case_never_calls_trial(self):
        with patch("ucie_miner.b1_first_party_receipt_link_v01.run_first_party_synthetic_comparison") as trial:
            with self.assertRaises(ValueError):
                run_scoped_receipt("FAKE-CASE", None)
            trial.assert_not_called()

    def test_forged_trial_result_fails_closed(self):
        cap = self.caps[0]
        from ucie_miner.skillbook_principle_composer_v01 import run_first_party_synthetic_comparison
        actual = run_first_party_synthetic_comparison()
        for field, value in (
            ("independent_qa_verified", True),
            ("rights_approved", True),
            ("export_allowed", True),
            ("git_parsed_status_entries", 999),
            ("directory_origin", "USER_DIRECTORY"),
            ("network_requests", 1),
        ):
            fake = dict(actual)
            fake[field] = value
            with self.subTest(field=field), patch(
                "ucie_miner.b1_first_party_receipt_link_v01.run_first_party_synthetic_comparison",
                return_value=fake,
            ):
                with self.assertRaisesRegex(FirstPartyReceiptError, "SYNTHETIC_TRIAL_CONTRACT_DRIFT"):
                    run_scoped_receipt(cap["case_id"], cap["source_tag"])

    def test_tampered_receipt_is_not_rendered(self):
        cap = self.caps[0]
        rec = run_scoped_receipt(cap["case_id"], cap["source_tag"])
        for field, value in (
            ("independent_qa_verified", True),
            ("source_document_sha256", "0" * 64),
            ("trial_executed", False),
            ("receipt_sha256", "f" * 64),
            ("observed_git_record_count", 3),
        ):
            fake = {**rec, field: value}
            with self.subTest(field=field), self.assertRaises(FirstPartyReceiptError):
                render_receipt_guidance(fake)

    def test_no_http_or_customer_input_supported(self):
        cap = self.caps[0]
        rec = run_scoped_receipt(cap["case_id"], cap["source_tag"])
        html = render_receipt_guidance(rec)
        self.assertNotIn("<form", html)
        self.assertNotIn("fetch(", html)
        self.assertNotIn("onclick=", html)
        self.assertIn("왜 이렇게 안내하나요?", html)
        self.assertIn("미승인", html)


if __name__ == "__main__":
    unittest.main()
