"""Synthetic-only W19 owner handoff regression tests (no host task/service writes)."""
from __future__ import annotations

from contextlib import closing
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_w19_lockstep_handoff_v01.py"
SPEC = importlib.util.spec_from_file_location("ucie_w19_handoff", SCRIPT)
assert SPEC and SPEC.loader
w19 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w19)


class W19SyntheticHandoffTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="ucie_w19_")
        self.addCleanup(self.scratch.cleanup)
        base = Path(self.scratch.name)
        self.source = base / "live_runtime"
        self.source.mkdir()
        self.archive = base / "archive"
        self.archive.mkdir()
        self.target_parent = base / "new_root"
        self.target_parent.mkdir()
        self.private = self.archive / "once"
        self.target = self.target_parent / "runtime"
        self.names = {"public_miner.sqlite3"} | {
            f"ucie_test_{index:02d}.sqlite3" for index in range(9)
        }
        for i, name in enumerate(sorted(self.names)):
            with closing(sqlite3.connect(self.source / name)) as db:
                db.execute("CREATE TABLE IF NOT EXISTS events(seq INTEGER, label TEXT)")
                db.execute("INSERT INTO events VALUES (?, ?)", (i, "UCIE-SYNTHETIC"))
                db.commit()

    def snapshot(self, **kwargs):
        return w19.handoff_locked(
            self.source, self.private, self.target, self.names, **kwargs)

    def test_captures_ten_consistent_writer_locked_db_images(self):
        seen = []

        def barrier():
            # Exercise a second independent SQLite writer while *all* source
            # locks are held; it must fail until the snapshot completes.
            for name in sorted(self.names)[:2]:
                with closing(sqlite3.connect(
                        self.source / name, timeout=0.05)) as contender:
                    with self.assertRaises(sqlite3.OperationalError):
                        contender.execute("INSERT INTO events VALUES (99, 'blocked')")
                seen.append(name)

        result = self.snapshot(at_barrier=barrier)
        self.assertEqual(len(seen), 2)
        self.assertEqual(result["database_count"], 10)
        self.assertTrue(result["sqlite_writer_barrier_held"])
        self.assertEqual(result["sqlite_quick_check"], "PASS")
        self.assertFalse(result["tasks_rebound_or_enabled"])
        self.assertFalse(result["c40_tunnel_health_verified"])
        self.assertFalse(result["live_cutover_authorized"])
        manifest = json.loads(
            (self.private / "private_handoff_manifest.json").read_text("utf-8"))
        self.assertEqual(len(manifest["dbs"]), 10)
        self.assertFalse(manifest["external_non_sqlite_state_frozen"])
        for name in self.names:
            with closing(sqlite3.connect(self.target / name)) as conn:
                self.assertEqual(
                    conn.execute("SELECT count(*) FROM events").fetchone()[0], 1)
                self.assertEqual(conn.execute("PRAGMA quick_check").fetchall(),
                                 [("ok",)])
            with closing(sqlite3.connect(self.source / name)) as conn:
                self.assertEqual(
                    conn.execute("SELECT count(*) FROM events").fetchone()[0], 1)
            self.assertEqual(
                (self.private / name).read_bytes(),
                (self.target / name).read_bytes())

    def test_refuses_any_existing_output_without_modification(self):
        self.target.mkdir()
        sentinel = self.target / "preserve.txt"
        sentinel.write_text("do-not-change", encoding="utf-8")
        with self.assertRaisesRegex(w19.HandoffHold, "OUTPUT_OR_DIRECT_PATH"):
            self.snapshot()
        self.assertEqual(sentinel.read_text("utf-8"), "do-not-change")
        self.assertFalse(self.private.exists())

    def test_refuses_repeat_after_success(self):
        self.snapshot()
        with self.assertRaisesRegex(w19.HandoffHold, "OUTPUT_OR_DIRECT_PATH"):
            self.snapshot()
        self.assertTrue((self.private / "private_handoff_manifest.json").is_file())

    def test_source_set_drift_rejected_before_output_reservation(self):
        with closing(sqlite3.connect(self.source / "extra.sqlite3")) as conn:
            conn.execute("CREATE TABLE drift(x)")
            conn.commit()
        with self.assertRaisesRegex(w19.HandoffHold, "CURRENT_DB_SET_CHANGED"):
            self.snapshot()
        self.assertFalse(self.private.exists())
        self.assertFalse(self.target.exists())

    def test_busy_writer_rejected_before_output(self):
        busy = self.source / sorted(self.names)[0]
        with closing(sqlite3.connect(busy, timeout=1, isolation_level=None)) as other:
            other.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                self.snapshot()
            other.rollback()
        self.assertFalse(self.private.exists())
        self.assertFalse(self.target.exists())

    def test_corrupt_source_rejected_before_output(self):
        damaged = self.source / sorted(self.names)[-1]
        damaged.write_bytes(b"not a SQLite database" * 40)
        with self.assertRaises(sqlite3.DatabaseError):
            self.snapshot()
        self.assertFalse(self.private.exists())
        self.assertFalse(self.target.exists())

    def test_symlink_source_db_refused(self):
        if not hasattr(Path, "symlink_to"):
            self.skipTest("no symlink support")
        name = sorted(self.names)[0]
        original = self.source / name
        other = self.source.parent / "test_data"
        shutil.copyfile(original, other)
        original.unlink()
        try:
            original.symlink_to(other)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks denied on this Windows runner")
        with self.assertRaisesRegex(w19.HandoffHold, "SOURCE_DB_TYPE_OR_SIZE"):
            self.snapshot()
        self.assertFalse(self.private.exists())

    def test_default_contract_only_and_approval_denial(self):
        cmd = [sys.executable, "-I", "-B", str(SCRIPT)]
        safe = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=25, check=False)
        self.assertEqual(safe.returncode, 0, safe.stderr)
        result = json.loads(safe.stdout.strip())
        self.assertEqual(result["status"], "UCIE_W19_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(result["task_or_c40_accessed"])
        bad = subprocess.run(
            cmd + ["--prepare"], capture_output=True, text=True,
            timeout=25, check=False)
        self.assertEqual(bad.returncode, 2, bad.stderr)
        result = json.loads(bad.stdout.strip())
        self.assertEqual(result["status"], "UCIE_W19_FINAL_SQLITE_HANDOFF_HOLD")
        self.assertEqual(result["reason_code"],
                         "UCIE_W19_EXPLICIT_OWNER_APPROVAL_REQUIRED")

    def test_wrong_platform_cannot_operate_with_approval(self):
        if sys.platform.startswith("win"):
            self.skipTest("native Windows no interactive owner approval fixture")
        cmd = [sys.executable, "-I", "-B", str(SCRIPT), "--prepare",
               "--owner-approval", w19.APPROVAL]
        completed = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=25, check=False)
        self.assertEqual(completed.returncode, 2, completed.stderr)
        result = json.loads(completed.stdout.strip())
        self.assertEqual(result["reason_code"],
                         "UCIE_W19_INTERACTIVE_WINDOWS_OWNER_REQUIRED")


if __name__ == "__main__":
    unittest.main()
