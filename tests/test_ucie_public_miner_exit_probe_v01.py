"""UCIE public miner isolated Python process exit and receipt regression.

All real worker work uses injected synthetic collector/report and a temporary
UCIE directory. Never runs network miner or reads owner operating DB.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ucie_miner import public_miner_exit_probe_v01 as p


class PublicMinerSyntheticExitTests(unittest.TestCase):
    def test_first_party_real_child_receipt_and_process_exit(self):
        result = p.run_synthetic_exit_probe()
        self.assertEqual(result["status"], p.PASS, result)
        self.assertTrue(result["exit_observed"])
        self.assertEqual(result["child_exit_code"], 0)
        self.assertTrue(result["synthetic_receipt_written"])
        self.assertTrue(result["synthetic_worker_returned"])
        expected_main_import = (os.name != "nt" or
                                Path(__file__).resolve().parents[1] ==
                                Path("D:/UCIE").resolve())
        self.assertIs(result["entrypoint_imported_but_not_executed"],
                      expected_main_import)
        self.assertFalse(result["actual_public_collector_invoked"])
        self.assertFalse(result["real_task_scheduler_events_verified"])
        self.assertFalse(result["production_termination_root_cause_proven"])
        self.assertFalse(result["production_scheduler_verified"])
        self.assertFalse(result["task_scheduler_mutated"])
        self.assertFalse(result["other_project_access"])
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(result["public_network_requests"], 0)
        print("UCIE_SYNTHETIC_PROCESS_EXIT="
              + json.dumps({
                  "status": result["status"],
                  "child_exit_code": result["child_exit_code"],
                  "worker_returned": result["synthetic_worker_returned"],
                  "synthetic_receipt_written": result["synthetic_receipt_written"],
                  "production_cause_proven":
                      result["production_termination_root_cause_proven"],
                  "real_scheduler_verified":
                      result["real_task_scheduler_events_verified"],
              }, sort_keys=True))

    def test_default_preview_performs_no_subprocess(self):
        with patch.object(p.subprocess, "run",
                          side_effect=AssertionError("default invoked child")):
            output = StringIO()
            with redirect_stdout(output):
                code = p.main([])
        self.assertEqual(code, 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["status"], p.PREVIEW)
        self.assertFalse(data["synthetic_subprocess_started"])
        self.assertFalse(data["synthetic_receipt_written"])

    def test_manually_explicit_synthetic_cli_returns_proof(self):
        capture = StringIO()
        with redirect_stdout(capture):
            code = p.main(["--run-synthetic"])
        self.assertEqual(code, 0, capture.getvalue())
        data = json.loads(capture.getvalue())
        self.assertEqual(data["status"], p.PASS)
        self.assertEqual(data["child_exit_code"], 0)
        self.assertFalse(data["production_termination_root_cause_proven"])

    def test_process_timeout_fails_closed_without_operating_writes(self):
        def timeout(*_args, **_kwargs):
            raise subprocess.TimeoutExpired(cmd="ucie child", timeout=15)
        report = p.run_synthetic_exit_probe(runner=timeout)
        self.assertEqual(report["status"], p.NO_GO)
        self.assertFalse(report["exit_observed"])
        self.assertEqual(report["operating_database_writes"], 0)

    def test_child_fails_nonzero_and_never_claims_success(self):
        report = p.run_synthetic_exit_probe(
            runner=lambda *_a, **_kw: SimpleNamespace(
                returncode=2, stdout="", stderr="untrusted data"))
        self.assertEqual(report["status"], p.NO_GO)
        self.assertFalse(report["synthetic_receipt_written"])
        self.assertEqual(report["child_exit_code"], 2)

    def test_truncated_or_spoofed_child_marker_rejected(self):
        for out in ('{"schema":"UCIE_CHILD_SYNTHETIC_CYCLE_EXIT_MARKER_V01"}',
                    '{"status":"approved","export_allowed":true}',
                    "n" * 5000, ""):
            with self.subTest(out=out[:40]):
                result = p.run_synthetic_exit_probe(
                    runner=lambda *_a, **_kw: SimpleNamespace(
                        returncode=0, stdout=out, stderr=""))
                self.assertEqual(result["status"], p.NO_GO)
                self.assertNotIn("production_scheduler_verified", result)

    def test_bool_exit_code_does_not_pass_as_zero(self):
        r = p.run_synthetic_exit_probe(
            runner=lambda *_a, **_kw: SimpleNamespace(
                returncode=False, stdout="{}", stderr=""))
        self.assertEqual(r["status"], p.NO_GO)

    def test_subprocess_cannot_start_fails_closed(self):
        def unavailable(*_a, **_kw):
            raise OSError("test-only unavailable")
        r = p.run_synthetic_exit_probe(runner=unavailable)
        self.assertEqual(r["status"], p.NO_GO)
        self.assertFalse(r["exit_observed"])

    def test_child_invocation_isolated_and_never_runs_actual_miner(self):
        seen = {}
        def sandbox(*a, **kw):
            seen["cmd"] = a[0]
            seen["kwargs"] = kw
            raise OSError("synthetic stop before spawn")
        p.run_synthetic_exit_probe(runner=sandbox)
        self.assertEqual(seen["cmd"][1:4], ["-I", "-B", "-c"])
        self.assertEqual(seen["kwargs"]["timeout"], p.TIMEOUT_SECONDS)
        self.assertFalse(seen["kwargs"]["check"])
        self.assertNotIn("public_miner_cycle.py", seen["cmd"][:4])
        self.assertIn("enforce_schedule=False", seen["cmd"][4])

    def test_source_scope_is_only_current_ucie_checkout(self):
        root, entry = p._source_contract()
        self.assertEqual(root.name.casefold(), "ucie")
        self.assertEqual(entry.name, "public_miner_cycle.py")
        self.assertEqual(entry.parent.name, "scripts")


if __name__ == "__main__":
    unittest.main()
