"""Host P8 targeted source sync with backups, rollback and source trust tests."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import os
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import p11_host_sync as s


class P8HostSyncTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        base = Path(t.name)
        self.release = base / "UCIE_RELEASE" / "UCIE"
        self.live = base / "operating" / "UCIE"
        self.release.mkdir(parents=True)
        (self.live / "runtime").mkdir(parents=True)
        (self.release / "src" / "ucie_miner").mkdir(parents=True)
        (self.live / "src" / "ucie_miner").mkdir(parents=True)
        self.originals = {}
        self.new = {}
        self.run_git("init")
        for rel in s.FILES[1:]:
            x = b"# UCIE original first-party module\n"
            path = self.release / rel
            path.write_bytes(x)
            (self.live / rel).write_bytes(x)
            self.originals[rel] = x
        self.run_git("add", ".")
        self.run_git("-c", "user.email=test@ucie.local",
                     "-c", "user.name=UCIE Test",
                     "commit", "-m", "base")
        self.base = self.run_git("rev-parse", "HEAD").decode().strip()
        for i, rel in enumerate(s.FILES):
            x = ("# UCIE first-party P8 patched %d\n" % i).encode("ascii")
            (self.release / rel).write_bytes(x)
            self.new[rel] = x
        self.run_git("add", ".")
        self.run_git("-c", "user.email=test@ucie.local",
                     "-c", "user.name=UCIE Test",
                     "commit", "-m", "target")
        self.target = self.run_git("rev-parse", "HEAD").decode().strip()
        self.patch1 = patch.object(s, "BASE", self.base)
        self.patch2 = patch.object(s, "PIN", self.target)
        self.patch1.start()
        self.patch2.start()
        self.addCleanup(self.patch1.stop)
        self.addCleanup(self.patch2.stop)
        with closing(sqlite3.connect(
                self.live / "runtime" / "ucie_internal_pending_queue_v1.sqlite3"
        )) as db:
            db.execute("CREATE TABLE jobs(status TEXT)")
            db.commit()
        (self.live / "runtime" / "do_not_touch.txt").write_text("KEEP")
        (self.live / "src" / "ucie_miner" / "local_only.py").write_text(
            "# LOCAL OWNED DO NOT TOUCH\n")

    def run_git(self, *args):
        p = subprocess.run(
            ["git", "-C", str(self.release), *args],
            capture_output=True, check=False, timeout=10)
        if p.returncode:
            raise AssertionError(p.stderr.decode(errors="replace"))
        return p.stdout

    def test_preflight_no_files_changed_then_exact_three_file_apply(self):
        preview = s.sync(
            self.release, self.live, allow_test_root=True)
        self.assertEqual(preview["status"], "EXACT_P8_HOST_SYNC_READY_NO_CHANGE")
        self.assertEqual(preview["files_needing_update"], 3)
        self.assertEqual(len(preview["files_to_update"]), 3)
        self.assertFalse((self.live / s.FILES[0]).exists())
        self.assertFalse((self.live / "runtime" /
                          "p8_pinned_sync_backups").exists())
        result = s.sync(
            self.release, self.live, apply=True, allow_test_root=True)
        self.assertEqual(result["status"],
                         "P8_HOST_PINNED_CODE_APPLIED_NOT_LIVE_WORKER_ATTESTED")
        self.assertEqual(set(result["changed_files"]), set(s.FILES))
        for rel in s.FILES:
            self.assertEqual((self.live / rel).read_bytes(), self.new[rel])
        backup = Path(result["backup_dir"])
        self.assertTrue(backup.is_dir())
        for rel in s.FILES[1:]:
            self.assertEqual(
                (backup / (Path(rel).name + ".previous")).read_bytes(),
                self.originals[rel])
        self.assertEqual((backup / "receipt.json").is_file(), True)
        self.assertEqual((self.live / "runtime" / "do_not_touch.txt").read_text(),
                         "KEEP")
        self.assertEqual(
            (self.live / "src" / "ucie_miner" / "local_only.py").read_text(),
            "# LOCAL OWNED DO NOT TOUCH\n")
        twice = s.sync(
            self.release, self.live, apply=True, allow_test_root=True)
        self.assertEqual(twice["status"], "P8_HOST_ALREADY_PINNED_NO_CHANGE")

    def test_dirty_source_or_local_drift_blocks_all_writes(self):
        local = self.live / s.FILES[1]
        local.write_bytes(b"# local UCIE independent modification\n")
        with self.assertRaisesRegex(s.P8SyncError, "LOCAL_P8_SOURCE_DRIFT"):
            s.sync(self.release, self.live, apply=True, allow_test_root=True)
        self.assertEqual(local.read_bytes(),
                         b"# local UCIE independent modification\n")
        self.assertFalse((self.live / "runtime" /
                          "p8_pinned_sync_backups").exists())
        local.write_bytes(self.originals[s.FILES[1]])
        (self.release / s.FILES[1]).write_bytes(b"# edited release checkout\n")
        with self.assertRaisesRegex(s.P8SyncError, "dirty"):
            s.sync(self.release, self.live, allow_test_root=True)
        self.assertFalse((self.live / s.FILES[0]).exists())

    def test_active_worker_blocks_change_no_partial_install(self):
        db = self.live / "runtime" / "ucie_internal_pending_queue_v1.sqlite3"
        with closing(sqlite3.connect(db)) as conn:
            conn.execute("INSERT INTO jobs(status) VALUES('RUNNING')")
            conn.commit()
        with self.assertRaisesRegex(s.P8SyncError, "RUNNING_JOBS"):
            s.sync(self.release, self.live, apply=True, allow_test_root=True)
        self.assertFalse((self.live / s.FILES[0]).exists())
        self.assertEqual((self.live / s.FILES[2]).read_bytes(),
                         self.originals[s.FILES[2]])
        self.assertFalse((self.live / "runtime" /
                          "p8_pinned_sync_backups").exists())

    def test_install_failure_uses_backups_and_rolls_back_exact_originals(self):
        original = s.os.replace
        count = [0]
        def broken_second(*args, **kwargs):
            count[0] += 1
            if count[0] == 2:
                raise OSError("synthetic failure on second file")
            return original(*args, **kwargs)
        with patch.object(s.os, "replace", side_effect=broken_second):
            with self.assertRaises(OSError):
                s.sync(self.release, self.live, apply=True,
                       allow_test_root=True)
        self.assertFalse((self.live / s.FILES[0]).exists())
        for rel in s.FILES[1:]:
            self.assertEqual((self.live / rel).read_bytes(), self.originals[rel])
        self.assertEqual((self.live / "runtime" / "do_not_touch.txt").read_text(),
                         "KEEP")

    def test_real_windows_autocrlf_clean_checkout_and_local_baseline(self):
        # Git blob at PIN/BASE remains LF, despite a clean Windows checkout
        # with materialized CRLF source files. Treat only EOL as equivalent.
        self.run_git("config", "core.autocrlf", "true")
        for rel in s.FILES:
            (self.release / rel).write_bytes(
                self.new[rel].replace(b"\n", b"\r\n"))
        for rel in s.FILES[1:]:
            (self.live / rel).write_bytes(
                self.originals[rel].replace(b"\n", b"\r\n"))
        # Refresh only the synthetic test Git index after changing the
        # checkout's core.autocrlf setting. Git can report an M until the
        # index stat cache is refreshed even if the canonical blob is equal.
        self.run_git("add", "-u")
        self.assertEqual(
            self.run_git("diff", "--cached", "--name-only"), b"")
        self.assertEqual(
            self.run_git("status", "--porcelain", "--untracked-files=all"),
            b"")
        check = s.sync(self.release, self.live, allow_test_root=True)
        self.assertEqual(check["files_needing_update"], 3)
        self.assertTrue(check["source_worktree_crlf_normalization_allowed"])
        applied = s.sync(
            self.release, self.live, apply=True, allow_test_root=True)
        self.assertEqual(applied["status"],
                         "P8_HOST_PINNED_CODE_APPLIED_NOT_LIVE_WORKER_ATTESTED")
        self.assertEqual(len(applied["changed_files"]), 3)
        for rel in s.FILES:
            self.assertEqual((self.live / rel).read_bytes(), self.new[rel])
        for rel in s.FILES[1:]:
            backup = (Path(applied["backup_dir"]) /
                      (Path(rel).name + ".previous"))
            self.assertEqual(
                backup.read_bytes(),
                self.originals[rel].replace(b"\n", b"\r\n"))
        self.assertEqual(
            s.sync(self.release, self.live, allow_test_root=True)[
                "files_needing_update"], 0)

    def test_already_current_crlf_only_is_not_rewritten(self):
        self.run_git("config", "core.autocrlf", "true")
        for rel in s.FILES:
            source_bytes = self.new[rel].replace(b"\n", b"\r\n")
            (self.release / rel).write_bytes(source_bytes)
            (self.live / rel).write_bytes(source_bytes)
        self.run_git("add", "-u")
        self.assertEqual(
            self.run_git("diff", "--cached", "--name-only"), b"")
        self.assertEqual(
            self.run_git("status", "--porcelain", "--untracked-files=all"),
            b"")
        report = s.sync(
            self.release, self.live, apply=True, allow_test_root=True)
        self.assertEqual(report["status"], "P8_HOST_ALREADY_PINNED_NO_CHANGE")
        self.assertEqual(len(report["only_eol_equivalent_local_files_preserved"]), 3)
        for rel in s.FILES:
            self.assertEqual(
                (self.live / rel).read_bytes(),
                self.new[rel].replace(b"\n", b"\r\n"))
        self.assertFalse(
            (self.live / "runtime" / "p8_pinned_sync_backups").exists())

    def test_non_eol_change_in_clean_source_commit_still_blocks(self):
        rel = s.FILES[1]
        (self.release / rel).write_bytes(b"# different committed module\n")
        self.run_git("add", ".")
        self.run_git("-c", "user.email=test@ucie.local",
                     "-c", "user.name=UCIE Test",
                     "commit", "-m", "unrelated later source modification")
        self.assertEqual(
            self.run_git("status", "--porcelain", "--untracked-files=all"),
            b"")
        with self.assertRaisesRegex(
                s.P8SyncError, "source at pinned PR differs from checkout"):
            s.sync(self.release, self.live, allow_test_root=True)
        self.assertFalse(
            (self.live / "runtime" / "p8_pinned_sync_backups").exists())

    def test_line_endings_only_never_authorize_byte_changes(self):
        for actual, pinned, expected in (
            (b"a\r\nb\r\n", b"a\nb\n", True),
            (b"a\nb\n", b"a\nb\n", True),
            (b"a\rb", b"a\nb", False),
            (b"a\r\nb changed\n", b"a\nb\n", False),
            (b"a\x00b", b"a\x00b", False),
            (None, b"a\nb", False),
        ):
            with self.subTest(actual=actual):
                self.assertEqual(
                    s._same_python_source(actual, pinned), expected)

    def test_other_project_names_are_never_accepted(self):
        other = self.live.parent / "NOT_UCIE"
        (other / "runtime").mkdir(parents=True)
        with self.assertRaisesRegex(s.P8SyncError, "isolated UCIE"):
            s.plan(self.release, other, allow_test_root=True)
        self.assertFalse((other / "src").exists())


if __name__ == "__main__":
    unittest.main()
