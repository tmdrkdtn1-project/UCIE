"""UCIE owner Local V1 V02 live-HTTP, read-only visual-contract acceptance.

This is **not** a browser screenshot, CSS layout measurement, independent QA,
or approval to launch. It makes GET requests ONLY to fixed UCIE 127.0.0.1:18767
from the exact owner D:/UCIE checkout, without reading other projects.
No test server is created and no operating database is modified.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import socket
import unittest

HOST = "127.0.0.1"
PORT = 18767
MAX_BODY = 900_000
ROOT = Path(__file__).resolve().parents[1]
EXACT_OWNER = os.name == "nt" and ROOT == Path("D:/UCIE").resolve()


@unittest.skipUnless(EXACT_OWNER, "OWNER_HOST_EXACT_D_UCIE_ONLY")
class OwnerLiveV02HttpAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            with socket.create_connection((HOST, PORT), timeout=1):
                pass
        except OSError:
            raise unittest.SkipTest("UCIE_OWNER_LOCAL_V1_NOT_LISTENING") from None

    def fetch(self, path: str) -> tuple[int, dict[str, str], str]:
        self.assertTrue(path.startswith("/"), "bounded UCIE relative route")
        self.assertLessEqual(len(path), 180)
        connection = http.client.HTTPConnection(HOST, PORT, timeout=12)
        try:
            connection.request("GET", path, headers={
                "Host": f"{HOST}:{PORT}", "Connection": "close",
            })
            response = connection.getresponse()
            body = response.read(MAX_BODY + 1)
            self.assertLessEqual(len(body), MAX_BODY, "bounded local response")
            headers = {key.lower(): value for key, value in response.getheaders()}
            return response.status, headers, body.decode("utf-8", "strict")
        finally:
            connection.close()

    def test_live_server_identity_and_no_release(self):
        status, headers, body = self.fetch("/local/health")
        self.assertEqual(status, 200)
        self.assertIn("application/json", headers.get("content-type", ""))
        self.assertEqual(headers.get("cache-control"), "no-store")
        data = json.loads(body)
        self.assertEqual(data.get("schema"), "UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01")
        self.assertEqual(data.get("bound_host"), HOST)
        self.assertEqual(data.get("bound_port"), PORT)
        self.assertIs(data.get("owner_acceptance_verified"), True)
        self.assertIs(data.get("online_release_authorized"), False)
        self.assertEqual(data.get("operating_database_writes"), 0)

    def test_live_home_dashboard_and_security_headers(self):
        status, headers, body = self.fetch("/local")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers.get("content-type", ""))
        self.assertEqual(headers.get("cache-control"), "no-store")
        self.assertEqual(headers.get("x-frame-options"), "DENY")
        self.assertIn("default-src 'none'", headers.get("content-security-policy", ""))
        self.assertIn('class="app-shell"', body)
        self.assertIn('class="pillar-grid"', body)
        self.assertEqual(body.count('class="pillar-card"'), 4)
        self.assertIn('aria-label="주요 기능"', body)
        self.assertIn("온라인·고객 출시 보류", body)
        self.assertNotIn("<script", body.lower())
        for route in (
                "/local/error", "/local/engine",
                "/local/library", "/local/evolution"):
            self.assertIn(f'href="{route}"', body)

    def test_live_four_pillars_keep_read_only_presentation(self):
        routes = (
            "/local/error?q=python",
            "/local/engine",
            "/local/library?q=Git",
            "/local/evolution?q=python",
        )
        for route in routes:
            with self.subTest(route=route):
                status, headers, body = self.fetch(route)
                self.assertEqual(status, 200)
                self.assertEqual(headers.get("cache-control"), "no-store")
                self.assertIn('class="app-shell"', body)
                self.assertIn('class="content-stack"', body)
                self.assertIn("온라인·고객 출시 보류", body)
                self.assertNotIn('method="post"', body.lower())
                self.assertNotIn("CUSTOMER_RELEASE_AUTHORIZED=true", body)

    def test_live_nested_library_routes_receive_the_same_visual_theme(self):
        routes = (
            "/catalog?shelf=all&limit=5",
            "/skillbooks",
            "/skillbooks/qa-plan",
            "/skillbooks/release-gates",
        )
        for route in routes:
            with self.subTest(route=route):
                status, headers, body = self.fetch(route)
                self.assertEqual(status, 200)
                self.assertIn("text/html", headers.get("content-type", ""))
                self.assertEqual(body.count('data-ucie-nested-theme="v02"'), 1)
                self.assertIn('<style data-ucie-nested-theme="v02">', body)
                self.assertIn("미승인" if route == "/skillbooks"
                              else "UCIE", body)
                self.assertNotIn("<script", body.lower())


if __name__ == "__main__":
    unittest.main()
