"""UCIE W11 isolated first-party shutdown phase QA; no operating collector."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import unittest
from unittest.mock import patch

from ucie_miner import public_miner_shutdown_phase_w11 as w11


class PublicMinerShutdownPhaseW11Tests(unittest.TestCase):
    def test_default_preview_spawns_no_process(self):
        with patch.object(w11.subprocess, "run", side_effect=AssertionError(
                "preview must not spawn child")):
            buf = StringIO()
            with redirect_stdout(buf):
                code = w11.main([])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["status"], w11.PREVIEW)
        self.assertEqual(data["synthetic_subprocesses_started"], 0)

    def test_disposable_real_child_four_phase_modes(self):
        report = w11.run_all()
        self.assertEqual(report["status"], w11.PASS, report)
        self.assertEqual(report["cases"], 4)
        self.assertEqual(report["passed"], 4)
        self.assertEqual([x["mode"] for x in report["results"]],
                         list(w11.MODES))
        self.assertEqual(report["task_scheduler_mutations"], 0)
        self.assertEqual(report["owner_operating_db_writes"], 0)
        self.assertEqual(report["network_requests"], 0)
        self.assertFalse(report["production_termination_root_cause_proven"])
        self.assertFalse(report["real_task_scheduler_verified"])
        self.assertFalse(report["released"])

    def test_clean_receipt_fsync_return_stdout_flush_and_atexit(self):
        x = w11.run_one("clean")
        self.assertEqual(x["status"], "SYNTHETIC_CASE_OBSERVED", x)
        self.assertEqual(x["child_returncode"], 0)
        self.assertTrue(x["fsync_entered"])
        self.assertTrue(x["fsync_returned"])
        self.assertTrue(x["receipt_write_returned"])
        self.assertTrue(x["worker_returned"])
        self.assertTrue(x["temp_cleanup_returned"])
        self.assertTrue(x["stdout_flush_returned"])
        self.assertTrue(x["python_atexit_observed"])
        self.assertFalse(x["child_timeout_observed"])

    def test_fsync_error_does_not_prove_receipt_return(self):
        x = w11.run_one("fsync_error")
        self.assertEqual(x["status"], "SYNTHETIC_CASE_OBSERVED", x)
        self.assertNotEqual(x["child_returncode"], 0)
        self.assertTrue(x["fsync_entered"])
        self.assertFalse(x["fsync_returned"])
        self.assertFalse(x["receipt_write_returned"])
        self.assertFalse(x["worker_returned"])
        self.assertTrue(x["python_atexit_observed"])

    def test_synthetic_stdout_error_after_worker_is_detected(self):
        x = w11.run_one("stdout_error")
        self.assertEqual(x["status"], "SYNTHETIC_CASE_OBSERVED", x)
        self.assertTrue(x["receipt_write_returned"])
        self.assertTrue(x["worker_returned"])
        self.assertTrue(x["temp_cleanup_returned"])
        self.assertFalse(x["stdout_flush_returned"])
        self.assertTrue(x["python_atexit_observed"])
        self.assertNotEqual(x["child_returncode"], 0)

    def test_synthetic_post_stdout_hold_is_killed_by_bound(self):
        x = w11.run_one("post_stdout_hold")
        self.assertEqual(x["status"], "SYNTHETIC_CASE_OBSERVED", x)
        self.assertTrue(x["receipt_write_returned"])
        self.assertTrue(x["worker_returned"])
        self.assertTrue(x["temp_cleanup_returned"])
        self.assertTrue(x["stdout_flush_returned"])
        self.assertTrue(x["child_timeout_observed"])
        self.assertIsNone(x["child_returncode"])
        self.assertFalse(x["python_atexit_observed"])

    def test_cli_opt_in_runs_only_disposable_synthetic(self):
        buf = StringIO()
        with redirect_stdout(buf):
            code = w11.main(["--run-synthetic"])
        self.assertEqual(code, 0, buf.getvalue())
        report = json.loads(buf.getvalue())
        self.assertEqual(report["passed"], 4)
        self.assertFalse(report["real_public_miner_executed"])
        self.assertEqual(report["task_scheduler_mutations"], 0)

    def test_rejects_unknown_and_boolean_mode(self):
        for mode in ("owner", "", "D:/UCIE", None, True, 0):
            with self.subTest(mode=mode):
                with self.assertRaises(w11.ShutdownPhaseError):
                    w11.run_one(mode)

    def test_untrusted_child_marker_not_accepted(self):
        for mode in w11.MODES:
            with self.subTest(mode=mode):
                p = SimpleNamespace(
                    returncode=0, stdout='{"approved":true}\n',
                    stderr="UCIE_W11_PHASE:PYTHON_ATEXIT\n")
                x = w11.run_one(mode, runner=lambda *a, **k: p)
                self.assertEqual(x["status"],
                                 "SYNTHETIC_CASE_NOT_PROVEN_NO_GO")

    def test_forged_phase_marker_rejected(self):
        self.assertEqual(w11._phase_names(
            "UCIE_W11_PHASE:PRODUCTION_APPROVED\n"), ())
        self.assertEqual(w11._phase_names(
            b"UCIE_W11_PHASE:RECEIPT_ENTER\n"),
            ("RECEIPT_ENTER",))
        self.assertEqual(w11._phase_names("A" * 15000), ())

    def test_timeout_without_evidence_is_not_success(self):
        def timeout(*a, **k):
            raise subprocess.TimeoutExpired(cmd="disposable-only", timeout=1,
                                            output=b"", stderr=b"")
        x = w11.run_one("post_stdout_hold", runner=timeout)
        self.assertEqual(x["status"], "SYNTHETIC_CASE_NOT_PROVEN_NO_GO")
        self.assertFalse(x["worker_returned"])

    def test_zero_exit_boolean_is_not_valid_code(self):
        x = w11.run_one("clean", runner=lambda *a, **k: SimpleNamespace(
            returncode=False, stdout='{"synthetic_receipt_only":true}\n',
            stderr=("UCIE_W11_PHASE:RECEIPT_ENTER\n"
                    "UCIE_W11_PHASE:FSYNC_ENTER\n"
                    "UCIE_W11_PHASE:FSYNC_RETURN\n"
                    "UCIE_W11_PHASE:RECEIPT_RETURN\n"
                    "UCIE_W11_PHASE:WORKER_RETURN\n"
                    "UCIE_W11_PHASE:TEMP_CLEANED\n"
                    "UCIE_W11_PHASE:STDOUT_FLUSH_RETURN\n"
                    "UCIE_W11_PHASE:MAIN_END\n"
                    "UCIE_W11_PHASE:PYTHON_ATEXIT\n")))
        self.assertEqual(x["status"], "SYNTHETIC_CASE_NOT_PROVEN_NO_GO")

    def test_valid_phase_names_but_forged_order_rejected(self):
        valid = (
            "RECEIPT_ENTER", "FSYNC_ENTER", "FSYNC_RETURN",
            "RECEIPT_RETURN", "WORKER_RETURN", "TEMP_CLEANED",
            "STDOUT_FLUSH_RETURN", "MAIN_END", "PYTHON_ATEXIT",
        )
        self.assertTrue(w11._ordered(valid, valid))
        self.assertFalse(w11._ordered(
            ("RECEIPT_ENTER", "WORKER_RETURN", "FSYNC_ENTER",
             "FSYNC_RETURN", "RECEIPT_RETURN", "TEMP_CLEANED",
             "STDOUT_FLUSH_RETURN", "MAIN_END", "PYTHON_ATEXIT"), valid))
        self.assertFalse(w11._expected(
            "clean", 0, tuple(reversed(valid)),
            '{"synthetic_receipt_only":true}', False))

    def test_invocation_isolated_no_running_actual_collector(self):
        args = {}
        def spy(*a, **kw):
            args["cmd"], args["kw"] = a[0], kw
            raise OSError("synthetic-only process prevented")
        x = w11.run_one("clean", runner=spy)
        self.assertEqual(x["status"], "SYNTHETIC_CASE_NOT_PROVEN_NO_GO")
        self.assertEqual(args["cmd"][1:4], ["-I", "-B", "-c"])
        self.assertEqual(args["cmd"][-1], "clean")
        self.assertFalse(args["kw"]["check"])
        self.assertIn("enforce_schedule=False", args["cmd"][4])
        self.assertEqual(args["kw"]["timeout"], w11.CHILD_TIMEOUT_SECONDS)
        self.assertEqual(x["owner_operating_db_writes"], 0)

    def test_bounded_child_timeout(self):
        self.assertLessEqual(w11.HOLD_TIMEOUT_SECONDS, 2)
        self.assertLessEqual(w11.CHILD_TIMEOUT_SECONDS, 5)
        self.assertEqual(len(w11.MODES), 4)

    def test_source_scoped_to_ucie_worker_only(self):
        root = w11._source_contract()
        self.assertEqual(root.name.casefold(), "ucie")
        self.assertTrue((root / "src/ucie_miner/worker.py").is_file())

    def test_all_synthetic_reports_never_approve_production(self):
        for name in w11.MODES:
            x = w11.run_one(name)
            self.assertFalse(x["production_termination_root_cause_proven"])
            self.assertFalse(x["real_task_scheduler_verified"])
            self.assertEqual(x["task_scheduler_mutations"], 0)
            self.assertEqual(x["owner_operating_db_writes"], 0)
            self.assertEqual(x["network_requests"], 0)

    def test_owner_script_is_preview_by_default_and_fixed_root(self):
        code = (Path(__file__).resolve().parents[1] / "scripts" /
                "ucie_public_miner_shutdown_phase_w11.ps1").read_text(
                    encoding="utf-8")
        self.assertIn("param([switch]$RunSynthetic)", code)
        self.assertIn("UCIE_OWNER_ROOT_REQUIRED", code)
        self.assertIn("if ($RunSynthetic.IsPresent)", code)
        self.assertIn("--run-synthetic", code)
        self.assertIn(".venv\\Scripts\\python.exe", code)
        for mutator in ("Start-ScheduledTask", "Stop-ScheduledTask",
                        "Register-ScheduledTask", "Unregister-ScheduledTask",
                        "Set-ScheduledTask", "Start-Process",
                        "Stop-Process", "Invoke-RestMethod"):
            self.assertNotIn(mutator + " ", code)

    def test_isolated_child_never_loads_owner_runtime_or_network_collector(self):
        self.assertIn("with tempfile.TemporaryDirectory(", w11._CHILD)
        self.assertIn("collect=fake_collect", w11._CHILD)
        self.assertIn("enforce_schedule=False", w11._CHILD)
        self.assertIn("worker.os.fsync = observed_fsync", w11._CHILD)
        self.assertIn("worker._write_receipt = observed_receipt", w11._CHILD)
        self.assertNotIn("mine_once(", w11._CHILD)
        self.assertNotIn("public_miner_cycle.py", w11._CHILD)
        self.assertNotIn("Get-ScheduledTask", w11._CHILD)


if __name__ == "__main__":
    unittest.main()
