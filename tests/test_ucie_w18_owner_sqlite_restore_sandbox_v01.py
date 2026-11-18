"""W18: private SQLite restore rehearsal using disposable synthetic evidence.

No D: reads, PyPI, C40, Windows Task Scheduler, or operating DB access in CI.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import file_digest
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ucie_owner_sqlite_restore_sandbox_v01.py"


def load():
    spec = importlib.util.spec_from_file_location(
        "ucie_w18_test_restore_sandbox", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synthetic_w16(folder: Path, *, extra=False) -> tuple[Path, int, dict]:
    source = folder / "private_w16"
    source.mkdir()
    rows: list[dict] = []
    for name in ("public_miner.sqlite3", "ucie_queue.sqlite3"):
        database = source / name
        with sqlite3.connect(database) as conn:
            conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO sample(value) VALUES (?)", ("FIRST_PARTY_SYNTHETIC",))
        with database.open("rb") as stream:
            checksum = file_digest(stream, "sha256").hexdigest()
        rows.append({
            "name": name, "sha256": checksum, "bytes": database.stat().st_size})
    manifest = {
        "schema": "UCIE_W16_OWNER_SQLITE_REHEARSAL_V01",
        "status": "UCIE_W16_PRIVATE_SQLITE_REHEARSAL_COMPLETE",
        "rehearsal_only": True,
        "single_global_transaction": False,
        "cutover_data_freshness_accepted": False,
        "original_sqlite_updated_by_ucie_sql": False,
        "tasks_or_c40_modified": False,
        "owner_live_cutover_authorized": False,
        "dbs": rows,
    }
    (source / "private_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8")
    if extra:
        (source / "unexpected.log").write_text("synthetic", encoding="utf-8")
    return source, sum(r["bytes"] for r in rows), manifest


class W18RestoreSandboxTests(unittest.TestCase):
    def test_contract_does_not_use_host(self):
        m = load()
        with redirect_stdout(io.StringIO()) as result:
            self.assertEqual(m.main([]), 0)
        r = json.loads(result.getvalue())
        self.assertEqual(r["status"], "UCIE_W18_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(r["sandbox_written"])
        self.assertFalse(r["snapshot_opened"])

    def test_reconstruct_two_verified_dbs_without_modifying_w16_snapshot(self):
        m = load()
        with tempfile.TemporaryDirectory(prefix="UCIE_W18_RESTORE_") as temp:
            root = Path(temp)
            source, size, old_manifest = synthetic_w16(root)
            original = {p.name: p.read_bytes() for p in source.iterdir()}
            dest = root / "private_w18_sandbox"
            status = m.restore_rehearsal(
                source, dest, expected_count=2, expected_total=size)
            self.assertEqual(
                status["status"], "UCIE_W18_PRIVATE_RESTORE_PASS__LIVE_CUTOVER_HOLD")
            self.assertEqual(status["restored_database_count"], 2)
            self.assertEqual(status["restored_bytes"], size)
            self.assertFalse(status["new_root_runtime_data_written"])
            self.assertFalse(status["live_cutover_authorized"])
            for row in old_manifest["dbs"]:
                with sqlite3.connect(dest / row["name"]) as conn:
                    self.assertEqual(
                        conn.execute("SELECT value FROM sample").fetchone()[0],
                        "FIRST_PARTY_SYNTHETIC")
                self.assertEqual((dest / row["name"]).read_bytes(),
                                 original[row["name"]])
            self.assertEqual(
                {p.name: p.read_bytes() for p in source.iterdir()}, original)
            private_receipt = json.loads(
                (dest / "private_restore_receipt.json").read_text("utf-8"))
            self.assertTrue(private_receipt["w16_snapshot_rehearsal_only"])
            self.assertFalse(private_receipt["global_consistent_cutover_data"])
            self.assertFalse(private_receipt["tasks_or_c40_modified"])

    def test_tampered_w16_file_fails_before_creating_destination(self):
        m = load()
        with tempfile.TemporaryDirectory(prefix="UCIE_W18_RESTORE_") as temp:
            root = Path(temp)
            source, size, _ = synthetic_w16(root)
            db = source / "public_miner.sqlite3"
            with db.open("ab") as f:
                f.write(b"TAMPERED")
            dest = root / "target"
            with self.assertRaisesRegex(m.RestoreHold, "HASH_OR_LENGTH"):
                m.restore_rehearsal(
                    source, dest, expected_count=2, expected_total=size)
            self.assertFalse(dest.exists())

    def test_existing_output_never_overwritten_and_extra_file_denied(self):
        m = load()
        with tempfile.TemporaryDirectory(prefix="UCIE_W18_RESTORE_") as temp:
            root = Path(temp)
            source, size, _ = synthetic_w16(root, extra=True)
            dest = root / "target"
            with self.assertRaisesRegex(m.RestoreHold, "UNLISTED"):
                m.restore_rehearsal(
                    source, dest, expected_count=2, expected_total=size)
            self.assertFalse(dest.exists())
            dest.mkdir()
            protected = dest / "keep.txt"
            protected.write_text("PRESERVE", encoding="utf-8")
            with self.assertRaisesRegex(m.RestoreHold, "NO_OVERWRITE"):
                m.restore_rehearsal(source, dest)
            self.assertEqual(protected.read_text(), "PRESERVE")

    def test_global_atomicity_forgery_denied(self):
        m = load()
        with tempfile.TemporaryDirectory(prefix="UCIE_W18_RESTORE_") as temp:
            root = Path(temp)
            source, _, manifest = synthetic_w16(root)
            manifest["single_global_transaction"] = True
            (source / "private_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(m.RestoreHold, "PROVENANCE"):
                m.restore_rehearsal(source, root / "target")
            self.assertFalse((root / "target").exists())

    def test_pins_owner_W16_snapshot_and_W17_new_root_without_live_access(self):
        code = SCRIPT.read_text("utf-8")
        for expected in (
            "EXPECTED_DB_COUNT = 10",
            "EXPECTED_SNAPSHOT_BYTES = 5_656_576",
            'ROOT = Path(r"D:\\UCIE_PROJECT\\UCIE")',
            'W16 = ARCHIVE / "UCIE_W16_SQLITE_REHEARSAL_V01"',
            'SANDBOX = ARCHIVE / "UCIE_W18_SQLITE_RESTORE_SANDBOX_V01"',
            'OWNER_MARKER = ARCHIVE / ".ucie_owner_runtime_opt_in_v01"',
            'if (ROOT / "runtime").exists() or OWNER_MARKER.exists():',
            'target.as_uri() + "?mode=ro&immutable=1"',
            "PRAGMA quick_check",
            "UCIE_W18_PRIVATE_RESTORE_PASS__LIVE_CUTOVER_HOLD",
        ):
            self.assertIn(expected, code)
        for forbidden in (
            'D:\\UCIE\\runtime', 'Set-ScheduledTask', 'Start-ScheduledTask',
            'Stop-ScheduledTask', 'cloudflared.exe', 'git clean', 'git reset',
            'shutil.rmtree', 'shutil.move', '.unlink(',
        ):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
