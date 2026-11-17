"""UCIE-only first-party 232-file byte-verified disposable stage acceptance.

All actual copies here are inside unittest TemporaryDirectory, never owner D:.
Git object reads use only this repository's present HEAD source tree.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_code_only_stage_once_v01.py"
MANIFEST = ROOT / "docs" / "UCIE_PR305_CODE_ONLY_STAGE_MANIFEST_V01.json"

spec = importlib.util.spec_from_file_location("ucie_owner_stage_once", SCRIPT)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class OwnerCodeOnlyStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("git"):
            raise AssertionError("first-party Git source identity verification unavailable")
        cls.tmp = tempfile.TemporaryDirectory(prefix="UCIE_PR305_CI_STAGE_")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.temp = Path(cls.tmp.name)
        cls.source = cls.temp / "UCIE_PR305_SOURCE"
        cls.source.mkdir()
        verifier = stage._load_verifier()
        cls.meta, cls.files = verifier.load_manifest(MANIFEST)

        # Confirm Git's indexed commit tree maps every claimed path to the
        # manifest identity; never just trust that an arbitrary blob exists.
        args = ["git", "-C", str(ROOT), "ls-tree", "-rz", "HEAD", "--",
                "src/ucie_miner", "src/ucie_public",
                "scripts/bootstrap_local.ps1",
                "scripts/install_hourly_task.ps1",
                "scripts/install_internal_minute_task.ps1",
                "scripts/ucie_isolated_library_smoke_v01.py"]
        tree = subprocess.run(args, capture_output=True, timeout=30, check=True).stdout
        found = {}
        for line in tree.split(b"\0"):
            if not line:
                continue
            mode_type_sha, name = line.split(b"\t", 1)
            mode, kind, blob_sha = mode_type_sha.decode("ascii").split(" ")
            name = name.decode("utf-8")
            if name in {row["path"] for row in cls.files}:
                if mode not in {"100644", "100755"} or kind != "blob":
                    raise AssertionError("first-party Git object kind mismatch")
                found[name] = blob_sha
        self_map = {row["path"]: row["git_blob_sha1"] for row in cls.files}
        if found != self_map:
            raise AssertionError("manifest and first-party actual Git tree differ")

        for row in cls.files:
            out = subprocess.run(
                ["git", "-C", str(ROOT), "cat-file", "blob", row["git_blob_sha1"]],
                capture_output=True, timeout=15, check=True)
            blob = out.stdout
            if len(blob) != row["bytes"] or stage._git_blob(blob) != row["git_blob_sha1"]:
                raise AssertionError("Git first-party blob bytes or size differ")
            destination = cls.source.joinpath(*row["path"].split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blob)

    def _stage_destination(self, name="UCIE"):
        parent = self.temp / name.replace("UCIE", "OWNER_PARENT", 1)
        parent.mkdir(exist_ok=True)
        return parent / name

    def test_01_real_git_first_party_232_immutable_files(self):
        self.assertEqual(self.meta["source_commit_sha"],
                         "96c6187430fc126214e93f57cfcd0b86331dc1a4")
        self.assertEqual(len(self.files), 232)
        self.assertEqual(sum(x["bytes"] for x in self.files), 2934205)
        verifier = stage._load_verifier()
        receipt = verifier.preflight(self.source, MANIFEST)
        self.assertEqual(receipt["file_count"], 232)
        self.assertFalse(receipt["destination_written"])
        self.assertFalse(receipt["live_task_or_mcp_changed"])

    def test_02_preview_all_real_bytes_no_destination_writes(self):
        dest = self._stage_destination("UCIE_P02")
        report = stage.stage_once(
            self.source, MANIFEST, dest, mode="preview", owner_only=False)
        self.assertEqual(report["planned_files"], 232)
        self.assertEqual(report["status"], "UCIE_CODE_ONLY_STAGE_PREVIEW_NO_WRITES")
        self.assertFalse(report["destination_written"])
        self.assertFalse(dest.exists())

    def test_03_apply_without_explicit_owner_approval_denied(self):
        dest = self._stage_destination("UCIE_P03")
        with self.assertRaises(stage.StageCopyRejected):
            stage.stage_once(self.source, MANIFEST, dest,
                             mode="apply", owner_only=False)
        self.assertFalse(dest.exists())

    def test_04_real_all_232_disposable_apply_then_verified_receipt(self):
        # Match PR #304/305 realistic UCIE_PROJECT/UCIE code-only hierarchy.
        parent = self.temp / "UCIE_PROJECT"
        parent.mkdir(exist_ok=True)
        dest = parent / "UCIE"
        report = stage.stage_once(
            self.source, MANIFEST, dest, mode="apply",
            owner_approval=stage.OWNER_APPROVAL, owner_only=False)
        self.assertTrue(report["destination_written"])
        self.assertEqual(report["verified_files"], 232)
        self.assertFalse(report["live_task_mcp_tunnel_or_database_changed"])
        self.assertFalse(report["original_owner_root_moved_or_modified"])
        self.assertFalse(report["live_cutover_authorized"])
        rec = json.loads((dest / stage.RECEIPT).read_text("utf-8"))
        self.assertEqual(rec, report)
        for row in self.files:
            p = dest.joinpath(*row["path"].split("/"))
            self.assertTrue(p.is_file())
            self.assertEqual(p.stat().st_size, row["bytes"])
            self.assertEqual(stage._git_blob(p.read_bytes()), row["git_blob_sha1"])
        # Real relocated P3/P6 search runs in an isolated Python -I -B process
        # with all 27 UCIE-authored synthetic revisions and no operating DB.
        for forbidden in (".git", ".venv", "runtime", ".ucie_bridge_state"):
            self.assertFalse((dest / forbidden).exists())
        source_digest = sha256((dest / "src" / "ucie_miner" /
                                "library_exact_index.py").read_bytes()).hexdigest()
        smoke = subprocess.run([
            sys.executable, "-I", "-B",
            str(dest / "scripts" / "ucie_isolated_library_smoke_v01.py"),
            "--source-sha256", source_digest,
        ], capture_output=True, timeout=40, check=False, cwd=dest)
        self.assertEqual(smoke.returncode, 0,
                         smoke.stderr.decode("utf-8", "replace")[-1000:])
        proof = json.loads(smoke.stdout.decode("utf-8"))
        self.assertEqual(proof["results_retrieved"], 27)
        self.assertEqual(proof["network_requests"], 0)
        self.assertEqual(proof["operating_database_writes"], 0)
        self.assertFalse(proof["real_owner_windows_drive_migrated"])

        # All three PR #305 owner script previews run as real native PowerShell
        # on Windows, without executing -Install, -Setup, or any live Task.
        if os.name == "nt":
            ps = shutil.which("powershell.exe")
            self.assertIsNotNone(ps, "native Windows PowerShell required")
            for name in ("bootstrap_local.ps1", "install_hourly_task.ps1",
                         "install_internal_minute_task.ps1"):
                with self.subTest(owner_preview=name):
                    run = subprocess.run([
                        ps, "-NoProfile", "-NonInteractive", "-File",
                        str(dest / "scripts" / name), "-StagePreview",
                    ], cwd=dest, capture_output=True, timeout=25, check=False)
                    self.assertEqual(run.returncode, 0,
                                     run.stderr.decode("utf-8", "replace")[-600:])
                    self.assertIn("UCIE_STAGE_PREVIEW_ONLY_NO_SETUP_OR_TASK_MUTATION",
                                  run.stdout.decode("utf-8-sig", "replace"))
        with self.assertRaises(stage.StageCopyRejected):
            stage.stage_once(self.source, MANIFEST, dest, mode="apply",
                             owner_approval=stage.OWNER_APPROVAL, owner_only=False)

    def test_05_preexisting_destination_and_parent_missing_denied(self):
        dest = self._stage_destination("UCIE_P05")
        dest.mkdir()
        (dest / "keep_user_data.txt").write_text("DO NOT TOUCH", encoding="utf-8")
        with self.assertRaises(stage.StageCopyRejected):
            stage.stage_once(self.source, MANIFEST, dest,
                             mode="apply", owner_approval=stage.OWNER_APPROVAL,
                             owner_only=False)
        self.assertEqual((dest / "keep_user_data.txt").read_text("utf-8"),
                         "DO NOT TOUCH")
        unknown = self.temp / "missing_parent" / "UCIE"
        with self.assertRaises(stage.StageCopyRejected):
            stage.stage_once(self.source, MANIFEST, unknown,
                             mode="apply", owner_approval=stage.OWNER_APPROVAL,
                             owner_only=False)
        self.assertFalse(unknown.parent.exists())

    def test_06_source_after_pinned_preflight_tampered_denied(self):
        entry = self.files[0]
        source = self.source.joinpath(*entry["path"].split("/"))
        original = source.read_bytes()
        try:
            source.write_bytes(original + b"forgery")
            target = self._stage_destination("UCIE_P06")
            with self.assertRaises(ValueError):
                stage.stage_once(self.source, MANIFEST, target, mode="preview",
                                 owner_only=False)
            self.assertFalse(target.exists())
        finally:
            source.write_bytes(original)

    def test_07_symlink_parent_denied_without_writes(self):
        real_parent = self.temp / "real_stage_parent"
        real_parent.mkdir(exist_ok=True)
        link = self.temp / "link_stage_parent"
        try:
            link.symlink_to(real_parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("OS forbids test symlink creation")
        with self.assertRaises(stage.StageCopyRejected):
            stage.stage_once(self.source, MANIFEST, link / "UCIE",
                             mode="apply", owner_approval=stage.OWNER_APPROVAL,
                             owner_only=False)
        self.assertEqual(list(real_parent.iterdir()), [])

    def test_08_actual_owner_target_is_not_general_writable_argument(self):
        arbitrary = self._stage_destination("UCIE_P08")
        with self.assertRaises(stage.StageCopyRejected):
            stage.stage_once(self.source, MANIFEST, arbitrary, mode="apply",
                             owner_approval=stage.OWNER_APPROVAL, owner_only=True)
        self.assertFalse(arbitrary.exists())
        text = SCRIPT.read_text("utf-8")
        self.assertIn('OWNER_TARGET = r"D:\\UCIE_PROJECT\\UCIE"', text)
        self.assertIn("partial_destination_requires_owner_review", text)
        self.assertNotIn("rmtree(", text)
        self.assertNotIn("os.replace(", text)
        self.assertNotIn("subprocess.run(", text)
        self.assertNotIn("sqlite3.connect(", text)
        self.assertNotIn("Start-ScheduledTask", text)
        self.assertNotIn("Register-ScheduledTask", text)


if __name__ == "__main__":
    unittest.main()
