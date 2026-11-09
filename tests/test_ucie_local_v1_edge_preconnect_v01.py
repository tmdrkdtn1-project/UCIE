"""UCIE Local V1 Edge/Chromium speculative-socket regression.

Reproduce a real HTTPServer head-of-line block using only a first-party
disposable loopback listener and an intentionally unfinished HTTP header.
No real 18767 listener, TaskScheduler, Cloudflare, SQLite or other project.
"""
from __future__ import annotations

import http.client
from http.server import HTTPServer
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest

from ucie_miner import local_v1_app_v01 as app


class BrowserSpeculativeConnectionRegression(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="UCIE_EDGE_LOCAL_")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "UCIE"
        (root / ".git").mkdir(parents=True)
        # On old Local V1 this falls back to the actual HTTPServer class and
        # reproduces the stall. After fix the real launcher uses this class.
        self.server_class = getattr(app, "LOCAL_SERVER_CLASS", HTTPServer)
        self.server = self.server_class(
            ("127.0.0.1", 0), app.make_handler(root)
        )
        worker = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        worker.start()
        self.addCleanup(worker.join, 2)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def test_edge_preopened_connection_cannot_starve_local_home(self):
        host = "127.0.0.1"
        port = self.server.server_port
        unfinished = socket.create_connection((host, port), timeout=2)
        try:
            # The browser may pre-open a socket or leave request headers
            # incomplete. A single-threaded HTTPServer waits for this
            # connection, blocking the actual /local navigation.
            unfinished.sendall(
                ("GET /local/health HTTP/1.1\r\nHost: " + host +
                 ":" + str(port) + "\r\nX-UCIE-First-Party: preview\r\n"
                 ).encode("ascii")
            )
            time.sleep(0.10)
            conn = http.client.HTTPConnection(host, port, timeout=1.2)
            try:
                conn.request("GET", "/local", headers={
                    "Host": host + ":" + str(port),
                    "Connection": "close",
                })
                response = conn.getresponse()
                data = response.read()
                self.assertEqual(response.status, 200)
                self.assertIn(b'class="app-shell"', data)
                self.assertIn(b"<html", data.lower())
                self.assertLess(len(data), 100_000)
            finally:
                conn.close()
        finally:
            unfinished.close()

    def test_local_csp_and_no_online_release_stay_enforced(self):
        conn = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=2)
        try:
            conn.request("GET", "/local/health", headers={
                "Host": "127.0.0.1:" + str(self.server.server_port)})
            response = conn.getresponse()
            body = response.read()
            self.assertEqual(response.status, 200)
            self.assertIn(b'"online_release_authorized": false', body)
            self.assertIn(
                "default-src 'none'",
                response.getheader("Content-Security-Policy", ""),
            )
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
