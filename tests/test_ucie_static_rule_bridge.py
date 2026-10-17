"""Synthetic-only Stage 5 -> Stage 6 candidate binding contract regression."""
from copy import deepcopy
import hashlib
from pathlib import Path
import unittest

from ucie_miner.patterns import PatternError, group_patterns
from ucie_miner.rule_candidates import candidate_rulepack
from ucie_miner.static_concurrency import inspect_python_scandir_source
from ucie_miner.static_rule_bridge import preview_static_rule_candidates

ROOT = Path(__file__).resolve().parents[1]


def python_receipt():
    return inspect_python_scandir_source(
        "import os\n"
        "def worker(it):\n    return next(it)\n"
        "def run(path, pool):\n"
        "    it = os.scandir(path)\n"
        "    return pool.submit(worker, it)\n")


def powershell_receipt():
    return {
        "schema": "UCIE_POWERSHELL_STATIC_CANDIDATES_V1",
        "source_sha256": hashlib.sha256(b"UCIE approved synthetic").hexdigest(),
        "finding_count": 2,
        "findings": [
            {"pattern_code": "PS_FUZZY_GET_COMMAND_DUPLICATES",
             "line": 1, "column": 1,
             "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
             "public_evidence":
                 "https://github.com/PowerShell/PowerShell/pull/28042",
             "safe_fix_guidance":
                 "Inspect fuzzy matches for duplicate Name/CommandType/Source "
                 "identities before using results",
             "runtime_bug_reproduced": False},
            {"pattern_code": "PS_RESOLVE_PATH_DOT_PREFIX",
             "line": 2, "column": 1,
             "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
             "public_evidence":
                 "https://github.com/PowerShell/PowerShell/pull/28087",
             "safe_fix_guidance":
                 "Review dot-prefixed relative paths and use an anchored "
                 "base-directory conversion if needed",
             "runtime_bug_reproduced": False},
        ],
        "parser_executed_supplied_code": False,
        "confidence": "HUMAN_REVIEW_REQUIRED",
        "approved_rules": 0,
        "source_files_read": 0,
        "persistent_writes": 0,
        "production_approved": False,
    }


def known_pack(source, number, pattern):
    family = group_patterns([{
        "source": source, "pr_number": number,
        "canonical_pr_number": number, "pattern_code": pattern,
        "evidence_sha256": hashlib.sha256(b"synthetic-upstream-metadata").hexdigest(),
        "status": "UNVERIFIED_CANDIDATE_ONLY",
    }])
    return candidate_rulepack(family)


