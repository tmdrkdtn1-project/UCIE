"""Fail-closed tests for UCIE's pinned upstream method probe (no SDK import)."""
from __future__ import annotations

import ast
import importlib.util
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_mcp_pinned_method_probe_v01.py"
spec = importlib.util.spec_from_file_location("ucie_pinned_probe_v01", SCRIPT)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


class PinnedMethodProbeV01Tests(unittest.TestCase):
    def test_exact_upstream_source_gate_has_four_fixed_git_blobs(self):
        self.assertEqual(
            set(probe.FILE_BLOBS),
            {"before_manager.py", "before_base.py",
             "after_manager.py", "after_base.py"},
        )
        self.assertEqual(probe.BASE_COMMIT,
                         "2118f14f8a19bc158d8a1cf90af58d85d187f849")
        self.assertEqual(probe.FIXED_COMMIT,
                         "754254c08fe1c3eda18b69da3d336106fe8d72d6")
        self.assertTrue(all(len(x) == 40 for x in probe.FILE_BLOBS.values()))

    def test_git_blob_sha_is_git_object_digest_not_plain_file_hash(self):
        self.assertEqual(
            probe.git_blob_sha(b"hello\n"),
            "ce013625030ba8dba906f756967f9e9ca394464a",
        )
        self.assertNotEqual(
            probe.git_blob_sha(b"hello\n"),
            __import__("hashlib").sha1(b"hello\n").hexdigest(),
        )

    def test_missing_or_modified_source_fails_before_ast_execution(self):
        with self.assertRaises(probe.SourceGateError):
            probe.check_source_payload("another_project.py", b"unsafe")
        for name in probe.FILE_BLOBS:
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    probe.SourceGateError, "GIT_BLOB_SHA_MISMATCH"
                ):
                    probe.check_source_payload(name, b"print('changed')")

    def test_no_path_traversal_or_unpinned_folder(self):
        with tempfile.TemporaryDirectory(prefix="ucie_pinned_probe_") as d:
            folder = Path(d)
            with self.assertRaises(probe.SourceGateError):
                probe.load_source_dir(folder)
            (folder / "before_manager.py").write_bytes(b"x" * (probe.MAX_BYTES + 1))
            with self.assertRaises(probe.SourceGateError):
                probe.load_source_dir(folder)

    def test_symlink_snapshot_not_accepted_if_supported(self):
        with tempfile.TemporaryDirectory(prefix="ucie_pinned_probe_") as d:
            folder = Path(d)
            target = folder / "target.txt"
            target.write_bytes(b"safe")
            pointer = folder / "before_manager.py"
            try:
                pointer.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("local test runner symlink unavailable")
            with self.assertRaises(probe.SourceGateError):
                probe.load_source_dir(folder)

    def test_missing_class_or_wrong_method_has_no_fallback(self):
        module = ast.parse("class NotPromptManager:\n    pass\n")
        with self.assertRaises(probe.SourceGateError):
            probe.source_method(module, "PromptManager", "render_prompt")
        module = ast.parse("class PromptManager:\n    def render_prompt(self): pass\n")
        with self.assertRaises(probe.SourceGateError):
            probe.source_method(module, "PromptManager", "render_prompt")

    def test_malformed_manager_or_argument_guard_is_rejected(self):
        manager = ast.parse(
            "class PromptManager:\n"
            "    async def render_prompt(self, name, arguments, context):\n"
            "        __import__('os').system('whoami')\n"
        )
        with self.assertRaises(probe.SourceGateError):
            probe.extract_vetted_manager_function(manager, fixed=False)
        prompt = ast.parse(
            "class Prompt:\n"
            "    async def render(self, arguments, context):\n"
            "        if self.arguments:\n"
            "            import os\n"
        )
        with self.assertRaises(probe.SourceGateError):
            probe.extract_vetted_prompt_guard(prompt, fixed=False)

    def test_synthetic_fixed_manager_and_guard_paths_execute(self):
        # UCIE-authored fixture, not copied upstream source and not SDK evidence.
        fragment = ast.parse(
            "class PromptManager:\n"
            "    async def render_prompt(self, name, arguments, context):\n"
            "        prompt = self.get_prompt(name)\n"
            "        if not prompt:\n"
            "            raise MCPError(code=INVALID_PARAMS, message=f'Unknown prompt: {name}')\n"
            "        return await prompt.render(arguments, context)\n"
            "class Prompt:\n"
            "    async def render(self, arguments, context):\n"
            "        if self.arguments:\n"
            "            required = {arg.name for arg in self.arguments if arg.required}\n"
            "            provided = set(arguments or {})\n"
            "            missing = required - provided\n"
            "            if missing:\n"
            "                raise MCPError(code=INVALID_PARAMS, message=f'Missing: {missing}')\n"
        )
        import asyncio
        manager = probe.extract_vetted_manager_function(fragment, fixed=True)
        guard = probe.extract_vetted_prompt_guard(fragment, fixed=True)
        out = asyncio.run(probe.check_variant(manager, guard))
        self.assertEqual(out["unknown"], {"kind": "MCPError", "code": -32602})
        self.assertEqual(out["missing"], {"kind": "MCPError", "code": -32602})
        self.assertEqual(out["valid_guard"],
                         {"kind": "RESULT", "value": "ARGUMENT_GUARD_OK"})
        self.assertEqual(out["function_exception_control"],
                         {"kind": "RuntimeError", "code": None})

    def test_unapproved_host_cannot_run_source_probe_cli(self):
        with patch.dict("os.environ", {"UCIE_DISPOSABLE_PINNED_QA": ""}):
            with self.assertRaises(SystemExit) as cm:
                probe.main(["/tmp/ucie-anything"])
        self.assertIn("DISPOSABLE_ISOLATED_LINUX_RUNNER_REQUIRED", str(cm.exception))

    def test_full_snapshot_set_is_mandatory(self):
        for bad in ({}, {"before_manager.py": b""}, None):
            with self.subTest(bad=bad):
                with self.assertRaises(probe.SourceGateError):
                    probe.compare_sources(bad)


if __name__ == "__main__":
    unittest.main()
