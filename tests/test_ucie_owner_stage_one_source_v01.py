"""UCIE one-module actual source staging: synthetic files, no owner host data."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ucie_miner import layout_audit_v01 as layout

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ucie_owner_stage_one_source_v01.py"
_spec = importlib.util.spec_from_file_location("_ucie_stage_one_synthetic", _SCRIPT)
stage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stage)


class UCIEOneSourceStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="UCIE_STAGE_ONE_SYNTHETIC_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / "UCIE"
        self.dev = self.root / "UCIE_PROJECT" / "UCIE"
        for root in (self.original, self.dev):
            (root / "src" / "ucie_miner").mkdir(parents=True)
        self._make_packet()
        self.relp = "src/ucie_miner/owner_01.py"
        self.bytecode = b"def original_entry():\n    return 4\n"
        source = self.original / self.relp
        source.write_bytes(self.bytecode)
        self.source_sha = sha256(source.read_bytes()).digest()

    def _make_packet(self):
        cards = []
        for n in range(1, 21):
            rel = f"src/ucie_miner/owner_{n:02d}.py"
            cards.append({
                "original_relative_src_path": rel,
                "original_module_name": f"ucie_miner.owner_{n:02d}",
                "priority": ("P1_DIRECT_SOURCE_CONTRACT_REVIEW" if n <= 8
                             else "P2_ROOT_SYMBOL_AMBIGUITY_HOLD" if n <= 16
                             else "P3_UNOBSERVED_HOLD"),
                "current_action": "K0_HOLD",
            })
        packet = {
            "schema": stage.OWNER_PACKET_SCHEMA,
            "status": "PRIVATE_LOCAL_REVIEW_ONLY__NO_MIGRATION",
            "do_not_upload_or_paste": True,
            "contains_original_code_bodies": False,
            "module_cards": cards,
        }
        self.packet = self.root / "UCIE_OWNER_MODULE_REVIEW_SYNTHETIC.json"
        self.packet.write_text(json.dumps(packet), encoding="utf-8")

    def _unchanged(self):
        self.assertEqual(sha256(
            (self.original / self.relp).read_bytes()).digest(), self.source_sha)

    def test_01_packet_p1_selection_is_exactly_eight_modules(self):
        cards = stage._read_priority_packet(self.packet, layout)
        self.assertEqual(len(cards), 8)
        self.assertEqual(cards[0]["original_module_name"],
                         "ucie_miner.owner_01")
        self.assertEqual(cards[-1]["original_module_name"],
                         "ucie_miner.owner_08")
        self._unchanged()

    def test_02_one_real_source_file_is_written_only_to_new_dev_tree(self):
        selected = stage._read_priority_packet(self.packet, layout)[0]
        source_name = selected["original_relative_src_path"]
        target = stage._validate_absent_target(self.dev, source_name, layout)
        data = stage._read_one_source(self.original, source_name, layout)
        stage._exclusive_copy(data, target, layout)
        self.assertTrue(target.is_file())
        self.assertEqual(target.read_bytes(), self.bytecode)
        self.assertFalse((self.dev / "runtime").exists())
        self.assertFalse((self.original / "src/ucie_miner/other.py").exists())
        self._unchanged()
        with self.assertRaises((FileExistsError, stage.StageOneError)):
            stage._exclusive_copy(data, target, layout)
        self._unchanged()

    def test_03_never_replace_existing_staged_source(self):
        target = self.dev / self.relp
        target.write_bytes(b"NO_OVERWRITE_EXISTING_STAGE")
        with self.assertRaises(stage.StageOneError):
            stage._validate_absent_target(self.dev, self.relp, layout)
        self.assertEqual(target.read_bytes(), b"NO_OVERWRITE_EXISTING_STAGE")
        self._unchanged()

    def test_04_traversal_private_runtime_and_non_source_rejected(self):
        for name in ("../UCIE/root.py", "runtime/secret.py",
                     ".ucie_bridge_state/private.py",
                     "src/ucie_miner/../../secrets.py",
                     "tests/test_private.py", "scripts/runner.py",
                     "src/ucie_miner/saved.bak"):
            with self.subTest(name=name), self.assertRaises(stage.StageOneError):
                stage._module_path_name(layout, name)
        self._unchanged()

    def test_05_untrusted_packet_is_rejected_before_module_copy(self):
        data = json.loads(self.packet.read_text(encoding="utf-8"))
        data["module_cards"][0]["original_relative_src_path"] = (
            "src/ucie_miner/../../private.py")
        self.packet.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(stage.StageOneError):
            stage._read_priority_packet(self.packet, layout)
        self.assertFalse((self.dev / self.relp).exists())
        self._unchanged()

    def test_06_invalid_owner_python_syntax_is_not_staged(self):
        source = self.original / self.relp
        source.write_bytes(b"def : invalid\n")
        with self.assertRaises(stage.StageOneError):
            stage._read_one_source(self.original, self.relp, layout)
        self.assertFalse((self.dev / self.relp).exists())

    def test_07_existing_junction_or_link_parent_is_rejected(self):
        other = self.root / "OTHER"
        other.mkdir()
        link = self.dev / "src" / "ucie_miner" / "linked"
        try:
            link.symlink_to(other, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks not enabled on this runner")
        with self.assertRaises(stage.StageOneError):
            stage._validate_absent_target(
                self.dev, "src/ucie_miner/linked/untrusted.py", layout)
        self._unchanged()

    def test_08_stage_head_owner_approval_and_origin_guard_are_required(self):
        with self.assertRaises(stage.StageOneError):
            stage._checks(self.dev, self.original, layout, "invalid", 1)
        with self.assertRaises(stage.StageOneError):
            stage._checks(self.dev, self.original, layout, "a"*40, 9)
        if os.name != "nt":
            with self.assertRaises(stage.StageOneError):
                stage.stage_one(expected_head="a"*40, module_index=1,
                                mode="apply",
                                approval="APPROVE_UCIE_ONE_MODULE_01_TO_NEW_DEV_ROOT")
        self._unchanged()

    def test_09_apply_requires_exact_module_specific_approval(self):
        stage._require_exact_per_module_approval("preview", 1, "")
        stage._require_exact_per_module_approval(
            "apply", 1, "APPROVE_UCIE_ONE_MODULE_01_TO_NEW_DEV_ROOT")
        with self.assertRaises(stage.StageOneError):
            stage._require_exact_per_module_approval("apply", 1, "")
        with self.assertRaises(stage.StageOneError):
            stage._require_exact_per_module_approval(
                "apply", 2, "APPROVE_UCIE_ONE_MODULE_01_TO_NEW_DEV_ROOT")
        with self.assertRaises(stage.StageOneError):
            stage._require_exact_per_module_approval("apply", 9, "")
        self.assertFalse((self.dev / self.relp).exists())
        self._unchanged()

    def test_10_status_receipt_is_count_only_and_no_private_source(self):
        if os.name != "nt":
            with patch("sys.argv", [
                str(_SCRIPT), "--expected-head", "a"*40, "--mode", "preview"
            ]):
                from contextlib import redirect_stdout
                from io import StringIO
                output = StringIO()
                with redirect_stdout(output):
                    code = stage.main()
                self.assertEqual(code, 2)
                result = json.loads(output.getvalue())
                self.assertEqual(result["status"], "UCIE_STAGE_ONE_FAIL_CLOSED")
                self.assertNotIn("owner_01", output.getvalue())
        self._unchanged()


if __name__ == "__main__":
    unittest.main()
