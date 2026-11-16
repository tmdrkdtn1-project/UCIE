"""UCIE P3/P6 exact Virtual Library pagination: real first-party behavior QA.

Twenty-seven distinct UCIE-authored source-linked synthetic evidence revisions
exceed the old single-page limit (20). Verify deterministic complete retrieval,
negative page guards and CLI reachability without source execution/GET/DB writes.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from test_ucie_positive_capability_discovery import handoff_two_evidence_revisions
from ucie_miner.library_exact_index import (
    ExactLibraryError, exact_search_linked_public_candidates,
    search_exact_existing_public_library,
)
from ucie_miner.library_search import main, MAX_PAGE_OFFSET

KEY = ("repo:modelcontextprotocol/python-sdk", "MCP/API",
       "PUBLIC_TECHNICAL_EVIDENCE", "EXCEPTION_HANDLING")


def synthetic_linked_batch(n: int = 27) -> dict:
    base = handoff_two_evidence_revisions()
    template = base["tasks"][0]
    base["tasks"] = []
    for i in range(n):
        row = deepcopy(template)
        row["candidate_id_sha256"] = sha256(
            f"UCIE-only synthetic candidate:{i}".encode("ascii")).hexdigest()
        row["evidence_sha256"] = sha256(
            f"UCIE-only synthetic revision:{i}".encode("ascii")).hexdigest()
        base["tasks"].append(row)
    base["source_revisions"] = n
    base["linked_revisions"] = n
    base["pending_source_revisions"] = 0
    return base


class UCIEP3ExactPaginationFunctionalTests(unittest.TestCase):
    def setUp(self):
        self.handoff = synthetic_linked_batch()
        self.baseline = exact_search_linked_public_candidates(
            self.handoff, queries=(KEY,), limit=20)

    def search(self, *, queries=(KEY,), limit=10, offset=0):
        return exact_search_linked_public_candidates(
            self.handoff, queries=queries, limit=limit, offset=offset)

    def test_01_27_distinct_revisions_accessible_across_three_pages(self):
        pages = [self.search(offset=i) for i in (0, 10, 20)]
        rows = [p["items"][0] for p in pages]
        ids = [x["library_item_id"] for item in rows for x in item["items"]]
        self.assertEqual(len(ids), 27)
        self.assertEqual(len(set(ids)), 27)
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(
            [x["returned_count"] for x in rows], [10, 10, 7])
        self.assertEqual(
            [x["omitted_count"] for x in rows], [17, 7, 0])
        self.assertEqual(
            [x["next_offset"] for x in rows], [10, 20, None])
        self.assertEqual(
            [x["has_more"] for x in rows], [True, True, False])
        self.assertEqual(
            [x["page_offset"] for x in rows], [0, 10, 20])
        self.assertEqual(
            [x["total_matches"] for x in rows], [27] * 3)
        self.assertTrue(pages[0]["has_more_any_query"])
        self.assertFalse(pages[-1]["has_more_any_query"])
        self.assertFalse(pages[-1]["v1_accepted"])
        self.assertFalse(pages[-1]["auto_promoted"])
        self.assertEqual(pages[-1]["network_requests"], 0)
        self.assertEqual(pages[-1]["operating_database_writes"], 0)
        self.assertTrue(all(not x["export_allowed"]
                            for item in rows for x in item["items"]))

    def test_02_fully_paged_output_matches_old_unpaged_first20_and_tail(self):
        full = self.search(limit=20, offset=0)["items"][0]["items"]
        second = self.search(limit=20, offset=20)["items"][0]["items"]
        self.assertEqual(self.baseline["items"][0]["items"], full)
        self.assertEqual(len(full), 20)
        self.assertEqual(len(second), 7)
        self.assertEqual([x["library_item_id"] for x in full + second],
                         sorted(x["library_item_id"] for x in full+second))
        self.assertEqual(self.baseline["selected_strategy"], "LINEAR_EXACT_SCAN")
        self.assertFalse(self.baseline["index_built"])

    def test_03_index_and_linear_pages_are_exactly_equivalent(self):
        absent = KEY[:3] + ("UCIE_NOT_PRESENT",)
        for offset in (0, 1, 9, 10, 20, 26, 27, 30):
            with self.subTest(offset=offset):
                scan = self.search(offset=offset)
                idx = self.search(queries=(KEY, absent, KEY), offset=offset)
                self.assertEqual(scan["items"][0], idx["items"][0])
                self.assertEqual(scan["items"][0], idx["items"][2])
                self.assertEqual(idx["items"][1]["total_matches"], 0)
                self.assertFalse(idx["items"][1]["has_more"])
                self.assertFalse(idx["production_index_replaced"])
                self.assertTrue(idx["index_built"])

    def test_04_page_beyond_total_returns_empty_with_no_false_cursor(self):
        page = self.search(offset=100)["items"][0]
        self.assertEqual(page["items"], [])
        self.assertEqual(page["returned_count"], 0)
        self.assertEqual(page["omitted_before_count"], 27)
        self.assertEqual(page["omitted_count"], 0)
        self.assertIsNone(page["next_offset"])
        self.assertFalse(page["has_more"])
        self.assertEqual(page["total_matches"], 27)

    def test_05_missing_source_linkage_still_no_go_with_offset(self):
        incomplete = dict(self.handoff)
        incomplete["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        incomplete["pending_source_revisions"] = 1
        p = exact_search_linked_public_candidates(
            incomplete, queries=(KEY,), offset=10)
        self.assertEqual(p["status"], "INCOMPLETE_SOURCE_LINKED_CATALOG_NO_GO")
        self.assertEqual(p["page_offset"], 10)
        self.assertEqual(p["items"], [])
        self.assertFalse(p["has_more_any_query"])
        self.assertFalse(p["v1_accepted"])

    def test_06_invalid_offsets_rejected_before_ledger_or_processing(self):
        for bad in (-1, True, False, -100, MAX_PAGE_OFFSET + 1,
                    3.5, "10", None, [], {}):
            with self.subTest(bad=bad):
                with patch("ucie_miner.library_exact_index._checked_handoff",
                           side_effect=AssertionError("source read not allowed")):
                    with self.assertRaises(ExactLibraryError):
                        exact_search_linked_public_candidates(
                            self.handoff, queries=(KEY,), offset=bad)

    def test_07_exact_wrapper_preserves_root_and_does_not_write(self):
        with TemporaryDirectory(prefix="UCIE_P3_P6_") as d:
            root = Path(d) / "UCIE"
            root.mkdir()
            with patch("ucie_miner.library_exact_index.prepare_verification_handoff",
                       return_value=self.handoff) as read, \
                 patch("urllib.request.urlopen",
                       side_effect=AssertionError("external GET forbidden")):
                page = search_exact_existing_public_library(
                    root, queries=(KEY,), limit=10, offset=20)
            read.assert_called_once_with(root)
            self.assertEqual(page["items"][0]["returned_count"], 7)
            self.assertFalse(list(root.iterdir()))
            self.assertEqual(page["operating_database_writes"], 0)

    def test_08_exact_wrapper_bad_page_never_loads_source(self):
        with TemporaryDirectory(prefix="UCIE_P3_P6_") as d:
            root = Path(d) / "UCIE"
            root.mkdir()
            with patch("ucie_miner.library_exact_index.prepare_verification_handoff",
                       side_effect=AssertionError("source read not allowed")) as reader:
                with self.assertRaises(ExactLibraryError):
                    search_exact_existing_public_library(
                        root, queries=(KEY,), limit=10, offset=-1)
            reader.assert_not_called()

    def test_09_user_cli_exact_paging_is_reachable_without_opt_in(self):
        args = ["ucie_library_search", "--source-id", KEY[0],
                "--domain", KEY[1], "--kind", KEY[2],
                "--exact-purpose", KEY[3], "--limit", "10", "--offset", "20"]
        with patch("sys.argv", args), \
             patch("ucie_miner.library_exact_index.search_exact_existing_public_library",
                   return_value={"status":"UCIE_SYNTH_PAGED_TEST"}) as query, \
             patch("builtins.print") as printed:
            self.assertEqual(main(), 0)
        self.assertEqual(query.call_args.kwargs["offset"], 20)
        self.assertEqual(query.call_args.kwargs["limit"], 10)
        self.assertEqual(json.loads(printed.call_args.args[0])["status"],
                         "UCIE_SYNTH_PAGED_TEST")

    def test_10_user_cli_default_offset_is_backward_compatible(self):
        args = ["ucie_library_search", "--source-id", KEY[0],
                "--domain", KEY[1], "--kind", KEY[2],
                "--exact-purpose", KEY[3]]
        with patch("sys.argv", args), \
             patch("ucie_miner.library_exact_index.search_exact_existing_public_library",
                   return_value={"status":"UCIE_UNCHANGED_DEFAULT"}) as query, \
             patch("builtins.print"):
            self.assertEqual(main(), 0)
        self.assertNotIn("offset", query.call_args.kwargs)

    def test_11_user_cli_bad_offset_fails_closed_before_search(self):
        for bad in ("-1", str(MAX_PAGE_OFFSET+1)):
            with self.subTest(bad=bad), \
                 patch("sys.argv", ["ucie_library_search", "--source-id", KEY[0],
                                    "--domain", KEY[1], "--kind", KEY[2],
                                    "--exact-purpose", KEY[3], "--offset", bad]), \
                 patch("ucie_miner.library_exact_index.search_exact_existing_public_library",
                       side_effect=AssertionError("no real read")) as query, \
                 patch("builtins.print") as printed:
                self.assertEqual(main(), 2)
                self.assertEqual(json.loads(printed.call_args.args[0])["status"],
                                 "FAIL_CLOSED")
                query.assert_not_called()

    def test_12_substring_cli_paging_reuses_existing_api(self):
        with patch("sys.argv", ["ucie_library_search", "--query", "Python",
                                "--offset", "5"]), \
             patch("ucie_miner.library_search.search_existing_public_library",
                   return_value={"status":"UCIE_PREEXISTING_PAGE_SUPPORT"}) as query, \
             patch("builtins.print") as printed:
            self.assertEqual(main(), 0)
        self.assertEqual(query.call_args.kwargs["offset"], 5)
        self.assertEqual(json.loads(printed.call_args.args[0])["status"],
                         "UCIE_PREEXISTING_PAGE_SUPPORT")


if __name__ == "__main__":
    unittest.main()
