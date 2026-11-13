"""Real UCIE Local V1 GET-only four-domain troubleshooting user flow.

No customer paths, personal error logs, network fetch, vendor execution, source
promotion, new collector, scheduler or operating DB. Uses localhost ephemeral
port only; no interaction with the user's resident Local V1 instance.
"""
from __future__ import annotations

import http.client
from http.server import HTTPServer
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import local_error_actionable_workflow_v01 as triage


class SafeLocalErrorWorkflowTests(unittest.TestCase):
    def test_four_official_public_domains_have_bounded_human_actions(self):
        self.assertEqual(set(triage.CASE_IDS), {
            "python-env", "powershell-command", "git-repository", "mcp-prompts"
        })
        for case_id in triage.CASE_IDS:
            with self.subTest(case_id=case_id):
                result = triage.get_case(case_id)
                self.assertEqual(result["schema"], triage.SCHEMA)
                self.assertEqual(result["status"], triage.STATUS)
                self.assertEqual(len(result["checks"]), 2)
                self.assertFalse(result["commands_executed"])
                self.assertFalse(result["user_logs_or_files_read"])
                self.assertFalse(result["independent_fix_validated"])
                self.assertFalse(result["automatic_rule_promotion"])
                self.assertFalse(result["customer_distribution_authorized"])
                self.assertEqual(result["network_requests"], 0)
                self.assertEqual(result["operating_database_writes"], 0)
                self.assertTrue(result["official_url"].startswith((
                    "https://docs.python.org/", "https://learn.microsoft.com/",
                    "https://git-scm.com/", "https://github.com/modelcontextprotocol/python-sdk/"
                )))

    def test_known_case_opens_actionable_guidance_without_any_db_lookup(self):
        with patch.object(app, "_search", side_effect=AssertionError("no db lookup")):
            for case_id in triage.CASE_IDS:
                page = app._error(Path("UCIE"), "case=" + case_id)
                self.assertIn('data-safe-triage="true"', page)
                self.assertIn(triage.get_case(case_id)["symptom"], page)
                self.assertIn("직접 확인할 안전한 명령", page)
                self.assertIn("자동 실행 안 함", page)
                self.assertIn(triage.get_case(case_id)["official_title"], page)
                self.assertIn("/local/library?q=", page)
                self.assertIn("NO_GO", page)

    def test_existing_search_and_source_guides_stay_available(self):
        empty = app._error(Path("UCIE"), "")
        self.assertIn('name="q"', empty)
        self.assertIn('name="case"', empty)
        self.assertIn("/local/error", empty)
        self.assertNotIn('data-safe-triage="true"', empty)
        mcp = app._error(Path("UCIE"), "case=mcp-prompts")
        self.assertIn("/local/guide/mcp-prompts", mcp)
        self.assertIn("/local/engine?purpose=MCP_PROMPTS_CONTRACT", mcp)

    def test_unknown_or_injected_case_fails_closed(self):
        for raw in (
            "case=unapproved", "case=python-env&case=git-repository",
            "case=python-env&page=2", "case=python-env&admin=true",
            "case=%3Cscript%3E", "case=python-env%0A", "case=python-env%2F",
            "case=../../OTHER", "case=%00", "case=" + "x" * 100,
        ):
            with self.subTest(raw=raw), self.assertRaises(
                    (app.LocalProductError, ValueError)):
                app._error(Path("UCIE"), raw)
        for raw in ("git-repository ", None, True, "OTHER", ""):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                triage.get_case(raw)

    def test_no_customer_log_or_arbitrary_command_execution(self):
        with patch("subprocess.run", side_effect=AssertionError("never execute")), \
             patch("os.system", side_effect=AssertionError("never execute")):
            for case_id in triage.CASE_IDS:
                app._error(Path("UCIE"), "case=" + case_id)


class LocalErrorLoopbackHTTPTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="UCIE_LOCAL_TRIAGE_")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "UCIE"
        (root / ".git").mkdir(parents=True)
        self.srv = HTTPServer(("127.0.0.1", 0), app.make_handler(root))
        thread = Thread(target=self.srv.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def request(self, route: str, *, method: str = "GET", host: str | None = None):
        client = http.client.HTTPConnection("127.0.0.1", self.srv.server_port, timeout=5)
        try:
            client.request(method, route, headers={
                "Host": host or "127.0.0.1:" + str(self.srv.server_port)
            })
            answer = client.getresponse()
            return answer.status, answer.read().decode("utf-8", "replace"), dict(
                answer.getheaders())
        finally:
            client.close()

    def test_real_four_domain_browser_journeys(self):
        for case_id in triage.CASE_IDS:
            with self.subTest(case_id=case_id):
                status, body, headers = self.request("/local/error?case=" + case_id)
                self.assertEqual(status, 200)
                self.assertIn(triage.get_case(case_id)["symptom"], body)
                self.assertIn("Cache-Control", headers)
                self.assertEqual(headers.get("X-Frame-Options"), "DENY")
                self.assertIn("default-src 'none'",
                              headers.get("Content-Security-Policy", ""))

    def test_real_http_rejects_unapproved_query_and_post(self):
        status, body, _ = self.request("/local/error?case=%3Cscript%3E")
        self.assertEqual(status, 400)
        self.assertIn("FAIL_CLOSED", body)
        status, _, _ = self.request("/local/error?case=python-env",
                                     host="outside.example")
        self.assertEqual(status, 403)
        status, body, _ = self.request("/local/error?case=python-env",
                                       method="POST")
        self.assertEqual(status, 405)
        self.assertIn("READ_ONLY", body)


if __name__ == "__main__":
    unittest.main()
