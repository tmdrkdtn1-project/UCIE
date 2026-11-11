"""B1/B2 Python official-doc -> candidate -> synthetic engine -> Local V04.

Only UCIE-owned synthetic temp files, ephemeral 127.0.0.1 HTTP, and exact
existing local app routes. Home design and improvement shell are not changed.
"""
from __future__ import annotations

from contextlib import closing
from hashlib import sha256
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import python_scandir_review_v01 as review


class PythonScandirLocalEngineTests(unittest.TestCase):
    def test_existing_v04_menu_has_second_python_case(self):
        before = sha256(app._home().encode("utf-8")).hexdigest()
        html = app._engine("")
        self.assertIn("/local/engine?purpose=PYTHON_SCANDIR_SAFE", html)
        self.assertIn("Python 반복자 안전 사용", html)
        self.assertIn("/local/engine?purpose=MCP_PROMPTS_CONTRACT", html)
        self.assertEqual(sha256(app._home().encode("utf-8")).hexdigest(),
                         before)
        self.assertEqual(tuple(x[0] for x in app.ROUTES), (
            "/local/error", "/local/engine",
            "/local/library", "/local/evolution",
        ))

    def test_python_page_exposes_safe_official_source_and_user_flow(self):
        html = app._engine("purpose=PYTHON_SCANDIR_SAFE")
        self.assertIn("Python os.scandir 반복자 안전 사용 검토", html)
        self.assertIn('href="https://docs.python.org/3/library/os.html"', html)
        for link in (
            "/local/error?q=Python", "/local/library?q=Python",
            "/local/evolution?q=Python",
        ):
            self.assertIn(link, html)
        self.assertIn("안전 호출 원칙", html)
        self.assertIn("합성 파일", html)
        self.assertIn("원본 문서 개정", html)
        self.assertIn("자동 승인·배포되지 않습니다", html)
        self.assertNotIn("CUSTOMER_RELEASE_GO", html)

    def test_engine_truly_calls_ucie_owned_safe_trial(self):
        real = review.run_python_scandir_review
        with patch.object(review, "run_python_scandir_review",
                          wraps=real) as trial:
            app._engine("purpose=PYTHON_SCANDIR_SAFE")
            trial.assert_called_once_with()
        record = real()
        self.assertEqual(record["network_requests"], 0)
        self.assertEqual(record["operating_database_writes"], 0)
        self.assertFalse(record["export_allowed"])
        self.assertTrue(record["synthetic_trial"]["unique_entries_match"])

    def test_forged_source_rights_or_trial_results_fail_closed(self):
        original = review.run_python_scandir_review()
        for field, value in (
            ("source_id", "doc:unapproved/private"),
            ("official_document_url", "https://private.invalid/x"),
            ("source_license_status", "SIGNED_AND_RELEASED"),
            ("documentation_revision_status", "PINNED_VERIFIED"),
            ("export_allowed", True),
            ("auto_promoted", True),
            ("customer_release_authorized", True),
            ("network_requests", 1),
            ("operating_database_writes", 1),
        ):
            with self.subTest(field=field):
                fake = dict(original)
                fake[field] = value
                with patch.object(review, "run_python_scandir_review",
                                  return_value=fake):
                    with self.assertRaises(app.LocalProductError):
                        app._engine("purpose=PYTHON_SCANDIR_SAFE")
        fake = dict(original)
        fake["synthetic_trial"] = dict(
            original["synthetic_trial"], unique_entries_match=False)
        with patch.object(review, "run_python_scandir_review",
                          return_value=fake):
            with self.assertRaises(app.LocalProductError):
                app._engine("purpose=PYTHON_SCANDIR_SAFE")

    def test_invalid_query_and_unregistered_engine_remain_denied(self):
        for args in (
            "purpose=PYTHON_SCANDIR_SAFE&run=external",
            "purpose=PYTHON_SCANDIR_SAFE&purpose=MCP_PROMPTS_CONTRACT",
            "purpose=UNAPPROVED_PLUGIN",
        ):
            with self.subTest(args=args):
                with self.assertRaises(app.LocalProductError):
                    app._engine(args)

    def test_ephemeral_http_real_get_and_negative_post(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / ".git").is_dir():
            self.skipTest("only exact UCIE project checkout has local HTTP test")
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(root))
        srv.daemon_threads = True
        thread = Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            with closing(HTTPConnection(
                    "127.0.0.1", srv.server_port, timeout=10)) as conn:
                conn.request("GET", "/local/engine?purpose=PYTHON_SCANDIR_SAFE")
                response = conn.getresponse()
                payload = response.read(600_000)
                self.assertEqual(response.status, 200)
                self.assertIn("승인된 Python 공식 문서".encode("utf-8"),
                              payload)
                self.assertIn(b"https://docs.python.org/3/library/os.html",
                              payload)
            with closing(HTTPConnection(
                    "127.0.0.1", srv.server_port, timeout=10)) as conn:
                conn.request("POST", "/local/engine?purpose=PYTHON_SCANDIR_SAFE")
                response = conn.getresponse()
                self.assertEqual(response.status, 405)
                response.read()
            with closing(HTTPConnection(
                    "127.0.0.1", srv.server_port, timeout=10)) as conn:
                conn.request("GET", "/local/engine?purpose=UNKNOWN")
                response = conn.getresponse()
                self.assertEqual(response.status, 400)
                response.read()
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
