"""B1 source revision truth gate: explicit holds, no runtime or rights overclaims."""
import unittest
from unittest.mock import patch

from ucie_miner.b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from ucie_miner.b1_version_truth_gate_v01 import (
    B1TruthGateError, evaluate_b1_source_revision,
)


class B1SourceVersionTruthTests(unittest.TestCase):
    def setUp(self):
        self.capsules = build_pinned_b1_capsules()
        self.assertEqual(len(self.capsules), 2)

    def test_exact_source_revision_is_not_runtime_pass(self):
        for cap in self.capsules:
            with self.subTest(case=cap["case_id"]):
                value = evaluate_b1_source_revision(cap["case_id"], cap["source_tag"])
                self.assertEqual(value["source_revision_decision"], "UNKNOWN_NO_PROOF")
                self.assertTrue(value["source_revision_match_only"])
                self.assertEqual(value["runtime_version_applicability"], "UNKNOWN_NO_PROOF")
                self.assertIsNone(value["first_party_runtime_receipt"])
                self.assertFalse(value["release_approved"])
                self.assertFalse(value["export_allowed"])
                self.assertEqual(value["capsule_id"], cap["capsule_id"])
                self.assertEqual(value["capsule_sha256"], cap["content_sha256"])

    def test_unknown_source_revision_holds(self):
        for cap in self.capsules:
            row = evaluate_b1_source_revision(cap["case_id"], None)
            self.assertFalse(row["source_revision_match_only"])
            self.assertEqual(row["source_revision_decision"], "UNKNOWN_NO_PROOF")
            self.assertIn("확인되지", row["human_next_step"])

    def test_declared_mismatch_holds_without_revision_fetch(self):
        for cap in self.capsules:
            other = "unverified-v99"
            row = evaluate_b1_source_revision(cap["case_id"], other)
            self.assertEqual(row["source_revision_decision"],
                             "SOURCE_REVISION_MISMATCH_HOLD")
            self.assertEqual(row["runtime_version_applicability"], "UNKNOWN_NO_PROOF")
            self.assertEqual(row["source_fetches"], 0)
            self.assertEqual(row["test_execution"], "NOT_RUN")

    def test_unknown_or_wrong_type_rejected(self):
        case = self.capsules[0]["case_id"]
        for invalid_case in ("invalid", "", 123, None, ["bad"]):
            with self.subTest(invalid_case=repr(invalid_case)):
                with self.assertRaises(B1TruthGateError):
                    evaluate_b1_source_revision(invalid_case, None)
        for invalid_tag in ("", "v1/branch", "a" * 65, 1, True, {}):
            with self.subTest(invalid_tag=repr(invalid_tag)):
                with self.assertRaises(B1TruthGateError):
                    evaluate_b1_source_revision(case, invalid_tag)

    def test_forged_rights_and_qa_status_fail_closed(self):
        cap = dict(self.capsules[0])
        for field, bad in (("rights_approved", True),
                           ("independent_qa_verified", True),
                           ("export_allowed", True),
                           ("owner_approved", True),
                           ("upstream_authenticity", "ATTESTED")):
            forged = {**cap, field: bad}
            with self.subTest(field=field):
                with patch("ucie_miner.b1_version_truth_gate_v01.build_pinned_b1_capsules",
                           return_value=(forged, self.capsules[1])):
                    with self.assertRaisesRegex(B1TruthGateError,
                                                "SOURCE_RIGHTS_OR_PROOF_STATUS_DRIFT"):
                        evaluate_b1_source_revision(cap["case_id"], cap["source_tag"])

    def test_stable_receipt_and_no_mutation(self):
        case, tag = self.capsules[0]["case_id"], self.capsules[0]["source_tag"]
        one = evaluate_b1_source_revision(case, tag)
        self.assertEqual(one, evaluate_b1_source_revision(case, tag))
        self.assertEqual(one["customer_project_reads"], 0)
        self.assertEqual(one["operating_database_writes"], 0)


if __name__ == "__main__":
    unittest.main()
