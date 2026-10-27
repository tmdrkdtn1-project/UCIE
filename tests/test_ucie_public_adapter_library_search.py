"""Focused W03 existing-collector adapter and W04 real read-only Library search."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_source_adapter import (
    adapt_existing_public_discovery, adapter_plan,
)
from ucie_miner.library_search import (
    search_existing_public_library, search_linked_public_candidates,
    LibrarySearchError,
)
from ucie_miner.public_candidate_learning import (
    OPT_IN_FILENAME, OPT_IN_TOKEN, optional_hourly_review_learning,
)
from ucie_miner.public_candidate_staging import stage_public_candidates, DB_NAME
from ucie_miner.verification_handoff import prepare_verification_handoff
from test_ucie_stage11_hourly_stage import fixture_batch
from test_ucie_stage9_batch import metadata, NOW


class W03SourceAdapterTests(unittest.TestCase):
    def test_exact_existing_route_only_without_a_get(self):
        p = adapter_plan("repo:python/cpython")
        self.assertEqual(p["cursor"], {"page": 1})
        self.assertEqual(p["existing_collector_route"],
                         "https://api.github.com/repos/python/cpython/"
                         "pulls?state=closed&sort=updated&direction=desc&per_page=20")
        self.assertFalse(p["registry_grants_network_permission"])
        self.assertFalse(p["transport_invoked"])
        self.assertEqual(p["persistent_writes"], 0)

    def test_research_docs_invalid_pages_are_never_generic_github_gets(self):
        for source in ("research:GH Archive", "doc:python/cpython",
                       "repo:unknown/private"):
            with self.subTest(source=source):
                with self.assertRaises(DiscoveryError):
                    adapter_plan(source)
        for page in (0, True, 4):
            with self.subTest(page=page):
                with self.assertRaises(DiscoveryError):
                    adapter_plan("repo:python/cpython", page=page)

    def test_genuine_existing_stage9_metadata_callback_is_reused(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("new network forbidden")):
            result = adapt_existing_public_discovery(
                source_ids=("repo:python/cpython",),
                fetch=metadata, now=NOW, backfill_pages=1)
        self.assertEqual(result["schema"], "UCIE_W03_PUBLIC_DISCOVERY_ADAPTER_V1")
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["transport_callback_invocations"], 1)
        self.assertLessEqual(result["candidate_leads_total"], 20)
        self.assertEqual(result["sources"][0]["source_id"], "repo:python/cpython")
        self.assertEqual(result["persistent_writes"], 0)
        self.assertFalse(result["auto_promoted"])
        self.assertFalse(result["scheduler_registered"])

    def test_unapproved_source_stops_before_fetch(self):
        requested = []
        def fetch(url):
            requested.append(url)
            return []
        for ids in (
            ("research:GH Archive",),
            ("repo:python/cpython", "repo:python/cpython"),
            ("repo:unknown/private",),
            ("doc:python/cpython",),
        ):
            with self.subTest(ids=ids):
                with self.assertRaises(DiscoveryError):
                    adapt_existing_public_discovery(source_ids=ids, fetch=fetch)
        self.assertEqual(requested, [])


class W04ReadOnlyLibrarySearchTests(unittest.TestCase):
    def test_existing_stage10_and_stage12_real_fixture_search_no_writes(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            batch = fixture_batch(
                root=root,
                sources=("python/cpython", "PowerShell/PowerShell",
                         "git/git", "modelcontextprotocol/python-sdk",
                         "actions/runner-images"),
                max_enrich=1, include_git_commits=True,
                include_docs=False, include_advisories=False,
                backfill_pages=1)
            stage_public_candidates(batch, root=root, allow_disk_write=True)
            (runtime / OPT_IN_FILENAME).write_text(OPT_IN_TOKEN, encoding="ascii")
            review = optional_hourly_review_learning(root)
            self.assertEqual(review["new_review_proposals"], 2)
            handoff = prepare_verification_handoff(root)
            self.assertEqual(handoff["status"], "LINKED_UNVERIFIED_NO_GO")
            staged = runtime / DB_NAME
            reviewdb = runtime / "stage12_unverified_review.sqlite3"
            before = (staged.read_bytes(), reviewdb.read_bytes())
            with patch("urllib.request.urlopen",
                       side_effect=AssertionError("no public network")):
                out = search_existing_public_library(root, limit=10)
                filtered = search_existing_public_library(root, query="python")
                git = search_existing_public_library(root, source_id="repo:git/git")
            after = (staged.read_bytes(), reviewdb.read_bytes())
            self.assertEqual(before, after)
            self.assertEqual(out["status"],
                             "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO")
            self.assertEqual(out["source_linked_count"], 2)
            self.assertEqual(out["total_matches"], 2)
            self.assertEqual(out["returned_count"], 2)
            self.assertGreaterEqual(filtered["total_matches"], 1)
            self.assertEqual(git["total_matches"], 1)
            for item in out["items"]:
                self.assertEqual(item["lifecycle"], "UNVERIFIED_CANDIDATE_ONLY")
                self.assertFalse(item["export_allowed"])
                self.assertFalse(item["human_approved"])
            self.assertFalse(out["full_library_implemented"])
            self.assertFalse(out["search_index_persisted"])
            self.assertEqual(out["operating_database_writes"], 0)
            self.assertEqual(out["network_requests"], 0)

    def test_lagging_or_missing_stage12_queue_never_emits_library_items(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / "UCIE"
            (root / "runtime").mkdir(parents=True)
            out = search_existing_public_library(root)
            self.assertEqual(out["status"], "SOURCE_LINKAGE_INCOMPLETE_NO_GO")
            self.assertEqual(out["items"], [])
            self.assertEqual(out["approved_or_exportable_items"], 0)

    def test_search_filters_reject_script_or_excessive_limit(self):
        handoff = {
            "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
            "status": "REVIEW_LEDGER_ABSENT_NO_GO",
            "source_revisions": 0,
            "linked_revisions": 0,
            "pending_source_revisions": 0,
            "tasks": [], "auto_promoted": False,
            "production_approved": False, "deploy_allowed": False,
        }
        for kwargs in (
            {"query": "hello\nworld"},
            {"kind": "UCIE_EXPERIENCE"},
            {"source_id": "repo:unknown/evil?url="},
            {"limit": 999},
            {"limit": True},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(LibrarySearchError):
                    search_linked_public_candidates(handoff, **kwargs)


if __name__ == "__main__":
    unittest.main()
