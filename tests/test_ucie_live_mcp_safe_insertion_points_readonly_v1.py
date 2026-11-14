"""UCIE-only live MCP insertion point metadata, never imports/runs live server.

Reports only AST node types, declaration names of MCP tools, limited line
numbers, and public SDK symbols. No expression values, tokens, or code dump.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import unittest

UCIE_PROFILE = Path(r"D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml")
SERVER = Path(r"D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py")
SAFE_TARGETS = {"mcp", "server", "app", "ucie_server", "mcp_server", "srv"}


def callable_name(expr):
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return ""


def scan() -> dict:
    if not SERVER.is_file() or SERVER.is_symlink() or SERVER.stat().st_size > 250000:
        raise AssertionError("Pinned UCIE live MCP source unavailable")
    tree = ast.parse(SERVER.read_bytes().decode("utf-8-sig"), filename="UCIE_MCP_LIVE")
    result = {
        "schema": "UCIE_MCP_SAFE_INSERTION_AST_V1",
        "status": "READ_ONLY_METADATA_NOT_RUNTIME_AUTH",
        "sdk_mcpserver_instantiations": [],
        "declaration_count": 0,
        "decorator_target_counts": {},
        "bounded_tool_function_declarations": [],
        "server_start_calls": [],
        "main_guard_count": 0,
        "ucie_owner_hook_import_count": 0,
        "no_source_or_secret_exposed": True,
        "no_tool_or_task_mutations": True,
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            parts = ([node.module or ""] if isinstance(node, ast.ImportFrom)
                     else [alias.name for alias in node.names])
            if any("owner_scoped" in part for part in parts):
                result["ucie_owner_hook_import_count"] += 1
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            if isinstance(value, ast.Call) and callable_name(value.func) in ("FastMCP", "MCPServer"):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                target_names = [x.id for x in targets if isinstance(x, ast.Name)]
                result["sdk_mcpserver_instantiations"].append({
                    "line": int(node.lineno), "var": target_names[0] if target_names and
                    target_names[0] in SAFE_TARGETS else "UNKNOWN",
                    "constructor": callable_name(value.func),
                })
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["declaration_count"] += 1
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                attr = callable_name(dec.func)
                if attr in ("tool", "resource", "prompt"):
                    result["decorator_target_counts"][attr] = (
                        result["decorator_target_counts"].get(attr, 0) + 1
                    )
                    if attr == "tool" and len(result["bounded_tool_function_declarations"]) < 22:
                        target = dec.func.value if isinstance(dec.func, ast.Attribute) else None
                        # Only existing explicit UCIE tool names and line positions;
                        # no function bodies, docstrings or arbitrary caller values.
                        name = node.name
                        if not name.startswith(("ucie_", "search_", "admin_", "library_")):
                            name = "OTHER"
                        result["bounded_tool_function_declarations"].append({
                            "line": int(node.lineno), "function": name,
                            "decorator_receiver": getattr(target, "id", "UNKNOWN")
                            if isinstance(target, ast.Name) else "UNKNOWN",
                        })
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("run", "run_stdio", "run_stdio_async", "serve"):
                target = node.func.value
                target_name = getattr(target, "id", "UNKNOWN") if isinstance(target, ast.Name) else "UNKNOWN"
                if target_name in SAFE_TARGETS and len(result["server_start_calls"]) < 12:
                    result["server_start_calls"].append({
                        "line": int(node.lineno), "receiver": target_name,
                        "method": node.func.attr,
                    })
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            if isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__":
                result["main_guard_count"] += 1
    result["sdk_mcpserver_instantiations"].sort(key=lambda x: x["line"])
    result["bounded_tool_function_declarations"].sort(key=lambda x: x["line"])
    result["server_start_calls"].sort(key=lambda x: x["line"])
    return result


class SafeInsertionSurvey(unittest.TestCase):
    def test_no_runtime_import_or_mutation(self):
        import inspect
        code = inspect.getsource(scan)
        for forbidden in ("exec(", "eval(", "importlib.", "subprocess",
                          "write_text(", "write_bytes(", "unlink(", "kill("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)

    def test_owner_host_mcp_structural_metadata(self):
        if os.name != "nt" or not UCIE_PROFILE.is_file():
            self.skipTest("UCIE owner Windows host only")
        result = scan()
        print("UCIE_MCP_SAFE_INSERTION_AST=" + json.dumps(result, sort_keys=True))
        self.assertEqual(result["schema"], "UCIE_MCP_SAFE_INSERTION_AST_V1")
        self.assertTrue(result["no_source_or_secret_exposed"])
        self.assertTrue(result["no_tool_or_task_mutations"])


if __name__ == "__main__":
    unittest.main()
