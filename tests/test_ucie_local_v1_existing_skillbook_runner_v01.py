"""Local V1 L2: use the TWO existing SkillBook consumers through one browser.

No new skill, source miner, customer file, process launch, or promotion.
The only inputs executed are the pre-existing UCIE-owned static/disposable
fixtures, explicitly labelled synthetic.
"""
from __future__ import annotations

from http.server import HTTPServer
import http.client
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app


class ExistingSkillbookLocalUserWorkflowTests(unittest.TestCase):
    def test_two_available_books_link_into_same_local_product(self):
        with patch.object(app, "_paged_evidence", return_value="<section>W04</section>"):
            html = app._library(Path("UCIE"), "q=")
        self.assertIn('/local/skillbook-run?book=python', html)
        self.assertIn('/local/skillbook-run?book=git', html)
        self.assertIn('/skillbooks/', html)
        self.assertIn("미승인", html)

    def test_preview_never_executes_recipe(self):
        with (
            patch("ucie_miner.skillbook_consumer_pilot_v01.demonstrate_synthetic_consumer",
                  side_effect=AssertionError("unexpected Python demo")),
            patch("ucie_miner.skillbook_git_porcelain_product_v01.demonstrate_in_memory_consumer",
                  side_effect=AssertionError("unexpected Git demo")),
        ):
            for book in ("python", "git"):
                html = app._skillbook_runner("book=" + book)
                self.assertIn("기존 기계 계약으로 한정형 예제 직접 실행", html)
                self.assertIn("미승인", html)
                self.assertNotIn("실제 실행 결과", html)

    def test_python_first_party_recipe_executed_with_disposable_fixture(self):
        html = app._skillbook_runner("book=python&run=1")
        self.assertIn("첫 번째 파티 코드 실제 실행 결과", html)
        self.assertIn("정규 파일: 2개", html)
        self.assertIn("상대 경로 차단: 예", html)
        self.assertIn("소유자 실제 파일 스캔: 없음", html)
        self.assertIn("FIRST_PARTY_CONSUMER_EXECUTION_OBSERVED_NO_RELEASE", html)
        self.assertIn("독립 QA", html)

    def test_git_first_party_recipe_executed_without_git_or_repo(self):
        html = app._skillbook_runner("book=git&run=1")
        self.assertIn("Git 기계 계약 실제 파싱 결과", html)
        self.assertIn("합성 Git 레코드: 4건", html)
        self.assertIn("추적 변경: 1", html)
        self.assertIn("충돌: 1", html)
        self.assertIn("저장소 스캔: 없음", html)
        self.assertIn("FIRST_PARTY_SYNTHETIC_GIT_CONSUMER_OBSERVED_NO_RELEASE", html)

    def test_deferred_or_forged_parameters_fail_closed(self):
        for raw in (
            "", "book=other", "book=git&run=0", "book=git&run=yes",
            "book=python&run=1&repo=D:/other", "book=git&book=python",
            "book=git&run=1&approved=true", "book=python&run=1&path=.",
        ):
            with self.subTest(raw=raw), self.assertRaises(app.LocalProductError):
                app._skillbook_runner(raw)

    def test_forged_approval_and_unsafe_consumer_claims_rejected(self):
        from ucie_miner.skillbook_git_porcelain_product_v01 import (
            demonstrate_in_memory_consumer,
        )
        original = demonstrate_in_memory_consumer()
        for field, value in (
            ("owner_release_approved", True),
            ("real_repository_inspected", True),
            ("git_subprocess_invoked", True),
            ("independent_qa_verified", True),
            ("operating_database_writes", 1),
            ("export_allowed", True),
        ):
            forged = {**original, field: value}
            with self.subTest(field=field), patch(
                "ucie_miner.skillbook_git_porcelain_product_v01.demonstrate_in_memory_consumer",
                return_value=forged,
            ), self.assertRaises(app.LocalProductError):
                app._skillbook_runner("book=git&run=1")


class LocalSkillbookHttpTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="UCIE_LOCAL_BOOK_RUN_")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "UCIE"
        (root / ".git").mkdir(parents=True)
        self.server = HTTPServer(("127.0.0.1", 0), app.make_handler(root))
        worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(worker.join, 2)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, path, *, method="GET", host=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=10)
        try:
            connection.request(method, path, headers={
                "Host": host or "127.0.0.1:" + str(self.server.server_port)})
            response = connection.getresponse()
            return response.status, response.read().decode("utf-8", "replace")
        finally:
            connection.close()

    def test_http_both_existing_book_consumers_and_fail_closed(self):
        for book in ("python", "git"):
            with self.subTest(book=book):
                status, html = self.request(
                    "/local/skillbook-run?book=" + book + "&run=1")
                self.assertEqual(status, 200)
                self.assertIn("UCIE 작성 예제만 실행", html)
                self.assertIn("실제 실행 결과" if book == "python"
                              else "Git 기계 계약 실제 파싱 결과", html)
        status, body = self.request("/local/skillbook-run?book=unknown&run=1")
        self.assertEqual(status, 400)
        self.assertIn("FAIL_CLOSED", body)

    def test_post_and_remote_hosts_remain_blocked(self):
        self.assertEqual(self.request("/local/skillbook-run?book=git",
                                      method="POST")[0], 405)
        self.assertEqual(self.request("/local/skillbook-run?book=git",
                                      host="other.example")[0], 403)


if __name__ == "__main__":
    unittest.main()
