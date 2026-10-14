"""Stage 6/7 fail-closed offline candidate and approval tests."""
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.patterns import PatternError, group_patterns
from ucie_miner.rule_candidates import candidate_rulepack, approval_gate


class CandidateRulepackTests(unittest.TestCase):
    def preview(self):
        row = {"source": "python/cpython", "pr_number": 42,
               "canonical_pr_number": 42, "pattern_code": "API_CONTRACT",
               "evidence_sha256": hashlib.sha256(b"synthetic").hexdigest(),
               "status": "UNVERIFIED_CANDIDATE_ONLY"}
        return group_patterns([row])

    def test_rulepack_never_signs_or_executes(self):
        rulepack = candidate_rulepack(self.preview())
        self.assertEqual(len(rulepack["proposals"]), 1)
        self.assertIsNone(rulepack["proposals"][0]["executable_command"])
        self.assertFalse(rulepack["signed"])
        self.assertFalse(rulepack["published"])
        self.assertFalse(rulepack["approval"])
        self.assertEqual(rulepack["regressions_executed"], 0)
        self.assertFalse(approval_gate(rulepack)["deploy_allowed"])

    def test_unknown_rule_template_denied(self):
        row = self.preview()
        row["families"][0]["pattern_code"] = "UNSAFE_UNKNOWN_PATTERN"
        with self.assertRaises(PatternError):
            candidate_rulepack(row)

    def test_forged_approval_denied(self):
        rulepack = candidate_rulepack(self.preview())
        rulepack["approval"] = True
        with self.assertRaises(PatternError):
            approval_gate(rulepack)

    def test_wrong_stage5_schema_denied(self):
        row = self.preview()
        row["persistent_writes"] = 1
        with self.assertRaises(PatternError):
            candidate_rulepack(row)


if __name__ == "__main__":
    unittest.main()
