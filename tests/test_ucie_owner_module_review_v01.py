"""UCIE owner module contract review: synthetic repos only, no host writes."""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import layout_audit_v01 as layout
from ucie_miner import owner_module_review_v01 as review


class UCIEOwnerLocalContractPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_LOCAL_PACKET_SYNTHETIC_")
        self.addCleanup(self.tmp.cleanup)
        home = Path(self.tmp.name)
        self.stage = home / "UCIE_PROJECT" / "UCIE"
        self.original = home / "UCIE"
        self.stage.mkdir(parents=True)
        self.original.mkdir()
        (self.original / ".ucie_bridge_state").mkdir()
        (self.original / "runtime").mkdir()
        (self.original / ".ucie_bridge_state" / "hold.json").write_bytes(
            b"PRIVATE_BRIDGE_DO_NOT_OPEN_OR_PRINT")
        (self.original / "runtime" / "test.sqlite3").write_bytes(
            b"PRIVATE_DB_DO_NOT_OPEN_OR_PRINT")
        self.owner_protected = {
            name: sha256((self.original / name).read_bytes()).hexdigest()
            for name in (".ucie_bridge_state/hold.json", "runtime/test.sqlite3")
        }

    def _add(self, root: Path, name: str, body: bytes) -> None:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body)

    def _fixtures(self):
        staged = {
            "src/ucie_miner/ready.py":
                b"def preserve(value):\n    return value\n",
            "src/ucie_miner/utility.py":
                b"def unrelated():\n    return 20\n",
            "tests/test_stage_needs_owner.py":
                b"import ucie_miner.old_alpha\n",
        }
        original = {
            "src/ucie_miner/old_alpha.py":
                b"def preserve(value):\n    return value + 2\n",
            "src/ucie_miner/old_beta.py":
                b"class Legacy:\n"
                b"    def bridge(self, value):\n        return value\n",
            "src/ucie_miner/unobserved.py":
                b"def standby():\n    return True\n",
            "tests/test_first_alpha.py":
                b"import ucie_miner.old_alpha\n"
                b"def test_original(): assert True\n",
            "tests/test_second_alpha.py":
                b"import ucie_miner.old_alpha\n"
                b"def test_second(): assert True\n",
            "tests/test_symbol.py":
                b"from ucie_miner import old_alpha\n",
            "scripts/legacy_runner.py":
                b"from ucie_miner.old_beta import Legacy\n",
        }
        for name, value in staged.items():
            self._add(self.stage, name, value)
        for name, value in original.items():
            self._add(self.original, name, value)
        changes = [("untracked", name) for name in original]
        return set(staged), changes

    def _check_preservation(self):
        for name, digest in self.owner_protected.items():
            self.assertEqual(
                sha256((self.original / name).read_bytes()).hexdigest(), digest)

    def test_01_realistic_direct_root_and_unobserved_review_cards(self):
        stage_paths, changes = self._fixtures()
        with patch.object(layout, "_read_owner_ucie_code_bounded",
                          wraps=layout._read_owner_ucie_code_bounded) as reader:
            packet, summary = review._build_owner_packet(
                self.stage, self.original, stage_paths, changes, layout)
        self.assertEqual(packet["schema"], review.PRIVATE_SCHEMA)
        self.assertEqual(summary["schema"], review.SCHEMA)
        self.assertEqual(summary["owner_only_module_paths"], 3)
        self.assertEqual(summary["direct_import_referenced_unique_modules"], 2)
        self.assertEqual(summary["root_symbol_unique_modules"], 1)
        self.assertEqual(summary["both_reference_styles"], 1)
        self.assertEqual(summary["distinct_referenced_union"], 2)
        self.assertEqual(summary["other_modules_held"], 1)
        self.assertEqual(summary["original_only_code_files_without_stage_content_match"], 7)
        self.assertEqual(summary["staged_test_files_with_direct_owner_module_ref"], 1)
        self.assertEqual(summary["original_test_files_with_direct_owner_module_ref"], 2)
        self.assertEqual(summary["direct_module_public_api_items_observed"], 3)
        self.assertEqual(
            summary["direct_public_api_items_with_stage_name_shape_candidate"], 1)
        self.assertFalse(summary["staged_symbols_prove_functional_equivalence"])
        self.assertFalse(summary["original_code_imported_or_executed"])
        self.assertEqual(summary["all_original_modules"], "K0_HOLD")

        by_name = {card["original_module_name"]: card
                   for card in packet["module_cards"]}
        alpha = by_name["ucie_miner.old_alpha"]
        self.assertEqual(alpha["priority"], "P1_DIRECT_SOURCE_CONTRACT_REVIEW")
        self.assertEqual(len(alpha["original_test_paths_with_direct_import"]), 2)
        self.assertEqual(len(alpha["staged_test_paths_with_direct_import"]), 1)
        self.assertIn("src/ucie_miner/ready.py",
                      alpha["public_api"][0][
                          "stage_same_name_and_parameter_shape_paths"])
        self.assertEqual(
            by_name["ucie_miner.unobserved"]["priority"],
            "P3_UNOBSERVED_HOLD")
        self.assertEqual(len(packet["module_cards"]), 3)

        probed = [call.args[1] for call in reader.call_args_list]
        self.assertFalse(any(p.startswith(("runtime/", ".ucie_bridge_state/",
                                           "docs/", ".git/"))
                             for p in probed))
        public = json.dumps(summary, sort_keys=True)
        for secret in ("old_alpha", "old_beta", "unobserved",
                       "test_first_alpha", "PRIVATE_BRIDGE",
                       "PRIVATE_DB", "ready.py"):
            self.assertNotIn(secret, public)
        self._check_preservation()

    def test_02_dynamic_and_relative_imports_not_invented_as_direct(self):
        owner = {"ucie_miner.hidden"}
        examples = (
            b"from . import hidden\n",
            b"import importlib\n"
            b"importlib.import_module('ucie_miner.hidden')\n",
            b"from ucie_miner import *\n",
            b"__import__('ucie_miner.hidden')\n",
        )
        for data in examples:
            direct, ambiguous = review._owner_import_leads(
                data, "tests/test_old.py", owner, layout)
            self.assertFalse(direct)
            self.assertFalse(ambiguous)
        direct, ambiguous = review._owner_import_leads(
            b"from ucie_miner import hidden\n", "tests/test_old.py",
            owner, layout)
        self.assertFalse(direct)
        self.assertEqual(ambiguous, owner)
        self._check_preservation()

    def test_03_private_file_is_exclusive_and_never_in_original(self):
        stage_paths, changes = self._fixtures()
        packet, summary = review._build_owner_packet(
            self.stage, self.original, stage_paths, changes, layout)
        outside = Path(self.tmp.name) / "PRIVATE_REPORTS"
        outside.mkdir()
        private_file = outside / "one-owner-module-packet.json"
        review._write_private_file_exclusive(private_file, packet)
        readback = json.loads(private_file.read_text(encoding="utf-8"))
        self.assertEqual(readback["schema"], review.PRIVATE_SCHEMA)
        self.assertIn("ucie_miner.old_alpha", private_file.read_text())
        with self.assertRaises(ValueError):
            review._write_private_file_exclusive(private_file, packet)
        self.assertFalse((self.stage / "one-owner-module-packet.json").exists())
        self.assertFalse((self.original / "one-owner-module-packet.json").exists())
        self._check_preservation()

    def test_04_private_source_is_never_executed_to_extract_api(self):
        injected = (
            b"def demo(value=__import__('os').system("
            b"'echo OWNER_CODE_SHOULD_NOT_EXECUTE')):\n    return value\n")
        result = review._api_declarations(injected, layout)
        self.assertEqual(result["parse_status"], "STATIC_DECLARATIONS_ONLY")
        self.assertEqual(result["total"], 1)
        serialized = json.dumps(result)
        self.assertNotIn("OWNER_CODE_SHOULD_NOT_EXECUTE", serialized)
        self.assertNotIn("system(", serialized)
        self.assertIsNone(review._api_declarations(
            b"x=1" * (layout.MAX_LOCAL_AST_BYTES + 1),
            layout)["total"])
        self._check_preservation()

    def test_05_host_write_rejects_noncanonical_root(self):
        with self.assertRaises(ValueError):
            review._write_on_owner_host(
                Path("C:/not-ucie"), "a" * 40,
                {"schema": review.PRIVATE_SCHEMA}, layout)
        self._check_preservation()

    def test_06_noncanonical_root_is_rejected_before_loading_sibling(self):
        with patch.object(
                review, "_load_trusted_audit",
                side_effect=AssertionError("should not load sibling source")):
            if os.name != "nt":
                with self.assertRaises(ValueError):
                    review.run_owner_review(write_private_report=True)
        self._check_preservation()

    def test_07_isolated_cli_fails_closed_without_owner_host(self):
        if os.name == "nt":
            self.skipTest("Actual owner Windows host must not be probed by CI")
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(review.__file__).resolve())],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=20, check=False, text=True)
        self.assertEqual(result.returncode, 2)
        data = json.loads(result.stdout)
        self.assertEqual(
            data["status"], "UCIE_OWNER_MODULE_REVIEW_FAIL_CLOSED")
        self.assertNotIn("PRIVATE_BRIDGE", result.stdout)
        self.assertNotIn("PRIVATE_DB", result.stdout)
        self._check_preservation()

    def test_08_cli_errors_never_print_private_exception_detail(self):
        sink = StringIO()
        with patch.object(review, "run_owner_review",
                          side_effect=ValueError(
                              "sensitive owner file path should not appear")), \
                patch("sys.argv", ["ucie-owner", "--write-private-report"]), \
                redirect_stdout(sink):
            status = review.main()
        self.assertEqual(status, 2)
        report = json.loads(sink.getvalue())
        self.assertEqual(report["status"], "UCIE_OWNER_MODULE_REVIEW_FAIL_CLOSED")
        self.assertNotIn("sensitive owner file path", sink.getvalue())
        self._check_preservation()


if __name__ == "__main__":
    unittest.main()
