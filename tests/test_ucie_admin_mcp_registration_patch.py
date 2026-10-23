"""One minimal AST test for UCIE's existing make_server integration.

Only synthetic in-memory code: never reads or alters the user's MCP host.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

SCRIPT = (Path(__file__).resolve().parents[1]
          / "scripts" / "prepare_ucie_admin_mcp_registration.py")
spec = importlib.util.spec_from_file_location(
    "ucie_admin_registration_patcher_test_only", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

MINIMAL_SOURCE = '''
class DummyMCP:
    def tool(self, fn):
        return fn

def make_server():
    server = DummyMCP()
    @server.tool
    def search_ucie_evidence(query, category=None, tag=None, top=5):
        return {"status": "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY",
                "results": []}
    return server
'''


class UCIEAdminMakeServerLinkTests(unittest.TestCase):
    def test_gated_patch_preserves_original_server_factory(self):
        updated = module.prepare_registration(MINIMAL_SOURCE)
        self.assertEqual(updated.count(module.MARKER), 1)
        self.assertIn("register_ucie_local_admin_tools", updated)
        self.assertIn('UCIE_ADMIN_TOOLS_ENABLED', updated)
        compile(updated, "mcp_stdio_server.py", "exec")
        with patch.dict(os.environ, {"UCIE_ADMIN_TOOLS_ENABLED": ""}):
            env = {}
            exec(updated, env)
            server = env["make_server"]()
        self.assertTrue(callable(server.tool))
        with self.assertRaises(module.RegistrationError):
            module.prepare_registration(updated)

    def test_only_the_exact_nested_ucie_factory_is_patched(self):
        bad_sources = (
            MINIMAL_SOURCE.replace("def make_server():", "def factory():"),
            MINIMAL_SOURCE + MINIMAL_SOURCE,
            MINIMAL_SOURCE.replace("server = DummyMCP()", "mcp = DummyMCP()"),
            MINIMAL_SOURCE.replace("@server.tool", "@other.tool"),
            MINIMAL_SOURCE.replace("search_ucie_evidence",
                                   "search_another_tool"),
        )
        for value in bad_sources:
            with self.subTest(value=value[-40:]):
                with self.assertRaises(module.RegistrationError):
                    module.prepare_registration(value)

    def test_docstring_and_multiline_server_constructor(self):
        code = MINIMAL_SOURCE.replace(
            "    server = DummyMCP()",
            '    """Own UCIE FastMCP tools."""\n'
            "    server = (\n        DummyMCP()\n    )"
        )
        updated = module.prepare_registration(code)
        compile(updated, "mcp_stdio_server.py", "exec")
        self.assertIn("    _ucie_admin_register(server)", updated)

    def test_admin_tools_activate_only_with_explicit_host_gate(self):
        patched = module.prepare_registration(MINIMAL_SOURCE)
        calls = []
        stub = ModuleType("ucie_admin.mcp_registration")
        stub.register_ucie_local_admin_tools = (
            lambda server: calls.append(server)
        )
        with patch.dict(sys.modules, {"ucie_admin.mcp_registration": stub}):
            with patch.dict(os.environ,
                            {"UCIE_ADMIN_TOOLS_ENABLED": ""}):
                local = {}
                exec(patched, local)
                original_server = local["make_server"]()
                self.assertEqual(calls, [])
            with patch.dict(os.environ,
                            {"UCIE_ADMIN_TOOLS_ENABLED": "1"}):
                admin_server = local["make_server"]()
                self.assertEqual(calls, [admin_server])
                self.assertIsNot(original_server, admin_server)

    def test_other_project_roots_denied(self):
        with self.assertRaises(module.RegistrationError):
            module.prepare_registration(
                MINIMAL_SOURCE, admin_source=Path(r"D:\AnotherProject\src"))


if __name__ == "__main__":
    unittest.main()
