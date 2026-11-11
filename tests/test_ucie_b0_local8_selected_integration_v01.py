"""UCIE-only offline integration for selected, source-anchored local changes.

No live schedule, network, operating DB, private project or external source.
All run_cycle receipts live in isolated first-party TemporaryDirectory.
"""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucie_miner.worker import run_cycle


def report(root: Path) -> Path:
    folder = root / "runtime" / "reports"
    folder.mkdir(exist_ok=True)
    target = folder / "synthetic.md"
    target.write_text("# UCIE first-party synthetic only\n", encoding="utf-8")
    return target


def synthetic_base() -> dict:
    return {
        "status": "COLLECTED_UNVERIFIED",
        "new_candidates": 0,
        "sources_checked": 1,
        "verification_pass": 0,
        "production_approved": False,
    }


class TestUCIEB0Local8SelectedIntegration(unittest.TestCase):
    def setUp(self):
        ctx = tempfile.TemporaryDirectory(prefix="ucie-b0-only-")
        self.addCleanup(ctx.cleanup)
        self.root = Path(ctx.name) / "UCIE"
        self.root.mkdir()

    def test_stage17_quality_kept_in_bounded_worker_receipt(self):
        def collect(root):
            value = synthetic_base()
            value["stage10"] = {
                "status": "STAGE10_UNVERIFIED_STAGED_NO_GO",
                "stage17_quality_status": "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO",
                "stage17_quality_candidate_count": 7,
                "stage17_quality_candidate_delta": -2,
            }
            return value
        value = run_cycle(self.root, collect=collect, write_report=report)
        self.assertEqual(value["status"], "COLLECTED_UNVERIFIED")
        self.assertEqual(value["stage17_quality_candidate_count"], 7)
        self.assertEqual(value["stage17_quality_candidate_delta"], -2)
        self.assertEqual(value["stage17_quality_status"],
                         "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO")
        self.assertEqual(value["verification_pass"], 0)
        self.assertFalse(value["production_approved"])
        saved = json.loads((self.root / "runtime" / "last_run.json").read_text("utf-8"))
        self.assertEqual(saved, value)

    def test_stage17_forged_unbounded_quality_rejected(self):
        for count, status in (
            (1001, "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO"),
            (3, "STAGE17_QUALITY_DISABLED"),
        ):
            with self.subTest(count=count):
                def collect(root):
                    value = synthetic_base()
                    value["stage10"] = {
                        "status": "STAGE10_UNVERIFIED_STAGED_NO_GO",
                        "stage17_quality_status": status,
                        "stage17_quality_candidate_count": count,
                        "stage17_quality_candidate_delta": 0,
                    }
                    return value
                value = run_cycle(self.root, collect=collect, write_report=report)
                self.assertEqual(value["status"], "COLLECTION_FAILED")
                self.assertFalse(value["production_approved"])
                self.assertNotIn("stage17_quality_candidate_count", value)

    def test_worker_failure_phase_and_public_http_code_sanitized(self):
        def collect(root):
            error = RuntimeError("PRIVATE_TOKEN_REMOTE_TEXT_NOT_FOR_RECEIPT")
            error.ucie_public_source = "python/cpython"
            error.ucie_public_operation = "FETCH_PR_LIST"
            upstream = HTTPError(
                "https://example.invalid/private", 429,
                "PRIVATE_TOKEN_REMOTE_TEXT_NOT_FOR_RECEIPT", {}, None)
            try:
                raise error from upstream
            finally:
                upstream.close()
        output = run_cycle(self.root, collect=collect, write_report=report)
        self.assertEqual(output["status"], "COLLECTION_FAILED")
        self.assertEqual(output["error_phase"], "BASE_COLLECTION")
        self.assertEqual(output["error_public_source"], "python/cpython")
        self.assertEqual(output["error_public_operation"], "FETCH_PR_LIST")
        self.assertEqual(output["error_http_status"], 429)
        serialized = (self.root / "runtime" / "last_run.json").read_text("utf-8")
        self.assertNotIn("PRIVATE_TOKEN", serialized)
        self.assertNotIn("example.invalid", serialized)

    def test_unknown_source_operation_and_http_status_do_not_leak(self):
        def collect(root):
            error = RuntimeError("UNTRUSTED_REMOTE_SECRET_42")
            error.ucie_public_source = "unapproved/private"
            error.ucie_public_operation = "UNTRUSTED_SECRET_PHASE_42"
            raise error
        output = run_cycle(self.root, collect=collect, write_report=report)
        self.assertEqual(output["status"], "COLLECTION_FAILED")
        self.assertEqual(output["error_phase"], "BASE_COLLECTION")
        self.assertNotIn("error_public_source", output)
        self.assertNotIn("error_public_operation", output)
        serialized = (self.root / "runtime" / "last_run.json").read_text("utf-8")
        self.assertNotIn("SECRET_42", serialized)

    def test_report_failure_has_local_only_phase(self):
        def broken_report(root):
            raise OSError("UNTRUSTED_PRIVATE_REPORT_LOCATION")
        output = run_cycle(self.root, collect=lambda root: synthetic_base(),
                           write_report=broken_report)
        self.assertEqual(output["status"], "COLLECTION_FAILED")
        self.assertEqual(output["error_phase"], "REPORT_WRITER")
        self.assertNotIn("UNTRUSTED_PRIVATE", json.dumps(output))

    def test_hourly_entrypoint_passes_stage17_from_opt_in_stage(self):
        # Compile only the trusted nested CLI function AST; this bypasses
        # Windows D:/UCIE host guards without invoking the CLI module at
        # import time in Linux/Windows CI. It runs no external collectors.
        script = ROOT / "scripts" / "public_miner_cycle.py"
        tree = ast.parse(script.read_text(encoding="utf-8-sig"))
        main = next(
            x for x in tree.body
            if isinstance(x, ast.FunctionDef) and x.name == "main")
        env = {
            "ROOT": self.root, "json": json,
            "mine_once": lambda root, **kwargs: synthetic_base(),
            "run_cycle": lambda root, *, collect, enforce_schedule:
                collect(root),
        }
        compiled = ast.fix_missing_locations(
            ast.Module(body=[main], type_ignores=[]))
        exec(compile(compiled, str(script), "exec"), env)
        from ucie_miner import public_hourly_staging
        staged = {
            "status": "STAGE10_UNVERIFIED_STAGED_NO_GO",
            "stage17_quality_status": "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO",
            "stage17_quality_candidate_count": 3,
            "stage17_quality_candidate_delta": -1,
        }
        with patch.object(public_hourly_staging, "optional_public_skill_staging",
                          return_value=staged):
            output = StringIO()
            with redirect_stdout(output):
                exit_code = env["main"]()
        self.assertEqual(exit_code, 0)
        printed = json.loads(output.getvalue())
        self.assertEqual(printed["stage10"]["stage17_quality_candidate_count"], 3)
        self.assertEqual(printed["stage10"]["stage17_quality_candidate_delta"], -1)
        self.assertEqual(printed["stage10"]["stage17_quality_status"],
                         "STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO")
        self.assertFalse(printed["production_approved"])


if __name__ == "__main__":
    unittest.main()
