"""UCIE Local V1 owner workload controls: real UCIE algorithms, synthetic inputs.

No customer project, arbitrary code, path, shell, file, network, operating DB,
or commercial change. Exact, bounded GET controls preserve original engine UI.
"""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from ucie_miner import local_v1_app_v01 as app
from ucie_miner.capability_trials import RECIPES


class OwnerEngineWorkloadTests(unittest.TestCase):
    def test_01_default_own_engine_has_editable_safe_controls(self):
        page = app._engine("purpose=SKILL_TEST_AUTOMATION")
        self.assertIn('data-owner-workload="true"', page)
        self.assertIn('data-owner-workload-result="true"', page)
        self.assertIn('action="/local/engine" method="get"', page)
        for field, default in (("rows", "128"), ("queries", "16"), ("repeats", "2")):
            self.assertIn('name="' + field + '"', page)
            self.assertIn('value="' + default + '"', page)
        self.assertIn("TAGGED_TEST_CASE_LOOKUP_V1", page)
        self.assertIn("기준 연산", page)
        self.assertIn("후보 연산", page)
        self.assertIn("합성 workload", page)

    def test_02_owner_numbers_change_real_first_party_results(self):
        page = app._engine(
            "purpose=SKILL_TEST_AUTOMATION&rows=64&queries=8&repeats=1")
        self.assertIn('name="rows" min="64" max="512" step="1" required value="64"', page)
        self.assertIn('name="queries" min="8" max="64" step="1" required value="8"', page)
        self.assertIn('name="repeats" min="1" max="5" step="1" required value="1"', page)
        # Existing UCIE algorithm: 64*8 baseline, 64+8 indexed candidate.
        self.assertIn("512</dd>", page)
        self.assertIn("72</dd>", page)
        self.assertIn("440</dd>", page)
        self.assertIn("True</dd>", page)
        self.assertNotIn("실제 프로젝트 또는 운영환경 개선 효과를 검증했습니다", page)

    def test_03_all_three_first_party_algorithms_run_for_bounded_owner_values(self):
        for purpose in RECIPES:
            with self.subTest(purpose=purpose):
                page = app._engine(
                    "purpose=" + purpose + "&rows=96&queries=12&repeats=1")
                self.assertIn('data-owner-workload-result="true"', page)
                self.assertIn("결과 동등성", page)
                self.assertIn("True</dd>", page)
                self.assertIn("실제 CPU 명령이나 처리 시간의 보장이 아닙니다", page)

    def test_04_exact_lower_and_upper_limits_accepted(self):
        for purpose in RECIPES:
            with self.subTest(purpose=purpose, bounds="lower"):
                html = app._engine("purpose=" + purpose +
                                   "&rows=64&queries=8&repeats=1")
                self.assertIn('value="64"', html)
            with self.subTest(purpose=purpose, bounds="upper"):
                html = app._engine("purpose=" + purpose +
                                   "&rows=512&queries=64&repeats=5")
                self.assertIn('value="512"', html)

    def test_05_numeric_out_of_bounds_noninteger_and_injection_refused(self):
        invalid = (
            "rows=63", "rows=513", "queries=7", "queries=65",
            "repeats=0", "repeats=6", "rows=0", "rows=-64", "rows=+64",
            "rows=64.0", "rows=064", "rows=1e3", "rows=x",
            "rows=%3Cscript%3E", "rows=", "rows=64&rows=128",
            "rows=64&unexpected=1", "rows=999999999999999999999",
        )
        for fields in invalid:
            with self.subTest(fields=fields), self.assertRaises(app.LocalProductError):
                app._engine("purpose=ENGINE_INCREMENTAL_BUILD&" + fields)

    def test_06_workload_cannot_override_four_pillar_or_security_examples(self):
        for purpose in ("B2_CONNECTED_TRIAGE", "PYTHON_SCANDIR_SAFE",
                        "MCP_PROMPTS_CONTRACT", "REAL_PUBLIC_CATALOG", ""):
            with self.subTest(purpose=purpose), self.assertRaises(app.LocalProductError):
                app._engine("purpose=" + purpose + "&rows=128")

    def test_07_existing_other_engines_unchanged_without_workload_params(self):
        for text in (
            "purpose=B2_CONNECTED_TRIAGE&case=python-env&scenario=issue",
            "purpose=MCP_PROMPTS_CONTRACT",
            "purpose=PYTHON_SCANDIR_SAFE",
        ):
            with self.subTest(query=text):
                body = app._engine(text)
                self.assertNotIn('data-owner-workload-result="true"', body)
                self.assertIn("UCIE", body)

    def test_08_repeat_query_is_not_ever_request_or_content_execution(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            for purpose in RECIPES:
                page = app._engine(
                    "purpose=" + purpose + "&rows=128&queries=24&repeats=2")
                self.assertIn('data-owner-workload-result="true"', page)
                self.assertIn("합성 workload 비교", page)
                self.assertNotIn("user_file", page)

    def test_09_actual_get_only_loopback_routes_and_failure_codes(self):
        with TemporaryDirectory(prefix="UCIE_OWNER_ENGINE_WORKLOAD_") as tmp:
            root = Path(tmp) / "UCIE"
            (root / ".git").mkdir(parents=True)
            with HTTPServer(("127.0.0.1", 0), app.make_handler(root)) as srv:
                thread = Thread(target=srv.serve_forever, daemon=True)
                thread.start()
                try:
                    def request(path, method="GET", host=None):
                        with closing(HTTPConnection("127.0.0.1", srv.server_port, timeout=8)) as conn:
                            conn.request(method, path, headers={
                                "Host": host or "127.0.0.1:" + str(srv.server_port)})
                            response = conn.getresponse()
                            return response.status, response.read().decode("utf-8", "replace")
                    for purpose in RECIPES:
                        url = ("/local/engine?purpose=" + purpose +
                               "&rows=64&queries=8&repeats=1")
                        with self.subTest(purpose=purpose):
                            status, body = request(url)
                            self.assertEqual(status, 200)
                            self.assertIn('data-owner-workload-result="true"', body)
                    self.assertEqual(request("/local/engine?purpose=ENGINE_INCREMENTAL_BUILD&rows=1000")[0], 400)
                    self.assertEqual(request("/local/engine?purpose=ENGINE_INCREMENTAL_BUILD", method="POST")[0], 405)
                    self.assertEqual(request("/local/engine", host="external.example")[0], 403)
                finally:
                    srv.shutdown()
                    thread.join(timeout=4)
                    self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
