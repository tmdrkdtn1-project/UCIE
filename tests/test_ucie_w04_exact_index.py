"""W04 optional real exact index: preserve default substring search and all UCIE ledgers."""
from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.library_exact_index import (
    SCHEMA, ExactLibraryError,
    exact_search_linked_public_candidates, search_exact_existing_public_library,
)
from ucie_miner.library_search import search_linked_public_candidates, main
from ucie_miner.public_candidate_staging import stage_public_candidates, DB_NAME
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)
from test_ucie_stage11_hourly_stage import fixture_batch
from test_ucie_positive_capability_discovery import handoff_two_evidence_revisions


class W04ExactIndexTests(unittest.TestCase):
    def test_batch_exact_results_match_legacy_original_public_evidence(self):
        handoff = handoff_two_evidence_revisions()
        key = ("repo:modelcontextprotocol/python-sdk", "MCP/API",
               "PUBLIC_TECHNICAL_EVIDENCE", "EXCEPTION_HANDLING")
        absent = key[:3] + ("NO_MATCHING_PURPOSE",)
        exact = exact_search_linked_public_candidates(
            handoff, queries=(key, absent), limit=10)
        old = search_linked_public_candidates(
            handoff, domain="MCP/API", kind="PUBLIC_TECHNICAL_EVIDENCE",
            source_id=key[0], limit=10)
        self.assertEqual(exact["schema"], SCHEMA)
        self.assertEqual(exact["catalog_items"], 2)
        self.assertEqual(exact["query_count"], 2)
        self.assertEqual(exact["items"][0]["total_matches"], 2)
        self.assertEqual(exact["items"][1]["total_matches"], 0)
        self.assertEqual(
            {i["library_item_id"] for i in exact["items"][0]["items"]},
            {i["library_item_id"] for i in old["items"]})
        self.assertEqual(exact["linear_scan_comparisons_for_same_queries"], 4)
        self.assertEqual(exact["index_build_plus_lookup_operations"], 4)
        self.assertFalse(exact["production_index_replaced"])
        self.assertFalse(exact["index_persisted"])
        self.assertEqual(exact["network_requests"], 0)
        self.assertEqual(exact["operating_database_writes"], 0)
        self.assertEqual(exact["approved_or_exportable_items"], 0)
        self.assertTrue(all(not i["export_allowed"] and not i["human_approved"]
                            for i in exact["items"][0]["items"]))

    def test_single_query_not_claimed_faster_just_because_index_exists(self):
        handoff = handoff_two_evidence_revisions()
        key = ("repo:modelcontextprotocol/python-sdk", "MCP/API",
               "PUBLIC_TECHNICAL_EVIDENCE", "EXCEPTION_HANDLING")
        out = exact_search_linked_public_candidates(handoff, queries=(key,))
        self.assertEqual(out["index_build_plus_lookup_operations"], 3)
        self.assertEqual(out["linear_scan_comparisons_for_same_queries"], 2)
        self.assertFalse(out["production_index_replaced"])
        self.assertNotIn("guaranteed_faster", out)

    def test_cost_policy_selects_linear_for_one_query_and_equal_cost(self):
        handoff = handoff_two_evidence_revisions()
        key = ("repo:modelcontextprotocol/python-sdk", "MCP/API",
               "PUBLIC_TECHNICAL_EVIDENCE", "EXCEPTION_HANDLING")
        single = exact_search_linked_public_candidates(
            handoff, queries=(key,), limit=10)
        self.assertEqual(single["selected_strategy"], "LINEAR_EXACT_SCAN")
        self.assertFalse(single["index_built"])
        self.assertIsNone(single["unique_index_keys"])
        self.assertEqual(single["executed_strategy_estimated_operations"], 2)
        self.assertEqual(single["alternative_strategy_estimated_operations"], 3)
        self.assertEqual(single["items"][0]["total_matches"], 2)
        # 2 * 2 = 2 + 2: tie must not build the index needlessly.
        tie = exact_search_linked_public_candidates(
            handoff, queries=(key, key), limit=10)
        self.assertEqual(tie["selected_strategy"], "LINEAR_EXACT_SCAN")
        self.assertEqual(tie["linear_scan_comparisons_for_same_queries"], 4)
        self.assertEqual(tie["index_build_plus_lookup_operations"], 4)
        self.assertFalse(tie["index_built"])

    def test_cost_policy_selects_shared_index_for_three_queries(self):
        handoff = handoff_two_evidence_revisions()
        key = ("repo:modelcontextprotocol/python-sdk", "MCP/API",
               "PUBLIC_TECHNICAL_EVIDENCE", "EXCEPTION_HANDLING")
        missing = key[:3] + ("NO_SUCH_PURPOSE",)
        batch = exact_search_linked_public_candidates(
            handoff, queries=(key, missing, key), limit=1)
        self.assertEqual(batch["selected_strategy"], "BUILD_ONCE_COMPOSITE_INDEX")
        self.assertTrue(batch["index_built"])
        self.assertEqual(batch["unique_index_keys"], 1)
        self.assertEqual(batch["linear_scan_comparisons_for_same_queries"], 6)
        self.assertEqual(batch["index_build_plus_lookup_operations"], 5)
        self.assertEqual(batch["executed_strategy_estimated_operations"], 5)
        self.assertEqual(batch["items"][0]["total_matches"], 2)
        self.assertEqual(batch["items"][0]["omitted_count"], 1)
        self.assertEqual(batch["items"][1]["total_matches"], 0)
        self.assertEqual(batch["items"][2]["items"], batch["items"][0]["items"])
        self.assertEqual(batch["operating_database_writes"], 0)
        self.assertFalse(batch["auto_promoted"])

    def test_policy_choices_preserve_identical_results_across_scan_and_index(self):
        handoff = handoff_two_evidence_revisions()
        key = ("repo:modelcontextprotocol/python-sdk", "MCP/API",
               "PUBLIC_TECHNICAL_EVIDENCE", "EXCEPTION_HANDLING")
        scan = exact_search_linked_public_candidates(
            handoff, queries=(key,), limit=10)
        indexed = exact_search_linked_public_candidates(
            handoff, queries=(key, key, key), limit=10)
        self.assertEqual(scan["items"][0], indexed["items"][0])
        self.assertEqual(scan["items"][0], indexed["items"][2])
        self.assertNotIn("elapsed_time_guaranteed_faster", indexed)
        self.assertFalse(indexed["production_index_replaced"])

    def test_unapproved_sources_and_invalid_fields_are_denied(self):
        good = ("repo:python/cpython", "Python",
                "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT")
        for key in (
            ("research:GH Archive", "Python", good[2], good[3]),
            ("repo:unapproved/repo", "Python", good[2], good[3]),
            ("doc:python/cpython", "Python", good[2], good[3]),
            ("repo:python/cpython", "python", good[2], good[3]),
            ("repo:python/cpython", "Python", "REUSABLE_SKILL", good[3]),
            ("repo:python/cpython", "Python", good[2], "IGNORE; DROP TABLE"),
        ):
            with self.subTest(key=key):
                with self.assertRaises(ExactLibraryError):
                    exact_search_linked_public_candidates(
                        handoff_two_evidence_revisions(), queries=(key,))
        with self.assertRaises(ExactLibraryError):
            exact_search_linked_public_candidates(
                handoff_two_evidence_revisions(), queries=(good,) * 33)
        with self.assertRaises(ExactLibraryError):
            exact_search_linked_public_candidates(
                handoff_two_evidence_revisions(), queries=(good,), limit=True)

    def test_validated_sqlite_stage10_12_15_real_reader_preserves_all_bytes(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            batch = fixture_batch(
                root=root, sources=(
                    "python/cpython", "PowerShell/PowerShell", "git/git",
                    "modelcontextprotocol/python-sdk", "actions/runner-images"),
                max_enrich=1, include_git_commits=True,
                include_docs=False, include_advisories=False, backfill_pages=1)
            stage_public_candidates(batch, root=root, allow_disk_write=True)
            (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="ascii")
            self.assertEqual(optional_hourly_review_learning(root)["new_review_proposals"], 2)
            stage10 = runtime / DB_NAME
            stage12 = runtime / "stage12_unverified_review.sqlite3"
            before = (stage10.read_bytes(), stage12.read_bytes())
            queries = (
                ("repo:git/git", "Git", "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT"),
                ("repo:python/cpython", "Python", "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT"),
            )
            with patch("urllib.request.urlopen",
                       side_effect=AssertionError("no external GET")):
                out = search_exact_existing_public_library(
                    root, queries=queries, limit=10)
            self.assertEqual(before, (stage10.read_bytes(), stage12.read_bytes()))
            self.assertEqual(out["catalog_items"], 2)
            self.assertEqual(out["query_count"], 2)
            self.assertFalse(out["index_persisted"])
            self.assertEqual(out["operating_database_writes"], 0)

    def test_incomplete_stage12_never_emits_made_up_approved_results(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / "UCIE"
            (root / "runtime").mkdir(parents=True)
            key = ("repo:python/cpython", "Python",
                   "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT")
            out = search_exact_existing_public_library(root, queries=(key,))
            self.assertEqual(out["status"], "INCOMPLETE_SOURCE_LINKED_CATALOG_NO_GO")
            self.assertEqual(out["items"], [])
            self.assertFalse(out["v1_accepted"])

    def test_default_cli_unchanged_and_explicit_cli_dispatch_is_bounded(self):
        from unittest.mock import ANY
        exact_args = ["ucie_library_search", "--source-id", "repo:python/cpython",
                      "--domain", "Python", "--kind", "PUBLIC_TECHNICAL_EVIDENCE",
                      "--exact-purpose", "API_CONTRACT",
                      "--exact-purpose", "CONCURRENCY"]
        with patch("sys.argv", exact_args):
            with patch("ucie_miner.library_exact_index.search_exact_existing_public_library",
                       return_value={"schema": SCHEMA, "status": "MOCK_QUERY"}) as query:
                with patch("builtins.print") as printed:
                    self.assertEqual(main(), 0)
        query.assert_called_once_with(
            ANY,
            queries=(("repo:python/cpython", "Python",
                      "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT"),
                     ("repo:python/cpython", "Python",
                      "PUBLIC_TECHNICAL_EVIDENCE", "CONCURRENCY")),
            limit=10)
        self.assertEqual(json.loads(printed.call_args.args[0])["status"], "MOCK_QUERY")
        with patch("sys.argv", exact_args + ["--query", "python"]):
            with patch("builtins.print") as printed:
                self.assertEqual(main(), 2)
        self.assertEqual(json.loads(printed.call_args.args[0])["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
