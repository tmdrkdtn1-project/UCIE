"""Tests for UCIE-only Git intake: no add, commit, content read or export."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from ucie_miner.ucie_git_baseline_v01 import (
    BaselineError,
    classify_untracked,
    parse_porcelain_v1_z,
    scan_ucie_repo,
    summarize,
)


class UCIEGitBaselineTests(unittest.TestCase):
    def test_parse_untracked_and_modified(self):
        rows = parse_porcelain_v1_z(
            b" M src/ucie_miner/core.py\0"
            b"?? docs/UCIE_REPORT.md\0"
            b"?? .ucie_bridge_state/data.json\0"
        )
        self.assertEqual(rows[0], (" M", "src/ucie_miner/core.py"))
        self.assertEqual(len(rows), 3)

    def test_rename_uses_exact_extra_nul_field(self):
        rows = parse_porcelain_v1_z(b"R  scripts/new name.py\0scripts/old name.py\0")
        self.assertEqual(rows, [("R ", "scripts/new name.py")])

    def test_rename_missing_origin_fails_closed(self):
        with self.assertRaisesRegex(BaselineError, "MISSING_RENAME"):
            parse_porcelain_v1_z(b"R  scripts/new.py\0")

    def test_truncated_data_fails_closed(self):
        with self.assertRaisesRegex(BaselineError, "TRUNCATED_STATUS"):
            parse_porcelain_v1_z(b"?? docs/new.md")

    def test_rejects_traversal_and_absolute(self):
        for value in (b"?? ../escape.py\0", b"?? C:/outside.py\0",
                      b"?? /root/outside\0", b"?? tests//double.py\0"):
            with self.subTest(value=value):
                with self.assertRaises(BaselineError):
                    parse_porcelain_v1_z(value)

    def test_rejects_oversize(self):
        with self.assertRaisesRegex(BaselineError, "OVERSIZED"):
            parse_porcelain_v1_z(b"x" * (8 * 1024 * 1024 + 1))

    def test_sensitive_and_runtime_paths_are_held(self):
        for name in (
            ".ucie_bridge_state/audit.json",
            "runtime/public_miner.sqlite3",
            "scripts/task_status.ps1.pre_pr158.bak",
            "docs/private_key.pem",
            ".env.local",
            "src/auth_password.py",
            "tests/credential_fixture.py",
        ):
            with self.subTest(path=name):
                self.assertEqual(classify_untracked(name), "sensitive_or_runtime_hold")

    def test_review_buckets_never_auto_stage(self):
        report = summarize(
            b" M src/ucie_miner/core.py\0"
            b"?? src/ucie_miner/new.py\0"
            b"?? tests/test_new.py\0"
            b"?? scripts/new.ps1\0"
            b"?? docs/new.md\0"
            b"?? .ucie_bridge_state/x\0"
            b"?? unknown.bin\0"
        )
        self.assertEqual(report["tracked_changes"], 1)
        self.assertEqual(report["untracked_total"], 6)
        self.assertEqual(report["staged_changes"], 0)
        self.assertEqual(sum(report["untracked_categories"].values()), 6)
        for key in ("auto_stage", "production_release_allowed", "file_contents_read"):
            self.assertFalse(report[key])
        self.assertEqual(report["git_mutations"], 0)
        rendered = json.dumps(report)
        for secret in ("unknown.bin", ".ucie_bridge_state", "core.py"):
            self.assertNotIn(secret, rendered)

    def test_fails_if_target_is_not_ucie_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(BaselineError, "UCIE_ROOT_NOT_VERIFIED"):
                scan_ucie_repo(Path(tmp))

    def test_fixed_git_command_and_readonly_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "UCIE"
            (root / ".git").mkdir(parents=True)
            completed = mock.Mock(returncode=0, stdout=b"?? docs/new.md\0", stderr=b"")
            with mock.patch(
                "ucie_miner.ucie_git_baseline_v01.subprocess.run", return_value=completed
            ) as call:
                result = scan_ucie_repo(root)
            args, kwargs = call.call_args
            self.assertEqual(args[0][0], "git")
            self.assertIn("--porcelain=v1", args[0])
            self.assertIn("-z", args[0])
            self.assertIn("--untracked-files=all", args[0])
            self.assertNotIn("add", args[0])
            self.assertNotIn("commit", args[0])
            self.assertNotIn("push", args[0])
            self.assertFalse(kwargs.get("shell", False))
            self.assertEqual(kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
            self.assertEqual(result["untracked_total"], 1)

    @unittest.skipUnless(shutil.which("git"), "Git missing from owner host")
    def test_owner_repo_readonly_worktree_counts(self):
        root = Path(__file__).resolve().parents[1]
        if root.name.casefold() != "ucie" or not (root / ".git").exists():
            self.skipTest("UCIE working tree not mounted")
        result = scan_ucie_repo(root)
        self.assertEqual(result["status"], "UCIE_GIT_BASELINE_REVIEW_ONLY")
        self.assertEqual(result["git_mutations"], 0)
        self.assertFalse(result["auto_stage"])
        self.assertEqual(
            result["untracked_total"],
            sum(result["untracked_categories"].values())
        )
        self.assertEqual(len(result["status_fingerprint_sha256"]), 64)
        print("UCIE_GIT_BASELINE_LIVE_READONLY=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
