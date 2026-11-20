"""UCIE-only layout/cleanup inventory: disposable Git repo, no owner writes."""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import layout_audit_v01 as layout


class UCIELightweightLayoutReadOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_LAYOUT_ONLY_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "UCIE"
        self.root.mkdir()
        self._git("init", "-q")
        self._git("config", "user.email", "ucie-layout@invalid.example")
        self._git("config", "user.name", "Synthetic UCIE Layout")
        self._git("config", "core.autocrlf", "false")
        (self.root / "scripts").mkdir()
        (self.root / "src" / "ucie_miner").mkdir(parents=True)
        (self.root / "tests").mkdir()
        (self.root / ".github" / "workflows").mkdir(parents=True)
        (self.root / "runtime").mkdir()
        (self.root / ".venv").mkdir()
        (self.root / ".ucie_bridge_state").mkdir()
        (self.root / ".gitignore").write_text(
            "/runtime/\n/.venv/\n/.ucie_bridge_state/\n__pycache__/\n",
            encoding="utf-8")
        (self.root / "scripts" / "live.ps1").write_text(
            "$root='D:\\UCIE'\n$cfg='D:\\UCIE_DATA\\mcp_tunnel_profiles'\n"
            "$admin='D:\\UCIE_PREVIEW\\UCIE_ADMIN'\n", encoding="utf-8")
        (self.root / "src" / "ucie_miner" / "engine.py").write_text(
            "def main():\n    return 'UCIE'\n", encoding="utf-8")
        (self.root / "tests" / "test_layout_ref.py").write_text(
            "OLD_UCIE_PATH = r'D:\\UCIE'\n", encoding="utf-8")
        (self.root / "runtime" / "public_miner.sqlite3").write_bytes(
            b"UCIE-only protected fake database bytes")
        (self.root / "runtime" / "stage10_hourly_opt_in.txt").write_bytes(
            b"synthetic owner opt-in\n")
        (self.root / ".ucie_bridge_state" / "health.json").write_bytes(
            b'{"UCIE_only":"private-state"}')
        (self.root / ".venv" / "python.exe").write_bytes(
            b"private synthetic virtualenv")
        self._git("add", "--", ".gitignore", "scripts/live.ps1",
                  "src/ucie_miner/engine.py", "tests/test_layout_ref.py")
        self._git("commit", "-qm", "UCIE-only original receipt")
        self.original = self._git("rev-parse", "HEAD").strip()
        self.protected = {
            rel: sha256((self.root / rel).read_bytes()).hexdigest()
            for rel in ("runtime/public_miner.sqlite3",
                        "runtime/stage10_hourly_opt_in.txt",
                        ".ucie_bridge_state/health.json",
                        ".venv/python.exe")
        }

    def _git(self, *args: str) -> bytes:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=15).stdout

    def _assert_state_unchanged(self):
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.original)
        for rel, digest in self.protected.items():
            self.assertEqual(
                sha256((self.root / rel).read_bytes()).hexdigest(), digest)
        self.assertFalse((self.root / "UCIE_PROJECT").exists())

    def test_01_clean_synthetic_repo_stays_no_go_for_live_move(self):
        r = layout.inspect_ucie_layout(self.root)
        self.assertEqual(r["schema"], layout.SCHEMA)
        self.assertIn("MIGRATION_BLOCKED", r["status"])
        self.assertTrue(r["git"]["working_tree_clean_certified"])
        self.assertFalse(r["path_dependencies"]["safe_to_move_live_root"])
        self.assertFalse(r["owner_runtime_moved"])
        self.assertEqual(r["operating_db_writes"], 0)
        self.assertFalse(r["cache"]["cache_removed_or_quarantined"])
        self._assert_state_unchanged()

    def test_02_scan_records_only_exact_ucie_path_dependencies(self):
        r = layout.inspect_ucie_layout(self.root)
        refs = r["path_dependencies"]
        self.assertEqual(refs["literal_path_reference_counts"], {
            "live_root": 2, "data_root": 1, "preview_root": 1})
        self.assertEqual(
            refs["affected_ucie_source_files"]["live_root"],
            ["scripts/live.ps1", "tests/test_layout_ref.py"])
        self.assertFalse(r["other_drive_roots_or_projects_scanned"])
        self.assertFalse(r["ucie_data_or_preview_presence_verified"])

    def test_03_real_git_status_detects_modified_and_untracked(self):
        (self.root / "scripts" / "live.ps1").write_text(
            "# UCIE modified synthetic script\n", encoding="utf-8")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "untracked-important.md").write_text(
            "important source evidence", encoding="utf-8")
        r = layout.inspect_ucie_layout(self.root)
        self.assertEqual(r["git"]["tracked_changed_records"], 1)
        self.assertEqual(r["git"]["untracked_records"], 1)
        self.assertFalse(r["git"]["working_tree_clean_certified"])
        self.assertEqual(r["git"]["counts_by_ucie_subdir"], {
            "docs": 1, "scripts": 1})
        self.assertTrue((self.root / "docs" / "untracked-important.md").exists())
        self._assert_state_unchanged()

    def test_04_fast_git_does_not_misreport_clean_if_untracked_skipped(self):
        (self.root / "docs").mkdir()
        (self.root / "docs" / "untracked-important.md").write_text("KEEP")
        r = layout.inspect_ucie_layout(self.root, fast_git=True)
        self.assertEqual(r["git"]["mode"], "FAST_TRACKED_ONLY")
        self.assertIsNone(r["git"]["untracked_records"])
        self.assertTrue(r["git"]["untracked_scan_skipped"])
        self.assertFalse(r["git"]["working_tree_clean_certified"])
        self._assert_state_unchanged()

    def test_05_real_git_full_mode_does_not_delete_untracked_evidence(self):
        d = self.root / "docs"
        d.mkdir()
        precious = d / "signed_approval_unverified.md"
        precious.write_bytes(b"owner review draft DO NOT DELETE")
        layout.inspect_ucie_layout(self.root)
        self.assertEqual(precious.read_bytes(), b"owner review draft DO NOT DELETE")
        self._assert_state_unchanged()

    def test_06_cache_candidate_is_only_inventory_not_quarantined(self):
        cache = self.root / "tests" / "__pycache__"
        cache.mkdir()
        (cache / "synthetic.pyc").write_bytes(b"123456789")
        result = layout.inspect_ucie_layout(self.root)
        rows = result["cache"]["read_only_cache_candidates"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["ucie_relative_path"], "tests/__pycache__")
        self.assertEqual(rows[0]["estimated_bytes"], 9)
        self.assertEqual(rows[0]["file_count"], 1)
        self.assertFalse(rows[0]["approved_for_deletion"])
        self.assertEqual((cache / "synthetic.pyc").read_bytes(), b"123456789")
        self._assert_state_unchanged()

    def test_07_does_not_count_runtime_or_private_files_as_cache(self):
        result = layout.inspect_ucie_layout(self.root)
        self.assertEqual(result["cache"]["cache_files_observed"], 0)
        self.assertEqual(result["cache"]["cache_bytes_observed"], 0)
        self.assertFalse(result["operating_sqlite_opened"])
        self._assert_state_unchanged()

    def test_08_wrong_or_nonexistent_git_root_is_denied(self):
        other = Path(self.tmp.name) / "Unrelated"
        other.mkdir()
        with self.assertRaises(layout.LayoutAuditError):
            layout.inspect_ucie_layout(other)
        empty = Path(self.tmp.name) / "Empty" / "UCIE"
        empty.mkdir(parents=True)
        with self.assertRaises(layout.LayoutAuditError):
            layout.inspect_ucie_layout(empty)

    def test_09_gitdir_file_indirection_denied(self):
        other = Path(self.tmp.name) / "Secondary" / "UCIE"
        other.mkdir(parents=True)
        (other / ".git").write_text(
            "gitdir: ../../UCIE/.git\n", encoding="utf-8")
        with self.assertRaises(layout.LayoutAuditError):
            layout.inspect_ucie_layout(other)

    def test_10_indirected_runtime_denied_if_symlink_allowed(self):
        target = Path(self.tmp.name) / "external-ucie-synthetic-runtime"
        target.mkdir()
        path = self.root / "runtime"
        try:
            path.rename(self.root / "old_runtime")
            path.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink privilege unavailable in runner")
        with self.assertRaises(layout.LayoutAuditError):
            layout.inspect_ucie_layout(self.root)

    def test_11_symlinked_root_denied_if_supported(self):
        alias = Path(self.tmp.name) / "aliases" / "UCIE"
        alias.parent.mkdir()
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink privilege unavailable in runner")
        with self.assertRaises(layout.LayoutAuditError):
            layout.inspect_ucie_layout(alias)

    def test_12_source_scan_symlink_denied_if_supported(self):
        symlink = self.root / "scripts" / "leak.ps1"
        target = Path(self.tmp.name) / "do-not-read-external.txt"
        target.write_text("D:\\UCIE_DATA\\PRIVATE", encoding="utf-8")
        try:
            symlink.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink privilege unavailable in runner")
        result = layout.inspect_ucie_layout(self.root)
        self.assertTrue(result["path_dependencies"]["source_scan_truncated_or_unreadable"])
        self.assertEqual(result["path_dependencies"]["literal_path_reference_counts"]["data_root"], 1)

    def test_13_git_environment_redirection_ignored(self):
        poison = {
            "GIT_DIR": str(Path(self.tmp.name) / "foreign_git"),
            "GIT_WORK_TREE": str(Path(self.tmp.name) / "foreign_worktree"),
            "GIT_INDEX_FILE": str(Path(self.tmp.name) / "foreign_index"),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.worktree",
            "GIT_CONFIG_VALUE_0": str(Path(self.tmp.name) / "foreign_worktree"),
        }
        with patch.dict(os.environ, poison):
            result = layout.inspect_ucie_layout(self.root)
        self.assertTrue(result["git"]["working_tree_clean_certified"])
        self._assert_state_unchanged()

    def test_14_nonbool_fast_flag_denied(self):
        for bad in (1, 0, None, "True", [], {}):
            with self.subTest(flag=bad):
                with self.assertRaises(layout.LayoutAuditError):
                    layout.inspect_ucie_layout(self.root, fast_git=bad)

    def test_15_invalid_source_directory_symlink_denied(self):
        other = self.root / "scripts"
        other.rename(self.root / "scripts_backup")
        target = Path(self.tmp.name) / "foreign-scripts"
        target.mkdir()
        try:
            other.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Windows symlink privilege unavailable in runner")
        with self.assertRaises(layout.LayoutAuditError):
            layout.inspect_ucie_layout(self.root)

    def test_16_no_git_gc_prune_reset_clean_checkout_or_mutation(self):
        with patch.object(layout.subprocess, "run",
                          wraps=subprocess.run) as call:
            layout.inspect_ucie_layout(self.root)
        calls = [c.args[0] for c in call.call_args_list]
        self.assertEqual(len(calls), 1)
        args = calls[0]
        self.assertIn("status", args)
        self.assertIn("--no-optional-locks", args)
        self.assertFalse(any(x in args for x in (
            "gc", "prune", "reset", "clean", "checkout", "fetch", "pull", "push")))
        self._assert_state_unchanged()

    def test_17_protected_bridge_state_not_added_to_git(self):
        # Exact UCIE-only .gitignore protection, never source file blanket ignore.
        ignored = self._git("check-ignore", ".ucie_bridge_state/health.json").strip()
        self.assertEqual(ignored.decode("utf-8"), ".ucie_bridge_state/health.json")
        r = layout.inspect_ucie_layout(self.root)
        self.assertEqual(r["git"]["untracked_records"], 0)
        self.assertFalse(r["cache"]["cache_removed_or_quarantined"])


    def test_18_full_git_status_counts_each_untracked_file_not_just_parent(self):
        # This reproduces the owner 210-untracked census failure: Git's
        # default --untracked-files=normal collapses nested paths to folders.
        d = self.root / "docs" / "historical"
        d.mkdir(parents=True)
        for number in range(11):
            (d / f"ucie_review_{number:02d}.md").write_text(
                f"UCIE-only synthetic historical metadata {number}", encoding="utf-8"
            )
        (self.root / "source-review.todo").write_text("UCIE synthetic root item")
        r = layout.inspect_ucie_layout(self.root)
        self.assertEqual(r["git"]["untracked_records"], 12)
        self.assertEqual(r["git"]["counts_by_ucie_subdir"]["docs"], 11)
        self.assertEqual(
            r["git"]["counts_by_ucie_subdir"]["_ROOT_LEVEL_REVIEW_REQUIRED_"], 1)
        self.assertNotIn("source-review.todo",
                         str(r["git"]["counts_by_ucie_subdir"]))
        with patch.object(layout.subprocess, "run",
                          wraps=subprocess.run) as subprocess_call:
            layout.inspect_ucie_layout(self.root)
        self.assertEqual(subprocess_call.call_count, 1)
        cmd = subprocess_call.call_args.args[0]
        self.assertIn("--untracked-files=all", cmd)
        self.assertNotIn("--untracked-files=normal", cmd)
        self._assert_state_unchanged()

    def test_19_staged_observer_requires_exact_windows_source_root(self):
        src = Path(r"D:\UCIE_PROJECT\UCIE")
        layout._require_staged_observer(src, platform="nt")
        for root, platform in (
            (Path(r"D:\UCIE"), "nt"),
            (Path(r"D:\UCIE_PROJECT\UCIE"), "posix"),
            (Path(r"D:\UCIE_PROJECT\other"), "nt"),
            (Path(r"E:\UCIE_PROJECT\UCIE"), "nt"),
        ):
            with self.subTest(root=str(root), platform=platform):
                with self.assertRaises(layout.LayoutAuditError):
                    layout._require_staged_observer(root, platform=platform)
        with self.assertRaises(layout.LayoutAuditError):
            layout.inspect_original_ucie_git_from_stage(
                self.root, self.root, platform="posix")

    def test_20_original_dirty_census_from_independent_synthetic_staged_repo(self):
        # The actual CLI hardcodes the two owner Windows paths. Exercise the
        # same metadata-only internal engine on TWO disposable UCIE roots.
        stage = Path(self.tmp.name) / "UCIE_PROJECT" / "UCIE"
        stage.mkdir(parents=True)
        subprocess.run(["git", "-C", str(stage), "init", "-q"],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        historical = self.root / "docs" / "review"
        historical.mkdir(parents=True)
        for index in range(5):
            (historical / f"important_{index}.md").write_text(
                "UCIE synthetic review draft", encoding="utf-8")
        with patch.object(layout.subprocess, "run", wraps=subprocess.run) as observe:
            record = layout._original_git_report(stage, self.root)
        self.assertEqual(observe.call_count, 1)
        self.assertEqual(record["schema"],
                         "UCIE_ORIGINAL_GIT_EXACT_INVENTORY_READONLY_V01")
        self.assertEqual(record["git"]["untracked_records"], 5)
        self.assertEqual(record["git"]["counts_by_ucie_subdir"]["docs"], 5)
        self.assertTrue(record["untracked_individual_files_enumerated"])
        for protected in (
            "original_source_code_imported_or_executed",
            "original_file_contents_exposed_in_report", "operating_database_opened",
            "other_drive_roots_or_projects_scanned", "git_index_or_history_modified",
            "original_owner_files_moved_or_deleted", "task_or_tunnel_modified",
            "archive_backup_performed", "cleanup_approval_granted",
            "full_cutover_authorized",
        ):
            self.assertIs(record[protected], False, protected)
        self.assertEqual(self._git("rev-parse", "HEAD").strip(), self.original)
        self._assert_state_unchanged()

    def test_21_never_confuse_staged_source_with_dirty_original(self):
        with self.assertRaises(layout.LayoutAuditError):
            layout._original_git_report(self.root, self.root)
        other = Path(self.tmp.name) / "OTHER"
        other.mkdir()
        with self.assertRaises(layout.LayoutAuditError):
            layout._original_git_report(self.root, other)


    def test_22_synthetic_original_and_stage_path_overlap_is_not_byte_equality(self):
        # Two disposable first-party-only Git repos, no owner host access.
        stage = Path(self.tmp.name) / "UCIE_PROJECT" / "UCIE"
        stage.mkdir(parents=True)
        subprocess.run(["git", "-C", str(stage), "init", "-q"],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "-C", str(stage), "config", "user.email",
                        "ucie-path-overlap@invalid.example"], check=True)
        subprocess.run(["git", "-C", str(stage), "config", "user.name",
                        "Synthetic UCIE Path Audit"], check=True)
        (stage / "docs").mkdir()
        (stage / "scripts").mkdir()
        (stage / "docs" / "same.md").write_text("STAGED CONTENT", encoding="utf-8")
        (stage / "scripts" / "live.ps1").write_text("STAGED", encoding="utf-8")
        (stage / "scripts" / "same.ps1").write_text("STAGED", encoding="utf-8")
        subprocess.run(["git", "-C", str(stage), "add", "--", "."], check=True)
        subprocess.run(["git", "-C", str(stage), "commit", "-qm",
                        "Synthetic stage commit"], check=True)

        # Original has the SAME names but DIFFERENT content, plus old-only
        # files; no claim of duplicate bytes may be made from name overlap.
        (self.root / "docs").mkdir()
        (self.root / "docs" / "same.md").write_text(
            "DIFFERENT ORIGINAL CONTENT", encoding="utf-8")
        (self.root / "docs" / "original_only.md").write_text(
            "OWNER UCIE historical evidence", encoding="utf-8")
        (self.root / "scripts" / "same.ps1").write_text(
            "DIFFERENT OWNER CODE", encoding="utf-8")
        (self.root / "scripts" / "live.ps1").write_text(
            "EXISTING ORIGINAL TRACKED MODIFICATION", encoding="utf-8")
        (self.root / "tests" / "only_original.py").write_text(
            "UCIE-only test", encoding="utf-8")
        (self.root / "RootUnknownArtifact").write_text("opaque", encoding="utf-8")
        # A legacy original ignore rule can differ from the clean canonical
        # staged ignore policy; count bridge state only, never inspect it.
        (self.root / ".gitignore").write_text(
            "/runtime/\n/.venv/\n__pycache__/\n", encoding="utf-8")

        from unittest.mock import patch
        with patch.object(Path, "read_bytes", side_effect=AssertionError(
                "original files must not be read by Python")), patch.object(
                    Path, "read_text", side_effect=AssertionError(
                        "original files must not be read by Python")):
            result = layout._stage_original_path_crosswalk(stage, self.root)
        self.assertEqual(
            result["schema"], "UCIE_ORIGINAL_STAGE_PATH_OVERLAP_READONLY_V01")
        self.assertEqual(result["original_untracked_records"], 6)
        self.assertEqual(result["original_tracked_modified_records"], 2)
        self.assertEqual(result["original_status_total"], 8)
        self.assertEqual(result["protected_bridge_records_not_compared"], 1)
        self.assertEqual(result["unclassified_root_or_other_records"], 2)
        self.assertEqual(result["review_area_records_compared"], 5)
        self.assertEqual(result["by_review_area"]["docs"], {
            "original_untracked": 2, "original_tracked_changed": 0,
            "same_relative_path_in_stage_tracked": 1,
            "not_tracked_in_stage": 1,
        })
        self.assertEqual(result["by_review_area"]["scripts"], {
            "original_untracked": 1, "original_tracked_changed": 1,
            "same_relative_path_in_stage_tracked": 2,
            "not_tracked_in_stage": 0,
        })
        self.assertEqual(result["by_review_area"]["tests"], {
            "original_untracked": 1, "original_tracked_changed": 0,
            "same_relative_path_in_stage_tracked": 0,
            "not_tracked_in_stage": 1,
        })
        self.assertIsNone(result["byte_duplicate_count_verified"])
        for field in (
            "path_overlap_proves_identical_file_bytes",
            "file_content_hashes_read", "raw_file_paths_or_contents_returned",
            "operating_database_opened", "files_moved_or_deleted",
            "git_index_or_history_modified", "task_or_tunnel_modified",
            "cleanup_approved", "full_cutover_authorized",
        ):
            self.assertIs(result[field], False, field)
        self._assert_state_unchanged()

    def test_23_git_crosswalk_rejects_path_escape_duplicates_and_rename(self):
        for raw in (
            b"../outside", b"/outside", b"C:/foreign", b"docs//unsafe.md",
            b"docs/../outside", b"docs/./unsafe", b"docs\\..\\outside",
        ):
            with self.subTest(raw=raw), self.assertRaises(layout.LayoutAuditError):
                layout._safe_repo_relative(raw)
        for raw in (
            b"?? docs/ok.md",  # Missing NUL terminator.
            b"R  scripts/new.ps1\0scripts/old.ps1\0",
            b"!! docs/ignored.md\0",
            b"?? docs/X.md\0?? docs/x.md\0",  # Case collision.
            b"?? ../escape\0",
        ):
            with self.subTest(status=raw), self.assertRaises(
                    layout.LayoutAuditError):
                layout._parse_original_status_paths(raw)
        with self.assertRaises(layout.LayoutAuditError):
            layout._parse_tracked_git_paths(
                b"scripts/X.py\0scripts/x.py\0")
        self.assertEqual(layout._parse_original_status_paths(b""), [])

    def test_24_real_owner_crosswalk_is_denied_outside_exact_staged_windows(self):
        with self.assertRaises(layout.LayoutAuditError):
            layout.compare_original_ucie_git_to_stage(
                self.root, self.root, platform="posix")
        with self.assertRaises(layout.LayoutAuditError):
            layout.compare_original_ucie_git_to_stage(
                self.root, self.root, platform="nt")
        # The source root may be correct syntactically, but target is always
        # the *exact* original UCIE checkout, not an arbitrary project.
        with self.assertRaises(layout.LayoutAuditError):
            layout.compare_original_ucie_git_to_stage(
                Path(r"D:\UCIE_PROJECT\UCIE"), Path(r"D:\FOREIGN\UCIE"),
                platform="nt")


    def test_25_crosswalk_git_stage_failure_reports_fixed_sanitized_phase(self):
        stage = Path(self.tmp.name) / "Staged" / "UCIE"
        stage.mkdir(parents=True)
        subprocess.run(["git", "-C", str(stage), "init", "-q"],
                       check=True, capture_output=True)
        with patch.object(layout, "_git_metadata_bytes", side_effect=
                          layout.LayoutAuditError("PRIVATE path is never exported")):
            with self.assertRaises(layout.LayoutAuditPhaseError) as caught:
                layout._stage_original_path_crosswalk(stage, self.root)
        self.assertEqual(caught.exception.phase, "STAGED_TRACKED_QUERY")
        self.assertNotIn("PRIVATE", str(caught.exception))
        self._assert_state_unchanged()

    def test_26_original_host_malformed_status_has_no_raw_path_in_phase(self):
        stage = Path(self.tmp.name) / "Staged" / "UCIE"
        stage.mkdir(parents=True)
        subprocess.run(["git", "-C", str(stage), "init", "-q"],
                       check=True, capture_output=True)
        emitted = [
            b"docs/readme.md\0",
            b"?? ../SECRET_private_path_not_to_be_returned\0",
        ]
        with patch.object(layout, "_git_metadata_bytes", side_effect=emitted):
            with self.assertRaises(layout.LayoutAuditPhaseError) as caught:
                layout._stage_original_path_crosswalk(stage, self.root)
        self.assertEqual(caught.exception.phase, "ORIGINAL_STATUS_PARSE")
        self.assertNotIn("SECRET", str(caught.exception))
        self._assert_state_unchanged()

    def test_27_owner_fail_closed_phase_never_claims_cleanup_or_success(self):
        from unittest.mock import patch as mock_patch
        stage = Path(self.tmp.name) / "Staged" / "UCIE"
        stage.mkdir(parents=True)
        subprocess.run(["git", "-C", str(stage), "init", "-q"],
                       check=True, capture_output=True)
        with mock_patch.object(layout, "_git_metadata_bytes",
                               side_effect=layout.LayoutAuditError("foreign details")):
            with self.assertRaises(layout.LayoutAuditPhaseError) as caught:
                layout._stage_original_path_crosswalk(stage, self.root)
        self.assertIn(caught.exception.phase, (
            "STAGED_ROOT", "STAGED_TRACKED_QUERY",
        ))
        self.assertTrue(issubclass(layout.LayoutAuditPhaseError, layout.LayoutAuditError))
        self.assertEqual(layout.CROSSWALK_FAILURE_SCHEMA,
                         "UCIE_ORIGINAL_STAGE_PATH_OVERLAP_DIAGNOSTIC_V01")
        self._assert_state_unchanged()


if __name__ == "__main__":
    unittest.main()
