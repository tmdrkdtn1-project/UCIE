"""Synthetic-only Stage 6-8 external before/after claim validation tests.

Tests never fetch, checkout, import or execute untrusted upstream code.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.patterns import PatternError, group_patterns
from ucie_miner.rule_candidates import candidate_rulepack
from ucie_miner.regression_plans import create_regression_matrix
from ucie_miner.regression_receipts import inspect_regression_claims


def sha(value):
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def fixtures(source="python/cpython", code="PY_SCANDIR_SHARED_ITERATOR_RACE"):
    number = 42
    merged = "a" * 40
    family = group_patterns([{
        "source": source, "pr_number": number, "canonical_pr_number": number,
        "pattern_code": code, "evidence_sha256": sha("candidate"),
        "status": "UNVERIFIED_CANDIDATE_ONLY",
    }])
    plan = create_regression_matrix(candidate_rulepack(family))
    pinned = {"schema": "UCIE_PUBLIC_PR_MERGE_SNAPSHOT_V1", "entries": [{
        "source": source, "pr_number": number,
        "public_url": f"https://github.com/{source}/pull/{number}",
        "merged_at": "2026-10-13T00:00:00Z", "base_branch": "main",
        "merge_commit_sha": merged,
    }]}
    claim = {
        "schema": "UCIE_EXTERNAL_REGRESSION_CLAIM_V1",
        "case_id": plan["cases"][0]["case_id"], "source": source,
        "rule_code": code,
        "evidence_fingerprint": plan["cases"][0]["evidence_fingerprint"],
        "merge_commit_sha": merged,
        "runtime_product": "CPython" if source == "python/cpython" else "PowerShell",
        "runtime_version": "3.15.0" if source == "python/cpython" else "7.6.0",
        "platform": "Linux" if source == "python/cpython" else "Windows",
        "fixture_sha256": sha("synthetic-fixture"),
        "pre_fix": {"revision_sha": "b" * 40,
                    "result": "FAILURE_OBSERVED_CLAIM",
                    "observation_sha256": sha("failure-artifact")},
        "post_fix": {"revision_sha": merged,
                     "result": "SUCCESS_OBSERVED_CLAIM",
                     "observation_sha256": sha("success-artifact")},
        "recorded_utc": "2026-10-14T00:00:00Z",
        "independent_attestation": None,
    }
    return plan, pinned, claim


class ExternalRegressionReceiptTests(unittest.TestCase):
    def test_no_external_data_is_not_a_pass(self):
        plan, pins, _ = fixtures()
        result = inspect_regression_claims(plan, pins)
        self.assertEqual(result["status"], "AWAITING_EXTERNAL_CLAIMS")
        self.assertEqual(result["missing_claims"], 1)
        self.assertEqual(result["runtime_executions_by_ucie"], 0)
        self.assertEqual(result["reproduced_fixes_verified"], 0)
        self.assertFalse(result["production_approved"])

    def test_structurally_valid_claim_is_never_verified(self):
        plan, pins, claim = fixtures()
        original = deepcopy(claim)
        result = inspect_regression_claims(plan, pins, [claim])
        self.assertEqual(claim, original)
        self.assertEqual(result["status"], "UNTRUSTED_CLAIMS_PRESENT")
        self.assertEqual(result["claimed_cases"], 1)
        self.assertEqual(result["missing_claims"], 0)
        self.assertEqual(result["comparisons"][0]["claim_consistency"],
                         "STRUCTURAL_ONLY")
        self.assertFalse(result["comparisons"][0]["reproduction_verified"])
        self.assertEqual(result["reproduced_fixes_verified"], 0)
        self.assertEqual(result["independent_attestations_verified"], 0)
        self.assertFalse(result["rulepack_signed"])
        self.assertFalse(result["production_approved"])
        self.assertEqual(result["persistent_writes"], 0)

    def test_powershell_windows_only_fixture(self):
        plan, pins, claim = fixtures(
            "PowerShell/PowerShell", "PS_SSH_PATH_WITHOUT_RUNSPACE")
        self.assertEqual(inspect_regression_claims(
            plan, pins, [claim])["claimed_cases"], 1)
        claim["platform"] = "Linux"
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_wrong_merge_sha_fails_closed(self):
        plan, pins, claim = fixtures()
        claim["merge_commit_sha"] = "c" * 40
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_post_fix_must_be_exact_merge_revision(self):
        plan, pins, claim = fixtures()
        claim["post_fix"]["revision_sha"] = "d" * 40
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_same_pre_and_post_revision_denied(self):
        plan, pins, claim = fixtures()
        claim["pre_fix"]["revision_sha"] = "a" * 40
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_claimed_success_without_failure_denied(self):
        plan, pins, claim = fixtures()
        claim["pre_fix"]["result"] = "PASS"
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_untrusted_command_field_fails_closed(self):
        plan, pins, claim = fixtures()
        claim["command"] = "untrusted-shell-code"
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_claim_attestation_cannot_escalate(self):
        plan, pins, claim = fixtures()
        claim["independent_attestation"] = {"approved": True}
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_wrong_evidence_fingerprint_denied(self):
        plan, pins, claim = fixtures()
        claim["evidence_fingerprint"] = "0" * 64
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_duplicate_case_denied(self):
        plan, pins, claim = fixtures()
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim, deepcopy(claim)])

    def test_future_timestamp_denied(self):
        plan, pins, claim = fixtures()
        claim["recorded_utc"] = "2999-01-01T00:00:00Z"
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_unapproved_source_in_snapshot_denied(self):
        plan, pins, claim = fixtures()
        pins["entries"][0]["source"] = "unauthorized/repository"
        with self.assertRaises(PatternError):
            inspect_regression_claims(plan, pins, [claim])

    def test_digest_determinism(self):
        plan, pins, claim = fixtures()
        first = inspect_regression_claims(plan, pins, [claim])
        second = inspect_regression_claims(deepcopy(plan), deepcopy(pins),
                                            [deepcopy(claim)])
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
