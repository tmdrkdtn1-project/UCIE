"""UCIE owner-local Slack MCP read-only staging regression suite.

Never starts/stops C40, never reads Slack credentials, and never changes
the actual UCIE admin MCP server. All writes use disposable temp dirs.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest import mock

from ucie_miner import ucie_slack_mcp_owner_dispatch_v1 as dispatcher

SCRIPT = (Path(__file__).resolve().parents[1] / "scripts" /
          "ucie_owner_stage_slack_mcp_readonly_v1.py")
spec = importlib.util.spec_from_file_location("ucie_slack_owner_stage_test", SCRIPT)
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def minimal_registration():
    lines = [
        "def register_ucie_local_admin_tools(fastmcp, bridge=None):",
        '    """Synthetic owner-approved registration."""',
        "    if bridge is None:",
        "        bridge = object()",
    ]
    for name in sorted(stage.EXPECTED_TOOLS):
        lines.extend([
            f"    @fastmcp.tool(name={name!r})",
            f"    def {name}():",
            "        return {'status': 'inert synthetic'}",
            "",
        ])
    lines.extend([
        "    return {",
        "        'status': 'UCIE_ADMIN_TOOLS_REGISTERED_WITH_EXISTING_FASTMCP_INSTANCE',",
        "        'tool_count': 9,",
        "    }",
        "",
    ])
    return "\n".join(lines)


def verified_cli(anchor_list=None, **overrides):
    status = {
        "schema": "UCIE_SLACK_WINDOWS_EVIDENCE_READER_V1",
        "status": "UCIE_SLACK_WINDOWS_READ_ONLY_HISTORY_VERIFIED",
        "block_code": None,
        "pinned_history_anchors": sorted(dispatcher.ANCHORS)
        if anchor_list is None else anchor_list,
        "token_or_raw_messages_exposed": False,
        "new_owner_mcp_tools_enabled": False,
        "c40_or_scheduled_tasks_modified": False,
        "operating_database_modified": False,
        "server_mcp_runtime_hook_wired": False,
    }
    status.update(overrides)
    return json.dumps(status, sort_keys=True)


class UCIESlackReadOnlyMCPStageTests(unittest.TestCase):
    def test_patch_preserves_nine_admin_tools(self):
        src = minimal_registration()
        patched = stage.patch_registration(src)
        self.assertIn(stage.MARKER, patched)
        self.assertEqual(patched.count("ucie_slack_history_verify_readonly"), 2)
        self.assertIn("return _ucie_fixed_history_verify()", patched)
        self.assertIn("'tool_count': 9", patched)
        compile(patched, "ucie_admin/mcp_registration.py", "exec")
        # Verify synthetically that the new tool never takes arguments and
        # keeps the original nine tools unchanged.
        module = ModuleType("ucie_admin.slack_history_readonly_mcp_v1")
        module.verify_ucie_slack_history_fixed = lambda: {"status": "READONLY"}
        package = ModuleType("ucie_admin")
        package.__path__ = []
        with mock.patch.dict(sys.modules, {
            "ucie_admin": package,
            "ucie_admin.slack_history_readonly_mcp_v1": module,
        }):
            ns = {}
            exec(patched, ns)
            class FakeMCP:
                def __init__(self):
                    self.names = {}
                def tool(self, name):
                    def decorate(fn):
                        self.names[name] = fn
                        return fn
                    return decorate
            fake = FakeMCP()
            result = ns["register_ucie_local_admin_tools"](fake)
        self.assertEqual(result["tool_count"], 9)
        self.assertEqual(set(fake.names) - stage.EXPECTED_TOOLS,
                         {"ucie_slack_history_verify_readonly"})
        self.assertEqual(fake.names["ucie_slack_history_verify_readonly"](),
                         {"status": "READONLY"})

    def test_exact_pr78_and_live_stage_versions_pinned(self):
        self.assertEqual(len(stage.ALLOWED_BASE_BLOBS), 2)
        self.assertIn("8516baa69e768f2589d5df305200ebcd99b76e0d",
                      stage.ALLOWED_BASE_BLOBS)
        self.assertIn("c26be40528d421bf384acbccd1501a1c522cc666",
                      stage.ALLOWED_BASE_BLOBS)

    def test_duplicate_install_and_extra_admin_tools_denied(self):
        src = minimal_registration()
        with self.assertRaises(stage.UCIEStageError):
            stage.patch_registration(stage.patch_registration(src))
        with self.assertRaises(stage.UCIEStageError):
            stage.patch_registration(src.replace(
                "'tool_count': 9", "'tool_count': 9"
            ).replace(
                "    return {",
                "    @fastmcp.tool(name='ucie_admin_shell')\n"
                "    def ucie_admin_shell():\n"
                "        return 'not allowed'\n"
                "    return {", 1))

    def test_missing_original_tool_or_registration_function_denied(self):
        src = minimal_registration()
        for bad in (
            src.replace("ucie_admin_capabilities", "ucie_admin_unknown"),
            src.replace("register_ucie_local_admin_tools", "other_register"),
            src.replace("    return {", "    pass\n    return {"),
            src + src,
        ):
            if "    pass\n" in bad:
                continue
            with self.subTest(bad=bad[:90]), self.assertRaises(stage.UCIEStageError):
                stage.patch_registration(bad)

    def test_pinned_positive_receipt_returns_no_messages(self):
        row = dispatcher._evaluate_cli(verified_cli(), 0)
        self.assertEqual(row["status"], "UCIE_SLACK_MCP_HISTORY_VERIFIED")
        self.assertEqual(set(row["pinned_history_anchors"]), dispatcher.ANCHORS)
        self.assertTrue(row["readonly_only"])
        self.assertFalse(row["token_or_messages_returned"])
        self.assertFalse(row["owner_write_tools_enabled"])

    def test_forged_or_partial_receipt_never_passes(self):
        fixtures = (
            (verified_cli(), 3),
            (verified_cli(anchor_list=[]), 0),
            (verified_cli(anchor_list=["UCIE_ADMIN_PR78_OWNER_LAUNCH"] * 3), 0),
            (verified_cli(token_or_raw_messages_exposed=True), 0),
            (verified_cli(new_owner_mcp_tools_enabled=True), 0),
            (verified_cli(c40_or_scheduled_tasks_modified=True), 0),
            (verified_cli(operating_database_modified=True), 0),
            ("".join("x" for _ in range(dispatcher.MAX_CLI_OUTPUT + 2)), 0),
            ("not-json", 0),
            (verified_cli() + "\n" + verified_cli(), 0),
        )
        for output, code in fixtures:
            with self.subTest(code=code, prefix=output[:30]):
                row = dispatcher._evaluate_cli(output, code)
                self.assertEqual(row["status"],
                                 "HISTORY_RECHECK_REQUIRED_BLOCK_VERDICT")
                self.assertFalse(row["token_or_messages_returned"])

    def test_missing_source_and_non_windows_denied(self):
        with tempfile.TemporaryDirectory(prefix="ucie-scope-") as tmp:
            self.assertFalse(dispatcher._pinned_reader_present(Path(tmp)))
        if os.name != "nt":
            self.assertEqual(dispatcher.verify_ucie_slack_history_fixed()["block_code"],
                             "UCIE_WINDOWS_HOST_REQUIRED")

    def test_source_pin_checks_detect_drift_in_disposable_root(self):
        with tempfile.TemporaryDirectory(prefix="ucie-codepin-") as tmp:
            base = Path(tmp)
            python = base / ".venv" / "Scripts" / "python.exe"
            python.parent.mkdir(parents=True)
            python.write_bytes(b"synthetic interpreter")
            package = base / "src" / "ucie_miner"
            package.mkdir(parents=True)
            blobs = {name: (b"test-" + name.encode("ascii"))
                     for name in dispatcher.PINS}
            for name, blob in blobs.items():
                (package / name).write_bytes(blob)
            pins = {name: dispatcher._git_blob_sha(blob)
                    for name, blob in blobs.items()}
            self.assertTrue(dispatcher._pinned_reader_present(base, pins))
            (package / "ucie_slack_windows_reader_v1.py").write_bytes(b"tampered")
            self.assertFalse(dispatcher._pinned_reader_present(base, pins))

    def test_actual_stage_pin_is_not_assumed(self):
        if os.name != "nt" or not stage.ROOT.is_dir():
            self.skipTest("UCIE owner Windows host only")
        try:
            blob, before, after = stage.prepare()
            report = {
                "schema": stage.SCHEMA,
                "status": "UCIE_SLACK_READONLY_STAGE_PREVIEW_READY",
                "registration_git_blob_matches_pr78":
                    stage._git_blob(before) == stage.PR78_GIT_BLOB,
                "module_bytes": len(blob),
                "source_read_only": True,
                "c40_restarted": False,
            }
        except stage.UCIEStageError as exc:
            report = {
                "schema": stage.SCHEMA,
                "status": "UCIE_SLACK_READONLY_STAGE_PREVIEW_BLOCKED",
                "block_code": str(exc),
                "source_read_only": True,
                "c40_restarted": False,
            }
        print("UCIE_SLACK_MCP_OWNER_STAGE_PREFLIGHT=" +
              json.dumps(report, sort_keys=True))
        self.assertTrue(report["source_read_only"])
        self.assertFalse(report["c40_restarted"])

    def test_test_only_atomic_stage_backup_and_rollback(self):
        with tempfile.TemporaryDirectory(prefix="ucie-stage-test-") as tmp:
            folder = Path(tmp)
            reg = folder / "mcp_registration.py"
            src = folder / "dispatch.py"
            dest = folder / "slack_history_readonly_mcp_v1.py"
            raw = minimal_registration().encode("utf-8")
            patched = stage.patch_registration(raw.decode()).encode()
            reg.write_bytes(raw)
            src.write_bytes(b"# Test-only UCIE dispatch\n")
            backup = stage.install_atomic(src, reg, dest,
                                          src.read_bytes(), raw, patched)
            self.assertEqual(reg.read_bytes(), patched)
            self.assertEqual(dest.read_bytes(), src.read_bytes())
            self.assertEqual(backup.read_bytes(), raw)

    def test_no_app_write_or_c40_restart_anywhere(self):
        import inspect
        src = inspect.getsource(dispatcher)
        self.assertNotIn("Start-ScheduledTask", src)
        self.assertNotIn("Restart-Service", src)
        self.assertNotIn("UCIE_ADMIN_TOOLS_ENABLED", src)
        self.assertNotIn("D:\\OFFICE_AGENT", src)
        self.assertNotIn("D:\\MYGAME", src)
        self.assertIn("stdin=subprocess.DEVNULL", src)
        self.assertIn("shell=False", src)


if __name__ == "__main__":
    unittest.main()
