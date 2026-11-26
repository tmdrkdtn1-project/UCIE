"""Fourth source is real prior UCIE native evidence, not a new fix."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from ucie_miner import ucie_v2_b4_fourth_technology_bridge_v01 as s
from ucie_miner import ucie_v2_b4_multisource_hypothesis_v01 as composer


class FourthTechnologyBridgeTests(TestCase):
    def test_fourth_source_exact_p9_pin_and_native_negative(self):
        record = s.reviewed_powershell_record()
        self.assertEqual(record["source_id"], "repo:PowerShell/PowerShell")
        self.assertEqual(record["source_pin"], s.MERGE_SHA)
        self.assertEqual(record["technology"], "PowerShell")
        self.assertIn("VERSION_PINNED_TRIAL", record["mechanisms"])
        self.assertIn("HISTORICAL_TRIAL_NOT_CURRENT_COMPATIBILITY",
                      record["counterexamples"])

    def test_four_technologies_through_original_composer(self):
        review = s.build_four_technology_review()
        synth = review["source_pinned_synthesis"]
        self.assertEqual(synth["record_count"], 4)
        self.assertEqual(len(synth["hypotheses"]), 3)
        self.assertEqual(synth["held_candidates"], [])
        by_name = {r["claim"]: r for r in synth["hypotheses"]}
        self.assertEqual(
            set(by_name["VERSION_PINNED_TRIAL"]["supporting_records"]),
            {"mcp-prompts", "powershell-resolvepath"})
        self.assertFalse(review["claims_current_sdk_or_fixed_version"])
        self.assertFalse(review["new_native_trial_executed"])

    def test_prior_three_technology_behavior_retained(self):
        prior = composer.build_curated_multisource_demo()
        self.assertEqual(prior["record_count"], 3)
        self.assertEqual(len(prior["hypotheses"]), 2)
        self.assertEqual(len(prior["held_candidates"]), 1)

    def test_order_invariance_four_source(self):
        original = composer.pinned_records() + [s.reviewed_powershell_record()]
        self.assertEqual(composer.compose_hypotheses(original),
                         composer.compose_hypotheses(list(reversed(original))))

    def test_unpinned_powershell_merge_refuses(self):
        original = composer.pinned_records() + [s.reviewed_powershell_record()]
        original[-1]["source_pin"] = "0" * 40
        with self.assertRaises(composer.MultiSourceError):
            composer.compose_hypotheses(original)

    def test_no_fake_fixed_release_or_rights(self):
        r = s.build_four_technology_review()
        self.assertEqual(r["source_review_scope"],
                         "POWERSHELL_7_6_6_WINDOWS_X64_BUG_REPRODUCTION_NOT_FIX")
        self.assertFalse(r["approved_for_export"])
        self.assertFalse(r["rights_approved"])
        self.assertFalse(r["independent_qa_verified"])
        self.assertEqual(r["network_requests"], 0)
        self.assertEqual(r["operating_database_writes"], 0)

    def test_mismatched_review_sha_denied(self):
        with patch.object(s, "lookup_pinned_review", return_value=None):
            with self.assertRaises(s.FourthTechnologyError):
                s.reviewed_powershell_record()

    def test_release_claim_forgery_denied(self):
        real = s.lookup_pinned_review(
            source_id=s.SOURCE_ID, public_url=s.PR_URL, merge_sha=s.MERGE_SHA)
        forged = deepcopy(real)
        forged["release_contains_fix_verified"] = True
        with patch.object(s, "lookup_pinned_review", return_value=forged):
            with self.assertRaises(s.FourthTechnologyError):
                s.reviewed_powershell_record()

    def test_independent_qa_forgery_denied(self):
        real = s.lookup_pinned_review(
            source_id=s.SOURCE_ID, public_url=s.PR_URL, merge_sha=s.MERGE_SHA)
        forged = deepcopy(real)
        forged["independent_qa_completed"] = True
        with patch.object(s, "lookup_pinned_review", return_value=forged):
            with self.assertRaises(s.FourthTechnologyError):
                s.reviewed_powershell_record()

    def test_missing_native_receipt_denied(self):
        real = s.lookup_pinned_review(
            source_id=s.SOURCE_ID, public_url=s.PR_URL, merge_sha=s.MERGE_SHA)
        forged = deepcopy(real)
        forged["official_windows_release_runtime_observation"] = None
        with patch.object(s, "lookup_pinned_review", return_value=forged):
            with self.assertRaises(s.FourthTechnologyError):
                s.reviewed_powershell_record()

    def test_unknown_injected_mechanism_denied(self):
        original = composer.pinned_records() + [s.reviewed_powershell_record()]
        original[-1]["mechanisms"].append("ALL_RELEASES_FIXED")
        with self.assertRaises(composer.MultiSourceError):
            composer.compose_hypotheses(original)

    def test_stale_or_unapproved_registry_denied(self):
        real = s.get_source(s.SOURCE_ID)
        forged = deepcopy(real)
        forged["status"] = "RESEARCH_ONLY"
        with patch.object(s, "get_source", return_value=forged):
            with self.assertRaises(s.FourthTechnologyError):
                s.reviewed_powershell_record()
