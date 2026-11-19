"""W27 no-host current SQLite metadata inventory; never open database bytes.

Unit tests create synthetic dummy files named like SQLite and verify only
name/count/type/size; they do NOT open a user's SQLite or any Windows owner
Task Scheduler, archive, tunnel, C40 or live host. Synthetic fixtures only.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "ucie_owner_w27_source_metadata_readonly_v01.py"
spec = importlib.util.spec_from_file_location("ucie_w27_metadata_fixture", SOURCE)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

NAMES = {"public_miner.sqlite3"} | {f"synthetic_{i:02}.sqlite3" for i in range(9)}


def fixture(directory: Path, names: set[str] = NAMES) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        (directory / name).write_bytes(b"x" * 512)


class W27MetadataOnlyOwnerPreflightTests(unittest.TestCase):
    def test_contract_only_and_missing_owner_approval_do_not_access_host(self):
        cmd = [sys.executable, "-I", "-B", str(SOURCE)]
        safe = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        self.assertEqual(safe.returncode, 0, safe.stdout + safe.stderr)
        obj = json.loads(safe.stdout)
        self.assertEqual(obj["status"], "UCIE_W27_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(obj["host_files_read"])
        self.assertFalse(obj["sqlite_content_opened"])
        self.assertFalse(obj["task_or_c40_accessed"])
        self.assertFalse(obj["journal_written"])
        denied = subprocess.run(cmd + ["--check-owner"], capture_output=True,
                                text=True, timeout=25)
        self.assertEqual(denied.returncode, 2)
        self.assertEqual(json.loads(denied.stdout)["reason_code"],
                         "UCIE_W27_EXPLICIT_READONLY_OWNER_APPROVAL_REQUIRED")

    def test_exact_names_valid_sizes_without_reading_file_content(self):
        with tempfile.TemporaryDirectory(prefix="ucie_w27_metadata_") as td:
            source = Path(td) / "runtime"
            fixture(source)
            with patch.object(Path, "open", side_effect=AssertionError(
                    "metadata inventory must never open file bytes")):
                result = gate.inventory(source, set(NAMES))
            self.assertEqual(result["database_count"], 10)
            self.assertEqual(result["total_bytes_at_observation"], 5120)
            self.assertTrue(result["direct_non_reparse_paths"])

    def test_wrong_name_or_count_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ucie_w27_name_") as td:
            source = Path(td) / "runtime"
            fixture(source)
            (source / "synthetic_00.sqlite3").rename(
                source / "different_name.sqlite3")
            with self.assertRaisesRegex(gate.InventoryHold,
                                        "LIVE_SQLITE_NAME_SET_CHANGED"):
                gate.inventory(source, set(NAMES))
            (source / "synthetic_01.sqlite3").unlink()
            with self.assertRaisesRegex(gate.InventoryHold,
                                        "LIVE_SQLITE_COUNT_CHANGED"):
                gate.inventory(source, set(NAMES))

    def test_small_or_oversized_db_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ucie_w27_small_") as td:
            source = Path(td) / "runtime"
            fixture(source)
            (source / "synthetic_00.sqlite3").write_bytes(b"tiny")
            with self.assertRaisesRegex(gate.InventoryHold,
                                        "SOURCE_DB_SIZE_OUT_OF_BOUNDS"):
                gate.inventory(source, set(NAMES))
            with (source / "synthetic_00.sqlite3").open("wb") as f:
                f.truncate(gate.MAX_DB + 1)
            with self.assertRaisesRegex(gate.InventoryHold,
                                        "SOURCE_DB_SIZE_OUT_OF_BOUNDS"):
                gate.inventory(source, set(NAMES))

    def test_symlinked_source_entry_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ucie_w27_link_") as td:
            source = Path(td) / "runtime"
            fixture(source)
            target = Path(td) / "ordinary.bin"
            target.write_bytes(b"x" * 512)
            link = source / "synthetic_00.sqlite3"
            link.unlink()
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("This host cannot create symlinks")
            with self.assertRaisesRegex(gate.InventoryHold,
                                        "SOURCE_DB_INDIRECT_OR_NAME_INVALID"):
                gate.inventory(source, set(NAMES))

    def test_historical_names_require_exact_ten_and_public_miner(self):
        with tempfile.TemporaryDirectory(prefix="ucie_w27_hist_") as td:
            source = Path(td) / "runtime"
            fixture(source)
            with self.assertRaisesRegex(gate.InventoryHold,
                                        "HISTORICAL_NAMES_INVALID"):
                gate.inventory(source, set(NAMES) - {"public_miner.sqlite3"})
            with self.assertRaisesRegex(gate.InventoryHold,
                                        "HISTORICAL_NAMES_INVALID"):
                gate.inventory(source, {"public_miner.sqlite3"}
                               | {f"invalid/{i:02}.sqlite3" for i in range(9)})

    def test_source_declares_no_db_open_or_task_mutation(self):
        source = SOURCE.read_text("utf-8")
        self.assertNotIn("sqlite3.connect", source)
        self.assertNotIn("source.open(", source)
        self.assertNotIn("read_bytes(", source)
        self.assertNotIn("write_bytes(", source)
        self.assertNotIn("Stop-ScheduledTask", source)
        self.assertNotIn("Enable-ScheduledTask", source)
        self.assertNotIn("Disable-ScheduledTask", source)
        self.assertNotIn("Stop-Process", source)
        self.assertIn("UCIE_W27_RUNNING_OLD_SOURCE_SQLITE_METADATA_MATCH__LOCKS_NOT_TESTED", source)
        self.assertIn("sqlite_content_opened", source)
        self.assertIn("sqlite_locks_acquired", source)
        self.assertIn("historical_backup_is_current_global_snapshot", source)


if __name__ == "__main__":
    unittest.main()
