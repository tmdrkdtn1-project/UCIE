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
