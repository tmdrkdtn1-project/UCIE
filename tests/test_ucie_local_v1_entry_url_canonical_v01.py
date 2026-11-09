"""UCIE Local V1 browser entry-link compatibility regression.

Tests only a disposable first-party loopback listener. No owner port 18767,
no actual scheduler/browser/Cloudflare, and no operating database writes.
"""
from __future__ import annotations

import http.client
from pathlib import Path
import tempfile
import threading
import unittest

from ucie_miner import local_v1_app_v01 as app


class UCIEEntryUrlCanonicalRegression(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="UCIE_ENTRY_URL_")
        self.addCleanup(t.cleanup)
        root = Path(t.name) / "UCIE"
        (root / ".git").mkdir(parents=True)
        self.server = app.LOCAL_SERVER_CLASS(
            ("127.0.0.1", 0), app.make_handler(root))
        th = threading.Thread(target=self.server.serve_forever, daemon=True)
        th.start()
        self.addCleanup(th.join, 2)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, route, host=None):
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=3)
        try:
            conn.request("GET", route, headers={
                "Host": host or "127.0.0.1:" + str(self.server.server_port),
                "Connection": "close",
            })
            response = conn.getresponse()
            body = response.read(80000)
            headers = dict(response.getheaders())
            return response.status, body, headers
        finally:
            conn.close()

    def test_exact_local_url_remains_normal_html(self):
        status, body, headers = self.get("/local")
        self.assertEqual(status, 200)
        self.assertIn(b"UCIE Local V1", body)
        self.assertIn(b"<html", body.lower())
        self.assertIn("default-src 'none'",
                      headers.get("Content-Security-Policy", ""))

    def test_trailing_slash_redirects_only_to_canonical_local_home(self):
        status, body, headers = self.get("/local/")
        self.assertEqual(status, 302)
        self.assertEqual(body, b"")
        self.assertEqual(headers.get("Location"), "/local")
        self.assertEqual(headers.get("Cache-Control"), "no-store")

    def test_known_tracking_queries_are_stripped_not_reflected(self):
        for route in (
            "/local?utm_source=chatgpt.com",
            "/local/?utm_source=chatgpt.com",
            "/local/?utm_source=chatgpt.com&utm_medium=referral",
            "/local?utm_campaign=ucie&utm_content=link&utm_term=local",
        ):
            with self.subTest(route=route):
                status, body, headers = self.get(route)
                self.assertEqual(status, 302)
                self.assertEqual(body, b"")
                self.assertEqual(headers.get("Location"), "/local")
                self.assertNotIn("utm_", headers.get("Location", ""))

    def test_unknown_or_unbounded_query_still_fails_closed(self):
        for route in (
            "/local?approval=true",
            "/local/?customer=true",
            "/local?utm_source=one&utm_source=two",
            "/local?utm_source=",
            "/local?utm_source=%3Cscript%3E",
            "/local?utm_source=chatgpt.com&customer=true",
            "/local?utm_source=" + "a" * 250,
            "/?utm_source=chatgpt.com",
        ):
            with self.subTest(route=route):
                status, body, _ = self.get(route)
                self.assertEqual(status, 400)
                self.assertEqual(
                    body, b"UCIE_LOCAL_V1_FAIL_CLOSED_NO_RELEASE")

    def test_forged_host_unknown_path_and_health_are_unchanged(self):
        status, body, _ = self.get("/local/?utm_source=chatgpt.com",
                                   host="malicious.example")
        self.assertEqual(status, 403)
        self.assertEqual(body, b"LOOPBACK_ONLY")
        status, body, _ = self.get("/local/other")
        self.assertEqual(status, 404)
        self.assertEqual(body, b"ROUTE_NOT_FOUND")
        status, body, headers = self.get("/local/health")
        self.assertEqual(status, 200)
        self.assertIn(b'"online_release_authorized": false', body)
        self.assertIn("default-src 'none'",
                      headers.get("Content-Security-Policy", ""))


if __name__ == "__main__":
    unittest.main()
