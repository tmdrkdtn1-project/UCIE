"""Independent UCIE code-only relocated workspace functional exercise.

A disposable CI runner copies only first-party src/**/*.py and one smoke
runner to runner-temp/UCIE_PROJECT/UCIE, with zero Git metadata, venv,
SQLite runtime, MCP profile or owner's dirty worktree. Running the copied
source with -I -B proves path-portability of P3/P6, NOT tunnel cutover.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
SMOKE = REPO / "scripts" / "ucie_isolated_library_smoke_v01.py"
EXPECTED_SCHEMA = "UCIE_CODE_ONLY_RELOCATED_SEARCH_SMOKE_V01"


class UCIECodeOnlyRelocatedStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="UCIE_FIRST_PARTY_STAGE_")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.stage = self.base / "UCIE_PROJECT" / "UCIE"
        self.stage.mkdir(parents=True)
        source = REPO / "src"
        self.assertTrue(source.is_dir())
        self.py_files = 0
        for path in sorted(source.rglob("*.py")):
            relative = path.relative_to(source)
            if path.is_symlink() or (
                    hasattr(path, "is_junction") and path.is_junction()):
                self.fail("unexpected indirect UCIE first-party source")
            self.assertTrue(relative.parts[0] in ("ucie_miner", "ucie_public"))
            dst = self.stage / "src" / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dst)
            self.py_files += 1
        self.assertGreater(self.py_files, 200)
        (self.stage / "scripts").mkdir()
        shutil.copyfile(
            SMOKE, self.stage / "scripts" / "ucie_isolated_library_smoke_v01.py")
        self.source = self.stage / "src" / "ucie_miner" / "library_exact_index.py"
        self.expected_sha = sha256(self.source.read_bytes()).hexdigest()
        self.original_source_sha = sha256(
            (REPO / "src" / "ucie_miner" / "library_exact_index.py").read_bytes()
        ).hexdigest()
        self.assertEqual(self.expected_sha, self.original_source_sha)
        self.guard = self.base / "UCIE_ONLY_TEMP_SENTINEL.txt"
        self.guard.write_bytes(b"keep owner runtime, task and mcp out of test")
        self.guard_sha = sha256(self.guard.read_bytes()).hexdigest()

    def run_stage(self, expected_sha: str | None = None, *,
                  script: Path | None = None, extra_env: dict | None = None):
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, "-I", "-B",
             str(script or (self.stage / "scripts"
                            / "ucie_isolated_library_smoke_v01.py")),
             "--source-sha256", self.expected_sha if expected_sha is None
             else expected_sha],
            cwd=self.stage, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=35, check=False,
        )

    def test_01_real_subprocess_in_relocated_ucie_project_runs_p3_p6(self):
        proc = self.run_stage()
        self.assertEqual(proc.returncode, 0,
                         proc.stderr.decode("utf-8", errors="replace")[-800:])
        data = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(data["schema"], EXPECTED_SCHEMA)
        self.assertEqual(
            data["status"], "UCIE_CODE_ONLY_STAGE_SEARCH_PASS__LIVE_MIGRATION_NO_GO")
        self.assertEqual(data["code_only_stage"], "UCIE_PROJECT/UCIE")
        self.assertEqual(data["source_rows_synthetic"], 27)
        self.assertEqual(data["results_retrieved"], 27)
        self.assertEqual(data["exact_source_sha256"], self.expected_sha)
        self.assertTrue(data["one_pass_search_verified"])
        self.assertTrue(data["multiquery_page_verified"])
        self.assertTrue(data["invalid_source_and_approval_rejected"])
        self.assertTrue(data["incomplete_ledger_remains_no_go"])
        self.assertFalse(data["real_owner_windows_drive_migrated"])
        self.assertFalse(data["mcp_live_connection_verified"])
        self.assertFalse(data["customer_release_authorized"])
        self.assertEqual(data["network_requests"], 0)
        self.assertEqual(data["operating_database_writes"], 0)

    def test_02_stage_is_genuinely_gitless_code_only_and_source_pinned(self):
        self.assertFalse((self.stage / ".git").exists())
        self.assertFalse((self.stage / "runtime").exists())
        self.assertFalse((self.stage / ".venv").exists())
        self.assertFalse((self.stage / ".ucie_bridge_state").exists())
        self.assertEqual(
            sha256(self.source.read_bytes()).hexdigest(),
            self.original_source_sha)
        self.assertTrue((self.stage / "src" / "ucie_public" / "policy.py").is_file())
        self.assertEqual(
            sha256(self.guard.read_bytes()).hexdigest(), self.guard_sha)

    def test_03_modified_source_sha_fails_closed_before_import(self):
        self.source.write_bytes(self.source.read_bytes() + b"\n# INERT TAMPER\n")
        proc = self.run_stage()
        self.assertEqual(proc.returncode, 2)
        report = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(report["status"], "UCIE_CODE_ONLY_STAGE_FAIL_CLOSED")
        self.assertEqual(report["reason_type"], "ValueError")
        self.assertFalse(report["customer_release_authorized"])

    def test_04_forged_or_partial_sha_rejected(self):
        for bad in ("", "a"*64, "00", "A"*64, "0"*63+"X"):
            with self.subTest(bad=bad):
                proc = self.run_stage(expected_sha=bad)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(
                    json.loads(proc.stdout.decode("utf-8"))["status"],
                    "UCIE_CODE_ONLY_STAGE_FAIL_CLOSED")

    def test_05_operating_data_git_and_bridge_state_presence_are_denied(self):
        for dirname in (".git", ".venv", "runtime", ".ucie_bridge_state"):
            with self.subTest(dirname=dirname):
                path = self.stage / dirname
                path.mkdir()
                try:
                    proc = self.run_stage()
                    self.assertEqual(proc.returncode, 2)
                    self.assertEqual(
                        json.loads(proc.stdout.decode("utf-8"))["status"],
                        "UCIE_CODE_ONLY_STAGE_FAIL_CLOSED")
                finally:
                    path.rmdir()

    def test_06_wrong_parent_folder_is_not_an_approved_stage(self):
        wrong = self.base / "WRONG_PARENT" / "UCIE"
        wrong.parent.mkdir()
        self.stage.rename(wrong)
        self.stage = wrong
        proc = self.run_stage()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(
            json.loads(proc.stdout.decode("utf-8"))["status"],
            "UCIE_CODE_ONLY_STAGE_FAIL_CLOSED")

    def test_07_python_isolated_mode_does_not_trust_py_path_injection(self):
        poison = self.base / "POISON_TEST_ONLY"
        poison.mkdir()
        (poison / "ucie_miner.py").write_text(
            "raise RuntimeError('FOREIGN_IMPORT_ATTEMPT')", encoding="utf-8")
        proc = self.run_stage(extra_env={"PYTHONPATH": str(poison),
                                         "PYTHONNOUSERSITE": "0"})
        self.assertEqual(proc.returncode, 0,
                         proc.stderr.decode("utf-8", errors="replace")[-650:])
        self.assertEqual(
            json.loads(proc.stdout.decode("utf-8"))["results_retrieved"], 27)

    def test_08_stage_does_not_create_pycache_git_runtime_or_mutate_sentinel(self):
        proc = self.run_stage()
        self.assertEqual(proc.returncode, 0)
        self.assertFalse(list(self.stage.rglob("__pycache__")))
        self.assertFalse((self.stage / ".git").exists())
        self.assertFalse((self.stage / "runtime").exists())
        self.assertFalse((self.stage / ".venv").exists())
        self.assertEqual(
            sha256(self.guard.read_bytes()).hexdigest(), self.guard_sha)

    def test_09_missing_first_party_source_module_denied(self):
        self.source.unlink()
        proc = self.run_stage()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(
            json.loads(proc.stdout.decode("utf-8"))["status"],
            "UCIE_CODE_ONLY_STAGE_FAIL_CLOSED")

    def test_10_symlinked_library_source_denied_when_supported(self):
        target = self.base / "UCIE_FIRST_PARTY_TEMP_REFERENCE.py"
        target.write_bytes(self.source.read_bytes())
        self.source.unlink()
        try:
            self.source.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink privilege unavailable")
        proc = self.run_stage()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(
            json.loads(proc.stdout.decode("utf-8"))["status"],
            "UCIE_CODE_ONLY_STAGE_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
