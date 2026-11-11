"""UCIE W03/W04: only four already-approved other official docs, not fixes."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from ucie_miner import library_approved_document_shelf_v01 as shelf
from ucie_miner import python_scandir_review_v01 as python_trial
from ucie_miner import source_registry
from ucie_miner import public_evidence_routes
from ucie_miner.product_plan import APPROVED_REPOSITORIES


def public(rows=None, *, incomplete=False):
    items = [] if rows is None else rows
    return {
        "schema": shelf.W04_SCHEMA,
        "status": ("SOURCE_LINKAGE_INCOMPLETE_NO_GO" if incomplete
                   else "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"),
        "items": items,
        "returned_count": len(items),
        "total_matches": len(items),
        "network_requests": 0,
        "operating_database_writes": 0,
        "approved_or_exportable_items": 0,
        "auto_promoted": False,
    }


def sample(repo):
    return {
        "source_id": "repo:" + repo,
        "public_url": "https://github.com/" + repo + "/pull/12345",
        "library_item_id": "a" * 64,
        "kind": "PREVENTION_RULE",
        "purpose_code": "SYNTHETIC_REVIEW_ONLY",
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False,
        "export_allowed": False,
    }


class ApprovedSourceCatalogTests(unittest.TestCase):
    def test_all_four_nonpython_sources_have_w01_w02_unapproved_references(self):
        report = shelf.search_approved_document_references("")
        self.assertEqual(report["status"], shelf.STATUS)
        self.assertEqual(report["returned_count"], 4)
        self.assertEqual(set(x["related_repo"] for x in report["items"]),
                         set(APPROVED_REPOSITORIES) - {"python/cpython"})
        for row in report["items"]:
            with self.subTest(source=row["source_id"]):
                source = source_registry.get_source(row["source_id"])
                self.assertEqual(source["public_url"], row["public_url"])
                self.assertEqual(row["kind"], "PUBLIC_TECHNICAL_EVIDENCE")
                self.assertEqual(row["revision_hint"],
                                 "PUBLIC_DOCUMENT_REVISION_NOT_PINNED")
                self.assertEqual(row["version_scope_claim"], "UNDETERMINED")
                self.assertEqual(row["source_license_status"],
                                 "NOT_ATTESTED_PER_REVISION")
                self.assertEqual(row["reference_digest_scope"],
                                 "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES")
                self.assertFalse(row["trial_executed"])
                self.assertFalse(row["human_approved"])
                self.assertFalse(row["export_allowed"])
        self.assertEqual(report["network_requests"], 0)
        self.assertEqual(report["operating_database_writes"], 0)
        self.assertFalse(report["trial_executed_during_search"])

    def test_one_approved_repo_filter_only_returns_its_official_doc(self):
        for repo in APPROVED_REPOSITORIES:
            with self.subTest(repo=repo):
                report = shelf.search_approved_document_references(
                    "", source=repo)
                self.assertEqual(report["source_filter"], repo)
                if repo == "python/cpython":
                    self.assertEqual(report["returned_count"], 0)
                else:
                    self.assertEqual(report["returned_count"], 1)
                    self.assertEqual(report["items"][0]["related_repo"], repo)

    def test_fixed_keyword_matches_have_no_cross_source_leak(self):
        for query, repo in (
            ("Resolve-Path", "PowerShell/PowerShell"),
            ("PowerShell", "PowerShell/PowerShell"),
            ("Git", "git/git"),
            ("MCP", "modelcontextprotocol/python-sdk"),
            ("runner", "actions/runner-images"),
            ("러너", "actions/runner-images"),
            ("프로토콜", "modelcontextprotocol/python-sdk"),
        ):
            with self.subTest(query=query):
                result = shelf.search_approved_document_references(query)
                self.assertEqual(result["returned_count"], 1)
                self.assertEqual(result["items"][0]["related_repo"], repo)

    def test_disallowed_sources_and_unsafe_queries_refused(self):
        for value in (
            "other/private", "research:GH Archive", "repo:git/git",
            "doc:git/git", "Git/git", "../git/git", "a" * 90,
        ):
            with self.subTest(source=value):
                with self.assertRaises(shelf.ApprovedDocumentShelfError):
                    shelf.search_approved_document_references("", source=value)
        for query in ("<script>", "../data", "a" * 81, "a\nb", None, 4):
            with self.subTest(query=str(query)[:20]):
                with self.assertRaises(shelf.ApprovedDocumentShelfError):
                    shelf.search_approved_document_references(query)

    def test_research_only_source_and_w01_url_drift_fail_closed(self):
        expected = source_registry.get_source("doc:git/git")
        for changed in (
            dict(expected, status="RESEARCH_ONLY"),
            dict(expected, public_url="https://unknown.invalid"),
            dict(expected, fetch_authorized_by_this_registry=True),
            dict(expected, license_verdict="APPROVED"),
        ):
            with self.subTest(case=changed):
                original = shelf.get_source

                def source_probe(source_id, original=original):
                    if source_id == "doc:git/git":
                        return changed
                    return original(source_id)

                with patch.object(shelf, "get_source",
                                  side_effect=source_probe):
                    with self.assertRaises(shelf.ApprovedDocumentShelfError):
                        shelf.search_approved_document_references("git")
        other = dict(public_evidence_routes.DOC_ENDPOINTS)
        other["git/git"] = ("https://unknown.invalid", "git")
        with patch.object(shelf, "DOC_ENDPOINTS", other):
            with self.assertRaises(shelf.ApprovedDocumentShelfError):
                shelf.search_approved_document_references("git")

    def test_catalog_search_never_runs_python_trial(self):
        with patch.object(
            python_trial, "_evaluate_only_ucie_synthetic_inputs",
            side_effect=AssertionError("search must never run first-party trial")
        ) as trial:
            out = shelf.search_approved_document_references("mcp")
            self.assertEqual(out["returned_count"], 1)
            trial.assert_not_called()

    def test_same_source_candidate_comparison_is_explicitly_not_fix_proof(self):
        entry = shelf.search_approved_document_references(
            "", source="PowerShell/PowerShell")
        out = shelf.compare_public_prs_by_source(
            entry, public([sample("PowerShell/PowerShell"),
                           sample("python/cpython")]))
        self.assertEqual(out["status"], shelf.PR_PAGE)
        self.assertEqual(len(
            out["public_pr_items_per_source"]["PowerShell/PowerShell"]), 1)
        self.assertFalse(out["same_source_is_same_fix"])
        self.assertFalse(out["independent_version_or_licence_verified"])
        self.assertEqual(out["network_requests"], 0)
        self.assertEqual(out["operating_database_writes"], 0)

    def test_empty_and_incomplete_page_never_fabricates_verified_pr(self):
        entries = shelf.search_approved_document_references(
            "", source="git/git")
        self.assertEqual(
            shelf.compare_public_prs_by_source(entries, None)["status"],
            shelf.UNREQUESTED)
        partial = shelf.compare_public_prs_by_source(
            entries, public([], incomplete=True))
        self.assertEqual(partial["status"], shelf.INCOMPLETE)
        self.assertEqual(partial["public_pr_items_per_source"], {})
        with self.assertRaises(shelf.ApprovedDocumentShelfError):
            shelf.compare_public_prs_by_source(
                entries, public([sample("git/git")], incomplete=True))

    def test_invalid_or_promoted_w04_rows_fail_closed(self):
        entries = shelf.search_approved_document_references(
            "", source="actions/runner-images")
        for attr, val in (
            ("human_approved", True), ("export_allowed", True),
            ("lifecycle", "APPROVED"),
            ("public_url", "https://unknown.invalid/path"),
            ("public_url", "https://github.com/actions/runner-images/issues/1"),
            ("library_item_id", "NOT_SHA"),
            ("kind", "TEST_RECIPE"),
        ):
            with self.subTest(attr=attr):
                row = sample("actions/runner-images")
                row[attr] = val
                with self.assertRaises(shelf.ApprovedDocumentShelfError):
                    shelf.compare_public_prs_by_source(entries, public([row]))

    def test_git_commit_reference_allowed_but_not_wrong_repository(self):
        c = sample("git/git")
        c["public_url"] = "https://github.com/git/git/commit/" + "1" * 40
        out = shelf.compare_public_prs_by_source(
            shelf.search_approved_document_references("git"),
            public([c]))
        self.assertEqual(len(out["public_pr_items_per_source"]["git/git"]), 1)
        c["public_url"] = "https://github.com/git/git/commit/invalid"
        with self.assertRaises(shelf.ApprovedDocumentShelfError):
            shelf.compare_public_prs_by_source(
                shelf.search_approved_document_references("git"),
                public([c]))


if __name__ == "__main__":
    unittest.main()
