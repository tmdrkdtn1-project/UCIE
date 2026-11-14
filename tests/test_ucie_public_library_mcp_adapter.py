"""Existing UCIE public Library -> read-only MCP handler contract tests."""
from copy import deepcopy
from pathlib import Path
import json
import os
import subprocess
import sys
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
    extend_existing_ucie_mcp_evidence_response,
    extend_existing_ucie_mcp_wire_response,
    extend_existing_ucie_mcp_wire_response_if_public,
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

    def test_offline_feed_cli_output_contains_no_installable_skills(self):
        repo = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(repo / "src")
        run = subprocess.run(
            [sys.executable, "-m", "ucie_miner",
             "preview-library-skill-feed", "--references-per-domain", "2"],
            cwd=repo, env=env, text=True, capture_output=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        payload = json.loads(run.stdout)
        self.assertEqual(payload["schema"],
                         "UCIE_LIBRARY_PUBLIC_SKILL_FEED_PREVIEW_V1")
        self.assertEqual(payload["topic_count"], 5)
        self.assertEqual(payload["installable_skills"], [])
        self.assertFalse(payload["production_approved"])

    def test_additive_existing_mcp_search_contract_is_preserved(self):
        self.fill()
        legacy = {
            "status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
            "results": [{"source_key": "modelcontextprotocol/python-sdk",
                         "catalog_status": "METADATA_ONLY"}],
            "limitations": "untrusted metadata",
        }
        original = deepcopy(legacy)
        output = extend_existing_ucie_mcp_evidence_response(
            self.root, legacy, query="Python regression",
            category="Python", tag="REGRESSION", top=3)
        self.assertEqual(legacy, original)
        for key, value in legacy.items():
            self.assertEqual(output[key], value)
        extra = output["ucie_public_research_index"]
        self.assertEqual(extra["selected_skill_id"], "python-runtime-safety")
        self.assertTrue(all(not result["installable_skill"]
                            for result in extra["results"]))
        self.assertFalse(extra["production_approved"])
        self.assertFalse(extra["auto_install"])
        self.assertFalse(output.get("production_approved", False))

    def test_unrecognized_mcp_response_not_silently_replaced(self):
        for response in (
            {"status": "OTHER_PROJECT", "results": []},
            {"status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
             "results": "not-a-list"},
            {"status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
             "results": [], "ucie_public_research_index": "spoofed"},
        ):
            with self.subTest(response=response), self.assertRaises(DiscoveryError):
                extend_existing_ucie_mcp_evidence_response(
                    self.root, response, query="Python")
        self.assertEqual(list((self.root / "runtime").iterdir()), [])

    def test_existing_json_string_wire_response_preserved(self):
        self.fill()
        old = {
            "status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
            "results": [{"source_key": "modelcontextprotocol/python-sdk",
                         "catalog_status": "METADATA_ONLY"}],
            "limitations": "existing unverified public metadata",
        }
        wire = json.dumps(old)
        out = extend_existing_ucie_mcp_wire_response(
            self.root, wire, query="Python", category="Python", top=2)
        self.assertIsInstance(out, str)
        parsed = json.loads(out)
        self.assertEqual({key: parsed[key] for key in old}, old)
        self.assertEqual(parsed["ucie_public_research_index"]["selected_skill_id"],
                         "python-runtime-safety")
        self.assertFalse(parsed["ucie_public_research_index"]["production_approved"])
        self.assertEqual(parsed["ucie_public_research_index"]["skill_installable_count"], 0)

    def test_invalid_existing_wire_fails_closed(self):
        for invalid in (
            '{"status":"UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",'
            '"status":"UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY","results":[]}',
            '{"status":"OTHER_PROJECT","results":[]}',
            "not JSON",
            '[]',
        ):
            with self.subTest(wire=invalid), self.assertRaises(DiscoveryError):
                extend_existing_ucie_mcp_wire_response(
                    self.root, invalid, query="Python")
        self.assertEqual(list((self.root / "runtime").iterdir()), [])

    def test_optional_extension_preserves_original_error_returns(self):
        early = (
            {"status": "INVALID_QUERY", "results": [], "error": "bad input"},
            {"status": "NO_EVIDENCE", "results": []},
            None,
            "plain failure",
            '{"status":"NO_EVIDENCE","results":[]}',
            '{"status":"UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",'
            '"status":"UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY","results":[]}',
        )
        for value in early:
            with self.subTest(value=value):
                output = extend_existing_ucie_mcp_wire_response_if_public(
                    self.root, value, query="Python", top=2)
                self.assertIs(output, value)

    def test_optional_extension_appends_only_to_valid_public_success(self):
        self.fill()
        original = {
            "status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
            "results": [{"source_key": "python/cpython"}],
        }
        result = extend_existing_ucie_mcp_wire_response_if_public(
            self.root, original, query="Python", top=3)
        self.assertEqual(result["results"], original["results"])
        self.assertEqual(result["ucie_public_research_index"]
                         ["selected_skill_id"], "python-runtime-safety")
        self.assertGreaterEqual(result["ucie_public_research_index"]
                                ["result_count"], 1)
        self.assertFalse(result["ucie_public_research_index"]
                         ["production_approved"])

    def test_optional_extension_read_failure_preserves_public_success(self):
        original = {
            "status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
            "results": [{"source_key": "python/cpython"}],
        }
        # A nonexistent UCIE checkout causes the optional index to fail.
        # No existing MCP response field may be lost as a result.
        returned = extend_existing_ucie_mcp_wire_response_if_public(
            self.root / "not_available", original, query="Python")
        self.assertIs(returned, original)

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
