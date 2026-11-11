"""UCIE-only Windows-safe read-only HTTP POST denial across V03 and V07.

Synthetic ephemeral loopback only; no source GET, operational DB, public
network request, scheduler action, or lasting HTTP process.
"""
from __future__ import annotations

from contextlib import contextmanager
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ucie_miner import library_browser_v03 as v03
from ucie_miner import library_browser_v07 as v07


@contextmanager
def loopback(make_handler):
    with HTTPServer(("127.0.0.1", 0),
                    make_handler(Path("Z:/UCIE/SYNTHETIC_NO_DB"))) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            worker.join(timeout=5)


class LegacyBrowserPostDenialTests(unittest.TestCase):
    def reject(self, url, size, code):
        request = Request(url + "/audit", data=b"x" * size, method="POST")
        with self.assertRaises(HTTPError) as denied:
            urlopen(request, timeout=5)
        with denied.exception as response:
            self.assertEqual(response.code, code)
            self.assertEqual(
                response.read(),
                b"GET_ONLY" if code == 405 else b"POST_BODY_TOO_LARGE")

    def test_v03_bounded_post_denied_after_body_is_read(self):
        with loopback(v03.make_handler) as url:
            for size, code in ((0, 405), (1, 405), (512, 405),
                               (8192, 405), (8193, 413),
                               (16384, 413)):
                with self.subTest(size=size):
                    self.reject(url, size, code)

    def test_v07_inherits_bounded_post_denial_without_reset(self):
        with loopback(v07.make_handler) as url:
            for size, code in ((1, 405), (512, 405),
                               (8192, 405), (8193, 413)):
                with self.subTest(size=size):
                    for _ in range(3):
                        self.reject(url, size, code)

    def test_write_post_does_not_call_get_or_persist_anything(self):
        with loopback(v07.make_handler) as url:
            for _ in range(4):
                self.reject(url, 1, 405)
        # No actual data path exists at the synthetically selected root.
        self.assertFalse(Path("Z:/UCIE/SYNTHETIC_NO_DB").exists())


if __name__ == "__main__":
    unittest.main()
