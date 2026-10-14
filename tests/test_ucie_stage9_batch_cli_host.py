"""Stage 9 batch CLI and local-host acceptance never mutate operating state."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from ucie_miner.public_batch_host import inspect_public_batch_host
from ucie_miner.public_batch import build_public_batch
from test_ucie_stage9_batch import NOW, metadata, evidence

ROOT = Path(__file__).resolve().parents[1]


def cli(*args, input=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "ucie_miner", *args],
        input=input, text=True, capture_output=True,
        env=env, cwd=ROOT, timeout=15,
    )


class PublicBatchCommandTests(unittest.TestCase):
    def test_no_live_opt_in_fails_before_any_public_api_request(self):
        result = cli("batch-public-evidence")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL_CLOSED")

    def test_unapproved_pr_optout_cannot_expand_scope(self):
        # Command must reject the opt-out syntax rather than accidentally
        # making any public/foreign API calls.
        result = cli("batch-public-evidence", "--live",
                     "--skip-pr", "foreign/private#123")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "FAIL_CLOSED")

    def test_unapproved_source_is_rejected_by_argparse(self):
        result = cli("batch-public-evidence", "--live",
                     "--source", "foreign/private")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_offline_batch_receipt_goes_only_to_manual_review(self):
        receipt = build_public_batch(
            metadata_fetch=metadata, evidence_fetch=evidence,
            now=NOW, max_enrich=2)
        run = cli("preview-public-batch-stdin", input=json.dumps(receipt))
        self.assertEqual(run.returncode, 0, run.stderr)
        output = json.loads(run.stdout)
        self.assertEqual(output["status"], "MANUAL_CANDIDATE_REVIEW_PENDING")
        self.assertEqual(output["candidate_count"], 2)
        self.assertFalse(output["operational_go"])
        self.assertFalse(output["production_approved"])

    def test_duplicate_json_fields_fail_closed(self):
        run = cli("preview-public-batch-stdin",
                  input='{"schema":"x","schema":"y","candidate_skill_queue":[]}')
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)["status"], "FAIL_CLOSED")

    def test_oversized_json_fails_closed(self):
        run = cli("preview-public-batch-stdin", input=" " * 262145)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)["status"], "FAIL_CLOSED")


class HostPreflightTests(unittest.TestCase):
    def test_missing_runtime_does_not_create_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "UCIE"
            root.mkdir()
            result = inspect_public_batch_host(
                root, is_windows=True, python_version=(3, 15))
            self.assertEqual(result["status"], "READ_ONLY_PRECHECK_NO_GO")
            self.assertEqual(result["miner_database_state"], "ABSENT")
            self.assertFalse((root / "runtime").exists())
            self.assertFalse(result["production_approved"])
            self.assertFalse(result["operating_windows_host_identity_attested"])
            self.assertFalse(result["actual_public_batch_run_observed"])

    def test_fixture_databases_can_be_read_without_live_host_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "UCIE"
            runtime = root / "runtime"
            runtime.mkdir(parents=True)
            files = [(runtime / "public_miner.sqlite3", "candidates"),
                     (runtime / "knowledge.sqlite3", "evidence")]
            for db_file, table in files:
                with closing(sqlite3.connect(db_file)) as conn:
                    conn.execute(f"CREATE TABLE {table}(id INTEGER)")
                    conn.execute(f"INSERT INTO {table} VALUES(1)")
                    conn.commit()
            snapshots = {str(p): p.read_bytes() for p, _ in files}
            check = inspect_public_batch_host(
                root, is_windows=True, python_version=(3, 15))
            self.assertTrue(check["readonly_existing_db_precheck_complete"])
            self.assertEqual(check["miner_database_state"],
                             "READ_ONLY_INSPECTED")
            self.assertEqual(check["knowledge_database_state"],
                             "READ_ONLY_INSPECTED")
            self.assertEqual(check["status"], "READ_ONLY_PRECHECK_NO_GO")
            self.assertFalse(check["task_scheduler_binding_verified"])
            self.assertFalse(check["production_approved"])
            self.assertEqual(check["permanent_database_writes"], 0)
            self.assertEqual({str(p): p.read_bytes() for p, _ in files},
                             snapshots)

    def test_non_windows_compatibility_not_mislabeled_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "UCIE"
            root.mkdir()
            result = inspect_public_batch_host(
                root, is_windows=False, python_version=(3, 15))
            self.assertFalse(result["windows_python_315_compatible"])
            self.assertFalse(result["production_approved"])

    def test_wrong_project_root_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                inspect_public_batch_host(Path(directory),
                                          is_windows=True,
                                          python_version=(3, 15))


if __name__ == "__main__":
    unittest.main()
