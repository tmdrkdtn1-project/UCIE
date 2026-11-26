"""G0/G1/G2: real UCIE first-use existing-route join and negative controls.

These tests run on a disposable checkout. No owner runtime, no customer input,
network/public-source collection, new POST, operating DB or release path.
A separately started ephemeral localhost server checks existing GET handlers;
it never writes to or communicates with the owner's resident V04 server.
"""
from __future__ import annotations

from copy import deepcopy
from html.parser import HTMLParser
import http.client
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest import mock

from ucie_miner import ucie_v2_first_use_linked_v01 as g1
from ucie_miner import ucie_v2_beginner_preview_v01 as b2
from ucie_miner.ucie_v2_capsule_v01 import read_only_default
from ucie_miner.local_b2_connected_workbench_v01 import evaluate_case
from ucie_miner import local_v1_app_v01 as local_app


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href"))


class RealFirstUseJoinTests(unittest.TestCase):
    def model(self):
        return g1.build_existing_action_join(read_only_default())

    def test_reuses_exact_three_old_owner_actions(self):
        x = self.model()
        self.assertEqual(x["schema"], g1.SCHEMA)
        self.assertEqual(x["status"], g1.STATUS)
        self.assertEqual(
            {k: row["href"] for k, row in x["flows"].items()},
            g1.FLOW_HREFS,
        )
        self.assertEqual(set(x["cases"]), set(g1.EXPECTED_CODES))
        self.assertFalse(x["owner_v04_route_added"])
        self.assertFalse(x["real_owner_browser_tested"])

    def test_actual_b2_issues_and_controls_for_every_known_case(self):
        x = self.model()
        for case_id, row in x["cases"].items():
            with self.subTest(case_id=case_id):
                issue = evaluate_case(case_id, "issue")
                control = evaluate_case(case_id, "control")
                self.assertEqual(row["issue"]["status"], issue["result_code"])
                self.assertEqual(row["control"]["status"], control["result_code"])
                self.assertEqual(row["issue"]["observation"],
                                 issue["observed_synthetic_result"])
                self.assertEqual(row["control"]["observation"],
                                 control["observed_synthetic_result"])
                self.assertIn("scenario=issue", row["issue"]["href"])
                self.assertIn("scenario=control", row["control"]["href"])
                self.assertEqual(row["solve_href"],
                                 "/local/solve?case=" + case_id)

    def test_mcp_capsule_id_guide_revision_and_b4_are_same_case(self):
        x = self.model()
        self.assertEqual(x["capsule_id"], g1.MCP_CAPSULE)
        self.assertEqual(x["cases"]["mcp-prompts"]["capsule_id"], g1.MCP_CAPSULE)
        self.assertEqual(x["skillbook_id"],
                         "UCIE-SKILLBOOK-MCP-PROMPTS-003")
        self.assertEqual(x["mcp_guide_href"], "/local/guide/mcp-prompts")
        self.assertEqual(x["mcp_evolution_href"], "/local/evolution?q=MCP")
        self.assertTrue(x["b4_hypothesis_id"].startswith("UCIE-B4-HYP-"))
        self.assertTrue(x["revalidation_still_pending"])
        self.assertFalse(x["actual_new_upstream_revision_authenticated"])

    def test_other_three_cases_never_inherit_mcp_capsule(self):
        x = self.model()
        for case_id, case in x["cases"].items():
            if case_id != "mcp-prompts":
                self.assertIsNone(case["capsule_id"])
                self.assertTrue(case["no_other_capsule_claimed"])

    def test_no_approval_or_customer_environment_claim(self):
        x = self.model()
        self.assertEqual(x["rights"], "NOT_APPROVED")
        self.assertEqual(x["independent_qa"], "NOT_VERIFIED")
        self.assertEqual(x["customer_release"], "NOT_AUTHORIZED")
        for key in ("owner_v04_route_added", "real_owner_browser_tested",
                    "customer_code_read", "new_post_created"):
            self.assertIs(x[key], False)
        self.assertEqual(x["network_requests"], 0)
        self.assertEqual(x["operating_database_writes"], 0)

    def test_html_embeds_actual_fixed_action_urls_and_results(self):
        html = b2.render_preview()
        self.assertIn('id="existing-actions" hidden', html)
        for href in (
            "/local/ask",
            "/local/solve?case=mcp-prompts",
            "/local/guide/mcp-prompts",
            "/local/engine?purpose=SKILL_TEST_AUTOMATION",
            "/local/library?q=Git",
        ):
            self.assertIn('href="' + href + '"', html)
        self.assertIn("B2_CONNECTED_TRIAGE&amp;case=mcp-prompts&amp;scenario=issue", html)
        self.assertIn("B2_CONNECTED_TRIAGE&amp;case=mcp-prompts&amp;scenario=control", html)
        self.assertIn("UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01", html)
        self.assertIn("CONTRACT_VIOLATION", html)
        self.assertIn("CONTRACT_MATCH", html)

    def test_preview_has_actual_problem_demo_library_revision_links(self):
        html = b2.render_preview()
        self.assertIn('href="/local/solve?case=mcp-prompts"', html)
        self.assertIn('href="/local/guide/mcp-prompts"', html)
        self.assertIn('href="/local/evolution?q=MCP"', html)
        self.assertIn('href="/local/library?q=MCP"', html)
        self.assertIn("최신 공식 원본 재확인은 아직 필요", html)
        self.assertIn("다른 환경까지 자동 적용 가능하다는 뜻이 아닙니다", html)

    def test_unknown_case_only_shows_supported_path(self):
        html = b2.render_preview()
        self.assertIn('data-route-case="unmatched" hidden', html)
        self.assertIn("지원하는 대표 상황 외에는 원인이나 수정 성공을 추측하지 않습니다", html)

    def test_only_exact_allowlisted_old_get_destinations(self):
        parser = _Anchors()
        parser.feed(g1.render_existing_action_sections(read_only_default()))
        self.assertGreaterEqual(len(parser.hrefs), 24)
        for href in parser.hrefs:
            with self.subTest(href=href):
                self.assertEqual(g1._known_route(href), href)
                self.assertTrue(href.startswith("/local/"))
                self.assertNotIn("#", href)
                self.assertNotIn("javascript:", href)

    def test_external_javascript_file_and_unapproved_query_rejected(self):
        for url in (
            "javascript:alert(1)", "https://unapproved.example/private",
            "file:///local/engine", "//malicious.invalid/ucie",
            "/local/ask?question=secret", "/local/engine?purpose=UNKNOWN",
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=mcp-prompts&scenario=unknown",
            "/local/library?q=PRIVATE_PROJECT", "/local/ask%0aPOST",
        ):
            with self.subTest(url=url):
                with self.assertRaises(g1.FirstUseJoinError):
                    g1._known_route(url)

    def test_fake_customer_approval_rejected(self):
        for key, false_claim in (
            ("rights", "APPROVED"),
            ("independent_qa", "INDEPENDENTLY_VERIFIED"),
            ("customer_release", "AUTHORIZED"),
            ("decision", "PASS"),
            ("applicability", "EXACT_TESTED"),
            ("customer_pc_tested", True),
            ("sdk_reexecuted_now", True),
            ("auto_promoted", True),
            ("actual_code_repaired", True),
        ):
            with self.subTest(key=key):
                data = deepcopy(read_only_default())
                data[key] = false_claim
                with self.assertRaises(g1.FirstUseJoinError):
                    g1.build_existing_action_join(data)

    def test_fake_capsule_and_skillbook_id_rejected(self):
        for key in ("case_id", "capsule_id", "skillbook_id"):
            x = deepcopy(read_only_default())
            x[key] = "FORGED"
            with self.subTest(key=key):
                with self.assertRaises(g1.FirstUseJoinError):
                    g1.build_existing_action_join(x)

    def test_stale_revision_claim_rejected(self):
        x = deepcopy(read_only_default())
        x["revision_status"] = "CURRENT_REVALIDATION_PASS"
        with self.assertRaises(g1.FirstUseJoinError):
            g1.build_existing_action_join(x)

    def test_first_use_route_drift_is_not_silently_adopted(self):
        from ucie_miner import local_first_use_plain_v01 as first
        rows = list(first.START_TASKS)
        broken = list(rows[0])
        broken[4] = "/local/new-unapproved-route"
        rows[0] = tuple(broken)
        with mock.patch.object(first, "START_TASKS", tuple(rows)):
            with self.assertRaises(g1.FirstUseJoinError):
                self.model()

    def test_no_synthetic_trial_may_be_called_real_fix(self):
        from ucie_miner import local_b2_connected_workbench_v01 as workbench
        actual = workbench.evaluate_case
        def forged(case, scenario):
            result = actual(case, scenario)
            if case == "mcp-prompts" and scenario == "issue":
                result["independent_fix_validated"] = True
            return result
        proof = read_only_default()  # B1 already verified; now isolate G1's gate.
        with mock.patch.object(workbench, "evaluate_case", side_effect=forged):
            with self.assertRaises(g1.FirstUseJoinError):
                g1.build_existing_action_join(proof)

    def test_no_fake_machine_execution_or_approval(self):
        from ucie_miner import local_b2_connected_workbench_v01 as workbench
        actual = workbench.evaluate_case
        proof = read_only_default()  # The forged candidate belongs to G1, not B1.
        for name, value in (("third_party_code_executed", True),
                            ("human_review_approved", True),
                            ("operating_database_writes", 1),
                            ("network_requests", 1)):
            def forged(case, scenario):
                report = actual(case, scenario)
                if case == "mcp-prompts" and scenario == "issue":
                    report[name] = value
                return report
            with self.subTest(name=name):
                with mock.patch.object(workbench, "evaluate_case", side_effect=forged):
                    with self.assertRaises(g1.FirstUseJoinError):
                        g1.build_existing_action_join(proof)

    def test_unapproved_guide_source_rejected(self):
        from ucie_miner import mcp_prompts_guide_v01 as guide
        original = guide.build_readonly_guide
        proof = read_only_default()  # Keep B1 receipt constant to test G1 guide join.
        def forge():
            result = original()
            result["source_evidence"]["pr_url"] = "https://unapproved.invalid"
            return result
        with mock.patch.object(guide, "build_readonly_guide", side_effect=forge):
            with self.assertRaises(g1.FirstUseJoinError):
                g1.build_existing_action_join(proof)

    def test_b3_unauthenticated_or_unrelated_retest_cannot_be_claimed_pass(self):
        from ucie_miner import ucie_v2_revision_impact_v01 as b3
        original = b3.assess_revision_impacts
        def forge(signals):
            row = original(signals)
            row["proposed_test_files"] = ["unrelated.py"]
            return row
        with mock.patch.object(b3, "assess_revision_impacts", side_effect=forge):
            with self.assertRaises(g1.FirstUseJoinError):
                self.model()

    def test_b4_fabricated_export_authorization_rejected(self):
        from ucie_miner import ucie_v2_generalization_transfer_v01 as b4
        original = b4.build_hypothesis
        def forge():
            h = original()
            h["export_allowed"] = True
            return h
        with mock.patch.object(b4, "build_hypothesis", side_effect=forge):
            with self.assertRaises(g1.FirstUseJoinError):
                self.model()

    def test_native_navigation_works_without_inline_javascript(self):
        html = b2.render_preview()
        self.assertIn('id="direct-start-actions"', html)
        self.assertIn('aria-label="기존 UCIE 기능 바로가기"', html)
        self.assertGreater(
            html.index('id="direct-start-actions"'),
            html.index('id="stage3"'),
        )
        self.assertIn('href="/local/ask"', html)
        self.assertIn('href="/local/engine?purpose=SKILL_TEST_AUTOMATION"', html)
        self.assertIn('href="/local/library?q=Git"', html)
        self.assertIn(
            'document.querySelectorAll("#existing-actions a[href],#direct-start-actions a[href],[data-flow][href]")',
            html,
        )

    def test_first_user_primary_action_is_visible_with_technical_details_optional(self):
        html = b2.render_preview()
        self.assertIn('<details id="direct-start-actions"', html)
        self.assertIn('data-synthetic-details="mcp-prompts"', html)
        self.assertIn('안전한 확인 순서 보기', html)
        self.assertIn('예제·공개 근거 자세히 보기', html)
        self.assertIn('||flow==="solve"', html)
        self.assertIn('UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01', html)

    def test_three_first_options_are_native_get_links_under_script_csp(self):
        html = b2.render_preview()
        self.assertIn('class="start-choice" data-flow="solve" href="/local/ask"', html)
        self.assertIn('class="start-choice" data-flow="try" href="/local/engine?purpose=SKILL_TEST_AUTOMATION"', html)
        self.assertIn('class="start-choice" data-flow="learn" href="/local/library?q=Git"', html)
        self.assertIn('event.preventDefault(); // JS wizard when permitted', html)
        self.assertIn('role="status" aria-live="polite"', html)
        self.assertNotIn('data-flow="solve">', html)
        
    def test_static_file_links_are_disabled_until_owner_local_host(self):
        html = b2.render_preview()
        self.assertIn('window.location.protocol!=="http:"', html)
        self.assertIn('window.location.hostname!=="127.0.0.1"', html)
        self.assertIn('x.removeAttribute("href")', html)
        self.assertIn('x.setAttribute("aria-disabled","true")', html)
        self.assertIn("이 파일이 운영 서비스에 설치된 것은 아닙니다", html)

    def test_no_new_post_or_upload_or_untrusted_network(self):
        html = b2.render_preview()
        for forbidden in ('<form', 'method="post"', "fetch(", "XMLHttpRequest",
                          "WebSocket", "innerHTML", "localStorage",
                          "sessionStorage", 'type="file"', "sendBeacon"):
            self.assertNotIn(forbidden, html)

    def test_keyboard_korean_and_mobile_basics_preserved(self):
        html = b2.render_preview()
        self.assertIn('lang="ko"', html)
        self.assertIn("focus-visible", html)
        self.assertIn('max-width:690px', html)
        self.assertIn('name="viewport"', html)
        self.assertIn('tabindex="-1"', html)
        self.assertIn("prefers-reduced-motion", html)
        self.assertIn('data-route-flow="try" hidden', html)
        self.assertIn('data-route-flow="learn" hidden', html)


