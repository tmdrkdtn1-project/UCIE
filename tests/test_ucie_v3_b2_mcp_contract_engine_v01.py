"""V3 B2 local engine makes UCIE-authored MCP wire contract useful.

No external SDK, non-UCIE code, owner files, network, approval or automatic
promotion; this is an explicitly synthetic and bounded user-initiated demo.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch
from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import mcp_prompt_regression_v01 as wire


class MCPContractEngineTests(unittest.TestCase):
    def test_engine_menu_and_live_in_memory_contract_demo(self):
        choices = app._engine("")
        self.assertIn("/local/engine?purpose=MCP_PROMPTS_CONTRACT", choices)
        page = app._engine("purpose=MCP_PROMPTS_CONTRACT")
        self.assertIn("UCIE 자체 사례", page)
        self.assertIn("계약 일치", page)
        self.assertIn("입력 오류 -32602", page)
        self.assertIn("/local/guide/mcp-prompts", page)
        self.assertIn("실제 MCP SDK", page)
        self.assertIn("자동 승인", page)
        self.assertNotIn("CUSTOMER_RELEASE_GO", page)

    def test_a_real_first_party_contract_function_is_invoked(self):
        real = wire.synthetic_demonstration
        with patch.object(wire, "synthetic_demonstration",
                          wraps=real) as probe:
            app._engine("purpose=MCP_PROMPTS_CONTRACT")
            probe.assert_called_once_with()
        receipt = real()
        self.assertEqual(receipt["cases"], 8)
        self.assertEqual(receipt["contract_matches"], 6)
        self.assertEqual(receipt["non_input_controls"], 2)
        self.assertEqual(receipt["synthetic_pre_fix_violations_detected"], 4)
        self.assertFalse(receipt["customer_release_authorized"])
        self.assertFalse(receipt["auto_promoted"])
        self.assertEqual(receipt["network_requests"], 0)
        self.assertEqual(receipt["persistent_writes"], 0)

    def test_forged_approval_or_untested_sdk_evidence_is_rejected(self):
        for key, value in (
                ("customer_release_authorized", True),
                ("auto_promoted", True),
                ("independent_sdk_regression", "VERIFIED"),
                ("cases", 16),
                ("synthetic_pre_fix_violations_detected", 0),
                ("network_requests", 1)):
            with self.subTest(field=key):
                payload = wire.synthetic_demonstration()
                payload[key] = value
                with patch.object(wire, "synthetic_demonstration",
                                  return_value=payload):
                    with self.assertRaises(app.LocalProductError):
                        app._engine("purpose=MCP_PROMPTS_CONTRACT")

    def test_unregistered_and_unexpected_queries_remain_blocked(self):
        for query in ("purpose=UNSAFE_SDK_RUN",
                      "purpose=MCP_PROMPTS_CONTRACT&run=1",
                      "purpose=MCP_PROMPTS_CONTRACT&purpose=REAL_PUBLIC_CATALOG"):
            with self.subTest(query=query):
                with self.assertRaises(app.LocalProductError):
                    app._engine(query)

    def test_real_one_shot_loopback_http_engine_route(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / ".git").is_dir():
            self.skipTest("requires actual UCIE checkout")
        server = ThreadingHTTPServer(("127.0.0.1", 0),
                                     app.make_handler(root))
        server.daemon_threads = True
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            def probe(method, path):
                with closing(HTTPConnection(
                        "127.0.0.1", server.server_port, timeout=10)) as conn:
                    conn.request(method, path)
                    result = conn.getresponse()
                    self.assertLessEqual(int(result.getheader(
                        "Content-Length", "0")), 1_000_000)
                    body = result.read(1_000_001)
                    self.assertLessEqual(len(body), 1_000_000)
                    return result.status, body
            status, body = probe(
                "GET", "/local/engine?purpose=MCP_PROMPTS_CONTRACT")
            self.assertEqual(status, 200)
            self.assertIn("UCIE 자체 사례".encode(), body)
            self.assertIn(b"-32602", body)
            self.assertIn(b"/local/guide/mcp-prompts", body)
            self.assertIn("고객 배포".encode(), body)
            status, _ = probe(
                "GET", "/local/engine?purpose=UNAPPROVED_EXTERNAL_SDK")
            self.assertEqual(status, 400)
            status, _ = probe(
                "POST", "/local/engine?purpose=MCP_PROMPTS_CONTRACT")
            self.assertEqual(status, 405)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

    def test_guide_links_to_engine_but_stays_unapproved(self):
        guide = app._mcp_review_guide("")
        self.assertIn(
            "/local/engine?purpose=MCP_PROMPTS_CONTRACT", guide)
        self.assertIn("재배포", guide)
        self.assertIn("NO-GO", guide)
        self.assertEqual(tuple(item[0] for item in app.ROUTES), (
            "/local/error", "/local/engine",
            "/local/library", "/local/evolution",
        ))
        self.assertIn("THE UCIE EXPERIENCE", app._home())


if __name__ == "__main__":
    unittest.main()
