"""UCIE-only synthetic coverage for static MCP permission-gate metadata."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

PATH = (Path(__file__).resolve().parents[1]
        / "scripts" / "inspect_ucie_mcp_permission_gate.py")
spec = importlib.util.spec_from_file_location(
    "ucie_static_permission_gate_inspection", PATH)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)

EXAMPLE = """
import os

def require_ucie_context():
    if os.environ.get("UCIE_MCP_OWNER_CONTEXT") != "1":
        raise PermissionError("UCIE_MCP_CONTEXT_REQUIRED")

def make_server():
    require_ucie_context()
    server = object()
    return server
"""


class UCIEStaticStartupGuardTests(unittest.TestCase):
    def test_inspects_guard_without_executing_auth_or_leaking_values(self):
        lines = EXAMPLE.splitlines()
        error_line = next(i for i, s in enumerate(lines, 1)
                          if "raise PermissionError" in s)
        caller_line = next(i for i, s in enumerate(lines, 1)
                           if "    require_ucie_context()" in s)
        found = inspector.analyze(
            EXAMPLE, env={"UCIE_MCP_OWNER_CONTEXT": "PRIVATE_SHOULD_NOT_PRINT"},
            error_line=error_line, caller_line=caller_line)
        self.assertEqual(found["guard_function"], "require_ucie_context")
        self.assertEqual(found["caller_function"], "make_server")
        self.assertTrue(
            found["ucie_env_key_presence_only"]["UCIE_MCP_OWNER_CONTEXT"])
        self.assertFalse(found["executed_make_server"])
        self.assertTrue(found["guard_function_differs_from_factory"])
        self.assertNotIn("PRIVATE_SHOULD_NOT_PRINT", str(found))

    def test_missing_authorized_context_is_only_reported_not_bypassed(self):
        found = inspector.analyze(
            EXAMPLE, env={}, error_line=6, caller_line=9)
        self.assertFalse(
            found["ucie_env_key_presence_only"]["UCIE_MCP_OWNER_CONTEXT"])
        self.assertFalse(found["server_restarted"])

    def test_non_symbolic_permission_message_is_never_printed(self):
        source = EXAMPLE.replace(
            "UCIE_MCP_CONTEXT_REQUIRED", "token=very-sensitive-value")
        found = inspector.analyze(
            source, env={}, error_line=6, caller_line=9)
        self.assertNotIn("very-sensitive-value", str(found))

    def test_missing_factory_rejected_without_execution(self):
        with self.assertRaises(inspector.InspectionError):
            inspector.analyze(EXAMPLE.replace("make_server", "another_factory"),
                              env={}, error_line=6, caller_line=9)


if __name__ == "__main__":
    unittest.main()
