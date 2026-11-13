"""UCIE B2 integrated user job: error -> assessed synthetic engine -> library/evolution.

Real GET-only localhost HTTP, four domains × issue/control with safe negative
request tests. No user code, host commands, private files, network or promotion.
"""
from __future__ import annotations

import http.client
from http.server import HTTPServer
from pathlib import Path
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.parse import quote

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import local_b2_connected_workbench_v01 as b2


class B2FourPillarContractTests(unittest.TestCase):
    def test_all_four_domains_execute_issue_and_control_fixture(self):
        self.assertEqual(set(b2.EXPECTED), {
            "python-env", "powershell-command", "git-repository", "mcp-prompts"
        })
        for case_id in b2.EXPECTED:
            observed = []
            for scenario, expected in zip(b2.SCENARIOS, b2.EXPECTED[case_id]):
                with self.subTest(case_id=case_id, scenario=scenario):
                    report = b2.evaluate_case(case_id, scenario)
                    self.assertEqual(report["schema"], b2.SCHEMA)
                    self.assertEqual(report["status"], b2.STATUS)
                    self.assertEqual(report["result_code"], expected)
                    self.assertTrue(report["fixture_evaluated"])
                    self.assertEqual(report["fixture_origin"],
                                     "UCIE_AUTHORED_FIXED_SYNTHETIC")
                    self.assertEqual(report["public_library_query"],
                                     b2.PUBLIC_QUERIES[case_id])
                    self.assertEqual(report["evolution_query"],
                                     b2.PUBLIC_QUERIES[case_id])
                    self.assertFalse(report["independent_fix_validated"])
                    self.assertFalse(report["actual_user_environment_inspected"])
                    self.assertFalse(report["third_party_code_executed"])
                    self.assertFalse(report["human_review_approved"])
                    self.assertFalse(report["rule_or_skillbook_promoted"])
                    self.assertFalse(report["customer_distribution_authorized"])
                    self.assertEqual(report["network_requests"], 0)
                    self.assertEqual(report["operating_database_writes"], 0)
                    observed.append(report["result_code"])
            self.assertNotEqual(*observed)

    def test_synthetic_algorithms_do_not_inspect_host_or_execute_commands(self):
        with patch("os.system", side_effect=AssertionError("no shell")), \
             patch("subprocess.run", side_effect=AssertionError("no processes")):
            for case_id in b2.EXPECTED:
                b2.evaluate_case(case_id, "issue")
                b2.evaluate_case(case_id, "control")

    def test_unapproved_case_scenario_or_type_rejected(self):
        for case, scenario in (
            ("", "issue"), ("unapproved", "issue"), ("python-env", ""),
            ("python-env", "ISSUE"), ("python-env", "../../OTHER"),
            ("python-env", "<script>"), ("mcp-prompts", "issue "),
            (None, "issue"), (True, "issue"), ("git-repository", None),
        ):
            with self.subTest(case=case, scenario=scenario):
                with self.assertRaises(ValueError):
                    b2.evaluate_case(case, scenario)

    def test_mcp_contract_is_first_party_bounded_wire_check(self):
        from ucie_miner.mcp_prompt_regression_v01 import SOURCE_PR
        issue = b2.evaluate_case("mcp-prompts", "issue")
        control = b2.evaluate_case("mcp-prompts", "control")
        self.assertEqual(issue["result_code"], "CONTRACT_VIOLATION")
        self.assertEqual(control["result_code"], "CONTRACT_MATCH")
        self.assertEqual(issue["official_source_url"], SOURCE_PR)


