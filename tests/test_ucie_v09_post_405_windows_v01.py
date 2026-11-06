"""UCIE-only localhost HTTP 405 regression; no external network or file writes."""
from __future__ import annotations

from contextlib import contextmanager
from http.server import HTTPServer
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ucie_miner.library_browser_v09 import make_handler

IDENTITY = "f" * 64


@contextmanager
def isolated_browser():
    invoked = []
    def forbidden_public_probe(*args, **kwargs):
        invoked.append(True)
        raise AssertionError("POST must not dispatch a public-source probe")
    # A synthetic UCIE-only root. No disk access is made on POST.
    handler = make_handler(Path("Z:/UCIE/synthetic"),
                           public_prober=forbidden_public_probe)
    with HTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield "http://127.0.0.1:" + str(server.server_port), invoked
        finally:
            server.shutdown()
            thread.join(timeout=5)


class WindowsPostResponseTests(unittest.TestCase):
    def test_nonempty_post_body_is_rejected_by_http_405_without_tcp_reset(self):
        with isolated_browser() as (url, invoked):
            request = Request(url + "/public-check/" + IDENTITY,
                              data=b"x", method="POST")
            with self.assertRaises(HTTPError) as err:
                urlopen(request, timeout=5)
            self.assertEqual(err.exception.code, 405)
            self.assertEqual(invoked, [])

    def test_two_small_posts_are_rejected_without_public_fetch(self):
        with isolated_browser() as (url, invoked):
            for body in (b"", b"synthetic"):
                with self.subTest(length=len(body)):
                    request = Request(url + "/public-check/" + IDENTITY,
                                      data=body, method="POST")
                    with self.assertRaises(HTTPError) as err:
                        urlopen(request, timeout=5)
                    self.assertEqual(err.exception.code, 405)
            self.assertEqual(invoked, [])

    def test_no_infinite_read_for_bounded_post(self):
        # The handler caps body read at 1024 and rejects transfer encoding.
        # No external service or user-controlled file path is opened.
        with isolated_browser() as (url, invoked):
            request = Request(url + "/public-check/" + IDENTITY,
                              data=b"x" * 1024, method="POST")
            with self.assertRaises(HTTPError) as err:
                urlopen(request, timeout=5)
            self.assertEqual(err.exception.code, 405)
            self.assertEqual(invoked, [])


if __name__ == "__main__":
    unittest.main()