class RealExistingOwnerRoutesDisposableHTTPTests(unittest.TestCase):
    """Only ephemeral first-party loopback, never resident owner V04."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory(prefix="UCIE_V2_G2_LOOPBACK_")
        root = Path(cls.tmp.name) / "UCIE"
        (root / ".git").mkdir(parents=True)
        cls.server = HTTPServer(("127.0.0.1", 0), local_app.make_handler(root))
        cls.worker = Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=4)
        cls.tmp.cleanup()

    def call(self, path: str, *, method="GET", host=None, origin=None, body=None):
        client = http.client.HTTPConnection("127.0.0.1",
                                            self.server.server_port, timeout=10)
        valid_host = "127.0.0.1:" + str(self.server.server_port)
        headers = {"Host": valid_host if host is None else host}
        if origin is not None:
            headers["Origin"] = origin
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            client.request(method, path, body=body, headers=headers)
            response = client.getresponse()
            return response.status, response.read().decode("utf-8", "replace"), {
                k: v for k, v in response.getheaders()
            }
        finally:
            client.close()

    def test_real_old_owner_destinations_serve_get(self):
        routes = (
            "/local/ask", "/local/solve?case=mcp-prompts",
            "/local/engine?purpose=SKILL_TEST_AUTOMATION",
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=mcp-prompts&scenario=issue",
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=mcp-prompts&scenario=control",
            "/local/engine?purpose=MCP_PROMPTS_CONTRACT",
            "/local/guide/mcp-prompts", "/local/library?q=Git",
            "/local/library?q=MCP", "/local/evolution?q=MCP",
        )
        for route in routes:
            with self.subTest(route=route):
                status, body, headers = self.call(route)
                self.assertEqual(status, 200, (route, body[:80]))
                self.assertTrue(body)
                self.assertEqual(headers.get("Cache-Control"), "no-store")

    def test_existing_mcp_demo_is_synthetic_not_customer_fix(self):
        status, body, _ = self.call(
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=mcp-prompts&scenario=issue")
        self.assertEqual(status, 200)
        self.assertIn("CONTRACT_VIOLATION", body)
        self.assertIn("UCIE 작성 합성 사례", body)

    def test_existing_guide_is_draft_and_not_export_approved(self):
        status, html, _ = self.call("/local/guide/mcp-prompts")
        self.assertEqual(status, 200)
        self.assertIn("미승인", html)
        self.assertIn("재배포", html)
        self.assertIn("MCP", html)

    def test_wrong_host_rejected_on_existing_get(self):
        status, _, _ = self.call("/local/guide/mcp-prompts", host="evil.invalid")
        self.assertEqual(status, 403)

    def test_new_post_to_engine_is_not_allowed(self):
        status, _, _ = self.call("/local/engine", method="POST",
                                 origin="http://127.0.0.1:" +
                                        str(self.server.server_port),
                                 body=b"question=UCIE%20synthetic%20only")
        self.assertEqual(status, 405)

    def test_cross_origin_post_to_old_ask_is_rejected(self):
        status, _, _ = self.call("/local/ask", method="POST",
                                 origin="https://untrusted.invalid",
                                 body=b"question=UCIE%20synthetic%20only")
        self.assertEqual(status, 403)

    def test_query_question_not_echoed_or_accepted(self):
        status, _, _ = self.call("/local/ask?question=never-in-url")
        self.assertEqual(status, 400)

    def test_unreviewed_mcp_scenario_rejected(self):
        status, _, _ = self.call(
            "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=mcp-prompts&scenario=unreviewed")
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
