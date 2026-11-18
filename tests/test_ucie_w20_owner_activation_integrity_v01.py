"""W20 activation drift gate: ten-db synthetic acceptance, not owner host GO."""
from __future__ import annotations

from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
W19PATH = ROOT / "scripts" / "ucie_owner_w19_lockstep_handoff_v01.py"
W20PATH = ROOT / "scripts" / "ucie_owner_w20_activation_integrity_v01.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w19 = load(W19PATH, "w19_lease_fixture")
w20 = load(W20PATH, "w20_lease_fixture")


class W20ActivationDriftTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="ucie_w20_")
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        self.source = root / "original"
        self.source.mkdir()
        self.archive = root / "owner_archive"
        self.archive.mkdir()
        self.staged = root / "new_ucie"
        self.staged.mkdir()
        self.private = self.archive / "final_data"
        self.target = self.staged / "runtime"
        self.names = {"public_miner.sqlite3"} | {
            f"ucie_test_{i:02d}.sqlite3" for i in range(9)
        }
        for i, name in enumerate(sorted(self.names)):
            with closing(sqlite3.connect(self.source / name)) as db:
                db.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY, label TEXT)")
                db.execute("INSERT INTO events VALUES (?, 'synthetic')", (i,))
                db.commit()
        receipt = w19.handoff_locked(self.source, self.private, self.target,
                                     self.names)
        self.assertEqual(receipt["database_count"], 10)
        self.manifest = self.private / "private_handoff_manifest.json"

    def check(self, **kw):
        return w20.compare_frozen_sqlite(self.source, self.private, self.target,
                                         self.manifest, **kw)

    def test_ten_exact_staged_images_accepted_but_live_go_never_claimed(self):
        out = self.check()
        self.assertEqual(out["sqlitedb_count"], 10)
        self.assertEqual(
            out["status"], "UCIE_W20_FROZEN_SQLITE_IMAGES_MATCH__LIVE_ACTIVATION_HOLD")
        self.assertTrue(out["sqlite_writer_locks_overlap"])
        self.assertFalse(out["old_writers_permanently_stopped"])
        self.assertFalse(out["c40_mcp_round_trip_verified"])
        self.assertFalse(out["localv1_new_process_healthy"])
        self.assertFalse(out["live_cutover_authorized"])

    def test_one_source_write_after_w19_is_denied(self):
        with closing(sqlite3.connect(self.source / "public_miner.sqlite3")) as c:
            c.execute("INSERT INTO events VALUES (500, 'changed')")
            c.commit()
        with self.assertRaisesRegex(w20.ActivationHold, "SOURCE_SQLITE_DRIFT"):
            self.check()

    def test_one_new_root_write_is_denied(self):
        with closing(sqlite3.connect(self.target / "public_miner.sqlite3")) as c:
            c.execute("INSERT INTO events VALUES (500, 'changed')")
            c.commit()
        with self.assertRaisesRegex(w20.ActivationHold, "FINAL_COPY_DIGEST"):
            self.check()

    def test_one_protected_private_archive_tamper_is_denied(self):
        db = self.private / "public_miner.sqlite3"
        db.write_bytes(db.read_bytes()[:-1] + b"x")
        with self.assertRaisesRegex(w20.ActivationHold, "FINAL_COPY_DIGEST"):
            self.check()

    def test_manifest_changed_status_is_denied(self):
        m = json.loads(self.manifest.read_text("utf-8"))
        m["sqlite_writer_barrier_held"] = False
        self.manifest.write_text(json.dumps(m), encoding="utf-8")
        with self.assertRaisesRegex(w20.ActivationHold, "PROVENANCE_REJECTED"):
            self.check()

    def test_extra_source_database_is_denied(self):
        with closing(sqlite3.connect(self.source / "unknown.sqlite3")) as db:
            db.execute("CREATE TABLE other(x)")
            db.commit()
        with self.assertRaisesRegex(w20.ActivationHold, "DATABASE_SET_DRIFT"):
            self.check()

    def test_missing_target_database_is_denied(self):
        (self.target / "ucie_test_00.sqlite3").unlink()
        with self.assertRaisesRegex(w20.ActivationHold, "DATABASE_SET_DRIFT"):
            self.check()

    def test_busy_writer_holds_and_never_overwrites(self):
        p = self.source / "public_miner.sqlite3"
        with closing(sqlite3.connect(p, timeout=0.5,
                                     isolation_level=None)) as db:
            db.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                self.check()
            db.rollback()
        self.assertEqual(self.check()["sqlitedb_count"], 10)

    def test_lock_barrier_blocks_competing_sqlite_writer(self):
        blocked = []

        def barrier():
            for name in sorted(self.names)[:2]:
                with closing(sqlite3.connect(self.source / name,
                                             timeout=0.05)) as contender:
                    with self.assertRaises(sqlite3.OperationalError):
                        contender.execute(
                            "INSERT INTO events VALUES (999, 'blocked')")
                blocked.append(name)

        self.check(at_barrier=barrier)
        self.assertEqual(len(blocked), 2)

    def test_symlink_target_db_rejected_without_following(self):
        name = "public_miner.sqlite3"
        target = self.target / name
        new = self.target / "held_copy"
        shutil.copyfile(target, new)
        target.unlink()
        try:
            target.symlink_to(new)
        except (OSError, NotImplementedError):
            self.skipTest("symlink not available in this Windows environment")
        with self.assertRaisesRegex(w20.ActivationHold, "REPARSE_DATABASE"):
            self.check()

    def test_no_host_default_and_denied_owner_approval(self):
        cmd = [sys.executable, "-I", "-B", str(W20PATH)]
        safe = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        self.assertEqual(safe.returncode, 0, safe.stderr)
        payload = json.loads(safe.stdout)
        self.assertEqual(payload["status"], "UCIE_W20_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(payload["tasks_queried"])
        no = subprocess.run(cmd + ["--verify"], capture_output=True,
                            text=True, timeout=25)
        self.assertEqual(no.returncode, 2)
        self.assertEqual(json.loads(no.stdout)["reason_code"],
                         "UCIE_W20_EXPLICIT_OWNER_APPROVAL_REQUIRED")


if __name__ == "__main__":
    unittest.main()