class B2RealLocalLoopbackTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="UCIE_B2_FOUR_PILLAR_")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "UCIE"
        (root / ".git").mkdir(parents=True)
        self.server = HTTPServer(("127.0.0.1", 0), app.make_handler(root))
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.thread.join, 3)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path, *, method="GET", host=None):
        conn = http.client.HTTPConnection("127.0.0.1",
                                          self.server.server_port, timeout=5)
        try:
            conn.request(method, path, headers={
                "Host": host or "127.0.0.1:" + str(self.server.server_port),
            })
            res = conn.getresponse()
            return res.status, res.read().decode("utf-8", "replace"), dict(
                res.getheaders())
        finally:
            conn.close()

    def test_error_choice_links_to_same_case_in_real_engine(self):
        for case in b2.EXPECTED:
            status, page, _ = self.get("/local/error?case=" + case)
            self.assertEqual(status, 200)
            self.assertIn(
                "/local/engine?purpose=B2_CONNECTED_TRIAGE&amp;case=" + case,
                page,
            )

    def test_engine_eight_live_browser_scenarios_link_all_four_pillars(self):
        for case, expectations in b2.EXPECTED.items():
            q = quote(b2.PUBLIC_QUERIES[case], safe="")
            for scenario, outcome in zip(b2.SCENARIOS, expectations):
                with self.subTest(case=case, scenario=scenario):
                    route = ("/local/engine?purpose=B2_CONNECTED_TRIAGE&case="
                             + case + "&scenario=" + scenario)
                    status, page, headers = self.get(route)
                    self.assertEqual(status, 200)
                    self.assertIn('data-b2-connected="true"', page)
                    self.assertIn(outcome, page)
                    self.assertIn("/local/error?case=" + case, page)
                    self.assertIn("/local/library?q=" + q, page)
                    self.assertIn("/local/evolution?q=" + q, page)
                    self.assertIn("실제 사용자 PC 진단이 아닌", page)
                    self.assertIn("고객용 배포가 아닙니다", page)
                    self.assertEqual(headers["X-Frame-Options"], "DENY")
                    self.assertIn("default-src 'none'",
                                  headers["Content-Security-Policy"])
                    self.assertEqual(headers["Cache-Control"], "no-store")

    def test_default_is_issue_and_existing_python_shelf_not_broken(self):
        status, page, _ = self.get(
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=python-env")
        self.assertEqual(status, 200)
        self.assertIn("INTERPRETER_MISMATCH", page)
        status, page, _ = self.get(
            "/local/engine?purpose=PYTHON_SCANDIR_SAFE&case=shared_guarded")
        self.assertEqual(status, 200)
        self.assertIn("잠금 보호", page)

    def test_unknown_cases_duplicate_fields_oversized_values_fail_closed(self):
        for suffix in (
            "case=not-approved",
            "case=python-env&case=git-repository",
            "case=python-env&scenario=other",
            "case=python-env&scenario=issue&scenario=control",
            "case=python-env&scenario=%3Cscript%3E",
            "case=../OTHER&scenario=issue",
            "case=%00",
            "case=" + "x"*100,
            "case=mcp-prompts&admin=true",
        ):
            path = "/local/engine?purpose=B2_CONNECTED_TRIAGE&" + suffix
            with self.subTest(path=path):
                status, page, _ = self.get(path)
                self.assertEqual(status, 400)
                self.assertIn("FAIL_CLOSED", page)

    def test_real_navigation_arrives_at_library_and_evidence_views(self):
        # These existing federated views require actual UCIE public metadata;
        # an empty synthetic .git root is correctly fail-closed. Exercise a
        # second disposable localhost server against this UCIE repo ONLY.
        root = Path(__file__).resolve().parents[1]
        # runtime/ is intentionally gitignored. Fresh GitHub checkouts have
        # no UCIE evidence DB; their existing source-backed pages MUST deny
        # rendering instead of claiming an approved/empty evidence source.
        actual_captured_catalog = (root / "runtime" / "public_miner.sqlite3").is_file()
        live = HTTPServer(("127.0.0.1", 0), app.make_handler(root))
        worker = Thread(target=live.serve_forever, daemon=True)
        worker.start()
        try:
            for case in b2.EXPECTED:
                q = quote(b2.PUBLIC_QUERIES[case], safe="")
                for route in ("/local/library?q=" + q,
                              "/local/evolution?q=" + q):
                    with self.subTest(case=case, route=route):
                        client = http.client.HTTPConnection(
                            "127.0.0.1", live.server_port, timeout=6)
                        try:
                            client.request("GET", route, headers={
                                "Host": "127.0.0.1:" + str(live.server_port)})
                            response = client.getresponse()
                            status = response.status
                            page = response.read().decode("utf-8", "replace")
                            headers = dict(response.getheaders())
                        finally:
                            client.close()
                        if actual_captured_catalog:
                            self.assertEqual(status, 200,
                                             route + " " + page[:160])
                            self.assertIn("<!doctype html>", page.lower())
                            self.assertNotIn(
                                "customer_distribution_authorized=True", page)
                        else:
                            # Clean install has official UCIE-authored document
                            # pointers, but NO captured public PR ledger.
                            from ucie_miner.local_portable_official_reference_v01 import NOTE
                            self.assertEqual(status, 200,
                                             "official-reference route: " + route)
                            self.assertIn('data-offline-reference-only="true"', page)
                            self.assertIn(NOTE, page)
                            self.assertIn("NOT_ATTESTED_PER_REVISION", page)
                            self.assertNotIn(
                                "customer_distribution_authorized=True", page)
                        self.assertEqual(headers["Cache-Control"], "no-store")
        finally:
            live.shutdown()
            live.server_close()
            worker.join(timeout=3)

    def test_no_mutation_post_forbidden_host_and_unrelated_engine_scenario(self):
        for path in (
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=python-env",
            "/local/error?case=git-repository",
        ):
            status, page, _ = self.get(path, method="POST")
            self.assertEqual(status, 405)
            self.assertIn("READ_ONLY", page)
        status, page, _ = self.get(
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=python-env",
            host="other.example",
        )
        self.assertEqual(status, 403)
        self.assertIn("LOOPBACK_ONLY", page)
        status, page, _ = self.get(
            "/local/engine?purpose=MCP_PROMPTS_CONTRACT&scenario=issue")
        self.assertEqual(status, 400)
        self.assertIn("FAIL_CLOSED", page)


if __name__ == "__main__":
    unittest.main()
