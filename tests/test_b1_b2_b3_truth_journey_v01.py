"""B1-B2-B3 isolated first-party journey: one identity, no overclaims."""
import unittest
from unittest.mock import patch

from ucie_miner.b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from ucie_miner.b1_b2_b3_truth_journey_v01 import (
    TruthJourneyError, build_truth_journey, render_truth_journey,
)
from ucie_miner.b1_version_truth_gate_v01 import B1TruthGateError


class UCIETruthJourneyTests(unittest.TestCase):
    def setUp(self):
        self.caps = build_pinned_b1_capsules()
        self.assertEqual(len(self.caps), 2)

    def test_two_known_cases_have_exact_capsule_identity(self):
        for c in self.caps:
            with self.subTest(source=c["source_id"]):
                r = build_truth_journey(c["case_id"], c["source_tag"])
                self.assertEqual(r["case_id"], c["case_id"])
                self.assertEqual(r["capsule_id"], c["capsule_id"])
                self.assertEqual(r["capsule_sha256"], c["content_sha256"])
                self.assertEqual(r["source_document_sha256"], c["source_document_sha256"])
                self.assertEqual(r["runtime_version_applicability"], "UNKNOWN_NO_PROOF")
                self.assertFalse(r["rights_approved"])
                self.assertFalse(r["b3_retest_executed"])
                self.assertEqual(r["b3_retest_proposal_count"], 0)

    def test_unknown_version_not_treated_as_revision(self):
        for c in self.caps:
            result = build_truth_journey(c["case_id"], None)
            self.assertEqual(result["source_revision_decision"], "UNKNOWN_NO_PROOF")
            self.assertEqual(result["b3_retest_proposal_count"], 0)
            self.assertFalse(result["b3_revision_authenticated"])

    def test_mismatched_tag_proposes_only_one_retest(self):
        for c in self.caps:
            result = build_truth_journey(c["case_id"], "unknown-v99")
            self.assertEqual(result["source_revision_decision"],
                             "SOURCE_REVISION_MISMATCH_HOLD")
            self.assertEqual(result["b3_retest_proposal_count"], 1)
            self.assertFalse(result["b3_revision_authenticated"])
            self.assertFalse(result["b3_retest_executed"])
            self.assertFalse(result["export_allowed"])

    def test_render_safe_plain_korean_and_optional_proof(self):
        for c in self.caps:
            html = render_truth_journey(c["case_id"], "unknown-v99")
            self.assertIn("어떤 도움이 필요하세요?", html)
            self.assertIn("지금 확인해 볼 일", html)
            self.assertIn("왜 이렇게 안내하나요?", html)
            self.assertIn(c["capsule_id"], html)
            self.assertIn(c["source_document_sha256"], html)
            self.assertNotIn("<form", html)
            self.assertNotIn("fetch(", html)
            self.assertNotIn("onclick=", html)
            self.assertNotIn("고쳐졌습니다", html)

    def test_invalid_case_and_injected_tag_fail(self):
        with self.assertRaises(B1TruthGateError):
            build_truth_journey("not-a-real-case", None)
        c = self.caps[0]
        for tag in ("<script>", "v1/branch", "x" * 65, True):
            with self.subTest(tag=repr(tag)):
                with self.assertRaises(B1TruthGateError):
                    build_truth_journey(c["case_id"], tag)

    def test_forged_join_refused(self):
        c = self.caps[0]
        good = build_truth_journey(c["case_id"], None)
        self.assertEqual(good["operating_database_writes"], 0)
        self.assertEqual(good["network_requests"], 0)
        with patch("ucie_miner.b1_b2_b3_truth_journey_v01.build_b4_capsule_journey",
                   return_value={"case_id": c["case_id"], "capsule_id": "FAKE",
                                 "capsule_sha256": c["content_sha256"],
                                 "source_id": c["source_id"]}):
            with self.assertRaisesRegex(TruthJourneyError, "CASE_CAPSULE_PROOF_DRIFT"):
                build_truth_journey(c["case_id"], None)

    def test_idempotent_receipt_no_new_routes(self):
        c = self.caps[0]
        a = build_truth_journey(c["case_id"])
        self.assertEqual(a, build_truth_journey(c["case_id"]))
        self.assertFalse(a["first_use_routes_modified"])
        self.assertFalse(a["new_local_route_registered"])
        self.assertFalse(a["customer_code_executed"])
        self.assertEqual(set(a["first_use_destinations"]), {"solve", "try", "learn"})


if __name__ == "__main__":
    unittest.main()
