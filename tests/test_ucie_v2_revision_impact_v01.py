"""B3 exact-source change impact tests: no unrequested scans, tests or release."""
from __future__ import annotations

from unittest import TestCase, mock

from ucie_miner import ucie_v2_revision_impact_v01 as b3


def signal(sid: str, *, previous: str | None = None,
           candidate: str | None = None) -> dict:
    if previous is None and sid in b3.PINS:
        previous = b3.PINS[sid]
    if candidate is None:
        size = len(b3.PINS.get(sid, "x" * 40))
        candidate = "a" * size
    return {"source_id": sid, "previous_pin": previous,
            "candidate_pin": candidate}


class UCIEB3RevisionImpactTests(TestCase):
    def test_reads_existing_ucie_capsule_books_and_composer(self):
        g = b3.build_current_graph()
        self.assertEqual(g["status"], "READ_ONLY_SOURCE_AND_SKILLBOOK_GRAPH_REVIEW")
        self.assertEqual(len(g["assets"]), 5)
        self.assertFalse(g["autonomous_generalization_verified"])
        self.assertEqual(g["operating_database_writes"], 0)
        self.assertEqual(g["graph_scope"], "FIRST_FIVE_PINNED_ASSETS_ONLY")
        self.assertFalse(g["global_asset_coverage_verified"])

    def test_mcp_changed_only_mcp_assets(self):
        x = b3.assess_revision_impacts((
            signal("repo:modelcontextprotocol/python-sdk"),))
        self.assertEqual(x["affected_assets"], sorted([b3.MCP_ASSET, b3.MCP_SKILLBOOK]))
        self.assertNotIn(b3.PRINCIPLE, x["affected_assets"])
        self.assertNotIn(b3.PY_BOOK, x["affected_assets"])
        self.assertNotIn(b3.GIT_BOOK, x["affected_assets"])
        self.assertEqual(x["proposed_test_files"], sorted([
            "test_ucie_v2_capsule_v01.py",
            "test_ucie_mcp_guide_local_reader_v01.py",
            "test_ucie_mcp_prompt_regression_v01.py",
        ]))

    def test_python_change_propagates_only_to_principle(self):
        x = b3.assess_revision_impacts((signal("doc:python/cpython"),))
        self.assertEqual(x["affected_assets"], sorted([b3.PY_BOOK, b3.PRINCIPLE]))
        self.assertEqual(x["proposed_test_files"], sorted([
            "test_ucie_skillbook_product_v01.py",
            "test_ucie_skillbook_principle_composer_v01.py",
        ]))
        self.assertNotIn(b3.GIT_BOOK, x["affected_assets"])

    def test_git_change_propagates_only_to_principle(self):
        x = b3.assess_revision_impacts((signal("doc:git/git"),))
        self.assertEqual(x["affected_assets"], sorted([b3.GIT_BOOK, b3.PRINCIPLE]))
        self.assertNotIn(b3.PY_BOOK, x["affected_assets"])
        self.assertNotIn(b3.MCP_ASSET, x["affected_assets"])

    def test_two_source_changes_dedupe_shared_principle_trial(self):
        x = b3.assess_revision_impacts((
            signal("doc:git/git"), signal("doc:python/cpython")))
        self.assertEqual(x["affected_assets"], sorted([
            b3.GIT_BOOK, b3.PY_BOOK, b3.PRINCIPLE]))
        self.assertEqual(x["proposed_test_files"].count(
            "test_ucie_skillbook_principle_composer_v01.py"), 1)

    def test_unlinked_approved_powershell_never_triggers_test(self):
        x = b3.assess_revision_impacts((
            signal("repo:PowerShell/PowerShell", previous=None),))
        self.assertEqual(x["proposed_test_files"], [])
        self.assertEqual(x["affected_assets"], [])
        self.assertIn("repo:PowerShell/PowerShell",
                      x["unlinked_approved_source_ids"])

    def test_unchanged_pin_does_not_trigger(self):
        x = b3.assess_revision_impacts((
            signal("doc:git/git", candidate=b3.PINS["doc:git/git"]),))
        self.assertEqual(x["proposed_test_files"], [])
        self.assertEqual(x["status"], "NO_LINKED_RETEST_IN_BOUNDED_GRAPH")

    def test_empty_batch_is_no_action(self):
        x = b3.assess_revision_impacts(())
        self.assertEqual(x["affected_assets"], [])
        self.assertEqual(x["proposed_test_files"], [])

    def test_mixed_unrelated_and_relevant_does_not_expand(self):
        x = b3.assess_revision_impacts((
            signal("doc:python/cpython"),
            signal("repo:PowerShell/PowerShell"),
        ))
        self.assertEqual(x["affected_assets"], sorted([b3.PY_BOOK, b3.PRINCIPLE]))
        self.assertNotIn(b3.MCP_ASSET, x["affected_assets"])
        self.assertNotIn(b3.GIT_BOOK, x["affected_assets"])

    def test_false_deployment_qa_and_execution_never_published(self):
        x = b3.assess_revision_impacts((signal("doc:git/git"),))
        for field in ("candidate_pin_independently_authenticated",
                      "tests_executed", "independent_qa_verified",
                      "customer_release_authorized", "automatic_scheduling",
                      "auto_promoted", "model_trained"):
            self.assertIs(x[field], False)
        self.assertEqual(x["network_requests"], 0)
        self.assertEqual(x["operating_database_writes"], 0)
        self.assertFalse(x["global_asset_coverage_verified"])

    def test_invalid_unapproved_source_rejected(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((
                signal("repo:external/unapproved", previous=None),))

    def test_research_only_source_rejected(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((
                signal("research:open-web", previous=None),))

    def test_stale_old_source_pin_holds(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((
                signal("doc:python/cpython", previous="b"*64),))

    def test_unknown_source_with_forged_previous_pin_holds(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((
                signal("repo:PowerShell/PowerShell", previous="a"*40),))

    def test_duplicate_source_holds_all(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((
                signal("doc:git/git"), signal("doc:git/git"),))

    def test_wrong_pin_length_holds(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((
                signal("doc:git/git", candidate="a"*40),))

    def test_nonhex_and_uppercase_holds(self):
        for candidate in ("z"*64, "A"*64, "0"*66):
            with self.subTest(candidate=candidate[:3]):
                with self.assertRaises(b3.RevisionImpactError):
                    b3.assess_revision_impacts((
                        signal("doc:git/git", candidate=candidate),))

    def test_signal_shape_and_extra_field_holds(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts(([signal("doc:git/git")]))
        v = signal("doc:git/git")
        v["execute"] = True
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((v,))

    def test_boolean_or_integer_source_holds(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((
                {"source_id": False, "previous_pin": None,
                 "candidate_pin": "a"*40},))

    def test_batch_over_budget_holds(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts(tuple(signal("doc:git/git") for _ in range(9)))

    def test_actual_book_source_drift_holds(self):
        with mock.patch.dict(b3.PINS, {"doc:git/git":"b"*64}):
            with self.assertRaises(b3.RevisionImpactError):
                b3.build_current_graph()

    def test_previous_pin_false_not_equal_to_real_source(self):
        with self.assertRaises(b3.RevisionImpactError):
            b3.assess_revision_impacts((
                signal("repo:modelcontextprotocol/python-sdk", previous=False),))


if __name__ == "__main__":
    import unittest
    unittest.main()
