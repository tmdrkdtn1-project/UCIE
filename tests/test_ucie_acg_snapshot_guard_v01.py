"""Isolated disposable Git repository regression; no real project mutation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.ucie_acg_snapshot_guard_v01 import SnapshotDenied, checkpoint, inspect, recover_preview


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = "example-org/example-repo"
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args],
                                           stderr=subprocess.DEVNULL).decode().strip()
        self.git = git
        git("init", "-q")
        git("config", "user.name", "First Party Test")
        git("config", "user.email", "test@example.invalid")
        git("remote", "add", "origin", "https://github.com/" + self.repo + ".git")
        (self.root / "test.txt").write_text("committed\n")
        git("add", "test.txt")
        git("commit", "-qm", "baseline")
        self.head = git("rev-parse", "HEAD")

    def tearDown(self):
        self.tmp.cleanup()

    def test_scope_and_readonly_inspect(self):
        report = inspect(self.root, self.repo, "UCIE")
        self.assertEqual(report["head_sha"], self.head)
        self.assertTrue(report["worktree_clean"])
        self.assertFalse(report["github_actions_triggered"])
        with self.assertRaises(SnapshotDenied):
            inspect(self.root, "another/repo", "UCIE")

    def test_preview_does_not_write_ref(self):
        result = checkpoint(self.root, self.repo, "UCIE", "step_01", self.head)
        self.assertEqual(result["status"], "PREVIEW_ONLY_NO_WRITE")
        with self.assertRaises(subprocess.CalledProcessError):
            self.git("rev-parse", "--verify", result["checkpoint_ref"])

    def test_create_verify_and_no_overwrite(self):
        before = self.git("status", "--porcelain=v1")
        r = checkpoint(self.root, self.repo, "UCIE", "step_01", self.head, True)
        self.assertEqual(r["status"], "LOCAL_COMMITTED_HEAD_REF_CREATED_NOT_CI_VERIFIED")
        self.assertEqual(self.git("rev-parse", r["checkpoint_ref"]), self.head)
        self.assertEqual(self.git("status", "--porcelain=v1"), before)
        self.assertEqual(recover_preview(self.root, self.repo, "UCIE", "step_01")["checkpoint_sha"], self.head)
        with self.assertRaises(SnapshotDenied):
            checkpoint(self.root, self.repo, "UCIE", "step_01", self.head, True)

    def test_dirty_tracked_and_untracked_denied(self):
        (self.root / "test.txt").write_text("dirty")
        with self.assertRaisesRegex(SnapshotDenied, "UNCOMMITTED"):
            checkpoint(self.root, self.repo, "UCIE", "step_02", self.head, True)
        (self.root / "test.txt").write_text("committed\n")
        (self.root / "secret.tmp").write_text("untracked")
        with self.assertRaisesRegex(SnapshotDenied, "UNCOMMITTED"):
            checkpoint(self.root, self.repo, "UCIE", "step_02", self.head, True)

    def test_wrong_sha_and_unsafe_id(self):
        for sha in ("b" * 40, "bad"):
            with self.assertRaises(SnapshotDenied):
                checkpoint(self.root, self.repo, "UCIE", "step_01", sha, True)
        for ident in ("../escape", "bad/ref", ".hidden"):
            with self.assertRaises(SnapshotDenied):
                checkpoint(self.root, self.repo, "UCIE", ident, self.head, True)

    def test_missing_snapshot_recovery_denied(self):
        with self.assertRaises(SnapshotDenied):
            recover_preview(self.root, self.repo, "UCIE", "missing_01")

if __name__ == "__main__":
    unittest.main()
