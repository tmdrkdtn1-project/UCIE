"""UCIE W03/W04 read-only official-doc recipe + W04 public PR comparison.

Only deterministic first-party sources, no external HTTP, original project
files, operating database, C40, background learning or unapproved export.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from ucie_miner import library_python_recipe_shelf_v01 as shelf
from ucie_miner import python_scandir_review_v01 as review


def w04(*, status="READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
        rows=None):
    if rows is None:
        rows = []
    return {
        "schema": shelf.W04_SCHEMA,
        "status": status,
        "items": rows,
        "returned_count": len(rows),
        "total_matches": len(rows),
        "network_requests": 0,
        "operating_database_writes": 0,
        "approved_or_exportable_items": 0,
        "auto_promoted": False,
    }


def python_pr():
    return {
        "library_item_id": "a" * 64,
        "purpose_code": shelf.RELEVANT_PR,
        "source_id": "repo:python/cpython",
        "public_url": "https://github.com/python/cpython/pull/155365",
        "domain": "Python",
        "kind": "PREVENTION_RULE",
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False,
        "export_allowed": False,
    }


class UCIEW03W04ReferenceShelfTests(unittest.TestCase):
    def test_python_and_korean_queries_find_actual_w02_entry(self):
        for query in ("", "Python", "os.scandir", "scandir", "iterator",
                      "스레드", "반복자", "동시"):
            with self.subTest(query=query):
                result = shelf.search_python_reference_recipe(query)
                self.assertEqual(result["status"], shelf.SHELF_STATUS)
                self.assertEqual(result["returned_count"], 1)
                item = result["items"][0]
                self.assertEqual(item["kind"], "TEST_RECIPE")
                self.assertEqual(item["source_id"], "doc:python/cpython")
                self.assertEqual(item["public_url"],
                                 "https://docs.python.org/3/library/os.html")
                self.assertEqual(item["revision_hint"],
                                 "PUBLIC_DOCUMENT_REVISION_NOT_PINNED")
                self.assertEqual(item["source_license_status"],
                                 "NOT_ATTESTED_PER_REVISION")
                self.assertEqual(item["reference_digest_scope"],
                                 "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES")
                self.assertEqual(item["engine_route"],
                                 "/local/engine?purpose=PYTHON_SCANDIR_SAFE")
                self.assertFalse(item["human_approved"])
                self.assertFalse(item["export_allowed"])

    def test_other_domains_and_malicious_search_are_not_promoted(self):
        for query in ("Git", "PowerShell", "mcp", "notarecipe", "a", "P"):
            result = shelf.search_python_reference_recipe(query)
            self.assertEqual(result["items"], [])
            self.assertEqual(result["total_matches"], 0)
        for query in (None, 12, True, "<script>", "../private",
                      "Python?q=secret", "a" * 81, "a\nb"):
            with self.subTest(query=str(query)[:20]):
                with self.assertRaises(shelf.PythonRecipeShelfError):
                    shelf.search_python_reference_recipe(query)

    def test_search_is_inert_and_never_runs_scandir_trial(self):
        with patch.object(
                review, "_evaluate_only_ucie_synthetic_inputs",
                side_effect=AssertionError("should not execute during search")
        ) as synthetic:
            result = shelf.search_python_reference_recipe("scandir")
            self.assertEqual(result["status"], shelf.SHELF_STATUS)
            self.assertFalse(result["synthetic_trial_executed_during_search"])
            self.assertFalse(result["search_index_persisted"])
            self.assertEqual(result["operating_database_writes"], 0)
            self.assertEqual(result["network_requests"], 0)
            synthetic.assert_not_called()

    def test_distinct_pr_and_official_doc_can_be_compared_without_false_link(self):
        recipe = shelf.search_python_reference_recipe("Python")
        out = shelf.compare_with_w04_window(recipe, w04(rows=[python_pr()]))
        self.assertEqual(out["status"], shelf.COMPARISON_STATUS)
        self.assertEqual(out["official_doc_count"], 1)
        self.assertEqual(out["relevant_public_pr_count_in_page"], 1)
        self.assertEqual(out["relevant_public_prs"][0]["public_url"],
                         "https://github.com/python/cpython/pull/155365")
        self.assertTrue(out["different_evidence_types"])
        self.assertFalse(out["comparison_is_upstream_fix_validation"])
        self.assertFalse(out["reference_version_certified"])
        self.assertFalse(out["auto_promoted"])

    def test_other_pr_purpose_not_falsely_related_to_scandir(self):
        row = python_pr()
        row["purpose_code"] = "API_CONTRACT"
        out = shelf.compare_with_w04_window(
            shelf.search_python_reference_recipe("Python"), w04(rows=[row]))
        self.assertEqual(out["status"], shelf.COMPARISON_STATUS)
        self.assertEqual(out["relevant_public_prs"], [])

    def test_incomplete_public_source_does_not_fabricate_results(self):
        recipe = shelf.search_python_reference_recipe("Python")
        record = shelf.compare_with_w04_window(
            recipe, w04(status="SOURCE_LINKAGE_INCOMPLETE_NO_GO"))
        self.assertEqual(record["status"],
                         "W04_SOURCE_LINKAGE_INCOMPLETE_NO_COMPARISON")
        self.assertEqual(record["relevant_public_prs"], [])
        forged = w04(status="SOURCE_LINKAGE_INCOMPLETE_NO_GO", rows=[python_pr()])
        with self.assertRaises(shelf.PythonRecipeShelfError):
            shelf.compare_with_w04_window(recipe, forged)
        not_requested = shelf.compare_with_w04_window(recipe, None)
        self.assertEqual(not_requested["status"],
                         "W04_NOT_REQUESTED_OR_NO_RECIPE")

    def test_forgeries_rejected_without_emitting_external_text(self):
        recipe = shelf.search_python_reference_recipe("scandir")
        for key, val in (
            ("human_approved", True), ("export_allowed", True),
            ("network_requests", 1), ("auto_promoted", True),
        ):
            with self.subTest(key=key):
                bad = dict(recipe)
                bad[key] = val
                with self.assertRaises(shelf.PythonRecipeShelfError):
                    shelf.compare_with_w04_window(bad, w04())
        for key, val in (
            ("human_approved", True), ("export_allowed", True),
            ("lifecycle", "RELEASED"),
            ("public_url", "https://private.invalid/secret"),
            ("library_item_id", "NOT_A_SHA"),
        ):
            with self.subTest(field=key):
                bad = dict(python_pr())
                bad[key] = val
                with self.assertRaises(shelf.PythonRecipeShelfError):
                    shelf.compare_with_w04_window(recipe, w04(rows=[bad]))


if __name__ == "__main__":
    unittest.main()
