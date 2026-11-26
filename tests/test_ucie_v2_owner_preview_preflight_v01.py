"""Bounded owner preview: real B1-B5 contract and no false QA."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch
from ucie_miner import ucie_v2_owner_preview_preflight_v01 as s


class OwnerB1B5PreflightTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.html = s.build_owner_preflight()

    def test_full_b1_b5_static_contract_runs(self):
        self.assertEqual(self.report["case_count"],4)
        self.assertEqual(self.report["scenario_count"],3)
        self.assertEqual(self.report["b5_comparison_arms"],3)
        self.assertEqual(self.report["official_links_count"],3)

    def test_human_and_release_states_remain_open(self):
        for key in ("owner_edge_browser_viewed_new_head",
                    "actual_keyboard_responsive_qa_pass",
                    "actual_source_change_authenticated",
                    "source_qa_verified","rights_approved",
                    "customer_release_authorized"):
            self.assertIs(self.report[key],False)
        self.assertEqual(self.report["actual_novice_trials"],0)

    def test_read_only_check_does_not_save_or_open(self):
        with patch.object(s,"save_fixed_temp_preview",
                          side_effect=AssertionError("write")):
            with patch.object(s.os,"startfile",create=True,
                              side_effect=AssertionError("open")):
                output=StringIO()
                with redirect_stdout(output):
                    code=s.main(["--check"])
        self.assertEqual(code,0)
        self.assertIn("OFFLINE_B1_B5_STATIC_CONTRACT_VERIFIED_ONLY",
                      output.getvalue())

    def test_cli_accepts_only_two_explicit_modes(self):
        for opts in ([],["--check","--open"],["--output","C:/private"],
                     ["--url","https://outside.example"],["--open","--check"]):
            with self.subTest(opts=opts):
                err=StringIO()
                with redirect_stderr(err):
                    self.assertEqual(s.main(opts),2)
                self.assertNotIn("C:/private",err.getvalue())

    def test_no_implicit_write_on_build(self):
        with patch.object(Path,"open",side_effect=AssertionError("file open")):
            receipt,html=s.build_owner_preflight()
        self.assertFalse(receipt["file_written_by_preflight"])
        self.assertTrue(html.startswith("<!doctype html>"))

    def test_deterministic_output(self):
        self.assertEqual((self.report,self.html),s.build_owner_preflight())

    def test_actual_source_urls_bounded(self):
        from ucie_miner.ucie_v2_capsule_v01 import build_from_existing_ucie
        c=build_from_existing_ucie()
        links=(c.official_source_url,c.official_spec_url,c.first_party_sdk_ci_url)
        self.assertTrue(all('href="'+url+'"' in self.html for url in links))

    def test_script_and_form_injection_rejected(self):
        original=s.render_all_cases_page
        for injection in ('<script>alert(1)</script>','<form></form>',
                          '<iframe src="file:///private"></iframe>',
                          '<div onclick="evil()"></div>'):
            with self.subTest(injection=injection[:12]):
                with patch.object(s,"render_all_cases_page",
                                  return_value=original()+injection):
                    with self.assertRaises(s.PreflightError):
                        s.build_owner_preflight()

    def test_wrong_source_link_rejected(self):
        changed=self.html.replace('https://github.com/modelcontextprotocol',
                                  'https://example.com/other')
        with patch.object(s,"render_all_cases_page",return_value=changed):
            with self.assertRaises(s.PreflightError):
                s.build_owner_preflight()

    def test_duplicate_id_rejected(self):
        changed=self.html.replace('</body>',
             '<div id="case-mcp-prompts"></div></body>')
        with patch.object(s,"render_all_cases_page",return_value=changed):
            with self.assertRaises(s.PreflightError):
                s.build_owner_preflight()

    def test_static_proof_missing_rejected(self):
        changed=self.html.replace('id="b5-first-use-evaluation"',
                                  'id="missing-b5"')
        with patch.object(s,"render_all_cases_page",return_value=changed):
            with self.assertRaises(s.PreflightError):
                s.build_owner_preflight()

    def test_local_filename_fixed_and_byte_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(s.tempfile,"gettempdir",return_value=folder):
                path=s.save_fixed_temp_preview(self.html,self.report["page_sha256"])
                self.assertEqual(path.read_bytes(),self.html.encode("utf-8"))
                self.assertEqual(path,s.save_fixed_temp_preview(
                    self.html,self.report["page_sha256"]))

    def test_existing_tampered_temp_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(s.tempfile,"gettempdir",return_value=folder):
                target=Path(folder)/(s.PAGE_PREFIX+
                       self.report["page_sha256"][:16]+".html")
                target.write_bytes(b"not the expected UCIE preview")
                with self.assertRaises(s.PreflightError):
                    s.save_fixed_temp_preview(self.html,
                                              self.report["page_sha256"])
                self.assertEqual(target.read_bytes(),
                                 b"not the expected UCIE preview")

    def test_wrong_sha_never_saves(self):
        with self.assertRaises(s.PreflightError):
            s.save_fixed_temp_preview(self.html,"0"*64)

    def test_windows_open_requires_explicit_flag(self):
        out=StringIO()
        with patch.object(s.os,"name","nt"):
            with patch.object(s.os,"startfile",create=True) as opener:
                with patch.object(s,"save_fixed_temp_preview",
                                  return_value=Path("C:/temp/ucie_fixed.html")):
                    with redirect_stdout(out):
                        result=s.main(["--open"])
                self.assertEqual(result,0)
                opener.assert_called_once_with("C:/temp/ucie_fixed.html")
        self.assertIn("NOT verified",out.getvalue())

    def test_non_windows_cannot_open(self):
        out=StringIO()
        with patch.object(s.os,"name","posix"):
            with redirect_stderr(out):
                result=s.main(["--open"])
        self.assertEqual(result,2)
        self.assertIn("requires owner Windows",out.getvalue())

    def test_no_network_subprocess_or_extra_disk_on_check(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("network")):
            with patch("subprocess.run",
                       side_effect=AssertionError("subprocess")):
                report,_=s.build_owner_preflight()
        self.assertEqual(report["network_requests"],0)
        self.assertEqual(report["operating_database_writes"],0)
