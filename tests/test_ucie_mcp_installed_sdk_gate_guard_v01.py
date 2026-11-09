"""UCIE installed SDK disposable gate safety checks: no upstream SDK executed here."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_mcp_installed_sdk_client_server_gate_v01.py"
spec = importlib.util.spec_from_file_location("ucie_sdk_integration_gate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class InstalledSDKGateGuardTests(unittest.TestCase):
    def test_exact_pinned_upstream_commits(self):
        self.assertEqual(module.COMMITS, {
            "before": "2118f14f8a19bc158d8a1cf90af58d85d187f849",
            "after": "754254c08fe1c3eda18b69da3d336106fe8d72d6",
        })
        self.assertEqual(module.PROTOCOL_MODES, ("legacy", "2026-07-28"))

    def test_explicit_integration_scope_not_transport_or_approval(self):
        code = SCRIPT.read_text(encoding="utf-8")
        parsed = ast.parse(code)
        self.assertTrue(parsed)
        for expected in (
            "real_in_memory_client_server_integration",
            "http_transport_tested",
            "stdio_transport_tested",
            "fixed_published_version_verified",
            "license_and_dependency_rights_approved",
            "customer_release_authorized",
        ):
            self.assertIn(expected, code)
        for forbidden in ("Start-ScheduledTask", "subprocess.run", "os.system("):
            self.assertNotIn(forbidden, code)

    def test_no_sdk_import_on_regular_owner_or_ci_test_import(self):
        with patch.dict("os.environ", {"UCIE_DISPOSABLE_SDK_GATE": ""}):
            with tempfile.TemporaryDirectory() as path:
                with self.assertRaisesRegex(RuntimeError, "DISPOSABLE_LINUX_CI_REQUIRED"):
                    module.preflight("before", path)

    def test_bad_mode_does_not_get_past_preflight(self):
        with patch.dict("os.environ", {"UCIE_DISPOSABLE_SDK_GATE": ""}):
            with self.assertRaises(RuntimeError):
                module.preflight("NOT_APPROVED", "/")

    def test_no_silent_acceptance_of_wrong_upstream_ids(self):
        self.assertNotIn("v2.3.1", module.COMMITS)
        self.assertEqual(module.INVALID_PARAMS, -32602)
        self.assertTrue(all(len(x) == 40 for x in module.COMMITS.values()))

    def test_paths_are_synthetic_not_user_files(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('server = MCPServer("UCIE synthetic integration server")', src)
        self.assertIn('Client(server, mode=mode)', src)
        self.assertIn('async def greet(name: str)', src)
        self.assertIn('async def explode()', src)
        self.assertNotIn("D:\\", src)
        self.assertNotIn("httpx.", src)


if __name__ == "__main__":
    unittest.main()