class StaticRuleBridgeTests(unittest.TestCase):
    def test_python_scan_links_to_pinned_public_pr_and_unexecuted_plan(self):
        result = preview_static_rule_candidates(ROOT, python_receipt())
        self.assertEqual(result["finding_count"], 1)
        self.assertEqual(result["status"],
                         "PUBLIC_PR_PINNED_CANDIDATES_UNVERIFIED")
        proposal = result["proposals"][0]
        self.assertEqual(proposal["canonical_pr_number"], 153462)
        self.assertEqual(proposal["source"], "python/cpython")
        self.assertEqual(len(proposal["pinned_merge_commit_sha"]), 40)
        self.assertEqual(proposal["stage6_regression_case"]["actual_test_result"],
                         "NOT_EXECUTED")
        self.assertIsNone(
            proposal["stage6_rulepack_candidate"]["executable_command"])
        self.assertTrue(all(v == "NOT_VERIFIED" for v in
                            proposal["stage6_rulepack_candidate"]["required_gates"].values()))
        self.assertIsNone(
            proposal["stage6_rulepack_candidate"]["evidence_fingerprint"])
        self.assertFalse(result["source_digest_is_authoritative"])
        self.assertFalse(result["deploy_allowed"])
        self.assertFalse(result["production_approved"])
        self.assertEqual(result["persistent_writes"], 0)

    def test_powershell_scan_links_two_distinct_pinned_public_families(self):
        result = preview_static_rule_candidates(ROOT, powershell_receipt())
        self.assertEqual(result["finding_count"], 2)
        self.assertEqual([p["canonical_pr_number"] for p in result["proposals"]],
                         [28042, 28087])
        self.assertTrue(all(p["stage6_regression_case"]["platform"] == "Windows"
                            for p in result["proposals"]))
        self.assertFalse(result["auto_promoted"])

    def test_actual_python_xoption_misuse_links_to_pinned_stage6_review(self):
        # A PowerShell AST observation can point to an approved CPython PR.
        # This verifies detector -> pinned public evidence -> nonexecuting
        # prevention/repair instructions, not production auto-promotion.
        guidance = (
            "Use Python -X disable-remote-debug (hyphens), not disable_remote_debug; "
            "confirm target interpreter setting"
        )
        receipt = {
            "schema": "UCIE_POWERSHELL_STATIC_CANDIDATES_V1",
            "source_sha256": hashlib.sha256(b"python -X disable_remote_debug").hexdigest(),
            "finding_count": 1,
            "findings": [{
                "pattern_code": "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
                "line": 1, "column": 1,
                "confidence": "STATIC_HEURISTIC_REVIEW_REQUIRED",
                "public_evidence": "https://github.com/python/cpython/pull/159014",
                "safe_fix_guidance": guidance,
                "runtime_bug_reproduced": False,
            }],
            "parser_executed_supplied_code": False,
            "confidence": "HUMAN_REVIEW_REQUIRED",
            "approved_rules": 0,
            "source_files_read": 0,
            "persistent_writes": 0,
            "production_approved": False,
        }
        preview = preview_static_rule_candidates(ROOT, receipt)
        self.assertEqual(preview["finding_count"], 1)
        item = preview["proposals"][0]
        self.assertEqual(item["canonical_pr_number"], 159014)
        self.assertEqual(item["source"], "python/cpython")
        self.assertEqual(item["pinned_merge_commit_sha"],
                         "91248026c8a41910098032dd23f9a05ad2d9b513")
        self.assertIn("-X disable-remote-debug",
                      item["stage6_rulepack_candidate"]["safe_fix_guidance"])
        self.assertEqual(item["stage6_regression_case"]["actual_test_result"],
                         "NOT_EXECUTED")
        self.assertFalse(preview["deploy_allowed"])
        self.assertFalse(preview["auto_promoted"])
        linked = preview_static_rule_candidates(
            ROOT, receipt,
            existing_rulepack=known_pack(
                "python/cpython", 159014,
                "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO"))
        self.assertEqual(linked["status"], "STRUCTURALLY_LINKED_UNVERIFIED")
        self.assertFalse(linked["independent_regression_passed"])
        forged = deepcopy(receipt)
        forged["findings"][0]["public_evidence"] = (
            "https://github.com/PowerShell/PowerShell/pull/159014")
        with self.assertRaises(PatternError):
            preview_static_rule_candidates(ROOT, forged)

    def test_existing_unapproved_rulepack_can_be_structurally_linked(self):
        result = preview_static_rule_candidates(
            ROOT, python_receipt(),
            existing_rulepack=known_pack(
                "python/cpython", 153462, "PY_SCANDIR_SHARED_ITERATOR_RACE"))
        self.assertEqual(result["status"], "STRUCTURALLY_LINKED_UNVERIFIED")
        self.assertEqual(result["miner_knowledge_binding"], "STRUCTURAL_ONLY")
        self.assertEqual(len(result["proposals"][0]
                             ["stage6_rulepack_candidate"]["evidence_fingerprint"]), 64)
        self.assertFalse(result["independent_regression_passed"])
        self.assertFalse(result["rulepack_signed"])

    def test_wrong_family_rulepack_denied(self):
        with self.assertRaises(PatternError):
            preview_static_rule_candidates(
                ROOT, python_receipt(),
                existing_rulepack=known_pack(
                    "PowerShell/PowerShell", 28042,
                    "PS_FUZZY_GET_COMMAND_DUPLICATES"))

    def test_forged_existing_pack_approval_denied(self):
        pack = known_pack("python/cpython", 153462,
                          "PY_SCANDIR_SHARED_ITERATOR_RACE")
        pack["approval"] = True
        with self.assertRaises(PatternError):
            preview_static_rule_candidates(
                ROOT, python_receipt(), existing_rulepack=pack)

    def test_forged_evidence_url_denied(self):
        receipt = python_receipt()
        receipt["findings"][0]["public_evidence"] = (
            "https://github.com/unapproved/repo/pull/153462")
        with self.assertRaises(PatternError):
            preview_static_rule_candidates(ROOT, receipt)

    def test_forged_safe_fix_or_runtime_pass_denied(self):
        for key, value in (("safe_fix_guidance", "Run arbitrary executable"),
                           ("runtime_bug_reproduced", True)):
            receipt = python_receipt()
            receipt["findings"][0][key] = value
            with self.subTest(key=key), self.assertRaises(PatternError):
                preview_static_rule_candidates(ROOT, receipt)

    def test_unknown_pattern_denied(self):
        receipt = python_receipt()
        receipt["findings"][0]["pattern_code"] = "UNKNOWN_RULE"
        with self.assertRaises(PatternError):
            preview_static_rule_candidates(ROOT, receipt)

    def test_duplicate_finding_denied(self):
        receipt = python_receipt()
        receipt["findings"].append(deepcopy(receipt["findings"][0]))
        receipt["finding_count"] = 2
        with self.assertRaises(PatternError):
            preview_static_rule_candidates(ROOT, receipt)

    def test_claimed_approval_and_signed_receipts_denied(self):
        for key, value in (("approved_rules", 1),
                           ("parser_executed_supplied_code", True),
                           ("persistent_writes", 1),
                           ("source_files_read", 1),
                           ("production_approved", True)):
            receipt = python_receipt()
            receipt[key] = value
            with self.subTest(key=key), self.assertRaises(PatternError):
                preview_static_rule_candidates(ROOT, receipt)

    def test_missing_snapshot_denied_without_db_writes(self):
        with self.assertRaises(PatternError):
            preview_static_rule_candidates(Path("/path/without/ucie"),
                                           python_receipt())

    def test_empty_finding_scan_does_not_create_rules(self):
        receipt = inspect_python_scandir_source(
            "import os\n"
            "def safe(path):\n    return [x.name for x in os.scandir(path)]\n")
        response = preview_static_rule_candidates(ROOT, receipt)
        self.assertEqual(response["finding_count"], 0)
        self.assertEqual(response["proposals"], [])
        self.assertFalse(response["production_approved"])
        self.assertFalse(response["source_digest_is_authoritative"])

    def test_deterministic_review_digest_without_promotion(self):
        scan = python_receipt()
        first = preview_static_rule_candidates(ROOT, scan)
        second = preview_static_rule_candidates(ROOT, deepcopy(scan))
        self.assertEqual(first, second)
        self.assertEqual(len(first["review_digest_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
