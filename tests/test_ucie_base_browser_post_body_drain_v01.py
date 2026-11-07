"""UCIE loopback-only regression: POST rejected without socket resets.

The handler never reads project sources, writes databases, contacts external
services, or starts/stops the operating scheduler. Synthetic server only.
"""
from contextlib import contextmanager
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ucie_miner import library_browser_v02 as base
from ucie_miner import library_browser_v07 as audit


@contextmanager
def ephemeral_loopback(handler_factory):
    handler = handler_factory(Path("Z:/UCIE/synthetic"))
    with HTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port)
        finally:
            server.shutdown()
            thread.join(timeout=5)


class BrowserRejectedPostTests(unittest.TestCase):
    def _reject(self, url, payload, expected):
        request = Request(url + "/audit", data=payload, method="POST")
        with self.assertRaises(HTTPError) as caught:
            urlopen(request, timeout=5)
        with caught.exception as response:
            self.assertEqual(response.code, expected)
            self.assertEqual(
                response.read(), b"GET_ONLY" if expected == 405
                else b"POST_BODY_TOO_LARGE")

    def test_base_browser_returns_405_after_bounded_body_drain(self):
        with ephemeral_loopback(base.make_handler) as url:
            for size in (0, 1, 512, 8192):
                with self.subTest(size=size):
                    for repeat in range(3):
                        self._reject(url, b"x" * size, 405)

    def test_derived_v07_browser_inherits_reliable_405(self):
        with ephemeral_loopback(audit.make_handler) as url:
            for size in (1, 512, 8192):
                with self.subTest(size=size):
                    self._reject(url, b"x" * size, 405)

    def test_small_oversized_bodies_are_discarded_and_still_413(self):
        # The rejected request data must be fully drained (not processed)
        # before the server closes the connection on Windows.
        with ephemeral_loopback(base.make_handler) as url:
            for size in (8193, 8194, 16384):
                with self.subTest(size=size):
                    for _ in range(3):
                        self._reject(url, b"x" * size, 413)

    def test_zero_length_post_is_405_and_does_not_trigger_get(self):
        with ephemeral_loopback(base.make_handler) as url:
            self._reject(url, b"", 405)


if __name__ == "__main__":
    unittest.main()
