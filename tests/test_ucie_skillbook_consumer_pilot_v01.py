"""End-to-end use, safety and negative-path checks for UCIE SkillBook 001.

This is a *product-consumer* acceptance: it uses the real reusable function
and its machine contract, never a fake directory API or production data.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from ucie_miner import skillbook_consumer_pilot_v01 as pilot


class SkillBookConsumerPilotTests(unittest.TestCase):
    def test_manual_real_consumer_with_bounded_disposable_input(self):
        report = pilot.demonstrate_synthetic_consumer()
        self.assertEqual(report["status"], pilot.OBSERVED)
        self.assertEqual(report["skillbook_id"], pilot.SKILLBOOK_ID)
        self.assertEqual(report["baseline_method"],
                         "os.listdir_on_same_UCIE_synthetic_fixture")
        self.assertEqual(report["baseline_entry_count"], 3)
        self.assertEqual(report["bounded_regular_file_names"],
                         ["alpha.txt", "zeta.txt"])
        self.assertEqual(report["bounded_regular_file_name_count"], 2)
        self.assertEqual(report["directory_entry_budget"], 3)
        for key in ("budget_overflow_blocked", "invalid_budget_blocked",
                    "relative_path_blocked",
                    "empty_directory_returns_empty_tuple",
                    "nested_directory_skipped", "temporary_fixture_cleaned",
                    "real_ucie_authored_recipe_executed",
                    "only_temporary_synthetic_fixture_used",
                    "no_performance_superiority_claimed"):
            self.assertIs(report[key], True, key)
        self.assertEqual(len(report["recipe_sha256"]), 64)
        self.assertEqual(len(report["source_document_sha256"]), 64)

    def test_preview_does_not_touch_real_or_synthetic_filesystem(self):
        with patch.object(pilot, "TemporaryDirectory",
                          side_effect=AssertionError("preview created folder")), \
             patch.object(pilot, "bounded_regular_file_names",
                          side_effect=AssertionError("preview executed recipe")):
            buf = StringIO()
            with redirect_stdout(buf):
                status = pilot.main([])
        self.assertEqual(status, 0)
        report = json.loads(buf.getvalue())
        self.assertEqual(report["status"], pilot.PREVIEW)
        self.assertFalse(report["demo_executed"])
        self.assertFalse(report["actual_recipe_executed"])
        self.assertFalse(report["temporary_fixture_writes"])

    def test_manual_opt_in_cli_succeeds_with_explicit_synthetic_only(self):
        buf = StringIO()
        with redirect_stdout(buf):
            code = pilot.main(["--run-synthetic-demo"])
        self.assertEqual(code, 0)
        result = json.loads(buf.getvalue())
        self.assertEqual(result["status"], pilot.OBSERVED)
        self.assertFalse(result["export_allowed"])
        self.assertFalse(result["independent_qa_verified"])
        self.assertFalse(result["owner_release_approved"])
        self.assertFalse(result["package_created"])
        self.assertFalse(result["real_owner_directory_scanned"])
        self.assertFalse(result["file_contents_read"])
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(result["task_scheduler_mutations"], 0)
        self.assertFalse(result["other_project_access"])

    def test_cross_python_process_consumer_has_sanitized_json(self):
        root = Path(__file__).resolve().parents[1]
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root / "src")
        result = subprocess.run(
            [sys.executable, "-B", "-m",
             "ucie_miner.skillbook_consumer_pilot_v01",
             "--run-synthetic-demo"],
            cwd=root, env=env, capture_output=True, text=True, timeout=15,
            check=False)
        self.assertEqual(result.returncode, 0, result.stderr[-1200:])
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], pilot.OBSERVED)
        self.assertEqual(data["bounded_regular_file_names"],
                         ["alpha.txt", "zeta.txt"])
        self.assertNotIn("user_directory", result.stdout)
        self.assertNotIn("tmp\\", result.stdout)
        self.assertNotIn("TEMP\\", result.stdout)
        self.assertFalse(data["export_allowed"])

    def test_unknown_parameters_rejected_not_used_as_scan_path(self):
        for args in (["--directory", "C:/unknown"],
                     ["--export"], ["--run-synthetic-demo", "--publish"],
                     ["--help", "--allow-crawl"]):
            with self.subTest(args=args):
                with self.assertRaises(SystemExit):
                    pilot.main(args)

    def test_contract_forgery_blocks_consumer_before_fixture_creation(self):
        book = pilot.build_skillbook()
        cases = (
            ("published", lambda: book["proof_gates"].update(
                published=True)),
            ("export", lambda: book.update(export_allowed=True)),
            ("callable", lambda: book["machine_skill_contract"].update(
                callable="os.system")),
            ("source", lambda: book["source_evidence"].update(
                source_document_sha256="f" * 64)),
        )
        for name, change in cases:
            with self.subTest(case=name):
                book = pilot.build_skillbook()
                change()
                with patch.object(pilot, "build_skillbook", return_value=book), \
                     patch.object(pilot, "TemporaryDirectory",
                                  side_effect=AssertionError("forged input created fixture")):
                    with self.assertRaises(pilot.ConsumerPilotError):
                        pilot.demonstrate_synthetic_consumer()

    def test_recipe_behavior_drift_fails_closed(self):
        with patch.object(pilot, "bounded_regular_file_names",
                          return_value=("WRONG.txt",)):
            with self.assertRaises(pilot.ConsumerPilotError):
                pilot.demonstrate_synthetic_consumer()

    def test_failure_cli_never_reports_approved_release(self):
        with patch.object(pilot, "build_skillbook",
                          side_effect=pilot.ConsumerPilotError(
                              "forged source contract")):
            buff = StringIO()
            with redirect_stdout(buff):
                exit_code = pilot.main(["--run-synthetic-demo"])
        self.assertEqual(exit_code, 2)
        report = json.loads(buff.getvalue())
        self.assertEqual(report["status"], pilot.NO_GO)
        self.assertFalse(report["export_allowed"])
        self.assertEqual(report["task_scheduler_mutations"], 0)

    def test_machine_contract_name_and_real_source_digest_are_linked(self):
        sha = pilot._check_source()
        book = pilot.build_skillbook()
        self.assertEqual(len(sha), 64)
        self.assertEqual(book["machine_skill_contract"]["callable"],
                         "ucie_miner.skillbook_scandir_recipe_v01."
                         "bounded_regular_file_names")
        self.assertEqual(book["source_evidence"]["source_document_sha256"],
                         pilot.SOURCE_DOCUMENT_SHA256)
        self.assertFalse(book["proof_gates"]["independent_test_verified"])
        self.assertFalse(book["export_allowed"])


if __name__ == "__main__":
    unittest.main()
