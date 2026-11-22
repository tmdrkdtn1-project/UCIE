"""UCIE-only layout/cleanup inventory: disposable Git repo, no owner writes."""
from __future__ import annotations

from collections import Counter
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



    def test_28_strict_stage_crlf_only_is_verified_not_blindly_ignored(self):
        target = self.root / "src" / "ucie_miner" / "engine.py"
        original = target.read_bytes()
        self.assertIn(b"\n", original)
        # write_text() creates CRLF on Windows and LF on Linux.
        # Flip exactly one CR-at-EOL representation, never create CRCRLF.
        alternate_eol = (
            original.replace(b"\r\n", b"\n")
            if b"\r\n" in original
            else original.replace(b"\n", b"\r\n")
        )
        self.assertNotEqual(original, alternate_eol)
        target.write_bytes(alternate_eol)
        args = ("status", "--porcelain=v1", "-z", "--untracked-files=all")
        strict = layout._git_metadata_bytes(self.root, *args)
        self.assertTrue(strict.startswith(b" M "))
        self.assertTrue(layout._verified_crlf_only_staged_worktree(self.root, strict))

        self._git("branch", "-M", "main")
        self._git("remote", "add", "origin",
                  "https://github.com/tmdrkdtn1-project/UCIE.git")
        result_stub = {"schema": "SYNTHETIC_UCIE_STAGE_CROSSWALK"}
        with patch.object(layout, "_require_staged_observer"), patch.object(
                layout, "_stage_original_path_crosswalk",
                return_value=result_stub.copy()) as crosswalk:
            report = layout.compare_original_ucie_git_to_stage(
                self.root, Path(r"D:\UCIE"), platform="nt")
        self.assertTrue(report["stage_crlf_only_difference_verified"])
        crosswalk.assert_called_once_with(
            self.root.resolve(strict=True), Path(r"D:\UCIE"))
        self._assert_state_unchanged()

    def test_29_stage_content_index_and_untracked_changes_stay_blocked(self):
        target = self.root / "src" / "ucie_miner" / "engine.py"
        original = target.read_bytes()
        args = ("status", "--porcelain=v1", "-z", "--untracked-files=all")
        alternate_eol = (
            original.replace(b"\r\n", b"\n")
            if b"\r\n" in original
            else original.replace(b"\n", b"\r\n")
        )
        self.assertNotEqual(original, alternate_eol)
        target.write_bytes(alternate_eol)
        self.assertTrue(layout._verified_crlf_only_staged_worktree(
            self.root, layout._git_metadata_bytes(self.root, *args)))

        target.write_bytes(b"def main():\r\n    return 'CHANGED'\r\n")
        self.assertFalse(layout._verified_crlf_only_staged_worktree(
            self.root, layout._git_metadata_bytes(self.root, *args)))

        target.write_bytes(alternate_eol)
        extra = self.root / "docs" / "not-yet-tracked.md"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_bytes(b"NOT A DISPOSABLE CACHE")
        self.assertFalse(layout._verified_crlf_only_staged_worktree(
            self.root, layout._git_metadata_bytes(self.root, *args)))
        extra.unlink()

        target.write_bytes(b"def main():\n    return 'INDEX MODIFIED'\n")
        self._git("add", "--", "src/ucie_miner/engine.py")
        self.assertFalse(layout._verified_crlf_only_staged_worktree(
            self.root, layout._git_metadata_bytes(self.root, *args)))
        self._assert_state_unchanged()

    def test_30_stage_crlf_recheck_rejects_end_of_line_spaces(self):
        target = self.root / "src" / "ucie_miner" / "engine.py"
        original = target.read_bytes()
        target.write_bytes(
            original.replace(b"\r\n", b"  \r\n")
            if b"\r\n" in original
            else original.replace(b"\n", b"  \r\n")
        )
        self.assertFalse(layout._verified_crlf_only_staged_worktree(
            self.root, layout._git_metadata_bytes(
                self.root, "status", "--porcelain=v1", "-z",
                "--untracked-files=all")))
        self._assert_state_unchanged()



    def test_31_missing_path_triage_uses_only_fixed_labels_and_metadata(self):
        stage = {
            "src/new_area/old_module.py", "docs/current.md",
            "scripts/launch.ps1", "tests/test_current.py",
        }
        raw = [
            ("untracked", "src/ucie_miner/old_module.py"),
            ("untracked", "src/ucie_miner/secret_name.xyz"),
            ("tracked_changed", "scripts/old.ps1"),
            ("untracked", "tests/test_secret_legacy.py"),
            ("untracked", "docs/owner_history.md"),
            ("untracked", ".github/workflows/private_named.yml"),
            ("untracked", ".github/credentials/hidden.json"),
            ("untracked", ".ucie_bridge_state/secret.token"),
            ("untracked", "ROOT_SECRET"), 
        ]
        r = layout._classify_missing_git_paths(raw, stage)
        self.assertEqual(r["schema"], layout.MISSING_REVIEW_SCHEMA)
        self.assertEqual(r["unmatched_review_paths_total"], 6)
        self.assertEqual(
            r["by_review_area"]["src"]["original_paths_without_staged_relative_match"], 2)
        self.assertEqual(
            r["by_review_area"]["src"]["same_filename_elsewhere_in_stage"], 1)
        self.assertEqual(
            r["by_review_area"]["src"]["suffix_counts"],
            {"other_or_unknown": 1, "python": 1})
        self.assertEqual(
            r["by_review_area"]["scripts"]["original_tracked_changed"], 1)
        self.assertEqual(
            r["by_review_area"][".github"]["suffix_counts"], {"yaml": 1})
        self.assertFalse(r["source_bytes_or_sha256_compared"])
        self.assertFalse(r["raw_original_paths_or_contents_returned"])
        self.assertEqual(r["all_unmatched_records_disposition"],
                         "K0_HOLD_FOR_SOURCE_REVIEW")
        import json
        serialized = json.dumps(r, sort_keys=True)
        for forbidden in ("old_module", "secret", "ROOT_SECRET",
                          ".ucie_bridge_state", "credentials/hidden"):
            self.assertNotIn(forbidden, serialized)
        self._assert_state_unchanged()

    def test_32_missing_path_triage_real_git_never_imports_original_source(self):
        stage = Path(self.tmp.name) / "UCIE_PROJECT" / "UCIE"
        stage.mkdir(parents=True)
        def stage_git(*args):
            subprocess.run(
                ["git", "-C", str(stage), *args],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=15)
        stage_git("init", "-q")
        stage_git("config", "user.email", "ucie-triage@invalid.example")
        stage_git("config", "user.name", "Synthetic UCIE Triage")
        (stage / "scripts").mkdir()
        (stage / "scripts" / "live.ps1").write_text("STAGE ONLY", encoding="utf-8")
        stage_git("add", "--", "scripts/live.ps1")
        stage_git("commit", "-qm", "Synthetic triage index")
        (self.root / "src" / "ucie_miner" / "uncopied.py").write_bytes(
            b"UCIE FIRST PARTY SOURCE; DO NOT EXECUTE")
        (self.root / "scripts" / "uncopied.ps1").write_bytes(
            b"UCIE FIRST PARTY SCRIPT; DO NOT EXECUTE")
        (self.root / "tests" / "test_uncopied.py").write_bytes(
            b"UCIE FIRST PARTY TEST; DO NOT EXECUTE")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "history.md").write_bytes(
            b"UCIE HISTORICAL RECORD; DO NOT DISCARD")

        with patch.object(Path, "read_bytes", side_effect=AssertionError(
                "original source bytes must remain unread")), patch.object(
                    Path, "read_text", side_effect=AssertionError(
                        "original source text must remain unread")):
            result = layout._stage_original_path_crosswalk(
                stage, self.root, classify_unmatched=True)
        review = result["unmatched_path_metadata_review"]
        self.assertEqual(review["unmatched_review_paths_total"], 4)
        self.assertEqual(result["review_area_records_compared"], 4)
        self.assertEqual(
            {key: value["original_paths_without_staged_relative_match"]
             for key, value in review["by_review_area"].items()},
            {"docs": 1, "scripts": 1, "src": 1, "tests": 1})
        self.assertIsNone(result["byte_duplicate_count_verified"])
        self.assertFalse(result["files_moved_or_deleted"])
        self.assertFalse(result["full_cutover_authorized"])
        self._assert_state_unchanged()

    def test_33_missing_path_triage_validation_fails_closed(self):
        with self.assertRaises(layout.LayoutAuditError):
            layout._stage_original_path_crosswalk(
                self.root, self.root, classify_unmatched=1)
        with self.assertRaises(layout.LayoutAuditError):
            layout.compare_original_ucie_git_to_stage(
                self.root, self.root, platform="posix",
                classify_unmatched=True)
        self._assert_state_unchanged()


    def test_34_owner_local_content_review_compares_scoped_code_only(self):
        # Two disposable UCIE Git repos. No original source import,
        # owner host access, network, or file operations beyond test fixtures.
        stage = Path(self.tmp.name) / "UCIE_PROJECT" / "UCIE"
        stage.mkdir(parents=True)
        def sg(*argv):
            return subprocess.run(
                ["git", "-C", str(stage), *argv], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=20).stdout
        sg("init", "-q")
        sg("config", "user.name", "UCIE Synthetic Local Code Review")
        sg("config", "user.email", "ucie-local-content@invalid.example")
        sg("config", "core.autocrlf", "false")
        for folder in ("src/ucie_miner", "scripts", "tests"):
            (stage / folder).mkdir(parents=True, exist_ok=True)
        fixtures = {
            "src/ucie_miner/exact.py": b"def exact():\n    return 7\n",
            "src/ucie_miner/candidate_stage.py": b"def candidate():\n    return 99\n",
            "src/ucie_miner/ast_stage.py": b"import math\nVALUE = 5\n",
            "scripts/same.ps1": b"Write-Output 5\n",
            "scripts/live.ps1": b"STAGED VERSION\n",
        }
        for path, body in fixtures.items():
            (stage / path).write_bytes(body)
        sg("add", "--", ".")
        sg("commit", "-qm", "UCIE disposable stage")

        (self.root / "src" / "ucie_miner" / "exact.py").write_bytes(
            fixtures["src/ucie_miner/exact.py"])
        (self.root / "src" / "ucie_miner" / "candidate_original.py").write_bytes(
            fixtures["src/ucie_miner/candidate_stage.py"])
        (self.root / "src" / "ucie_miner" / "ast_original.py").write_bytes(
            b"import math  # formatting-only comment\nVALUE=5\n")
        (self.root / "scripts" / "same.ps1").write_bytes(b"Write-Output 5\r\n")
        (self.root / "scripts" / "live.ps1").write_bytes(b"OWNER MODIFIED\n")
        (self.root / "tests" / "test_secret_legacy.py").write_bytes(
            b"def test_secret_legacy():\n    assert False\n")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "confidential_history.md").write_bytes(
            b"NEVER READ OWNER DOCUMENT CONTENT")
        (self.root / "src" / "ucie_miner" / "recovery.bak").write_bytes(
            b"DO NOT READ BACKUP")

        original_doc_digest = sha256(
            (self.root / "docs" / "confidential_history.md").read_bytes()).hexdigest()
        with patch.object(
                layout, "_read_owner_ucie_code_bounded",
                wraps=layout._read_owner_ucie_code_bounded) as observed:
            report = layout._stage_original_path_crosswalk(
                stage, self.root, classify_unmatched=True,
                review_local_code=True)
        review = report["owner_local_code_content_review"]
        self.assertEqual(review["schema"], layout.LOCAL_CODE_REVIEW_SCHEMA)
        self.assertTrue(review["content_comparison_local_only"])
        self.assertFalse(review["code_imported_or_executed"])
        self.assertEqual(review["by_review_area"]["src"][
            "same_path_exact_bytes"], 1)
        self.assertEqual(review["by_review_area"]["src"][
            "original_only_exact_bytes_elsewhere_candidate"], 1)
        self.assertEqual(review["by_review_area"]["src"][
            "original_only_python_ast_candidate"], 1)
        self.assertEqual(review["by_review_area"]["scripts"][
            "same_path_eol_only"], 1)
        self.assertEqual(review["by_review_area"]["scripts"][
            "same_path_content_changed"], 1)
        self.assertEqual(review["by_review_area"]["tests"][
            "original_only_no_static_candidate_observed"], 1)
        self.assertEqual(review["code_status_records_reviewed_or_held"], 6)
        self.assertEqual(report["byte_duplicate_count_verified"], None)
        self.assertTrue(report["file_content_hashes_read"])
        self.assertFalse(report["files_moved_or_deleted"])
        self.assertFalse(report["full_cutover_authorized"])
        self.assertEqual(report["unmatched_path_metadata_review"][
            "all_unmatched_records_disposition"], "K0_HOLD_FOR_SOURCE_REVIEW")
        touched = [call.args[1] for call in observed.call_args_list]
        self.assertFalse(any(
            x.startswith((".ucie_bridge_state/", "docs/", "runtime/")) or
            x.endswith(".bak") for x in touched))
        import json
        receipt = json.dumps(report, sort_keys=True)
        for secret in ("test_secret_legacy", "confidential_history",
                       "candidate_original", "OWNER MODIFIED",
                       original_doc_digest):
            self.assertNotIn(secret, receipt)
        self.assertEqual(sha256(
            (self.root / "docs" / "confidential_history.md").read_bytes()
        ).hexdigest(), original_doc_digest)
        self._assert_state_unchanged()

    def test_35_owner_code_scope_rejects_indirection_private_and_backups(self):
        for item in (
            ".ucie_bridge_state/health.json", "runtime/owner.py",
            "docs/review.md", "src/private/secret.py",
            "src/ucie_miner/secrets/token.py",
            "scripts/recovery.bak", "tests/test_hidden.ps1",
            "src/ucie_miner/../escape.py",
            "scripts/../secrets/private.ps1",
            "src/ucie_miner/foo.txt",
        ):
            with self.subTest(item=item):
                self.assertIsNone(layout._ucie_code_scope(item))
                self.assertIsNone(layout._read_owner_ucie_code_bounded(
                    self.root, item))
        self.assertEqual(layout._ucie_code_scope(
            "src/ucie_miner/real.py"), "src")
        self.assertEqual(layout._ucie_code_scope(
            "scripts/setup.ps1"), "scripts")
        self.assertEqual(layout._ucie_code_scope(
            "tests/test_regression.py"), "tests")
        self.assertGreaterEqual(layout.MAX_LOCAL_CODE_RECORDS, 877 + 1586)
        self._assert_state_unchanged()

    def test_36_owner_content_review_oversized_and_zero_trust_hold(self):
        target = self.root / "src" / "ucie_miner" / "oversized.py"
        target.write_bytes(b"A" * (layout.MAX_LOCAL_CODE_FILE_BYTES + 1))
        name = "src/ucie_miner/oversized.py"
        self.assertIsNone(layout._read_owner_ucie_code_bounded(
            self.root, name))
        record = layout._compare_owner_code_content_locally(
            self.root, self.root, set(), [("untracked", name)])
        row = record["by_review_area"]["src"]
        self.assertEqual(row["code_status_records"], 1)
        self.assertEqual(row["original_file_unreadable_or_unsafe"], 1)
        self.assertEqual(row["original_only_no_static_candidate_observed"], 0)
        self.assertFalse(record["same_bytes_proves_functional_equivalence"])
        self.assertEqual(record["all_original_paths_remain"], "K0_HOLD_FOR_REVIEW")
        with self.assertRaises(layout.LayoutAuditError):
            layout._compare_owner_code_content_locally(
                self.root, self.root,
                set(f"scripts/fake_{i}.py" for i in range(
                    layout.MAX_LOCAL_CODE_RECORDS + 1)), [])
        self._assert_state_unchanged()

    def test_37_owner_code_review_boolean_and_platform_gates(self):
        with self.assertRaises(layout.LayoutAuditError):
            layout._stage_original_path_crosswalk(
                self.root, self.root, review_local_code=1)
        with self.assertRaises(layout.LayoutAuditError):
            layout.compare_original_ucie_git_to_stage(
                self.root, self.root, platform="posix",
                review_local_code=True)
        self._assert_state_unchanged()


    def test_38_same_path_changed_static_ast_buckets_are_complete(self):
        stage = Path(self.tmp.name) / "STAGED_SOURCE" / "UCIE"
        stage.mkdir(parents=True)
        originals = {
            "src/ucie_miner/comment_only.py":
                b"def answer():\n    return 1  # preserved meaning\n",
            "src/ucie_miner/changed_logic.py":
                b"def answer():\n    return 2\n",
            "src/ucie_miner/invalid_python.py":
                b"def : INVALID\n",
            "scripts/changed.ps1": b"Write-Output 2\n",
        }
        staged = {
            "src/ucie_miner/comment_only.py":
                b"def answer():\n    return 1\n",
            "src/ucie_miner/changed_logic.py":
                b"def answer():\n    return 1\n",
            "src/ucie_miner/invalid_python.py":
                b"def answer():\n    return 1\n",
            "scripts/changed.ps1": b"Write-Output 1\n",
        }
        for name, data in staged.items():
            p = stage / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        for name, data in originals.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        rows = [("untracked", p) for p in staged]
        result = layout._compare_owner_code_content_locally(
            stage, self.root, set(staged), rows)
        src = result["by_review_area"]["src"]
        self.assertEqual(src["same_path_content_changed"], 3)
        self.assertEqual(src["same_path_changed_ast_identical"], 1)
        self.assertEqual(src["same_path_changed_ast_different"], 1)
        self.assertEqual(src["same_path_changed_ast_unavailable"], 1)
        scripts = result["by_review_area"]["scripts"]
        self.assertEqual(scripts["same_path_content_changed"], 1)
        self.assertEqual(scripts["same_path_changed_ast_identical"], 0)
        self.assertEqual(scripts["same_path_changed_ast_different"], 0)
        self.assertEqual(scripts["same_path_changed_ast_unavailable"], 1)
        self.assertEqual(result["code_status_records_reviewed_or_held"], 4)
        self.assertFalse(result["ast_candidate_proves_functional_equivalence"])
        self.assertEqual(result["all_original_paths_remain"],
                         "K0_HOLD_FOR_REVIEW")
        import json
        output = json.dumps(result, sort_keys=True)
        for forbidden in ("comment_only.py", "invalid_python.py",
                          "Write-Output", "answer()"):
            self.assertNotIn(forbidden, output)
        self._assert_state_unchanged()

    def test_39_same_path_ast_fail_closed_for_oversize_and_invalid(self):
        self.assertIsNone(layout._code_ast_digest(
            b"def f():\n    return 1\n",
            "scripts/file.ps1"))
        self.assertIsNone(layout._code_ast_digest(
            b"x" * (layout.MAX_LOCAL_AST_BYTES + 1),
            "src/ucie_miner/bounded.py"))
        self.assertIsNone(layout._code_ast_digest(
            b"not valid python!",
            "src/ucie_miner/bounded.py"))
        self._assert_state_unchanged()


    def test_40_local_firstparty_reference_index_bounded_static_cases(self):
        stage_mods = {
            "ucie_miner", "ucie_miner.ready", "ucie_public",
            "ucie_public.model", "ucie_miner.sub",
        }
        cases = (
            (b"import ucie_miner.ready\n",
             "python_with_indexed_stage_module_only", 1, 0, False),
            (b"from ucie_miner.absent import service\n",
             "python_with_unindexed_stage_module_target", 0, 1, False),
            (b"from ucie_miner import CONSTANT\n",
             "python_with_unresolved_reference_style", 0, 0, False),
            (b"from . import sibling\n",
             "python_with_unresolved_reference_style", 0, 0, False),
            (b"import importlib\nimportlib.import_module('ucie_miner.absent')\n",
             "python_with_unresolved_reference_style", 0, 0, False),
            (b"import os\n",
             "python_without_direct_ucie_module_target", 0, 0, False),
            (b"def test_ucie():\n    assert True\n",
             "python_without_direct_ucie_module_target", 0, 0, True),
            (b"def ! INVALID\n", "python_ast_unavailable", 0, 0, False),
        )
        for source, bucket, indexed, unindexed, test_like in cases:
            with self.subTest(bucket=bucket, source=source[:12]):
                observed = layout._static_firstparty_module_targets(
                    source, "tests/test_fixture.py", stage_mods)
                self.assertEqual(observed, {
                    "bucket": bucket,
                    "indexed": indexed,
                    "unindexed": unindexed,
                    "test_like": test_like,
                })
        ps = layout._static_firstparty_module_targets(
            b"Import-Module UCIE", "scripts/runner.ps1", stage_mods)
        self.assertEqual(
            ps["bucket"], "powershell_static_reference_unverified")
        self.assertEqual(ps["indexed"], 0)
        self.assertEqual(ps["unindexed"], 0)
        self._assert_state_unchanged()

    def test_41_local_reference_review_counts_only_unmatched_no_candidate(self):
        stage = Path(self.tmp.name) / "UCIE_STAGE_SOURCE_ONLY"
        for name, data in (
            ("src/ucie_miner/ready.py", b"VALUE=1\n"),
            ("src/ucie_public/model.py", b"VALUE=2\n"),
        ):
            p = stage / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        fixtures = {
            "src/ucie_miner/missing_a.py":
                b"from ucie_miner.absent import missing\n",
            "src/ucie_miner/has_existing.py":
                b"import ucie_public.model\n",
            "scripts/unresolved.py":
                b"from ucie_miner import ATTRIBUTE_OR_MODULE\n",
            "scripts/old_job.ps1":
                b"Write-Output 'OLD REVIEW REQUIRED'\n",
            "tests/test_legacy_one.py":
                b"import ucie_miner.ready\n"
                b"def test_legacy_one(): assert True\n",
            "tests/test_legacy_two.py":
                b"import os\n",
        }
        for name, data in fixtures.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        changes = [("untracked", name) for name in fixtures]
        report = layout._compare_owner_code_content_locally(
            stage, self.root,
            {"src/ucie_miner/ready.py", "src/ucie_public/model.py"},
            changes)
        ref = report["original_only_no_static_match_import_review"]
        self.assertEqual(ref["schema"], layout.LOCAL_REFERENCE_SCHEMA)
        self.assertEqual(ref["code_paths_without_content_match_reviewed"], 6)
        self.assertEqual(ref["stage_firstparty_module_index_count"], 4)
        src = ref["by_review_area"]["src"]
        self.assertEqual(src["python_with_unindexed_stage_module_target"], 1)
        self.assertEqual(src["python_with_indexed_stage_module_only"], 1)
        scripts = ref["by_review_area"]["scripts"]
        self.assertEqual(scripts["python_with_unresolved_reference_style"], 1)
        self.assertEqual(scripts["powershell_static_reference_unverified"], 1)
        test = ref["by_review_area"]["tests"]
        self.assertEqual(test["python_with_indexed_stage_module_only"], 1)
        self.assertEqual(test["python_without_direct_ucie_module_target"], 1)
        self.assertEqual(test["test_like_static_nodes_observed"], 1)
        self.assertEqual(test["test_like_static_nodes_not_observed"], 1)
        self.assertEqual(ref["by_review_area"]["src"][
            "unindexed_stage_ucie_module_targets"], 1)
        self.assertFalse(ref["original_code_uploaded_or_copied"])
        self.assertFalse(ref["original_code_executed_or_imported"])
        self.assertEqual(ref["all_original_only_files_remain"],
                         "K0_HOLD_FOR_DEPENDENCY_REVIEW")
        import json
        output = json.dumps(report, sort_keys=True)
        for secret in ("missing_a", "has_existing", "test_legacy_one",
                       "ATTRIBUTE_OR_MODULE", "OLD REVIEW REQUIRED",
                       "ucie_miner.absent", "ucie_public.model"):
            self.assertNotIn(secret, output)
        self._assert_state_unchanged()

    def test_42_local_ref_census_fails_closed_on_missing_coverage(self):
        with self.assertRaises(layout.LayoutAuditError):
            layout._finalize_no_static_match_imports(
                {"tests": Counter({"no_static_match_code_files": 1,
                                   "python_ast_unavailable": 1})},
                {"tests": Counter({
                    "original_only_no_static_candidate_observed": 2})},
                {"ucie_miner"})
        self._assert_state_unchanged()

if __name__ == "__main__":
    unittest.main()
