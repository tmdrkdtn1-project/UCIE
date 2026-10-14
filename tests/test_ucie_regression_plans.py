"""Stage 6 candidate regression plans never execute or approve upstream code."""
from copy import deepcopy
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.patterns import PatternError, group_patterns
from ucie_miner.rule_candidates import candidate_rulepack
from ucie_miner.regression_plans import create_regression_matrix


def candidate(source="python/cpython", pattern="PY_SCANDIR_SHARED_ITERATOR_RACE"):
    rows = [{"source": source, "pr_number": 42, "canonical_pr_number": 42,
             "pattern_code": pattern,
             "evidence_sha256": hashlib.sha256(b"synthetic").hexdigest(),
             "status": "UNVERIFIED_CANDIDATE_ONLY"}]
    return candidate_rulepack(group_patterns(rows))


class RegressionPlanTests(unittest.TestCase):
    def test_nonexecuting_plan_remains_unverified(self):
        pack = candidate()
        result = create_regression_matrix(pack)
        self.assertEqual(result["candidate_count"], 1)
        self.assertFalse(result["upstream_code_executed"])
        self.assertEqual(result["regressions_independently_reproduced"], 0)
        self.assertFalse(result["rulepack_signed"])
        self.assertEqual(result["persistent_writes"], 0)
        case = result["cases"][0]
        self.assertIsNone(case["independent_test_script"])
        self.assertEqual(case["actual_test_result"], "NOT_EXECUTED")

    def test_forged_regression_pass_fails(self):
        pack = candidate()
        pack["proposals"][0]["required_gates"]["independent_regression_passed"] = "PASS"
        with self.assertRaises(PatternError):
            create_regression_matrix(pack)

    def test_injected_executable_command_rejected(self):
        pack = candidate()
        pack["proposals"][0]["executable_command"] = "unapproved"
        with self.assertRaises(PatternError):
            create_regression_matrix(pack)

    def test_modified_digest_is_rejected(self):
        pack = candidate()
        pack["digest_sha256"] = "0" * 64
        with self.assertRaises(PatternError):
            create_regression_matrix(pack)

    def test_wrong_source_for_pattern_rejected(self):
        pack = candidate(source="PowerShell/PowerShell")
        with self.assertRaises(PatternError):
            create_regression_matrix(pack)

    def test_invalid_template_is_rejected(self):
        pack = candidate(pattern="API_CONTRACT")
        with self.assertRaises(PatternError):
            create_regression_matrix(pack)

    def test_reproducible_output(self):
        p = candidate()
        self.assertEqual(create_regression_matrix(p),
                         create_regression_matrix(deepcopy(p)))


if __name__ == "__main__":
    unittest.main()
