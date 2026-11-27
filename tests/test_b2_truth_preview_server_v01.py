"""UCIE B2 owner browser preview route: allowlisted GET only."""
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch
import unittest

from ucie_miner.b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from ucie_miner.b1_first_party_receipt_link_v01 import run_scoped_receipt
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

    def test_mobile_numbered_links_keep_marker_at_first_line(self):
        code, html = route_truth_request("GET", ROUTE)
        self.assertEqual(code, 200)
        self.assertIn("main ol li>a{display:block", html)
        self.assertIn("word-break:keep-all", html)
        self.assertIn("min-height:44px", html)
        self.assertIn("main ol li::marker", html)
        self.assertEqual(html.count("<li><a href="), 2)
        self.assertLess(
            html.index("Git · 공식 문서 범위 살펴보기"),
            html.index("Python · 공식 문서 범위 살펴보기"))
        # A CSS contract test is not real Edge responsive visual QA.

    def test_first_use_steps_are_explicit_and_only_real_cases_clickable(self):
        code, html = route_truth_request("GET", ROUTE)
        self.assertEqual(code, 200)
        self.assertIn('class="preview-steps"', html)
        self.assertIn('class="case-choices"', html)
        self.assertIn("아직 모르는 내용을 구분", html)
        self.assertIn("고객 환경을 자동으로 점검하거나", html)
        self.assertIn("사용권·독립 품질 검증은 미확인", html)
        self.assertEqual(html.count('href="/v2/truth?case='), 2)
        self.assertEqual(html.count("<h1"), 1)
        self.assertIn(".case-choices li>a:focus-visible", html)
        self.assertIn("counter-reset:ucie-case", html)
        self.assertNotIn("<form", html)
        self.assertNotIn("코드를 고쳐", html)

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

    def test_b1_b2_b3_case_identity_and_unverified_revision_status(self):
        from ucie_miner.b1_b2_b3_truth_journey_v01 import build_truth_journey
        for cap in build_pinned_b1_capsules():
            with self.subTest(source=cap["source_id"]):
                code, page = route_truth_request(
                    "GET", ROUTE + "?case=" + cap["case_id"])
                self.assertEqual(code, 200)
                journey = build_truth_journey(cap["case_id"], cap["source_tag"])
                self.assertEqual(journey["capsule_id"], cap["capsule_id"])
                self.assertIn(cap["source_document_sha256"], page)
                self.assertIn(cap["source_tag"], page)
                self.assertIn(journey["b3_proposal_sha256"], page)
                self.assertIn("공식 사이트에서 최신 변경이 있는지 다시 조사한 결과는 아닙니다", page)
                self.assertIn("관련 예제 재시험:", page)
                self.assertIn("실행하지 않았습니다", page)
                self.assertIn("출처 갱신 인증: 미확인", page)
                self.assertEqual(journey["b3_retest_proposal_count"], 0)
                self.assertFalse(journey["b3_revision_authenticated"])
                self.assertFalse(journey["b3_retest_executed"])
                self.assertNotIn("업데이트 검증 완료", page)
                self.assertNotIn("고객 환경에 적용 승인", page)

    def test_b1_b2_b3_source_identity_drift_fails_closed(self):
        from unittest.mock import patch
        from ucie_miner.b1_b2_b3_truth_journey_v01 import build_truth_journey
        cap = build_pinned_b1_capsules()[0]
        journey = build_truth_journey(cap["case_id"], cap["source_tag"])
        forged = {**journey, "source_document_sha256": "0" * 64}
        with patch(
            "ucie_miner.b2_truth_preview_server_v01.build_truth_journey",
            return_value=forged,
        ), self.assertRaisesRegex(ValueError, "B1_B2_B3_PINNED_IDENTITY_DRIFT"):
            route_truth_request("GET", ROUTE + "?case=" + cap["case_id"])

    def test_reject_untrusted_query_and_post(self):
        for path in (ROUTE + "?case=unknown", ROUTE + "?case=x&case=y",
                     ROUTE + "?case=x&other=y", ROUTE + "?other=1",
                     ROUTE + "?case=", ROUTE + "?case=x#bad"):
            with self.subTest(path=path):
                self.assertNotEqual(route_truth_request("GET", path)[0], 200)
        self.assertEqual(route_truth_request("POST", ROUTE), (405, ""))
        self.assertEqual(route_truth_request("GET", "/local/ask"), (404, ""))

    def test_explicit_receipt_is_shown_without_get_triggered_trial(self):
        caps = build_pinned_b1_capsules()
        receipts = {cap["case_id"]: run_scoped_receipt(
            cap["case_id"], cap["source_tag"]) for cap in caps}
        for cap in caps:
            with self.subTest(source=cap["source_id"]), patch(
                "ucie_miner.b1_first_party_receipt_link_v01.run_first_party_synthetic_comparison",
                side_effect=AssertionError("GET must not start a trial"),
            ):
                code, page = route_truth_request(
                    "GET", ROUTE + "?case=" + cap["case_id"],
                    receipts=receipts)
                self.assertEqual(code, 200)
                self.assertIn(receipts[cap["case_id"]]["receipt_sha256"], page)
                self.assertIn("UCIE가 만든 예제에서는 확인했습니다", page)
                self.assertIn("독립적인 품질 검증은 미완료", page)
                self.assertIn("고객용 배포와 사용권 승인은 완료되지 않았", page)

    def test_absent_optional_receipt_stays_unverified(self):
        cap = build_pinned_b1_capsules()[0]
        code, html = route_truth_request(
            "GET", ROUTE + "?case=" + cap["case_id"], receipts={})
        self.assertEqual(code, 200)
        self.assertIn("아직 자체 시험 기록이 연결되지 않았", html)
        self.assertNotIn("UCIE가 만든 예제에서는 확인했습니다", html)

    def test_precomputed_receipt_mismatched_case_fails_closed(self):
        left, right = build_pinned_b1_capsules()
        fake = run_scoped_receipt(left["case_id"], left["source_tag"])
        with self.assertRaises(ValueError):
            route_truth_request(
                "GET", ROUTE + "?case=" + right["case_id"],
                receipts={right["case_id"]: fake})

    def test_http_precomputed_receipt_does_not_execute(self):
        cap = build_pinned_b1_capsules()[0]
        receipt = run_scoped_receipt(cap["case_id"], cap["source_tag"])
        server = ThreadingHTTPServer((HOST, 0), TruthPreviewHandler)
        server.ucie_receipts = {cap["case_id"]: receipt}
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch(
                "ucie_miner.b1_first_party_receipt_link_v01.run_first_party_synthetic_comparison",
                side_effect=AssertionError("HTTP must not run a trial"),
            ):
                conn = HTTPConnection(HOST, server.server_port, timeout=5)
                conn.request("GET", ROUTE + "?case=" + cap["case_id"])
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                body = response.read().decode("utf-8")
                self.assertIn(receipt["receipt_sha256"], body)
                conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

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
