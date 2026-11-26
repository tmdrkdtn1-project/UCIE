"""UCIE V2 original library asset lifecycle and falsifiable counterexamples."""
from copy import deepcopy
from hashlib import sha256
from unittest import TestCase, mock

from ucie_miner import ucie_v2_original_library_assets_v01 as a
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5
from ucie_miner import ucie_v2_revision_impact_v01 as b3


def row(method):
    return {
        "study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
        "anonymous_trial_token": "F01", "method": method,
        "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 1000,
        "correct_safe_action": True, "false_version_or_rights_claim": False,
        "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN,
    }


def signal(source):
    return {"source_id": source, "previous_pin": b3.PINS[source],
            "candidate_pin": "f" * len(b3.PINS[source])}


class OriginalLibraryAssetTests(TestCase):
    def setUp(self):
        self.complete = tuple(row(method) for method in b5.METHODS)

    def test_three_original_assets_created(self):
        x = a.assemble_original_library_assets(self.complete, ())
        self.assertEqual(x["schema"], a.SCHEMA)
        self.assertIn("가상도서관", x["chapter"]["text"])
        self.assertEqual(x["machine"]["asset_kind"],
                         "UCIE_FIRST_PARTY_MACHINE_ENGINE_TEST_CONTRACT")
        self.assertEqual(x["revision"]["review_status"], "REVIEW_ACTIVE_UNVERIFIED")
        self.assertEqual(len(x["chapter"]["source_lineage"]), 2)

    def test_idempotent_content_digests(self):
        left = a.assemble_original_library_assets(self.complete, ())
        right = a.assemble_original_library_assets(self.complete, ())
        self.assertEqual(left, right)
        self.assertEqual(left["content_sha256"], a._digest({
            key: value for key, value in left.items() if key != "content_sha256"}))
        self.assertEqual(left["chapter"]["text_sha256"],
                         sha256(left["chapter"]["text"].encode()).hexdigest())

    def test_changed_parent_holds_principle_study_and_only_related_tests(self):
        x = a.assemble_original_library_assets(
            self.complete, (signal("doc:python/cpython"),))
        self.assertEqual(x["revision"]["review_status"],
                         "REVIEW_HOLD_CANDIDATE_SOURCE_CHANGE")
        self.assertFalse(x["revision"]["prior_synthetic_study_valid_for_candidate"])
        self.assertIn("test_ucie_v2_generalization_transfer_v01.py",
                      x["revision"]["proposed_affected_only_tests"])
        self.assertNotIn(b3.GIT_BOOK, x["revision"]["affected_assets"])

    def test_mcp_target_changed_holds_b5(self):
        x = a.assemble_original_library_assets(
            self.complete, (signal("repo:modelcontextprotocol/python-sdk"),))
        self.assertFalse(x["revision"]["prior_synthetic_study_valid_for_candidate"])
        self.assertIn(b3.MCP_ASSET, x["revision"]["affected_assets"])

    def test_incomplete_pair_holds_without_inventing_retests(self):
        x = a.assemble_original_library_assets((row(b5.METHODS[0]),), ())
        self.assertEqual(x["revision"]["review_status"],
                         "REVIEW_HOLD_INCOMPLETE_PAIRED_FIXTURE")
        self.assertEqual(x["revision"]["proposed_affected_only_tests"], [])
        self.assertFalse(x["revision"]["prior_synthetic_study_complete"])

    def test_unapproved_source_is_denied(self):
        with self.assertRaises(b3.RevisionImpactError):
            a.assemble_original_library_assets(self.complete, (
                {"source_id": "unapproved/repo", "previous_pin": None,
                 "candidate_pin": "f"*40},))

    def test_wrong_prior_pin_denied(self):
        bad = signal("doc:git/git")
        bad["previous_pin"] = "a"*64
        with self.assertRaises(b3.RevisionImpactError):
            a.assemble_original_library_assets(self.complete, (bad,))

    def test_private_synthetic_row_rejected(self):
        bad = row(b5.METHODS[0])
        bad["name"] = "private"
        with self.assertRaises(b5.B5StudyContractError):
            a.assemble_original_library_assets((bad,), ())

    def test_explicit_privacy_counterexample_not_generalized(self):
        x = a.assemble_original_library_assets(self.complete, ())
        contract = x["machine"]["counterexample"]
        self.assertEqual(contract["result"],
                         "REJECTED_BY_EXPLICIT_DIFFERING_OUTPUT_CONTRACTS")
        self.assertEqual(len(set(contract["different_output_contracts"])), 2)
        self.assertFalse(x["machine"]["runtime_execution_enabled"])

    def test_false_rights_in_hypothesis_denied(self):
        actual = a.build_hypothesis()
        forged = deepcopy(actual)
        forged["rights_approved"] = True
        with mock.patch.object(a, "build_hypothesis", return_value=forged):
            with self.assertRaises(a.LibraryAssetError):
                a.assemble_original_library_assets(self.complete, ())

    def test_missing_negative_control_rejected(self):
        actual = a.run_bounded_transfer(a.build_hypothesis())
        forged = deepcopy(actual)
        forged["positive_negative_control"][1] = "CONTRACT_MATCH"
        with mock.patch.object(a, "run_bounded_transfer", return_value=forged):
            with self.assertRaises(a.LibraryAssetError):
                a.assemble_original_library_assets(self.complete, ())

    def test_forged_revision_receipt_denied(self):
        from ucie_miner.ucie_v2_b3_b4_b5_revision_review_v01 import (
            review_revision_sensitive_study,
        )
        result = review_revision_sensitive_study(self.complete, ())
        forged = deepcopy(result)
        forged["candidate_source_sha_authenticated"] = True
        with mock.patch.object(a, "review_revision_sensitive_study",
                               return_value=forged):
            with self.assertRaises(a.LibraryAssetError):
                a.assemble_original_library_assets(self.complete, ())

    def test_stable_no_side_effects_or_approval(self):
        x = a.assemble_original_library_assets(self.complete, ())
        for field in ("source_facts_independently_verified",
                      "real_upstream_tested", "actual_human_evidence",
                      "independent_qa_verified", "rights_approved",
                      "release_authorized", "automatic_training",
                      "automatic_promotion", "automatic_distribution"):
            self.assertIs(x[field], False)
        self.assertFalse(x["machine"]["external_code_execution_allowed"])
        self.assertFalse(x["machine"]["export_allowed"])
        self.assertEqual(x["network_requests"], 0)
        self.assertEqual(x["operating_database_writes"], 0)
