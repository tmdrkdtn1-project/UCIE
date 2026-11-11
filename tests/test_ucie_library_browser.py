"""Synthetic-only acceptance for the UCIE loopback read-only Library browser.

Uses a fake source-linked result. No owner databases, upstream network,
scheduler registration, external project access, or service deployment.
"""
from __future__ import annotations

from contextlib import contextmanager
from http.server import HTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError

from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.library_search import LibrarySearchError
from urllib.request import Request, urlopen

from ucie_miner.library_browser import (
    BrowserError, PUBLIC_LINK, SCHEMA, make_handler,
    parse_request_filters, render_page,
)


SAMPLE = {
    "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
    "total_matches": 1,
    "items": [{
        "source_id": "repo:python/cpython",
        "domain": "Python",
        "kind": "PUBLIC_TECHNICAL_EVIDENCE",
        "purpose_code": "CONCURRENCY",
        "revision_hint": "a" * 40,
        "evidence_sha256": "b" * 64,
        "public_url": "https://github.com/python/cpython/pull/123",
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False, "export_allowed": False,
    }],
}


@contextmanager
def local_only(searcher):
    server = HTTPServer(("127.0.0.1", 0),
                        make_handler(Path("Z:/synthetic/UCIE"), searcher=searcher))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


class UCIEBrowserTests(unittest.TestCase):
    def test_safe_filter_parser_with_original_library_bounds(self):
        parsed = parse_request_filters(
            "q=Python&domain=Python&kind=PUBLIC_TECHNICAL_EVIDENCE"
            "&source=repo%3Apython%2Fcpython&limit=5")
        self.assertEqual(parsed["source_id"], "repo:python/cpython")
        self.assertEqual(parsed["query"], "Python")
        self.assertEqual(parsed["limit"], 5)
        self.assertTrue(parsed["group_revisions"])
        for bad in (
            "q=abc&q=def", "foo=bar", "q=hi%0Aworld", "q=%3Cscript%3E",
            "source=repo%3Aunapproved%2Fprivate", "limit=21",
            "limit=-1", "limit=2x", "limit=0", "kind=REUSABLE_SKILL",
            "q=" + "a" * 81, "source=repo%3Apython%2Fcpython&source=",
        ):
            with self.subTest(bad=bad), self.assertRaises(BrowserError):
                parse_request_filters(bad)

    def test_render_escapes_metadata_and_never_approves_candidates(self):
        filters = parse_request_filters("q=Python")
        tampered = dict(SAMPLE)
        item = dict(SAMPLE["items"][0])
        item["purpose_code"] = '<svg onload="alert(1)">'
        item["public_url"] = 'javascript:alert(1)'
        tampered["items"] = [item]
        html = render_page(filters, tampered)
        self.assertNotIn("<svg", html)
        self.assertIn("&lt;svg", html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn("공개 링크 검증 불가", html)
        self.assertIn("미검증 후보 · 승인되지 않음", html)
        self.assertNotIn("<script", html)
        self.assertTrue(PUBLIC_LINK.fullmatch(SAMPLE["items"][0]["public_url"]))
        self.assertFalse(PUBLIC_LINK.fullmatch("https://github.com/unknown/private/pull/1"))

    def test_incomplete_source_linkage_hides_even_injected_rows(self):
        result = dict(SAMPLE)
        result["status"] = "SOURCE_LINKAGE_INCOMPLETE_NO_GO"
        page = render_page(parse_request_filters(""), result)
        self.assertIn("원장 연결 검증 미완료", page)
        self.assertNotIn("공개 근거 열기", page)

    def test_browser_http_real_loopback_routes_and_query(self):
        calls = []

        def searcher(root, **filters):
            calls.append(filters)
            return SAMPLE

        with local_only(searcher) as url:
            with urlopen(url + "/?q=Python&source=repo%3Apython%2Fcpython&limit=5",
                         timeout=5) as response:
                html = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertIn("frame-ancestors 'none'",
                              response.headers["Content-Security-Policy"])
                self.assertIn("공개 근거 열기", html)
                self.assertIn("검색된 후보 1건", html)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["source_id"], "repo:python/cpython")
            self.assertTrue(calls[0]["group_revisions"])
            with urlopen(url + "/health", timeout=5) as response:
                info = json.loads(response.read())
                self.assertEqual(info["schema"], SCHEMA)
                self.assertEqual(info["operating_database_writes"], 0)
                self.assertFalse(info["production_approved"])
            self.assertEqual(len(calls), 1)

    def test_reject_ambiguous_unsafe_and_nonget_requests_before_search(self):
        calls = []

        def searcher(root, **filters):
            calls.append(1)
            return SAMPLE

        with local_only(searcher) as url:
            for path in ("/?q=x&q=y", "/?source=repo%3Aunknown%2Fprivate",
                         "/?q=%3Cscript%3E", "/something", "/?limit=21"):
                with self.subTest(path=path):
                    with self.assertRaises(HTTPError) as exc:
                        urlopen(url + path, timeout=5)
                    self.assertIn(exc.exception.code, (400, 404))
            req = Request(url + "/", data=b"no writes allowed", method="POST")
            with self.assertRaises(HTTPError) as exc:
                urlopen(req, timeout=5)
            self.assertEqual(exc.exception.code, 405)
            with self.assertRaises(HTTPError) as exc:
                urlopen(Request(url + "/", headers={"Host": "ucie.invalid"}),
                        timeout=5)
            self.assertEqual(exc.exception.code, 403)
            self.assertEqual(calls, [])

    def test_bounded_denied_post_finishes_405_without_tcp_abort(self):
        # A Windows Python 3.15 regression: closing HTTP/1.0 while bytes
        # from a rejected POST remain unread can produce WinError 10053.
        # The request is still denied; its payload never reaches search.
        seen = []

        def searcher(root, **filters):
            seen.append(1)
            return SAMPLE

        with local_only(searcher) as url:
            for payload in (b"no writes allowed", b"X" * 8193):
                with self.subTest(size=len(payload)):
                    request = Request(url + "/", data=payload, method="POST")
                    with self.assertRaises(HTTPError) as denied:
                        urlopen(request, timeout=5)
                    self.assertEqual(denied.exception.code, 405)
                    self.assertEqual(denied.exception.read(),
                                     b"READ_ONLY_GET_ONLY")
                    denied.exception.close()
        self.assertEqual(seen, [])

    def test_new_browser_tab_renders_form_without_reading_any_ledger(self):
        filters = parse_request_filters("")
        self.assertEqual(filters["query"], "")
        self.assertEqual(filters["limit"], 10)
        self.assertIsNone(filters["source_id"])
        self.assertIsNone(filters["kind"])
        called = []

        def searcher(root, **received):
            called.append(received)
            return SAMPLE

        with local_only(searcher) as url:
            with urlopen(url + "/", timeout=5) as response:
                self.assertEqual(response.status, 200)
                page = response.read().decode("utf-8")
                self.assertNotIn("검색 조건 오류", page)
                self.assertNotIn("공개 근거 열기", page)
                self.assertIn("승인된 공개 근거 원장을 조회합니다", page)
            # An explicitly submitted empty form *does* invoke original W04.
            with urlopen(url + "/?q=&domain=&kind=&source=&limit=10", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn("공개 근거 열기", response.read().decode("utf-8"))
        self.assertEqual(called, [filters])

    def test_valid_search_rejects_invalid_source_ledger_without_blame_or_leak(self):
        cases = (
            (DiscoveryError, "SOURCE_VALIDATION_FAILED_NO_GO"),
            (LibrarySearchError, "SOURCE_VALIDATION_FAILED_NO_GO"),
            (ValueError, "SOURCE_VALIDATION_FAILED_NO_GO"),
            (OSError, "SOURCE_STORAGE_UNAVAILABLE_NO_GO"),
        )
        for exc_type, code in cases:
            with self.subTest(error=exc_type.__name__):
                private_message = "UNTRUSTED_SECRET_STRING_NOT_FOR_HTML"

                def broken_searcher(root, **filters):
                    raise exc_type(private_message)

                with local_only(broken_searcher) as url:
                    with self.assertRaises(HTTPError) as response:
                        urlopen(url + "/?q=Python&limit=5", timeout=5)
                    self.assertEqual(response.exception.code, 503)
                    html = response.exception.read().decode("utf-8")
                    self.assertIn(code, html)
                    self.assertIn("원장 조회/검증", html)
                    self.assertNotIn("검색 입력값이", html)
                    self.assertNotIn("검색 조건 오류", html)
                    self.assertNotIn(private_message, html)
                    self.assertNotIn("공개 근거 열기", html)
                    self.assertIn('value="Python"', html)

    def test_malformed_query_still_400_without_calling_searcher(self):
        invoked = []

        def must_not_call(root, **filters):
            invoked.append(True)
            return SAMPLE

        with local_only(must_not_call) as url:
            with self.assertRaises(HTTPError) as response:
                urlopen(url + "/?q=bad%0Aquery", timeout=5)
            self.assertEqual(response.exception.code, 400)
            html = response.exception.read().decode("utf-8")
            self.assertIn("검색 조건 오류", html)
            self.assertNotIn("원장 조회 차단", html)
        self.assertEqual(invoked, [])

    def test_unexpected_library_status_does_not_display_rows(self):
        fake = dict(SAMPLE, status="PUBLISH_READY")
        page = render_page(parse_request_filters(""), fake)
        self.assertNotIn("공개 근거 열기", page)
        self.assertIn("안전 검증 미완료", page)


if __name__ == "__main__":
    unittest.main()
