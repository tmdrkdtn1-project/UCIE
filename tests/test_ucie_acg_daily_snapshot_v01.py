"""UCIE daily 05:00 snapshots: disposable Git-only positive/negative QA."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tempfile
from unittest import TestCase

from scripts import ucie_acg_daily_snapshot_v01 as mod


class DailySnapshotTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args],
                                           stderr=subprocess.DEVNULL).decode().strip()
        self.git = git
        git("init", "-q")
        git("config", "user.name", "UCIE QA")
        git("config", "user.email", "qa@example.invalid")
        git("remote", "add", "origin", "https://github.com/" + mod.REPO + ".git")
        (self.root / "fixture.txt").write_text("hello")
        git("add", "fixture.txt")
        git("commit", "-qm", "baseline")
        self.head = git("rev-parse", "HEAD")
        self.now = datetime(2026, 11, 25, 20, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()

    def test_preview_no_write(self):
        report = mod.daily(self.root, now=self.now)
        self.assertEqual(report["status"], "PREVIEW_ONLY_NO_WRITE")
        with self.assertRaises(subprocess.CalledProcessError):
            self.git("rev-parse", "--verify", report["checkpoint_ref"])

    def test_create_then_identical_no_duplicate(self):
        report = mod.daily(self.root, write=True, now=self.now)
        self.assertEqual(report["checkpoint_id"], "daily_20261126")
        self.assertEqual(report["status"], "LOCAL_COMMITTED_HEAD_REF_CREATED_NOT_CI_VERIFIED")
        self.assertEqual(self.git("rev-parse", report["checkpoint_ref"]), self.head)
        self.assertEqual(mod.daily(self.root, write=True, now=self.now)["status"],
                         "ALREADY_CAPTURED_SAME_HEAD")

    def test_dirty_file_holds(self):
        (self.root / "fixture.txt").write_text("dirty")
        self.assertEqual(mod.daily(self.root, write=True, now=self.now)["status"],
                         "HOLD_DIRTY_NO_GIT_REF_CREATED")

    def test_untracked_secret_holds_without_mutation(self):
        extra = self.root / "secret.tmp"
        extra.write_text("sensitive")
        self.assertEqual(mod.daily(self.root, write=True, now=self.now)["status"],
                         "HOLD_DIRTY_NO_GIT_REF_CREATED")
        self.assertEqual(extra.read_text(), "sensitive")

    def test_existing_daily_ref_never_overwritten(self):
        first = mod.daily(self.root, write=True, now=self.now)
        (self.root / "fixture.txt").write_text("changed")
        self.git("add", "fixture.txt")
        self.git("commit", "-qm", "later")
        self.assertEqual(mod.daily(self.root, write=True, now=self.now)["status"],
                         "HOLD_DAILY_REF_EXISTS_DIFFERENT_SHA")
        self.assertEqual(self.git("rev-parse", first["checkpoint_ref"]), self.head)

    def test_wrong_origin_denied(self):
        self.git("remote", "set-url", "origin", "https://github.com/no/repo.git")
        with self.assertRaises(mod.SnapshotDenied):
            mod.daily(self.root, now=self.now)

    def test_offset_aware_korean_calendar(self):
        self.assertEqual(mod.daily(self.root, now=self.now)["checkpoint_id"],
                         "daily_20261126")

    def test_naive_datetime_fails(self):
        with self.assertRaises(mod.SnapshotDenied):
            mod.daily(self.root, now=datetime(2026, 11, 26, 5, 0))

    def test_installer_is_preview_only_and_separate(self):
        text = (Path(__file__).resolve().parents[1] / "scripts" /
                "install_ucie_acg_daily_snapshot_task_v01.ps1").read_text(encoding="utf-8")
        for token in ("UCIE-ACG-DailySnapshot",
                      "New-ScheduledTaskTrigger -Daily -At '05:00'",
                      "-StartWhenAvailable", "-MultipleInstances IgnoreNew",
                      "EXISTING_UCIE_ACG_TASK_REFUSE_OVERWRITE",
                      "PREVIEW_ONLY_NO_TASK_CREATED", "if (-not $Install)",
                      "-LogonType Interactive", "--run"):
            self.assertIn(token, text)
        self.assertNotIn("Unregister-ScheduledTask", text)
