"""B2 first real cross-pillar flow: error prevention -> reviewed MCP guide.

Local V04 shell is preserved; no package export, SDK execution, remote data,
file reads/writes or runtime release actions are performed by these tests.
"""
from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import mcp_prompts_guide_v01 as guide


class MCPPreventionGuideTests(unittest.TestCase):
    def _render(self, term: str) -> str:
        with patch.object(app, "_paged_evidence", return_value=
                          '<section data-test="public-evidence">unchanged</section>'):
            return app._error(Path("/unused/UCIE"), term)

    def test_mcp_error_prevention_links_to_pinned_review(self):
        for search in ("MCP", "mcp", "prompts/get", "-32602", "prompt"):
            with self.subTest(search=search):
                html = self._render("q=" + search)
                self.assertIn('href="/local/guide/mcp-prompts"', html)
                self.assertIn("SKILLBOOK", guide.SKILLBOOK_ID)
                self.assertIn("-32602", html)
                self.assertIn("검토 중인 기술 자료", html)
                self.assertIn('data-test="public-evidence"', html)
                self.assertNotIn("human_approved=true", html)

    def test_unrelated_search_and_second_page_do_not_add_mcp_link(self):
        for query in ("", "q=git", "q=scandir", "q=python", "q=MCP&page=2"):
            with self.subTest(query=query):
                html = self._render(query)
                self.assertNotIn('href="/local/guide/mcp-prompts"', html)

    def test_forged_approval_state_blocks_mcp_link(self):
        forged = guide.build_readonly_guide()
        forged["review_gates"]["human_approved"] = True
        with patch.object(guide, "build_readonly_guide",
                          return_value=forged):
            with patch.object(app, "_paged_evidence",
                              return_value=""):
                with self.assertRaises(app.LocalProductError):
                    app._error(Path("/unused/UCIE"), "q=MCP")

    def test_home_evolution_navigation_and_url_gates_stay_frozen(self):
        self.assertEqual(tuple(x[0] for x in app.ROUTES), (
            "/local/error", "/local/engine",
            "/local/library", "/local/evolution"))
        self.assertIn("THE UCIE EXPERIENCE", app._home())
        self.assertFalse(guide.build_readonly_guide()["export_allowed"])


if __name__ == "__main__":
    unittest.main()
