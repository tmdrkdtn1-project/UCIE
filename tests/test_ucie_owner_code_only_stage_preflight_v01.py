"""Synthetic independent negative QA for immutable UCIE code-only source stage."""
from __future__ import annotations

from hashlib import sha1
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_code_only_stage_preflight_v01.py"
MANIFEST = ROOT / "docs" / "UCIE_PR305_CODE_ONLY_STAGE_MANIFEST_V01.json"
spec = importlib.util.spec_from_file_location("ucie_owner_stage_preflight", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ImmutableCodeStageTests(unittest.TestCase):
    def test_01_manifest_exact_commit_and_first_party_allowlist(self):
        meta, files = mod.load_manifest(MANIFEST)
        self.assertEqual(meta["source_commit_sha"], mod.EXPECTED_COMMIT)
        self.assertEqual(len(files), 232)
        self.assertEqual(sum(x["bytes"] for x in files), 2934205)
        self.assertEqual(len({x["path"] for x in files}), len(files))
        self.assertTrue(all(mod._allowed_path(x["path"]) for x in files))

    def test_02_mutating_manifest_rejected(self):
        original = json.loads(MANIFEST.read_text("utf-8"))
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "manifest.json"
            for edit in ("commit", "traversal", "duplicate", "unsupported"):
                obj = json.loads(json.dumps(original))
                if edit == "commit":
                    obj["source_commit_sha"] = "0" * 40
                elif edit == "traversal":
                    obj["files"][0]["path"] = "../other/file.py"
                elif edit == "duplicate":
                    obj["files"][1]["path"] = obj["files"][0]["path"]
                else:
                    obj["files"][0]["path"] = "runtime/secrets.json"
                dest.write_text(json.dumps(obj), "utf-8")
                with self.subTest(edit=edit), self.assertRaises(mod.StageRejected):
                    mod.load_manifest(dest)

    def test_03_reject_unapproved_paths(self):
        for value in ("../../private/file.py", "runtime/secret.py", ".git/config",
                      "src/ucie_miner/subdir/extra.py",
                      "src/ucie_miner/../../outside.py",
                      "scripts/ucie_c40_recover.ps1",
                      "src\\ucie_miner\\core.py", "/tmp/src/ucie_miner/core.py"):
            with self.subTest(value=value):
                self.assertFalse(mod._allowed_path(value))

    def test_04_matching_one_file_synthetic_blob_and_tamper(self):
        with tempfile.TemporaryDirectory(prefix="UCIE_PR305_SOURCE_") as td:
            root = Path(td) / "UCIE_PR305_SOURCE"
            p = root / "src" / "ucie_miner" / "core.py"
            p.parent.mkdir(parents=True)
            data = b"test only"
            p.write_bytes(data)
            row = {"path": "src/ucie_miner/core.py", "bytes": len(data),
                   "git_blob_sha1": sha1(b"blob 9\0" + data).hexdigest()}
            manifest = Path(td) / "manifest.json"
            manifest.write_text("{}", "utf-8")
            obj = {"source_commit_sha": mod.EXPECTED_COMMIT}
            with patch.object(mod, "load_manifest", return_value=(obj, [row])):
                report = mod.preflight(root, manifest)
                self.assertEqual(report["file_count"], 1)
                self.assertFalse(report["destination_written"])
                self.assertFalse(report["live_task_or_mcp_changed"])
                p.write_bytes(b"test evil")
                with self.assertRaises(mod.StageRejected):
                    mod.preflight(root, manifest)

    def test_05_reject_symlink_snapshot_and_file(self):
        with tempfile.TemporaryDirectory(prefix="UCIE_PR305_SOURCE_") as td:
            root = Path(td) / "UCIE_PR305_SOURCE"
            root.mkdir()
            target = Path(td) / "target.py"
            target.write_text("test", "utf-8")
            link = root / "src"
            try:
                link.symlink_to(target, target_is_directory=False)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            self.assertFalse(mod._direct_chain(link))

    def test_06_cli_denies_nonexistent_snapshot_and_does_not_create_files(self):
        with tempfile.TemporaryDirectory(prefix="UCIE_PR305_SOURCE_") as td:
            nonexistent = Path(td) / "missing"
            p = subprocess.run(
                [sys.executable, "-I", "-B", str(SCRIPT),
                 "--snapshot", str(nonexistent), "--manifest", str(MANIFEST)],
                capture_output=True, text=True, timeout=20, check=False)
            self.assertEqual(p.returncode, 2)
            output = json.loads(p.stdout)
            self.assertEqual(output["status"], "UCIE_CODE_ONLY_SOURCE_PREFLIGHT_NO_GO")
            self.assertFalse(output["destination_written"])
            self.assertFalse(nonexistent.exists())

    def test_07_script_remains_nonmutating_source_only(self):
        source = SCRIPT.read_text("utf-8")
        for prohibited in ("shutil.copy", "shutil.move", "os.replace(",
                           "subprocess.run(", "sqlite3.connect(",
                           "Register-ScheduledTask", "Start-ScheduledTask",
                           "git clean", "git reset", "rmtree(", "mkdir("):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, source)
        self.assertIn("destination_written", source)
        self.assertIn("EXPECTED_COMMIT", source)
        self.assertIn("git_blob_sha1", source)


if __name__ == "__main__":
    unittest.main()
