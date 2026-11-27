"""UCIE B4 source-pinned static transfer contract: positive and negative cases."""
import unittest
from copy import deepcopy

from ucie_miner.b4_transfer_boundary_v01 import (
    SCHEMA, TransferBoundaryError, build_transfer_hypothesis,
    evaluate_transfer_case,
)


def example(case_id="UCIE_PY_POSITIVE_001", technology="BOUNDED_SCANDIR"):
    return {
        "case_id": case_id, "technology": technology,
        "caller_authorized": True, "bounded_input": True,
        "fail_closed": True, "disclosure_documented": True,
        "evidence_pinned": True,
    }


class TestB4Transfer(unittest.TestCase):
    def test_hypothesis_lineage_and_no_release(self):
        a, b = build_transfer_hypothesis(), build_transfer_hypothesis()
        self.assertEqual(a, b)
        self.assertEqual(a["schema"], SCHEMA)
        self.assertEqual(a["status"], "REVIEW_ONLY_UNVERIFIED")
        self.assertEqual(len(a["parent_source_refs"]), 2)
        self.assertEqual({x["source_id"] for x in a["parent_source_refs"]},
                         {"doc:python/cpython", "doc:git/git"})
        for key in ("rights_approved", "independent_qa_verified",
                    "owner_approved", "export_allowed", "automatic_promotion"):
            self.assertIs(a[key], False)

    def test_valid_scandir_and_git_only_candidate(self):
        for tech in ("BOUNDED_SCANDIR", "BOUNDED_GIT_PORCELAIN"):
            with self.subTest(technology=tech):
                out = evaluate_transfer_case(example(technology=tech))
                self.assertEqual(out["decision"], "CANDIDATE_WITHIN_TESTED_BOUNDARY")
                self.assertIs(out["release_approved"], False)

    def test_missing_each_required_gate_rejects(self):
        for field in ("caller_authorized", "bounded_input", "fail_closed",
                      "disclosure_documented", "evidence_pinned"):
            with self.subTest(gate=field):
                case = example()
                case[field] = False
                self.assertEqual(evaluate_transfer_case(case)["decision"], "REJECT")

    def test_third_held_out_synthetic_counterexample_rejects(self):
        case = example("UCIE_SYNTHETIC_UNBOUNDED_001",
                       "SYNTHETIC_UNBOUNDED_SERVICE_ENUMERATION")
        self.assertEqual(evaluate_transfer_case(case)["reason"],
                         "UNSUPPORTED_TECHNOLOGY_OR_SYNTHETIC_TRANSFER")

    def test_unauthorized_technology_with_all_other_gates_rejects(self):
        case = example(technology="BOUNDED_UNKNOWN_TECH")
        self.assertEqual(evaluate_transfer_case(case)["decision"], "REJECT")

    def test_no_dynamic_extra_claims(self):
        case = example()
        case["approved"] = True
        with self.assertRaises(TransferBoundaryError):
            evaluate_transfer_case(case)

    def test_reject_non_boolean_gate(self):
        case = example()
        case["bounded_input"] = 1
        with self.assertRaisesRegex(TransferBoundaryError, "NON_BOOLEAN_GATE"):
            evaluate_transfer_case(case)

    def test_reject_untrusted_case_identifier(self):
        case = example(case_id="../../owner")
        with self.assertRaisesRegex(TransferBoundaryError, "INVALID_CASE_ID"):
            evaluate_transfer_case(case)


if __name__ == "__main__":
    unittest.main()
