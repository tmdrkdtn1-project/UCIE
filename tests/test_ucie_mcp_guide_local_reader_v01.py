"""B1: MCP SkillBook 003 is readable/searchable without product approval."""
from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import mcp_prompts_guide_v01 as guide
from ucie_miner import skillbook_catalog_union_v01 as union


class MCP003LocalReaderTests(unittest.TestCase):
    def test_exact_public_source_and_no_go_gates(self):
        item = guide.build_readonly_guide()
        self.assertEqual(item["schema"], guide.SCHEMA)
        self.assertEqual(item["skillbook_id"], "UCIE-SKILLBOOK-MCP-PROMPTS-003")
        self.assertEqual(item["status"], guide.STATUS)
        self.assertEqual(len(item["chapters"]), 5)
        self.assertEqual(item["source_evidence"]["observed_cases"], 16)
        self.assertEqual(item["source_evidence"]["first_published_fixed_version"],
                         "NOT_VERIFIED")
        self.assertEqual(item["source_evidence"]["patch_merge_commit"],
                         "754254c08fe1c3eda18b69da3d336106fe8d72d6")
        self.assertTrue(all(v is False for v in item["review_gates"].values()))
        self.assertFalse(item["export_allowed"])
        self.assertFalse(item["machine_skill_contract"]["browser_execution_allowed"])
        self.assertEqual(item["network_requests"], 0)
        self.assertEqual(item["operating_database_writes"], 0)

    def test_search_matching_and_invalid_query_fail_closed(self):
        for term in ("MCP", "mcp", "프롬프트", "SDK", "-32602", ""):
            with self.subTest(term=term):
                self.assertTrue(guide.matches(term))
        self.assertFalse(guide.matches("scandir"))
        for term in ("../", "x" * 81, "mcp<script>", None, True):
            with self.subTest(term=term):
                with self.assertRaises(guide.MCPGuideError):
                    guide.matches(term)

    def test_detail_uses_frozen_local_v04_shell_and_escaped_chapters(self):
        html = app._mcp_review_guide("")
        self.assertIn("SKILLBOOK 003", html)
        self.assertIn("미승인", html)
        self.assertIn("-32602", html)
        self.assertIn("/local/guide/mcp-prompts.json", html)
        self.assertIn("/local/library?q=MCP", html)
        self.assertIn(guide.SOURCE_PR if hasattr(guide, "SOURCE_PR")
                      else "https://github.com/modelcontextprotocol/python-sdk/pull/3696", html)
        self.assertNotIn("human_approved=true", html)
        self.assertNotIn("<script>", html)

    def test_json_is_review_only_without_execution(self):
        value = json.loads(app._mcp_review_guide("", json_mode=True))
        self.assertEqual(value, guide.build_readonly_guide())
        self.assertFalse(value["auto_promoted"])
        self.assertFalse(value["review_gates"]["customer_release_authorized"])
        with self.assertRaises(app.LocalProductError):
            app._mcp_review_guide("approved=true")

    def test_forged_approved_status_is_rejected_before_render(self):
        fake = guide.build_readonly_guide()
        fake["review_gates"]["human_approved"] = True
        with patch.object(guide, "build_readonly_guide", return_value=fake):
            with self.assertRaises(app.LocalProductError):
                app._mcp_review_guide("")

    def test_library_search_now_exposes_unapproved_mcp_guide(self):
        fixture = {
            "schema": union.SCHEMA,
            "status": "READ_ONLY_TWO_SHELF_DRAFT_NOT_APPROVED",
            "public_shelf_status": "NOT_REQUESTED",
            "public_evidence_candidates": [],
            "human_approved": False, "export_allowed": False,
            "approved_packages": 0, "network_requests": 0,
            "operating_database_writes": 0, "skillbooks": [],
            "editorial_review_candidates": [],
        }
        with patch.object(union, "search_federated", return_value=fixture):
            with patch.object(app, "_paged_evidence", return_value=""):
                matched = app._library(Path("/unused/UCIE"), "q=MCP")
                unrelated = app._library(Path("/unused/UCIE"), "q=scandir")
        self.assertIn("/local/guide/mcp-prompts", matched)
        self.assertIn("SKILLBOOK 003", matched)
        self.assertIn("미승인", matched)
        self.assertNotIn("/local/guide/mcp-prompts", unrelated)

    def test_existing_home_and_evolution_route_definitions_unchanged(self):
        urls = [row[0] for row in app.ROUTES]
        self.assertEqual(urls, [
            "/local/error", "/local/engine",
            "/local/library", "/local/evolution",
        ])


if __name__ == "__main__":
    unittest.main()
