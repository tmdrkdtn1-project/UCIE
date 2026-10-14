"""Synthetic-only Stage 7 review agenda: no signatures or approvals."""
from copy import deepcopy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import unittest

from ucie_miner.merge_snapshot import load_merge_snapshot
from ucie_miner.patterns import PatternError, group_patterns
from ucie_miner.regression_plans import create_regression_matrix
from ucie_miner.regression_receipts import inspect_regression_claims
from ucie_miner.review_docket import prepare_independent_review_docket
from ucie_miner.rule_candidates import candidate_rulepack
from ucie_miner.static_concurrency import inspect_python_scandir_source
from ucie_miner.static_rule_bridge import preview_static_rule_candidates

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    scan = inspect_python_scandir_source(
        "import os\n"
        "def run(path, pool, worker):\n"
        "    iterator = os.scandir(path)\n"
        "    pool.submit(worker, iterator)\n")
    static = preview_static_rule_candidates(ROOT, scan)
    family = group_patterns([{
        "source": "python/cpython", "pr_number": 153462,
        "canonical_pr_number": 153462,
        "pattern_code": "PY_SCANDIR_SHARED_ITERATOR_RACE",
        "evidence_sha256": hashlib.sha256(b"ucie synthetic upstream evidence").hexdigest(),
        "status": "UNVERIFIED_CANDIDATE_ONLY",
    }])
    plan = create_regression_matrix(candidate_rulepack(family))
    pins = load_merge_snapshot(ROOT)
    return static, plan, pins


def fake_before_after(plan, pins):
    observed = next(item for item in pins["entries"]
                    if item["source"] == "python/cpython"
                    and item["pr_number"] == 153462)
    fingerprint = plan["cases"][0]["evidence_fingerprint"]
    def sha(s):
        return hashlib.sha256(s.encode("utf-8")).hexdigest()
    return {
        "schema": "UCIE_EXTERNAL_REGRESSION_CLAIM_V1",
        "case_id": "python/cpython#153462:PY_SCANDIR_SHARED_ITERATOR_RACE",
        "source": "python/cpython",
        "rule_code": "PY_SCANDIR_SHARED_ITERATOR_RACE",
        "evidence_fingerprint": fingerprint,
        "merge_commit_sha": observed["merge_commit_sha"],
        "runtime_product": "CPython", "runtime_version": "3.15.0",
        "platform": "Linux",
        "fixture_sha256": sha("fixture"),
        "pre_fix": {"revision_sha": "b" * 40,
                    "result": "FAILURE_OBSERVED_CLAIM",
                    "observation_sha256": sha("before")},
        "post_fix": {"revision_sha": observed["merge_commit_sha"],
                     "result": "SUCCESS_OBSERVED_CLAIM",
                     "observation_sha256": sha("after")},
        "recorded_utc": "2026-10-14T00:00:00Z",
        "independent_attestation": None,
    }


