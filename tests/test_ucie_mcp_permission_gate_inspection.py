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

    def test_guard_branch_shape_and_call_names_without_values(self):
        found = inspector.analyze(
            EXAMPLE, env={}, error_line=6, caller_line=9)
        self.assertEqual(
            found["guard_top_level_statement_types"], ["If"])
        self.assertTrue(found["guard_has_condition_or_control_flow"])
        self.assertFalse(found["guard_is_single_unconditional_raise"])
        self.assertIn("os.environ.get", found["guard_callable_names_only"])
        self.assertNotIn("PRIVATE_SHOULD_NOT_PRINT", str(found))

    def test_unconditional_hold_is_identified_without_bypass(self):
        source = """
def require_runtime_approval():
    raise PermissionError("UCIE_MCP_OPERATOR_GATE_HOLD")
def make_server():
    require_runtime_approval()
    server = object()
    return server
"""
        found = inspector.analyze(
            source, env={}, error_line=3, caller_line=5)
        self.assertTrue(found["guard_is_single_unconditional_raise"])
        self.assertFalse(found["guard_has_condition_or_control_flow"])
        self.assertFalse(found["executed_make_server"])

    def test_environment_alias_key_is_detected_without_approval_value(self):
        source = """
import os
def require_runtime_approval():
    e = os.environ
    if e.get("UCIE_MCP_OPERATOR_APPROVAL") != "very-sensitive-phrase":
        raise PermissionError("UCIE_MCP_OPERATOR_GATE_HOLD")
def make_server():
    require_runtime_approval()
    server = object()
    return server
"""
        found = inspector.analyze(
            source,
            env={"UCIE_MCP_OPERATOR_APPROVAL": "PRIVATE_SHOULD_NOT_PRINT"},
            error_line=6, caller_line=8)
        self.assertTrue(found["operator_gate_environment_alias_detected"])
        self.assertEqual(found["operator_gate_environment_alias_names"], ["e"])
        self.assertEqual(
            found["operator_gate_ucie_variable_presence_only"],
            {"UCIE_MCP_OPERATOR_APPROVAL": True})
        self.assertEqual(
            found["operator_gate_comparison_operator_types"], ["NotEq"])
        self.assertEqual(
            found["operator_gate_comparison_literal_hint"],
            "MASKED_TEXT_LITERAL")
        self.assertNotIn("very-sensitive-phrase", str(found))
        self.assertNotIn("PRIVATE_SHOULD_NOT_PRINT", str(found))

    def test_copy_of_environment_alias_is_supported(self):
        source = """
import os
def require_runtime_approval():
    e = os.environ.copy()
    if e.get("UCIE_MCP_OPERATOR_APPROVAL") != "1":
        raise PermissionError("UCIE_MCP_OPERATOR_GATE_HOLD")
def make_server():
    require_runtime_approval()
    server = object()
    return server
"""
        found = inspector.analyze(
            source, env={}, error_line=6, caller_line=8)
        self.assertTrue(found["operator_gate_environment_alias_detected"])
        self.assertEqual(
            found["operator_gate_ucie_variable_presence_only"],
            {"UCIE_MCP_OPERATOR_APPROVAL": False})
        self.assertEqual(found["operator_gate_comparison_literal_hint"], "1")

    def test_other_project_key_is_not_exposed(self):
        source = """
import os
def require_runtime_approval():
    e = os.environ
    if e.get("SOME_OTHER_PROJECT_SECRET") != "never-emit-this":
        raise PermissionError("UCIE_MCP_OPERATOR_GATE_HOLD")
def make_server():
    require_runtime_approval()
    server = object()
    return server
"""
        found = inspector.analyze(
            source, env={}, error_line=6, caller_line=8)
        self.assertEqual(found["operator_gate_ucie_variable_presence_only"], {})
        self.assertNotIn("SOME_OTHER_PROJECT_SECRET", str(found))
        self.assertNotIn("never-emit-this", str(found))

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
