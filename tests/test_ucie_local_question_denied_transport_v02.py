"""UCIE Local V1 rejected POST transport receipt on real loopback only.

Prevent Windows TCP resets for small denied request bodies without weakening
same-origin, size, privacy or route boundaries. Disposable first-party server.
"""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest

from ucie_miner import local_v1_app_v01 as app


class LocalDeniedPostTransportTests(unittest.TestCase):
    def test_01_denied_small_bodies_have_bounded_http_responses(self):
        with TemporaryDirectory(prefix="UCIE_QUESTION_DENIAL_V02_") as tmp:
            root = Path(tmp) / "UCIE"
            (root / ".git").mkdir(parents=True)
            with HTTPServer(("127.0.0.1", 0), app.make_handler(root)) as server:
                worker = Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    host = "127.0.0.1:" + str(server.server_port)
                    source = "http://" + host
                    default = {
                        "Host": host,
                        "Origin": source,
                        "Content-Type": "application/x-www-form-urlencoded",
                    }
                    cases = (
                        ("/local/ask", {"Origin": ""}, b"question=SANITIZED_TEST", 403),
                        ("/local/ask", {"Origin": "https://untrusted.invalid"},
                         b"question=SANITIZED_TEST", 403),
                        ("/local/ask", {"Content-Type": "application/json"},
                         b"question=SANITIZED_TEST", 400),
                        ("/local/solve", {}, b"question=SANITIZED_TEST", 405),
                        ("/local/ask", {}, b"question=" + b"x" * 6145, 413),
                    )
                    for repeat in range(3):
                        for path, override, payload, expected in cases:
                            with self.subTest(round=repeat, route=path,
                                              expected=expected,
                                              override=override):
                                headers = {**default, **override}
                                with closing(HTTPConnection(
                                        "127.0.0.1", server.server_port,
                                        timeout=4)) as client:
                                    client.request("POST", path, body=payload,
                                                   headers=headers)
                                    response = client.getresponse()
                                    content = response.read().decode(
                                        "utf-8", "replace")
                                    self.assertEqual(response.status, expected)
                                    self.assertEqual(
                                        response.getheader("Cache-Control"),
                                        "no-store")
                                    self.assertNotIn("SANITIZED_TEST", content)
                                    self.assertLess(len(content), 200)
                finally:
                    server.shutdown()
                    worker.join(timeout=5)
                    self.assertFalse(worker.is_alive())
            # Denied requests do not create a file, run a miner, or log text.
            self.assertEqual(
                {p.relative_to(root).as_posix() for p in root.rglob("*")},
                {".git"})


if __name__ == "__main__":
    unittest.main()
