"""B2 human evidence display: optional first-party proof and negative controls."""
import unittest

from ucie_miner.b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from ucie_miner.b1_first_party_receipt_link_v01 import run_scoped_receipt
from ucie_miner.b2_receipt_truth_view_v01 import (
    ReceiptTruthViewError, render_b2_receipt_truth_view,
)


class B2ReceiptTruthViewTests(unittest.TestCase):
    def setUp(self):
        self.caps = build_pinned_b1_capsules()

    def test_no_receipt_never_fabricates_a_pass(self):
        for c in self.caps:
            with self.subTest(source=c["source_id"]):
                html = render_b2_receipt_truth_view(c["case_id"])
                self.assertIn("자체 시험 기록이 연결되지 않았", html)
                self.assertIn("품질 검증은 미완료", html)
                self.assertIn("사용권 승인은 완료되지 않았", html)
                self.assertNotIn("UCIE가 만든 예제에서는 확인했습니다", html)
                self.assertNotIn("<form", html)

    def test_optional_actual_synthetic_receipt_has_same_capsule(self):
        for c in self.caps:
            with self.subTest(source=c["source_id"]):
                rec = run_scoped_receipt(c["case_id"], c["source_tag"])
                html = render_b2_receipt_truth_view(
                    c["case_id"], source_tag=c["source_tag"], receipt=rec)
                self.assertIn("UCIE가 만든 예제에서는 확인했습니다", html)
                self.assertIn(c["capsule_id"], html)
                self.assertIn(rec["receipt_sha256"], html)
                self.assertIn("현재 사용 중인 프로그램 버전에서 작동하는지는 미확인", html)
                self.assertNotIn("고객의 문제가 해결", html)
                self.assertNotIn("onclick=", html)
                self.assertNotIn("fetch(", html)

    def test_foreign_capsule_receipt_refused(self):
        left, right = self.caps
        rec = run_scoped_receipt(left["case_id"], left["source_tag"])
        with self.assertRaisesRegex(ReceiptTruthViewError, "RECEIPT_CASE_OR_VERSION_MISMATCH"):
            render_b2_receipt_truth_view(right["case_id"],
                                         source_tag=right["source_tag"],
                                         receipt=rec)

    def test_forged_observation_or_rights_refused(self):
        c = self.caps[0]
        receipt = run_scoped_receipt(c["case_id"], c["source_tag"])
        for key, value in [
            ("independent_qa_verified", True),
            ("rights_approved", True),
            ("source_document_sha256", "0" * 64),
            ("receipt_sha256", "0" * 64),
            ("trial_executed", False),
        ]:
            with self.subTest(key=key):
                altered = {**receipt, key: value}
                with self.assertRaises(ReceiptTruthViewError):
                    render_b2_receipt_truth_view(
                        c["case_id"], source_tag=c["source_tag"], receipt=altered)

    def test_mismatched_version_stays_hold(self):
        c = self.caps[0]
        html = render_b2_receipt_truth_view(c["case_id"], source_tag="declared-v99")
        self.assertIn("실제 공식 변경은 확인하지 않았습니다", html)
        self.assertIn("출처 버전이 달라", html)
        self.assertIn("현재 사용 중인 프로그램 버전에서 작동하는지는 미확인", html)

    def test_invalid_receipt_type_blocked(self):
        c = self.caps[0]
        for val in ([], "fake", True):
            with self.subTest(value=repr(val)):
                with self.assertRaisesRegex(ReceiptTruthViewError, "INVALID_RECEIPT"):
                    render_b2_receipt_truth_view(c["case_id"], receipt=val)

    def test_render_does_not_execute_trial_implicitly(self):
        c = self.caps[0]
        from unittest.mock import patch
        with patch("ucie_miner.b1_first_party_receipt_link_v01.run_scoped_receipt",
                   side_effect=AssertionError("should not run")):
            html = render_b2_receipt_truth_view(c["case_id"])
            self.assertIn("자체 시험 기록이 연결되지 않았", html)


if __name__ == "__main__":
    unittest.main()
