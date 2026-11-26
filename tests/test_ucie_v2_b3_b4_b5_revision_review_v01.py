"""B3 -> B4 -> B5 revision-sensitive, actual first-party bounded tests."""
from unittest import TestCase, mock

from ucie_miner import ucie_v2_revision_impact_v01 as b3
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_b3_b4_b5_revision_review_v01 as subject


def row(method):
    return {
        "study_id": b5.STUDY_ID,
        "case_id": b5.CASE_ID,
        "anonymous_trial_token": "F01",
        "method": method,
        "cohort": "FIRST_TIME_CODER",
        "first_safe_action_time_ms": 1000,
        "correct_safe_action": True,
        "false_version_or_rights_claim": False,
        "evidence_detail_found": False,
        "origin": b5.SYNTHETIC_ORIGIN,
    }


def change(sid, *, same=False):
    pin = b3.PINS[sid]
    return {"source_id": sid, "previous_pin": pin,
            "candidate_pin": pin if same else "f" * len(pin)}


class RevisionSensitiveTests(TestCase):
    def setUp(self):
        self.complete = tuple(row(x) for x in b5.METHODS)

    def test_no_signal_is_still_synthetic_review_not_release(self):
        result = subject.review_revision_sensitive_study(self.complete, ())
        self.assertEqual(result["status"], "UNCHANGED_PINNED_SYNTHETIC_REVIEW_ONLY")
        self.assertTrue(result["b5_synthetic_evidence_current_for_candidate"])
        self.assertFalse(result["real_competitive_advantage_verified"])
        self.assertFalse(result["candidate_source_sha_authenticated"])
        self.assertFalse(result["customer_release_authorized"])

    def test_python_candidate_invalidates_b5_and_only_proposes_affected(self):
        x = subject.review_revision_sensitive_study(
            self.complete, (change("doc:python/cpython"),))
        self.assertEqual(x["status"], "SOURCE_CHANGE_CANDIDATE_HOLD_PAIRED_STUDY_STALE")
        self.assertFalse(x["b5_synthetic_evidence_current_for_candidate"])
        self.assertIn(b3.PY_BOOK, x["impacted_existing_assets"])
        self.assertNotIn(b3.GIT_BOOK, x["impacted_existing_assets"])
        self.assertIn("test_ucie_v2_b5_b4_evidence_join_v01.py",
                      x["proposed_affected_only_test_files"])

    def test_git_candidate_invalidates_without_mcp_change(self):
        x = subject.review_revision_sensitive_study(
            self.complete, (change("doc:git/git"),))
        self.assertIn(b3.GIT_BOOK, x["impacted_existing_assets"])
        self.assertNotIn(b3.MCP_ASSET, x["impacted_existing_assets"])
        self.assertFalse(x["b5_synthetic_evidence_current_for_candidate"])

    def test_mcp_sdk_changed_invalidates_target_comparison(self):
        x = subject.review_revision_sensitive_study(
            self.complete, (change("repo:modelcontextprotocol/python-sdk"),))
        self.assertIn(b3.MCP_ASSET, x["impacted_existing_assets"])
        self.assertNotIn(b3.PRINCIPLE, x["impacted_existing_assets"])
        self.assertFalse(x["b5_synthetic_evidence_current_for_candidate"])

    def test_incomplete_pairs_hold_without_revision(self):
        x = subject.review_revision_sensitive_study((row(b5.METHODS[0]),), ())
        self.assertEqual(x["status"], "SYNTHETIC_PAIR_INCOMPLETE_HOLD")
        self.assertFalse(x["b5_synthetic_evidence_current_for_candidate"])
        self.assertEqual(x["proposed_affected_only_test_files"], [])

    def test_incomplete_and_changed_prioritize_source_hold(self):
        x = subject.review_revision_sensitive_study(
            (row(b5.METHODS[0]),), (change("doc:git/git"),))
        self.assertEqual(x["status"], "SOURCE_CHANGE_CANDIDATE_HOLD_PAIRED_STUDY_STALE")
        self.assertFalse(x["original_b5_synthetic_study_complete"])

    def test_unchanged_digest_does_not_retest(self):
        x = subject.review_revision_sensitive_study(
            self.complete, (change("doc:python/cpython", same=True),))
        self.assertEqual(x["proposed_affected_only_test_files"], [])
        self.assertTrue(x["b5_synthetic_evidence_current_for_candidate"])

    def test_multiple_changed_sources_dedupe_test(self):
        x = subject.review_revision_sensitive_study(
            self.complete, (change("doc:git/git"),
                            change("doc:python/cpython")))
        names = x["proposed_affected_only_test_files"]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(names.count("test_ucie_v2_b5_b4_evidence_join_v01.py"), 1)

    def test_unapproved_source_never_expands_research(self):
        with self.assertRaises(b3.RevisionImpactError):
            subject.review_revision_sensitive_study(
                self.complete, ({"source_id": "repo:unapproved/vendor",
                                 "previous_pin": None, "candidate_pin": "f"*40},))

    def test_original_source_pin_forgery_denied(self):
        signal = change("doc:git/git")
        signal["previous_pin"] = "a"*64
        with self.assertRaises(b3.RevisionImpactError):
            subject.review_revision_sensitive_study(self.complete, (signal,))

    def test_private_participant_input_denied(self):
        bad = row(b5.METHODS[0])
        bad["email"] = "private@example.invalid"
        with self.assertRaises(b5.B5StudyContractError):
            subject.review_revision_sensitive_study((bad,), ())

    def test_b4_hypothesis_mismatch_denied(self):
        import ucie_miner.ucie_v2_b5_b4_evidence_join_v01 as join
        original = join.source_linked_synthetic_review(self.complete)
        original["hypothesis_id"] = "FORGED"
        with mock.patch.object(subject, "source_linked_synthetic_review",
                               return_value=original):
            with self.assertRaises(subject.RevisionSensitiveStudyError):
                subject.review_revision_sensitive_study(self.complete, ())

    def test_invalid_b4_approval_claim_denied(self):
        import ucie_miner.ucie_v2_generalization_review_v01 as b4
        real = b4.assess_hypothesis_revision(())
        real["source_revision_authenticated"] = True
        with mock.patch.object(subject, "assess_hypothesis_revision", return_value=real):
            with self.assertRaises(subject.RevisionSensitiveStudyError):
                subject.review_revision_sensitive_study(self.complete, ())

    def test_never_executes_upstream_or_schedules_tests(self):
        x = subject.review_revision_sensitive_study(self.complete,
                (change("doc:python/cpython"),))
        for key in ("candidate_source_sha_authenticated", "automatic_scheduling",
                    "auto_promoted", "customer_release_authorized",
                    "independent_qa_verified", "owner_host_accepted"):
            self.assertFalse(x[key])
        self.assertEqual(x["network_requests"], 0)
        self.assertEqual(x["operating_database_writes"], 0)
