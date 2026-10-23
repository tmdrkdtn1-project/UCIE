"""UCIE-only admin bridge smoke: real temporary file ops, strict boundaries."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from ucie_admin.local_write_bridge import UCIEFileBridge, BridgeError
from ucie_admin.mcp_registration import register_ucie_local_admin_tools


class DummyMcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *, name):
        def decorate(func):
            self.tools[name] = func
            return func
        return decorate


class LocalWriteBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parent = Path(self.tmp.name)
        self.repo = parent / "UCIE"
        self.server = parent / "UCIE_DATA" / "library_app" / "private_lib"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "tests").mkdir()
        self.server.mkdir(parents=True)
        self.other = parent / "OtherProject"
        self.other.mkdir()
        (self.other / "keep.py").write_text("DO_NOT_TOUCH", encoding="utf-8")
        self.bridge = UCIEFileBridge(self.repo, self.server,
                                      python_exe=Path(sys.executable))
        self.src = self.repo / "src" / "sample.py"
        self.src.write_bytes(b"VALUE = 1\n")

    def test_read_preview_edit_backup_and_sha_lease(self):
        before = self.bridge.read_text("repo", "src/sample.py")
        self.assertEqual(before["content"], "VALUE = 1\n")
        preview = self.bridge.write_text(
            "repo", "src/sample.py", "VALUE = 2\n",
            before["sha256"], preview=True)
        self.assertFalse(preview["written"])
        self.assertEqual(self.src.read_text(), "VALUE = 1\n")
        done = self.bridge.write_text(
            "repo", "src/sample.py", "VALUE = 2\n",
            before["sha256"], preview=False)
        self.assertTrue(done["written"])
        self.assertIsNotNone(done["backup"])
        self.assertEqual(self.src.read_text(), "VALUE = 2\n")
        self.assertEqual(
            (self.repo / ".ucie_bridge_state" / done["backup"]).read_text(),
            "VALUE = 1\n")
        with self.assertRaises(BridgeError):
            self.bridge.write_text(
                "repo", "src/sample.py", "VALUE = 3\n",
                before["sha256"], preview=False)
        self.assertEqual(self.src.read_text(), "VALUE = 2\n")
        self.assertEqual((self.other / "keep.py").read_text(), "DO_NOT_TOUCH")

    def test_create_replace_directory_search_and_no_double_match(self):
        found = self.bridge.search_text("repo", "src", "VALUE")
        self.assertEqual(found["matches"][0]["path"], "src/sample.py")
        self.assertEqual(found["matches"][0]["line"], 1)
        self.bridge.create_directory("repo", "src/module")
        created = self.bridge.write_text(
            "repo", "src/module/tool.py", "ALPHA = True\n", "ABSENT",
            preview=False)
        self.assertTrue(created["written"])
        old = self.bridge.read_text("repo", "src/module/tool.py")
        changed = self.bridge.replace_once(
            "repo", "src/module/tool.py", "True", "False",
            old["sha256"], preview=False)
        self.assertTrue(changed["written"])
        self.assertEqual((self.repo / "src/module/tool.py").read_text(),
                         "ALPHA = False\n")
        current = self.bridge.read_text("repo", "src/module/tool.py")
        with self.assertRaises(BridgeError):
            self.bridge.replace_once(
                "repo", "src/module/tool.py", "A", "Z",
                current["sha256"], preview=False)
        listed = self.bridge.list_directory("repo", "src")
        self.assertTrue(any(item["name"] == "module"
                            for item in listed["items"]))

    def test_independent_mcp_server_source_edit(self):
        server_source = self.server / "mcp_stdio_server.py"
        done = self.bridge.write_text(
            "mcp_code", "mcp_stdio_server.py",
            "def test(): return True\n", "ABSENT", preview=False)
        self.assertTrue(done["written"])
        self.assertEqual(server_source.read_text(),
                         "def test(): return True\n")
        with self.assertRaises(BridgeError):
            self.bridge.read_text("mcp_code", "tunnel_profile.yaml")

    def test_cross_project_and_sensitive_access_denied(self):
        for scope, path in (
            ("repo", "../OtherProject/keep.py"),
            ("repo", "/tmp/out.py"),
            ("repo", "src\\sample.py"),
            ("repo", ".git/config"),
            ("repo", "runtime/secrets.json"),
            ("repo", "src/.env"),
            ("repo", "src/private_key.pem"),
            ("mcp_code", "../../other/server.py"),
            ("foreign", "src/sample.py"),
        ):
            with self.subTest(scope=scope, path=path):
                with self.assertRaises(BridgeError):
                    self.bridge.read_text(scope, path)
        self.assertEqual((self.other / "keep.py").read_text(), "DO_NOT_TOUCH")

    def test_symlink_leaving_root_cannot_be_read_or_written(self):
        target = self.other / "keep.py"
        link = self.repo / "src" / "linked.py"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable on current OS")
        for op in ("read", "write"):
            with self.assertRaises(BridgeError):
                if op == "read":
                    self.bridge.read_text("repo", "src/linked.py")
                else:
                    self.bridge.write_text("repo", "src/linked.py",
                                           "BAD", "ABSENT", preview=False)
        self.assertEqual(target.read_text(), "DO_NOT_TOUCH")

    def test_one_file_test_runner_requires_explicit_opt_in(self):
        test_path = self.repo / "tests" / "test_demo.py"
        test_path.write_text(
            "import unittest\n"
            "class Demo(unittest.TestCase):\n"
            "    def test_ok(self): self.assertEqual(1, 1)\n",
            encoding="utf-8",
        )
        with self.assertRaises(BridgeError):
            self.bridge.run_one_test_file("test_demo.py", approved=False)
        with self.assertRaises(BridgeError):
            self.bridge.run_one_test_file("../other.py", approved=True)
        outcome = self.bridge.run_one_test_file(
            "test_demo.py", approved=True)
        self.assertEqual(outcome["exit_code"], 0, outcome["stderr"])

    def test_tools_register_only_when_called(self):
        server = DummyMcp()
        info = register_ucie_local_admin_tools(server, self.bridge)
        self.assertEqual(info["tool_count"], 9)
        self.assertEqual(len(server.tools), 9)
        self.assertFalse(server.tools["ucie_admin_capabilities"]()
                         ["other_projects_access"])
        before = server.tools["ucie_admin_read_text"](
            "repo", "src/sample.py")
        self.assertIn("VALUE", before["content"])
        result = server.tools["ucie_admin_write_text"](
            "repo", "src/sample.py", "VALUE = 11\n",
            before["sha256"])
        self.assertFalse(result["written"])  # preview is the default
        self.assertEqual(self.src.read_text(), "VALUE = 1\n")


if __name__ == "__main__":
    unittest.main()
