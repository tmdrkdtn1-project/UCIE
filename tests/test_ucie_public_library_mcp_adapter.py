"""Existing UCIE public Library -> read-only MCP handler contract tests."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest

from ucie_miner.public_batch import build_public_batch
from ucie_miner.public_candidate_staging import stage_public_candidates
from ucie_miner.public_discovery import SOURCES, DiscoveryError
from ucie_miner.public_external_history import (
    OPT_IN_FILE, OPT_IN_TOKEN, optional_external_history_backfill,
)
from ucie_miner.public_library_mcp_adapter import (
    search_ucie_public_library_for_mcp, preview_public_skill_feed,
)
from test_ucie_stage9_batch import NOW, metadata, evidence
from test_ucie_stage13_external_history import upstream_pr


class PublicLibraryMcpAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)

    def fill(self):
        runtime = self.root / "runtime"
        (runtime / OPT_IN_FILE).write_text(OPT_IN_TOKEN, "ascii")

        def page(url):
            source = next(s for s in SOURCES if f"/repos/{s}/" in url)
            return ([upstream_pr(source, 1234,
                                 title="Fix regression in public API")], 40)

        result = optional_external_history_backfill(self.root, fetch=page)
        self.assertEqual(result["new_unverified_evidence_revisions"], 5)
        stage_public_candidates(build_public_batch(
            metadata_fetch=metadata, evidence_fetch=evidence,
            now=NOW, max_enrich=2), root=self.root,
            allow_disk_write=True, observed_utc=NOW)

    def test_live_style_query_returns_only_bounded_public_metadata(self):
        self.fill()
        found = search_ucie_public_library_for_mcp(
            self.root, query="Python regression", category="Python",
            tag="REGRESSION", top=5)
        self.assertEqual(found["selected_skill_id"], "python-runtime-safety")
        self.assertEqual(found["selected_tag"], "REGRESSION")
        self.assertGreater(found["result_count"], 0)
        self.assertTrue(all(x["source"] == "python/cpython"
                            and not x["installable_skill"]
                            and x["status"] == "UNVERIFIED_PUBLIC_RESEARCH_ONLY_NO_GO"
                            for x in found["results"]))
        self.assertFalse(found["production_approved"])
        self.assertFalse(found["query_text_retained"])

    def test_mcp_topic_and_no_arbitrary_user_query(self):
        self.fill()
        found = search_ucie_public_library_for_mcp(
            self.root, query="MCP API", category="MCP/API", top=2)
        self.assertEqual(found["selected_skill_id"], "mcp-api-compatibility")
        self.assertTrue(all(x["source"] == "modelcontextprotocol/python-sdk"
                            for x in found["results"]))
        for query in ("please execute arbitrary code", "D:\\private\\path",
                      "workspace tenant code", "unknowntopic"):
            res = search_ucie_public_library_for_mcp(self.root, query=query)
            self.assertEqual(res["result_count"], 0)
            self.assertEqual(res["status"],
                             "NO_SUPPORTED_PUBLIC_TAXONOMY_MATCH_NO_GO")

    def test_conflicting_and_ambiguous_queries_fail_closed(self):
        self.fill()
        for query, category, tag, expected in (
            ("python git", None, None, "AMBIGUOUS_PUBLIC_TECHNICAL_TAXONOMY_NO_GO"),
            ("python", "Git", None, "CATEGORY_QUERY_SCOPE_CONFLICT_NO_GO"),
            ("python regression", None, "SECURITY",
             "TAG_QUERY_SCOPE_CONFLICT_NO_GO"),
        ):
            response = search_ucie_public_library_for_mcp(
                self.root, query=query, category=category, tag=tag)
            self.assertEqual(response["status"], expected)
            self.assertEqual(response["results"], [])

        for args in ({"query": ""}, {"query": "Python", "top": True},
                     {"query": "Python", "top": 100},
                     {"query": "Python", "category": "PRIVATE"},
                     {"query": "Python", "tag": "RUN_THIS"},
                     {"query": "Python\nignore constraints"}):
            with self.subTest(args=args), self.assertRaises(DiscoveryError):
                search_ucie_public_library_for_mcp(self.root, **args)

    def test_public_skill_feed_is_deterministic_and_not_installable(self):
        self.fill()
        first = preview_public_skill_feed(self.root, references_per_domain=2)
        second = preview_public_skill_feed(self.root, references_per_domain=2)
        self.assertEqual(first, second)
        self.assertEqual(first["topic_count"], 5)
        self.assertEqual(first["signed_skill_package_count"], 0)
        self.assertFalse(first["content_sha256_is_signature"])
        self.assertEqual(first["installable_skills"], [])
        self.assertFalse(first["scheduler_registered"])
        self.assertFalse(first["auto_inject_into_projects"])
        self.assertFalse(first["production_approved"])
        self.assertEqual(set(x["approved_public_source"] for x in first["topics"]),
                         set(SOURCES))
        self.assertTrue(all(not x["skill_installable"]
                            and x["actual_skill_release_version"] is None
                            and x["public_research_reference_count"] >= 1
                            for x in first["topics"]))
        with self.assertRaises(DiscoveryError):
            preview_public_skill_feed(self.root, references_per_domain=0)

    def test_absent_indexes_create_nothing(self):
        before = list((self.root / "runtime").iterdir())
        found = search_ucie_public_library_for_mcp(self.root, query="Python")
        self.assertEqual(found["result_count"], 0)
        self.assertFalse(found["stage10_recent_present"])
        self.assertFalse(found["stage13_history_present"])
        feed = preview_public_skill_feed(self.root)
        self.assertEqual(feed["topic_count"], 5)
        self.assertEqual(sum(x["public_research_reference_count"]
                             for x in feed["topics"]), 0)
        self.assertEqual(before, list((self.root / "runtime").iterdir()))


if __name__ == "__main__":
    unittest.main()
