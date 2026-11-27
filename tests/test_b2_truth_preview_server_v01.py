"""UCIE B2 owner browser preview route: allowlisted GET only."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
import unittest

from ucie_miner.b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from ucie_miner.b2_truth_preview_server_v01 import (
    HOST, ROUTE, TruthPreviewHandler, route_truth_request,
)


class B2TruthPreviewTests(unittest.TestCase):
    def test_selection_page_is_read_only(self):
        code, page = route_truth_request("GET", ROUTE)
        self.assertEqual(code, 200)
        self.assertEqual(page.count("공식 문서 범위 살펴보기"), 2)
        self.assertEqual(page.count('<main id="main">'), 1)
        self.assertIn("viewport", page)
        self.assertNotIn("<form", page)
        self.assertNotIn("onclick=", page)

    def test_accessible_preview_landmarks_and_mobile_contract(self):
        landing_code, landing = route_truth_request("GET", ROUTE)
        self.assertEqual(landing_code, 200)
        self.assertIn('href="#main"', landing)
        self.assertEqual(landing.count('<main id="main">'), 1)
        self.assertEqual(landing.count("<h1>"), 1)
        self.assertIn("summary:focus-visible", landing)
        self.assertIn("max-width:390px", landing)
        self.assertIn("overflow-wrap:anywhere", landing)
        for cap in build_pinned_b1_capsules():
            with self.subTest(source=cap["source_id"]):
                code, detail = route_truth_request(
                    "GET", ROUTE + "?case=" + cap["case_id"])
                self.assertEqual(code, 200)
                self.assertEqual(detail.count("<h1>"), 1)
                self.assertIn("본문으로 건너뛰기", detail)
                self.assertIn("왜 이렇게 안내하나요?", detail)
                self.assertNotIn('<input', detail)
                self.assertNotIn('tabindex="-1"', detail)

    def test_source_bound_case_view_for_two_cases(self):
        for cap in build_pinned_b1_capsules():
            with self.subTest(source=cap["source_id"]):
                code, page = route_truth_request(
                    "GET", ROUTE + "?case=" + cap["case_id"])
                self.assertEqual(code, 200)
                self.assertIn(cap["capsule_id"], page)
                self.assertIn("자체 시험 기록이 연결되지 않았", page)
                self.assertIn("현재 사용 중인 프로그램 버전에서 작동하는지는 미확인", page)
                self.assertIn("사용권 승인은 완료되지 않았", page)

    def test_reject_untrusted_query_and_post(self):
        for path in (ROUTE + "?case=unknown", ROUTE + "?case=x&case=y",
                     ROUTE + "?case=x&other=y", ROUTE + "?other=1",
                     ROUTE + "?case=", ROUTE + "?case=x#bad"):
            with self.subTest(path=path):
                self.assertNotEqual(route_truth_request("GET", path)[0], 200)
        self.assertEqual(route_truth_request("POST", ROUTE), (405, ""))
        self.assertEqual(route_truth_request("GET", "/local/ask"), (404, ""))

    def test_loopback_rejects_wrong_and_duplicate_host_headers(self):
        server = ThreadingHTTPServer((HOST, 0), TruthPreviewHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for wrong in ("evil.example", "localhost", "127.0.0.1:9999"):
                with self.subTest(host=wrong):
                    conn = HTTPConnection(HOST, server.server_port, timeout=5)
                    conn.putrequest("GET", ROUTE, skip_host=True)
                    conn.putheader("Host", wrong)
                    conn.endheaders()
                    response = conn.getresponse()
                    self.assertEqual(response.status, 403)
                    self.assertEqual(response.read(), b"")
                    conn.close()
            conn = HTTPConnection(HOST, server.server_port, timeout=5)
            conn.putrequest("GET", ROUTE, skip_host=True)
            conn.putheader("Host", HOST + ":" + str(server.server_port))
            conn.putheader("Host", "evil.example")
            conn.endheaders()
            response = conn.getresponse()
            self.assertEqual(response.status, 403)
            self.assertEqual(response.read(), b"")
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_loopback_real_http_get_and_post(self):
        server = ThreadingHTTPServer((HOST, 0), TruthPreviewHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection(HOST, server.server_port, timeout=5)
            conn.request("GET", ROUTE)
            response = conn.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
            self.assertIn("UCIE", response.read().decode("utf-8"))
            conn.close()
            conn = HTTPConnection(HOST, server.server_port, timeout=5)
            conn.request("POST", ROUTE, body=b"private=ignored")
            response = conn.getresponse()
            self.assertEqual(response.status, 405)
            self.assertEqual(response.read(), b"")
            conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