class IndependentReviewDocketTests(unittest.TestCase):
    def test_no_claims_do_not_authorize_anything(self):
        static, plan, pins = fixture()
        review = inspect_regression_claims(plan, pins)
        docket = prepare_independent_review_docket(static, review)
        self.assertEqual(docket["status"], "REVIEW_PENDING_NO_GO")
        self.assertEqual(docket["candidate_findings"], 1)
        self.assertEqual(docket["claimed_reviewed_cases"], 0)
        self.assertEqual(docket["review_queue"][0]["claim_consistency"],
                         "NO_EXTERNAL_CLAIM")
        self.assertIsNone(docket["review_queue"][0]
                          ["claimed_external_regression_sha256"])
        self.assertFalse(docket["docket_sha256_is_signature"])
        self.assertFalse(docket["production_approved"])
        self.assertFalse(docket["deploy_allowed"])
        self.assertEqual(docket["persistent_writes"], 0)

    def test_structural_before_after_claim_stays_unverified(self):
        static, plan, pins = fixture()
        claim = fake_before_after(plan, pins)
        review = inspect_regression_claims(plan, pins, [claim])
        docket = prepare_independent_review_docket(static, review)
        self.assertEqual(docket["claimed_reviewed_cases"], 1)
        self.assertEqual(docket["review_queue"][0]["claim_consistency"],
                         "STRUCTURAL_ONLY_UNTRUSTED")
        self.assertFalse(docket["review_queue"][0]
                         ["regression_independently_verified"])
        self.assertFalse(docket["review_queue"][0]
                         ["reviewer_identity_authenticated"])
        self.assertEqual(docket["independent_approvals_verified"], 0)
        self.assertEqual(docket["rulepacks_signed"], 0)
        self.assertFalse(docket["production_approved"])

    def test_unlinked_external_claim_is_not_silently_counted_as_reviewed(self):
        static, plan, pins = fixture()
        review = inspect_regression_claims(plan, pins)
        # A structurally shaped *untrusted* claim about another family
        # must remain visible but cannot attach to this static finding.
        comparison = {
            "case_id": "PowerShell/PowerShell#28042:PS_FUZZY_GET_COMMAND_DUPLICATES",
            "external_claim_sha256": "a" * 64,
            "claim_consistency": "STRUCTURAL_ONLY",
            "reproduction_verified": False,
            "independent_attestation_verified": False,
            "version_applicability": "UNDETERMINED",
        }
        review["comparisons"] = [comparison]
        review["claimed_cases"] = 1
        review["missing_claims"] = 0
        review["status"] = "UNTRUSTED_CLAIMS_PRESENT"
        review["claim_set_sha256"] = hashlib.sha256(json.dumps(
            review["comparisons"], sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        docket = prepare_independent_review_docket(static, review)
        self.assertEqual(docket["claimed_reviewed_cases"], 0)
        self.assertEqual(docket["unlinked_external_claim_count"], 1)
        self.assertEqual(docket["unlinked_external_case_ids"],
                         [comparison["case_id"]])
        self.assertFalse(docket["unlinked_external_claims_are_verified"])
        self.assertFalse(docket["production_approved"])

    def test_forged_static_signature_denied(self):
        static, plan, pins = fixture()
        static["rulepack_signed"] = True
        with self.assertRaises(PatternError):
            prepare_independent_review_docket(
                static, inspect_regression_claims(plan, pins))

    def test_changed_candidate_digest_denied(self):
        static, plan, pins = fixture()
        static["proposals"][0]["source_line"] = 999
        with self.assertRaises(PatternError):
            prepare_independent_review_docket(
                static, inspect_regression_claims(plan, pins))

    def test_forged_external_verification_denied(self):
        static, plan, pins = fixture()
        review = inspect_regression_claims(
            plan, pins, [fake_before_after(plan, pins)])
        review["comparisons"][0]["reproduction_verified"] = True
        with self.assertRaises(PatternError):
            prepare_independent_review_docket(static, review)

    def test_forged_external_digest_denied(self):
        static, plan, pins = fixture()
        review = inspect_regression_claims(plan, pins)
        review["claim_set_sha256"] = "f" * 64
        with self.assertRaises(PatternError):
            prepare_independent_review_docket(static, review)

    def test_forged_independent_attestation_count_denied(self):
        static, plan, pins = fixture()
        review = inspect_regression_claims(plan, pins)
        review["independent_attestations_verified"] = 1
        with self.assertRaises(PatternError):
            prepare_independent_review_docket(static, review)

    def test_inconsistent_claim_totals_denied(self):
        static, plan, pins = fixture()
        review = inspect_regression_claims(plan, pins)
        review["claimed_cases"] = 1
        with self.assertRaises(PatternError):
            prepare_independent_review_docket(static, review)

    def test_bounded_cli_docket_remains_review_pending(self):
        static, plan, pins = fixture()
        review = inspect_regression_claims(plan, pins)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        command = [sys.executable, "-m", "ucie_miner",
                   "preview-review-docket-stdin"]
        done = subprocess.run(
            command, input=json.dumps({
                "static_preview": static, "external_review": review,
            }), capture_output=True, text=True,
            cwd=ROOT, env=env, timeout=12,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        output = json.loads(done.stdout)
        self.assertEqual(output["status"], "REVIEW_PENDING_NO_GO")
        self.assertEqual(output["candidate_findings"], 1)
        self.assertEqual(output["independent_approvals_verified"], 0)
        self.assertFalse(output["deploy_allowed"])

    def test_cli_rejects_duplicate_json_keys(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        done = subprocess.run(
            [sys.executable, "-m", "ucie_miner",
             "preview-review-docket-stdin"],
            input='{"static_preview":{},"static_preview":{},"external_review":{}}',
            capture_output=True, text=True, cwd=ROOT, env=env, timeout=12,
        )
        self.assertEqual(done.returncode, 2)
        self.assertEqual(json.loads(done.stdout)["status"], "FAIL_CLOSED")

    def test_deterministic_hash_not_signature(self):
        static, plan, pins = fixture()
        review = inspect_regression_claims(plan, pins)
        a = prepare_independent_review_docket(static, review)
        b = prepare_independent_review_docket(deepcopy(static), deepcopy(review))
        self.assertEqual(a, b)
        self.assertEqual(len(a["docket_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
