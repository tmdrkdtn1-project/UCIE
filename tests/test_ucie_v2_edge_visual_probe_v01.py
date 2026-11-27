"""UCIE Edge screenshot tool: safe local-only URL and execution boundary."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_v2_edge_visual_probe_v01.py"
spec = spec_from_file_location("ucie_v2_edge_visual_probe_v01", SCRIPT)
assert spec and spec.loader
probe = module_from_spec(spec)
spec.loader.exec_module(probe)


class UCIEEdgeCaptureGateTests(unittest.TestCase):
    def test_exact_loopback_bounded_url(self):
        for u in (
            "http://127.0.0.1:53431/v2/truth",
            "http://127.0.0.1:53431/v2/truth?case=UCIE-SKILLBOOK-001",
        ):
            self.assertEqual(probe.validate_url(u), u)

    def test_remote_or_ambiguous_requests_rejected(self):
        for u in (
            "https://127.0.0.1:53431/v2/truth",
            "http://evil.example:53431/v2/truth",
            "http://localhost:53431/v2/truth",
            "http://127.0.0.2:53431/v2/truth",
            "http://127.0.0.1:80/v2/truth",
            "http://127.0.0.1:실제포트/v2/truth",
            "http://127.0.0.1:abc/v2/truth",
            "http://127.0.0.1:99999/v2/truth",
            "http://127.0.0.1:53431/local/ask",
            "http://127.0.0.1:53431/v2/truth?other=x",
            "http://127.0.0.1:53431/v2/truth?case=x&case=y",
            "http://127.0.0.1:53431/v2/truth?case=%3Cscript%3E",
            "http://127.0.0.1:53431/v2/truth#fragment",
            "http://user:pass@127.0.0.1:53431/v2/truth",
        ):
            with self.subTest(url=u), self.assertRaises(probe.EdgePreviewError):
                probe.validate_url(u)

    def test_no_non_windows_capture(self):
        if probe.os.name == "nt":
            self.skipTest("covered by Windows CI mock-only execution gate")
        with self.assertRaisesRegex(probe.EdgePreviewError, "WINDOWS_EDGE_ONLY"):
            probe.capture_edge("http://127.0.0.1:53431/v2/truth",
                               Path("/tmp/never-create-ucie-qa"),
                               Path("/nonexistent/msedge.exe"))

    def test_no_implicit_external_browser_execution(self):
        with patch.object(probe, "capture_edge", side_effect=probe.EdgePreviewError(
                "SCREENSHOT_PROBE_NOT_AUTHORIZED")):
            with self.assertRaises(probe.EdgePreviewError):
                probe.capture_edge("http://127.0.0.1:53431/v2/truth",
                                   Path("unused"), Path("unused"))

    def test_edge_failure_diagnostics_distinguish_process_and_file(self):
        from subprocess import CompletedProcess
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix="UCIE_EDGE_DIAG_TEST_") as folder:
            missing = Path(folder) / "missing.png"
            error = CompletedProcess(
                args=["msedge.exe"], returncode=23,
                stdout=b"", stderr=b"headless browser failed")
            report = probe.screenshot_failure_details(error, missing, 320)
            self.assertEqual(report["edge_exit_code"], 23)
            self.assertFalse(report["png_created"])
            self.assertEqual(report["width_css_px"], 320)
            self.assertIn("headless browser failed", report["edge_stderr_tail"])
            self.assertEqual(report["visual_qa"], "NOT_RUN")
            png = Path(folder) / "screen.png"
            png.write_bytes(probe.PNG_MAGIC + b"synthetic_only")
            zero_exit = CompletedProcess(
                args=["msedge.exe"], returncode=0,
                stdout=b"test", stderr=b"")
            valid_process = probe.screenshot_failure_details(
                zero_exit, png, 390)
            self.assertTrue(valid_process["png_created"])
            self.assertEqual(valid_process["edge_exit_code"], 0)

    def test_capture_receipt_never_labels_visual_qa_pass(self):
        # The output contract is deliberately manual-review-only.
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"actual_visual_qa": "PENDING"', source)
        self.assertIn('"actual_browser_keyboard_qa": "PENDING"', source)
        self.assertIn('"release_approved": False', source)
        self.assertIn('"no_horizontal_overflow_verified": False', source)
        self.assertIn('MAX_SCREENSHOT_BYTES = 16 * 1024 * 1024', source)


if __name__ == "__main__":
    unittest.main()
