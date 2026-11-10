"""V3 B2: usable source-bound improvement comparison without UI redesign.

Only approved public MCP SDK pins and UCIE-authored bounded synthetic tests.
No source mutation, upstream SDK execution, private files, auto-promotion,
persistent service restart, or customer release.
"""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
from threading import Thread
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import mcp_prompt_regression_v01 as wire
from ucie_miner import mcp_prompts_guide_v01 as guide
from ucie_miner import public_collection_inventory_v01 as inventory


class MCPImprovementComparisonTests(unittest.TestCase):
    @staticmethod
    def _inventory():
        return {
            "schema": inventory.SCHEMA,
            "status": "UCIE_PUBLIC_COLLECTION_REVIEW_ONLY",
            "operating_database_writes": 0,
            "issues": [],
            "legacy_miner": {"candidates": 0},
            "stage10_public_candidate_staging": {"candidate_revisions": 0},
        }

    def _evolution(self, query):
        with patch.object(inventory, "collection_inventory",
                          return_value=self._inventory()):
            with patch.object(app, "_paged_evidence",
                              return_value='<section data-test="public-evidence">'
                              'source search retained</section>'):
                return app._evolution(Path("/unused/UCIE"), query)

    def test_mcp_change_comparison_links_actual_three_step_workflow(self):
        for key in ("MCP", "mcp", "prompts/get", "prompt", "-32602"):
            with self.subTest(key=key):
                html = self._evolution("q=" + key)
                self.assertIn("수정 전후 실제 관측 비교", html)
                self.assertIn("2025-11-25", html)
                self.assertIn("2026-07-28", html)
                self.assertIn("<code>0", html)
                self.assertIn("<code>-32603", html)
                self.assertIn("<code>-32602", html)
                self.assertIn("가상 수정 전 위반 감지", html)
                self.assertIn("공식 공개 수정 PR #3696", html)
                self.assertIn("/local/engine?purpose=MCP_PROMPTS_CONTRACT",
                              html)
                self.assertIn("/local/guide/mcp-prompts", html)
                self.assertIn('data-test="public-evidence"', html)
                self.assertIn("재배포 권리", html)
                self.assertNotIn("CUSTOMER_RELEASE_GO", html)

    def test_real_first_party_trial_invoked_once_per_selected_comparison(self):
        original = wire.synthetic_demonstration
        with patch.object(wire, "synthetic_demonstration", wraps=original) as spy:
            self._evolution("q=MCP")
            spy.assert_called_once_with()
        output = original()
        self.assertEqual((output["cases"], output["contract_matches"],
                          output["non_input_controls"],
                          output["synthetic_pre_fix_violations_detected"]),
                         (8, 6, 2, 4))
        self.assertFalse(output["auto_promoted"])
        self.assertFalse(output["customer_release_authorized"])

    def test_unrelated_terms_and_later_pages_do_not_forge_mcp_evidence(self):
        for query in ("", "q=Git", "q=Python", "q=MCP&page=2"):
            with self.subTest(query=query):
                html = self._evolution(query)
                self.assertNotIn("수정 전후 실제 관측 비교", html)
                self.assertIn('data-test="public-evidence"', html)

    def test_forged_publication_or_licensing_blocks_comparison(self):
        for key, value in (
                ("human_approved", True),
                ("license_redistribution_approved", True),
                ("customer_release_authorized", True)):
            with self.subTest(key=key):
                forged = guide.build_readonly_guide()
                forged["review_gates"][key] = value
                with patch.object(guide, "build_readonly_guide",
                                  return_value=forged):
                    with self.assertRaises(app.LocalProductError):
                        self._evolution("q=MCP")

    def test_unpinned_claims_and_faked_sdk_executed_are_rejected(self):
        forged = guide.build_readonly_guide()
        forged["source_evidence"]["first_published_fixed_version"] = "v2.4.0"
        with patch.object(guide, "build_readonly_guide", return_value=forged):
            with self.assertRaises(app.LocalProductError):
                self._evolution("q=MCP")
        trial = wire.synthetic_demonstration()
        trial["independent_sdk_regression"] = "VERIFIED"
        with patch.object(wire, "synthetic_demonstration", return_value=trial):
            with self.assertRaises(app.LocalProductError):
                self._evolution("q=MCP")

    def test_unregistered_query_cannot_override_review_state(self):
        for query in ("q=MCP&approved=1", "q=MCP&q=Git", "q=MCP&page=0"):
            with self.subTest(query=query):
                with self.assertRaises(app.LocalProductError):
                    self._evolution(query)

    def test_v04_home_navigation_and_engine_entry_unchanged(self):
        self.assertEqual(tuple(row[0] for row in app.ROUTES), (
            "/local/error", "/local/engine",
            "/local/library", "/local/evolution",
        ))
        self.assertIn("THE UCIE EXPERIENCE", app._home())
        self.assertIn("/local/evolution?q=MCP",
                      app._engine("purpose=MCP_PROMPTS_CONTRACT"))
        self.assertEqual(guide.build_readonly_guide()["export_allowed"], False)

    def test_one_shot_actual_owner_windows_loopback_http(self):
        root = Path(__file__).resolve().parents[1]
        if (os.name != "nt" or root.is_symlink()
                or root.resolve() != Path("D:/UCIE").resolve()):
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(root))
        server.daemon_threads = True
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def get(method, path):
                with closing(HTTPConnection("127.0.0.1", server.server_port,
                                            timeout=15)) as conn:
                    conn.request(method, path)
                    response = conn.getresponse()
                    size = int(response.getheader("Content-Length", "0"))
                    self.assertLessEqual(size, 2_000_000)
                    data = response.read(2_000_001)
                    self.assertLessEqual(len(data), 2_000_000)
                    return response.status, data
            status, page = get("GET", "/local/evolution?q=MCP")
            self.assertEqual(status, 200)
            self.assertIn("수정 전후 실제 관측 비교".encode(), page)
            self.assertIn(b"/local/engine?purpose=MCP_PROMPTS_CONTRACT", page)
            self.assertIn(b"/local/guide/mcp-prompts", page)
            status, page = get(
                "GET", "/local/engine?purpose=MCP_PROMPTS_CONTRACT")
            self.assertEqual(status, 200)
            self.assertIn(b"/local/evolution?q=MCP", page)
            status, page = get("GET", "/local/guide/mcp-prompts")
            self.assertEqual(status, 200)
            self.assertIn(b"SKILLBOOK 003", page)
            status, _ = get("GET", "/local/evolution?q=MCP&approved=true")
            self.assertEqual(status, 400)
            status, _ = get("POST", "/local/evolution?q=MCP")
            self.assertEqual(status, 405)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
