"""Stage 8 side-effect-free acceptance test fixture."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.operational_acceptance import REQUIRED, operational_acceptance


class Stage8Tests(unittest.TestCase):
    def test_missing_approval_no_go(self):
        evidence = dict.fromkeys(REQUIRED, True)
        evidence["stage7_independent_approval"] = False
        result = operational_acceptance(evidence)
        self.assertEqual(result["status"], "NO_GO")
        self.assertFalse(result["scheduler_registered"])
        self.assertFalse(result["package_published"])

    def test_even_positive_self_report_is_not_approval(self):
        result = operational_acceptance(dict.fromkeys(REQUIRED, True))
        self.assertEqual(result["status"], "READY_FOR_MANUAL_REVIEW")
        self.assertTrue(result["checks_claimed_by_caller_not_reverified"])
        self.assertFalse(result["production_approved"])

    def test_missing_gate_fails_closed(self):
        with self.assertRaises(ValueError):
            operational_acceptance({})

    def test_string_pass_disallowed(self):
        evidence = dict.fromkeys(REQUIRED, True)
        evidence["source_scope_reviewed"] = "PASS"
        with self.assertRaises(ValueError):
            operational_acceptance(evidence)


if __name__ == "__main__":
    unittest.main()
