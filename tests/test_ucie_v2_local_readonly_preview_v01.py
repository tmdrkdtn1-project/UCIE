"""Native UCIE offline HTML preview proves actual existing flow without V04 changes."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from ucie_miner import ucie_v2_local_readonly_preview_v01 as subject


class LocalReadOnlyPreviewTests(TestCase):
    def test_exact_mcp_capsule_and_review_flow_is_runnable(self):
        receipt = subject.build_fixed_demo("mcp-prompts")
        self.assertEqual(receipt["case_id"], "mcp-prompts")
        self.assertEqual(receipt["flow_kind"],
                         "HISTORIC_FIRST_PARTY_MCP_CAPSULE_RELATED_LIBRARY_REVIEW")
        self.assertIn("UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01",
                      receipt["preview_html"])
        self.assertFalse(receipt["independent_qa_verified"])

    def test_all_four_fixed_cases_render_three_steps(self):
        for case in subject.EXAMPLE_IDS:
            with self.subTest(case=case):
                html = subject.render_fixed_demo_page(case)
                self.assertIn('<html lang="ko">', html)
                self.assertIn("1. 어떤 도움이 필요하세요?", html)
                self.assertIn("2. ", html)
                self.assertIn("3. ", html)
                self.assertNotIn("<form", html)
                self.assertIn("배포 불가", html)

    def test_non_mcp_uses_fixed_examples_not_mcp_capsule(self):
        for case in ("python-env", "powershell-command", "git-repository"):
            with self.subTest(case=case):
                receipt = subject.build_fixed_demo(case)
                self.assertEqual(receipt["flow_kind"],
                                 "FIRST_PARTY_SYNTHETIC_EXAMPLE_ONLY")
                self.assertNotIn("UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01",
                                 receipt["preview_html"])

    def test_cli_prints_safe_static_html_only(self):
        result, error = StringIO(), StringIO()
        with redirect_stdout(result), redirect_stderr(error):
            rc = subject.main(["--case", "git-repository"])
        self.assertEqual(rc, 0)
        self.assertIn("<!doctype html>", result.getvalue())
        self.assertEqual(error.getvalue(), "")

    def test_unknown_case_denied_without_echo(self):
        private = "C:/private/secret/token"
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = subject.main(["--case", private])
        self.assertEqual(rc, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn(private, err.getvalue())

    def test_no_automatic_network_or_subprocess(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("network")):
            with patch("subprocess.run",
                       side_effect=AssertionError("subprocess")):
                r = subject.build_fixed_demo("mcp-prompts")
                self.assertEqual(r["network_requests"], 0)
                self.assertEqual(r["persistent_writes"], 0)

    def test_deterministic_and_no_approval(self):
        a, b = subject.build_fixed_demo("mcp-prompts"), subject.build_fixed_demo("mcp-prompts")
        self.assertEqual(a, b)
        self.assertFalse(a["actual_owner_edge_browser_tested"])
        self.assertFalse(a["customer_distribution_authorized"])
        self.assertFalse(a["actual_customer_sdk_tested_now"])

    def test_invalid_case_is_fail_closed(self):
        for invalid in ("external-project", "", "MCP-PROMPTS", None, 1):
            with self.subTest(value=str(type(invalid))):
                with self.assertRaises(subject.PreviewError):
                    subject.build_fixed_demo(invalid)

    def test_no_file_creation_in_product_preview(self):
        from pathlib import Path
        with patch.object(Path, "write_text",
                          side_effect=AssertionError("file write")):
            html = subject.render_fixed_demo_page("python-env")
            self.assertIn("UCIE V2 첫 사용자 미리보기", html)


class EvidenceComparisonPageTests(TestCase):
    def test_all_page_runs_all_four_existing_cases(self):
        html=subject.render_all_cases_page()
        for case in subject.EXAMPLE_IDS:
            self.assertIn('id="case-'+case+'"',html)
            self.assertIn('href="#case-'+case+'"',html)
        self.assertIn('data-review-comparison="review-only"',html)
        self.assertIn("가상도서관에서 검토 중인 개정 후보",html)

    def test_real_mcp_source_links_and_qa_status_exposed(self):
        html=subject.render_evidence_details("mcp-prompts")
        self.assertIn("modelcontextprotocol/python-sdk/pull/3696",html)
        self.assertIn("actions/runs/42585148478",html)
        self.assertIn("754254c08fe1c3eda18b69da3d336106fe8d72d6",html)
        self.assertIn("독립 QA: 미확인",html)
        self.assertEqual(html.count('class="review-card"'),2)

    def test_three_other_cases_keep_synthetic_truth(self):
        for case in ("python-env","powershell-command","git-repository"):
            with self.subTest(case=case):
                html=subject.render_evidence_details(case)
                self.assertIn('data-proof-kind="synthetic-only"',html)
                self.assertIn("정상 통제 예제",html)
                self.assertNotIn("과거 첫-party CI",html)

    def test_all_cli_outputs_full_page_without_new_user_input(self):
        out=StringIO()
        with redirect_stdout(out):
            result=subject.main(["--case","all"])
        self.assertEqual(result,0)
        self.assertEqual(out.getvalue().count('class="case-panel"'),4)
        self.assertNotIn("<form",out.getvalue())
        self.assertNotIn("<script",out.getvalue())

    def test_evidence_panel_forged_rights_rejected(self):
        original=subject.build_fixed_demo
        def fake(case):
            item=original(case)
            if case=="mcp-prompts":
                item["linked_review_rows"][0]["rights_approved"]=True
            return item
        with patch.object(subject,"build_fixed_demo",side_effect=fake):
            with self.assertRaises(subject.PreviewError):
                subject.render_evidence_details("mcp-prompts")

    def test_evidence_panel_wrong_case_rejected(self):
        with self.assertRaises(subject.PreviewError):
            subject.render_evidence_details("unapproved-source")

    def test_offline_html_no_external_active_resources(self):
        html=subject.render_all_cases_page()
        self.assertNotIn("<script",html)
        self.assertNotIn("<iframe",html)
        self.assertNotIn("<form",html)
        self.assertNotIn('src="http',html)
        self.assertIn('rel="noopener noreferrer"',html)

    def test_deterministic_whole_page(self):
        self.assertEqual(subject.render_all_cases_page(),
                         subject.render_all_cases_page())
