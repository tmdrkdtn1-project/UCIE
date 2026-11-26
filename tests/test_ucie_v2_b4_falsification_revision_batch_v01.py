"""B4 end-to-end first-party executable counterexamples and revision review."""
from copy import deepcopy
from unittest import TestCase

from ucie_miner import ucie_v2_b4_falsification_revision_batch_v01 as b


class FalsificationBatchTests(TestCase):
    def test_executable_first_party_positive_and_negative(self):
        result = b.evaluate_first_party_trials(b._trial_specs())
        self.assertEqual(result["case_count"], 6)
        self.assertEqual(result["counts"]["baseline_correct"], 4)
        self.assertEqual(result["counts"]["challenger_correct"], 6)
        self.assertEqual(result["counts"]["baseline_false_accepts"], 2)
        self.assertEqual(result["counts"]["challenger_false_accepts"], 0)
        self.assertTrue(result["first_party_pure_python_executed"])
        self.assertFalse(result["upstream_runtime_executed"])

    def test_bounded_candidate_does_not_accept_prefix_spoof(self):
        self.assertTrue(b._legacy_prefix_match("7.6.6", "7.6.60"))
        self.assertFalse(b._bounded_exact_match("7.6.6", "7.6.60"))
        self.assertFalse(b._bounded_exact_match("3.15.0", "3.15.00"))
        self.assertTrue(b._bounded_exact_match("3.15.0", "3.15.0"))

    def test_non_numeric_version_is_not_valid(self):
        self.assertFalse(b._bounded_exact_match("7.6.6", "7.6.6-preview"))
        self.assertFalse(b._bounded_exact_match("7.6.6", "<script>"))

    def test_actual_review_batch_produces_original_assets(self):
        result = b.build_falsification_revision_batch()
        self.assertTrue(result["revision"]["observed_first_party_gain"])
        self.assertEqual(
            result["revision"]["review_option"],
            "PROPOSE_REVISION_FOR_INDEPENDENT_REVIEW")
        self.assertIn("접두 문자열", result["skillbook_chapter_draft"]["text"])
        self.assertEqual(
            result["machine_engine_draft"]["algorithm"],
            "EXACT_NUMERIC_VERSION_TOKEN_MATCH")
        self.assertFalse(result["machine_engine_draft"]["export_allowed"])
        self.assertFalse(result["skillbook_chapter_draft"]["publication_authorized"])
        self.assertFalse(result["actual_upstream_python_or_powershell_tested"])

    def test_same_fixture_replay_deterministic(self):
        self.assertEqual(b.build_falsification_revision_batch(),
                         b.build_falsification_revision_batch())

    def test_reordered_fixture_still_deterministic(self):
        self.assertEqual(
            b.evaluate_first_party_trials(b._trial_specs()),
            b.evaluate_first_party_trials(list(reversed(b._trial_specs()))))

    def test_tampered_expected_truth_rejected(self):
        cases = b._trial_specs()
        cases[1]["expected"] = True
        with self.assertRaises(b.FalsificationError):
            b.evaluate_first_party_trials(cases)

    def test_boolean_truth_int_spoof_rejected(self):
        cases = b._trial_specs()
        cases[0]["expected"] = 1
        with self.assertRaises(b.FalsificationError):
            b.evaluate_first_party_trials(cases)

    def test_affected_only_retests_and_unchanged_controls(self):
        revision = b.build_falsification_revision_batch()["revision"]
        self.assertEqual(revision["affected_only_retest_case_ids"],
                         ["ps-prefix-spoof", "py-prefix-spoof"])
        self.assertEqual(revision["unaffected_controls_preserved"],
                         ["ps-other", "py-other"])

    def test_bad_version_fields_rejected(self):
        cases = b._trial_specs()
        cases[0]["observed_version"] = ["7.6.6"]
        with self.assertRaises(b.FalsificationError):
            b.evaluate_first_party_trials(cases)

    def test_synthetic_draft_not_customer_proof(self):
        result = b.build_falsification_revision_batch()
        self.assertTrue(result["first_party_synthetic_trials_executed"])
        self.assertFalse(result["actual_upstream_python_or_powershell_tested"])
        self.assertFalse(result["revision"]["engine_activated"])
        self.assertFalse(result["revision"]["original_skillbook_replaced"])

    def test_unreviewed_fixture_id_rejected(self):
        cases = b._trial_specs()
        cases[0]["case_id"] = "outside"
        with self.assertRaises(b.FalsificationError):
            b.evaluate_first_party_trials(cases)

    def test_duplicate_fixture_rejected(self):
        cases = b._trial_specs()
        with self.assertRaises(b.FalsificationError):
            b.evaluate_first_party_trials(cases + [deepcopy(cases[0])])

    def test_untrusted_extra_field_rejected(self):
        cases = b._trial_specs()
        cases[0]["owner_approved"] = True
        with self.assertRaises(b.FalsificationError):
            b.evaluate_first_party_trials(cases)

    def test_unbounded_fixture_list_rejected(self):
        with self.assertRaises(b.FalsificationError):
            b.evaluate_first_party_trials([])
        with self.assertRaises(b.FalsificationError):
            b.evaluate_first_party_trials(b._trial_specs() * 5)

    def test_review_ledger_append_and_idempotent_replay(self):
        empty = b.new_in_memory_revision_ledger()
        bundle = b.build_falsification_revision_batch()
        once = b.append_revision_for_review(empty, bundle)
        twice = b.append_revision_for_review(once, bundle)
        self.assertEqual(once["count"], 1)
        self.assertEqual(once, twice)
        self.assertNotEqual(empty["content_sha256"], once["content_sha256"])
        self.assertFalse(once["persisted"])
        self.assertFalse(once["owner_approved"])

    def test_forged_release_in_rehashed_bundle_refused(self):
        bundle = b.build_falsification_revision_batch()
        forged = deepcopy(bundle)
        forged["owner_release_authorized"] = True
        forged["content_sha256"] = b._hash({
            k: v for k, v in forged.items() if k != "content_sha256"})
        with self.assertRaises(b.FalsificationError):
            b.append_revision_for_review(b.new_in_memory_revision_ledger(), forged)

    def test_history_hash_tampering_rejected(self):
        ledger = b.append_revision_for_review(
            b.new_in_memory_revision_ledger(),
            b.build_falsification_revision_batch())
        bad = deepcopy(ledger)
        bad["events"][0]["bundle"]["revision"]["baseline_correct"] = 6
        bad["content_sha256"] = b._hash({
            k: v for k, v in bad.items() if k != "content_sha256"})
        with self.assertRaises(b.FalsificationError):
            b.validate_in_memory_revision_ledger(bad)

    def test_no_io_or_auto_adoption(self):
        bundle = b.build_falsification_revision_batch()
        for name in ("source_revision_authenticated", "independent_qa_verified",
                     "rights_approved", "owner_release_authorized",
                     "auto_promotion", "model_training_performed",
                     "history_persisted"):
            self.assertIs(bundle[name], False)
        self.assertEqual(bundle["network_requests"], 0)
        self.assertEqual(bundle["operating_database_writes"], 0)
