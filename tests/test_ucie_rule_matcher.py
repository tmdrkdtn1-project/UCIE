"""Synthetic tests for generic matching AFTER a signed-pack trust check.

These tests DO NOT sign or approve any production candidate. Existing V1
owner/review pack tests exercise the actual trusted call sites.
"""
from copy import deepcopy
import unittest

from test_ucie_multi_review import scanner_receipt
from ucie_public.multi_owner_release import RELEASE_RULES
from ucie_public.multi_review import RULES
from ucie_public.policy import PolicyError
from ucie_public.rule_matcher import match_signed_static_rules


class SignedRuleMatcherTests(unittest.TestCase):
    def test_both_signed_owner_rules_match_once(self):
        found = match_signed_static_rules(
            scanner_receipt(), RELEASE_RULES,
            expected_approval="AUTOMATED_QA_OWNER_RISK_ACCEPTED")
        self.assertEqual(
            [x["rule_id"] for x in found],
            ["PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO",
             "PS_RESOLVE_PATH_DOT_PREFIX"])
        self.assertTrue(all(x["manual_review_required"] for x in found))
        self.assertTrue(all(
            x["runtime_bug_confirmed_for_this_input"] is False
            for x in found))

    def test_signed_subset_does_not_authorize_unsigned_rule(self):
        found = match_signed_static_rules(
            scanner_receipt(), RELEASE_RULES[:1],
            expected_approval="AUTOMATED_QA_OWNER_RISK_ACCEPTED")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["rule_id"],
                         "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO")
        self.assertEqual(
            match_signed_static_rules(
                {**scanner_receipt(), "findings": [], "finding_count": 0},
                RELEASE_RULES[:1],
                expected_approval="AUTOMATED_QA_OWNER_RISK_ACCEPTED"),
            [])

    def test_review_rule_identity_is_separate_from_owner_release(self):
        self.assertEqual(len(match_signed_static_rules(
            scanner_receipt(), RULES,
            expected_approval="HUMAN_REVIEW_REQUIRED")), 2)
        with self.assertRaises(PolicyError):
            match_signed_static_rules(
                scanner_receipt(), RULES,
                expected_approval="AUTOMATED_QA_OWNER_RISK_ACCEPTED")

    def test_unpinned_or_unapproved_rule_rejected(self):
        for change in ("duplicate", "sha", "source", "approval",
                       "scanner", "automation", "unknown", "empty", "oversized"):
            rules = deepcopy(RELEASE_RULES)
            if change == "duplicate":
                rules.append(deepcopy(rules[0]))
            elif change == "sha":
                rules[1]["upstream_merge_sha"] = "f" * 40
            elif change == "source":
                rules[1]["upstream"] = (
                    "https://github.com/PowerShell/PowerShell/pull/28042")
            elif change == "approval":
                rules[1]["approval"] = "HUMAN_REVIEW_REQUIRED"
            elif change == "scanner":
                rules[1]["scanner"] = "unexpected_scanner.ps1"
            elif change == "automation":
                rules[1]["automation"] = "AUTO_FIX"
            elif change == "unknown":
                rules[1]["rule_id"] = "PS_NOT_APPROVED"
            elif change == "empty":
                rules = []
            else:
                rules = rules * 33
            with self.subTest(change=change), self.assertRaises(PolicyError):
                match_signed_static_rules(
                    scanner_receipt(), rules,
                    expected_approval="AUTOMATED_QA_OWNER_RISK_ACCEPTED")

    def test_forged_receipts_fail_closed(self):
        for change in ("approved", "wrong_evidence", "duplicate", "bad_count"):
            receipt = scanner_receipt()
            if change == "approved":
                receipt["approved_rules"] = 1
            elif change == "wrong_evidence":
                receipt["findings"][1]["public_evidence"] = (
                    "https://github.com/PowerShell/PowerShell/pull/28042")
            elif change == "duplicate":
                receipt["findings"].append(deepcopy(receipt["findings"][0]))
                receipt["finding_count"] = 3
            else:
                receipt["finding_count"] = 0
            with self.subTest(change=change), self.assertRaises(PolicyError):
                match_signed_static_rules(
                    receipt, RELEASE_RULES,
                    expected_approval="AUTOMATED_QA_OWNER_RISK_ACCEPTED")


if __name__ == "__main__":
    unittest.main()
