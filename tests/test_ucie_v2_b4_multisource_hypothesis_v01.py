"""B4 curated multi-source synthesis is a proposal, never automatic fact."""
from copy import deepcopy
from unittest import TestCase
from ucie_miner import ucie_v2_b4_multisource_hypothesis_v01 as s


class MultiSourceHypothesisTests(TestCase):
    def test_cross_technology_hypotheses_and_hold(self):
        result = s.build_curated_multisource_demo()
        self.assertEqual(result["record_count"], 3)
        self.assertEqual([x["claim"] for x in result["hypotheses"]],
                         ["BOUNDED_SCOPE_BUDGET", "OUTPUT_CONTRACT_VALIDATION"])
        self.assertEqual([x["claim"] for x in result["held_candidates"]],
                         ["VERSION_PINNED_TRIAL"])
        self.assertEqual(result["held_candidates"][0]["supporter_count"], 1)

    def test_different_two_technologies_supported(self):
        result = s.compose_hypotheses(s.pinned_records()[:2])
        self.assertEqual(len(result["hypotheses"]), 2)
        self.assertIn("VERSION_PINNED_TRIAL",
                      [x["claim"] for x in result["held_candidates"]])

    def test_records_order_invariant(self):
        self.assertEqual(s.compose_hypotheses(s.pinned_records()),
                         s.compose_hypotheses(list(reversed(s.pinned_records()))))

    def test_cannot_self_corrobate_with_same_source_twice(self):
        records = s.pinned_records()
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses([records[0], deepcopy(records[0])])

    def test_unhashable_source_id_is_controlled_rejection(self):
        records = s.pinned_records()
        records[0]["source_id"] = ["doc:python/cpython"]
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_non_string_technology_is_controlled_rejection(self):
        records = s.pinned_records()
        records[0]["technology"] = {"language": "Python"}
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_source_sha_forgery_fails_closed(self):
        records = s.pinned_records()
        records[0]["source_pin"] = "f" * 64
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_relabeling_source_technology_rejected(self):
        records = s.pinned_records()
        records[0]["technology"] = "MCP"
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_unsupported_source_rejected(self):
        records = s.pinned_records()
        records[0]["source_id"] = "repo:unknown"
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_unpinned_new_record_cannot_claim_authority(self):
        records = s.pinned_records()
        records[0]["record_id"] = "fabricated-source"
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_arbitrary_mechanism_injection_rejected(self):
        records = s.pinned_records()
        records[0]["mechanisms"].append("AUTO_APPROVE_ALL")
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_omitted_counterexample_fails_closed(self):
        records = s.pinned_records()
        records[0]["counterexamples"] = []
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_unknown_extra_field_fails_closed(self):
        records = s.pinned_records()
        records[0]["license_approved"] = True
        with self.assertRaises(s.MultiSourceError):
            s.compose_hypotheses(records)

    def test_no_fake_runtime_or_distribution_flags(self):
        result = s.build_curated_multisource_demo()
        for key in ("actual_cross_sdk_execution_verified",
                    "autonomous_semantic_discovery_verified",
                    "independent_qa_verified", "rights_approved",
                    "customer_release_authorized"):
            self.assertIs(result[key], False)
        self.assertFalse(result["machine_contract"]["runtime_execution_enabled"])
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertTrue(result["original_human_skillbook_draft"])
        self.assertEqual(len(result["human_draft_sha256"]), 64)

    def test_source_pins_are_per_hypothesis(self):
        result = s.build_curated_multisource_demo()
        first = result["hypotheses"][0]
        self.assertEqual(len(first["supporting_source_pins"]), 3)
        self.assertFalse(first["retest_contract"]["actual_tests_executed"])
        self.assertEqual(first["status"], "REVIEW_ONLY_UNVERIFIED")
