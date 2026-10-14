"""UCIE pattern-safe-call guidance remains candidate-only, never executable."""
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.patterns import group_patterns
from ucie_miner.rule_candidates import GUIDANCE, candidate_rulepack, approval_gate


class SafeCallGuidanceTests(unittest.TestCase):
    def test_observed_failures_have_explicit_safe_call_guidance(self):
        self.assertIn("single owned lock",
                      GUIDANCE["PY_SCANDIR_SHARED_ITERATOR_RACE"][0])
        self.assertIn("CommandType",
                      GUIDANCE["PS_FUZZY_GET_COMMAND_DUPLICATES"][0])
        self.assertIn("GetRelativePath",
                      GUIDANCE["PS_RESOLVE_PATH_DOT_PREFIX"][0])

    def test_safe_call_candidate_cannot_be_executed_or_promoted(self):
        record = {
            "source": "python/cpython", "pr_number": 153462,
            "canonical_pr_number": 153462,
            "pattern_code": "PY_SCANDIR_SHARED_ITERATOR_RACE",
            "evidence_sha256": hashlib.sha256(b"synthetic").hexdigest(),
            "status": "UNVERIFIED_CANDIDATE_ONLY",
        }
        pack = candidate_rulepack(group_patterns([record]))
        item = pack["proposals"][0]
        self.assertIsNone(item["executable_command"])
        self.assertIn("serialize every next()", item["safe_fix_guidance"])
        self.assertTrue(all(x == "NOT_VERIFIED"
                            for x in item["required_gates"].values()))
        self.assertFalse(pack["signed"])
        self.assertFalse(pack["approval"])
        self.assertFalse(approval_gate(pack)["deploy_allowed"])


if __name__ == "__main__":
    unittest.main()
