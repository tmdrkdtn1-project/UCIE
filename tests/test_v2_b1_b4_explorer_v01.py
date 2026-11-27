"""UCIE V2 isolated actual browser route and source-bound content tests."""
from __future__ import annotations

from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
import unittest

from ucie_miner.b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from ucie_miner.v2_b1_b4_explorer_v01 import (
    HOST, ROUTE, V2ExplorerHandler, render_v2_explorer, route_v2_request,
)


class TestUCIEV2Explorer(unittest.TestCase):
    def test_landing_has_selectable_pinned_cases(self):
        html = render_v2_explorer()
        self.assertEqual(html.count('class="button"'), 2)
        self.assertIn("기술 근거에서 재사용 가능한 원리까지", html)
        for cap in build_pinned_b1_capsules():
            self.assertIn("?case=" + cap["case_id"], html)

    def test_two_case_details_show_real_capsule_and_b4(self):
        for cap in build_pinned_b1_capsules():
            with self.subTest(case=cap["case_id"]):
                html = render_v2_explorer(cap["case_id"])
                self.assertIn(cap["capsule_id"], html)
                self.assertIn(cap["content_sha256"], html)
                self.assertIn(cap["source_document_sha256"], html)
                self.assertIn("SkillBook", html)
                self.assertIn("REVIEW_ONLY_UNVERIFIED", html)

    def test_no_mutating_actions_on_preview(self):
        for name in (None, *[c["case_id"] for c in build_pinned_b1_capsules()]):
            html = render_v2_explorer(name).lower()
            for forbidden in ("<form", "method=\"post\"", "type=\"file\"",
                              "onclick=", "/local/repair", "fetch("):
                self.assertNotIn(forbidden, html)

    def test_invalid_selector_and_route_are_blocked(self):
        self.assertEqual(route_v2_request("POST", ROUTE)[0], 405)
        self.assertEqual(route_v2_request("GET", "/local/solve")[0], 404)
        self.assertEqual(route_v2_request("GET", ROUTE + "?case=x")[0], 400)
        self.assertEqual(route_v2_request("GET", ROUTE + "?case=x&case=y")[0], 400)
        self.assertEqual(route_v2_request("GET", ROUTE + "?other=1")[0], 400)

    def test_fixed_review_scenarios_are_real_engine_results(self):
        case_id = build_pinned_b1_capsules()[0]["case_id"]
        cases = (
            ("supported", "검토 후보 · 미승인"),
            ("missing_permission", "권한이 부족해 전이 후보를 거부했습니다"),
            ("unapproved_target", "현재 근거에 없는 기술이므로 전이를 거부했습니다"),
        )
        for review, expected in cases:
            with self.subTest(review=review):
                code, html = route_v2_request(
                    "GET", ROUTE + "?case=" + case_id + "&review=" + review)
                self.assertEqual(code, 200)
                self.assertIn(expected, html)
                self.assertIn("자동 코드 실행 없음", html)
                self.assertIn("재검토 제안은 <strong>0건</strong>", html)

    def test_invalid_review_is_rejected_and_no_input_forms(self):
        case_id = build_pinned_b1_capsules()[0]["case_id"]
        for params in ("&review=custom", "&review=supported&review=supported",
                       "&review=", "&unknown=1"):
            with self.subTest(params=params):
                code, body = route_v2_request(
                    "GET", ROUTE + "?case=" + case_id + params)
                self.assertEqual((code, body), (400, ""))
        for review in ("supported", "missing_permission", "unapproved_target"):
            html = render_v2_explorer(case_id, review=review)
            self.assertNotIn("<form", html)
            self.assertNotIn("onclick=", html)

    def test_b5_readonly_evaluation_page_and_no_tracking(self):
        landing = render_v2_explorer()
        self.assertIn('href="/v2/assessment"', landing)
        code, html = route_v2_request("GET", "/v2/assessment")
        self.assertEqual(code, 200)
        self.assertIn("로컬 기능 작동 측정", html)
        self.assertIn("총 21회 렌더링", html)
        self.assertIn("NOT_MEASURED", html)
        self.assertNotIn("<form", html)
        self.assertNotIn("fetch(", html)
        self.assertEqual(route_v2_request("GET", "/v2/assessment?x=1"), (400, ""))
        self.assertEqual(route_v2_request("POST", "/v2/assessment"), (405, ""))

    def test_main_default_uses_free_port_and_actual_url(self):
        from unittest.mock import patch
        from ucie_miner import v2_b1_b4_explorer_v01 as explorer

        class FakeServer:
            server_port = 49271

            def __init__(self, bind, handler):
                self.bind = bind

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def serve_forever(self):
                return None

        fake = FakeServer
        with (patch.object(explorer, "ThreadingHTTPServer", fake),
              patch("builtins.print") as printed,
              patch("webbrowser.open") as opened):
            self.assertEqual(explorer.main(["--open-browser"]), 0)
        self.assertEqual(explorer.HOST, "127.0.0.1")
        printed.assert_called_once_with(
            "UCIE_V2_B1_B4_PREVIEW_READY http://127.0.0.1:49271/v2/library",
            flush=True)
        opened.assert_called_once_with(
            "http://127.0.0.1:49271/v2/library", new=2)

    def test_local_http_server_responds_and_refuses_post(self):
        # Ephemeral loopback listener for one isolated test; no persistent task.
        server = ThreadingHTTPServer((HOST, 0), V2ExplorerHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection(HOST, server.server_port, timeout=5)
            conn.request("GET", ROUTE)
            res = conn.getresponse()
            page = res.read().decode("utf-8")
            self.assertEqual(res.status, 200)
            self.assertIn("UCIE / Virtual Library", page)
            self.assertEqual(res.getheader("Cache-Control"), "no-store")
            conn.close()

            cap = build_pinned_b1_capsules()[0]
            conn = HTTPConnection(HOST, server.server_port, timeout=5)
            conn.request("GET", ROUTE + "?case=" + cap["case_id"])
            res = conn.getresponse()
            self.assertEqual(res.status, 200)
            self.assertIn(cap["capsule_id"], res.read().decode("utf-8"))
            conn.close()

            conn = HTTPConnection(HOST, server.server_port, timeout=5)
            conn.request("POST", ROUTE, body=b"x=1")
            res = conn.getresponse()
            self.assertEqual(res.status, 405)
            self.assertEqual(res.read(), b"")
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
