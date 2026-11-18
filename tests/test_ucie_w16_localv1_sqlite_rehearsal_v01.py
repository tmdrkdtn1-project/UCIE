"""W16 LocalV1 root compatibility and isolated SQLite backup rehearsal.

Only disposable synthetic SQLite fixtures are used. No owner D: access, no
C40/task/SQLite operating mutations or actual live root migration.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "scripts" / "ucie_owner_sqlite_rehearsal_v01.py"


def load_snapshot():
    spec = importlib.util.spec_from_file_location(
        "ucie_w16_sqlite_snapshot_test", BACKUP)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class UCIEW16OwnerRehearsalTests(unittest.TestCase):
    def test_no_host_access_by_default(self):
        mod = load_snapshot()
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(mod.main([]), 0)
        receipt = json.loads(out.getvalue())
        self.assertEqual(receipt["status"],
                         "UCIE_W16_CONTRACT_ONLY_NO_HOST_ACCESS")
        self.assertFalse(receipt["source_sqlite_opened"])
        self.assertFalse(receipt["archive_written"])
        self.assertFalse(receipt["tasks_or_c40_modified"])

    def test_online_backup_preserves_committed_rows_without_copied_wal(self):
        mod = load_snapshot()
        with tempfile.TemporaryDirectory(prefix="UCIE_W16_DB_FIXTURE_") as temp:
            top = Path(temp)
            source = top / "runtime"
            source.mkdir()
            primary = source / "public_miner.sqlite3"
            secondary = source / "ucie_queue.sqlite3"
            with sqlite3.connect(primary) as c:
                c.execute("PRAGMA journal_mode=WAL")
                c.execute("CREATE TABLE miner_rows(id INTEGER PRIMARY KEY, value TEXT)")
                c.execute("INSERT INTO miner_rows(value) VALUES('UCIE_PUBLIC_SYNTHETIC')")
            c.close()
            with sqlite3.connect(secondary) as c:
                c.execute("CREATE TABLE queue_rows(id INTEGER PRIMARY KEY)")
                c.execute("INSERT INTO queue_rows VALUES(42)")
            c.close()
            dest = top / "private_rehearsal"
            report = mod.snapshot_databases(source, dest)
            self.assertEqual(
                report["status"],
                "UCIE_W16_PRIVATE_SQLITE_REHEARSAL_COMPLETE__CUTOVER_HOLD")
            self.assertEqual(report["snapshot_db_count"], 2)
            self.assertFalse(report["owner_live_cutover_authorized"])
            self.assertFalse(report["global_snapshot_atomicity_claimed"])
            self.assertTrue((dest / "private_manifest.json").is_file())
            manifest = json.loads((dest / "private_manifest.json").read_text())
            self.assertTrue(manifest["rehearsal_only"])
            self.assertFalse(manifest["single_global_transaction"])
            self.assertEqual(len(manifest["dbs"]), 2)
            with sqlite3.connect(dest / "public_miner.sqlite3") as c:
                self.assertEqual(
                    c.execute("SELECT value FROM miner_rows").fetchone()[0],
                    "UCIE_PUBLIC_SYNTHETIC")
            c.close()
            with sqlite3.connect(dest / "ucie_queue.sqlite3") as c:
                self.assertEqual(c.execute(
                    "SELECT id FROM queue_rows").fetchone()[0], 42)
            c.close()

    def test_existing_destination_is_held_without_overwrite(self):
        mod = load_snapshot()
        with tempfile.TemporaryDirectory(prefix="UCIE_W16_DB_FIXTURE_") as temp:
            top = Path(temp)
            src = top / "runtime"
            src.mkdir()
            with sqlite3.connect(src / "public_miner.sqlite3") as c:
                c.execute("CREATE TABLE v(i INTEGER)")
            c.close()
            target = top / "stage"
            target.mkdir()
            with self.assertRaises(mod.PrivateSnapshotError):
                mod.snapshot_databases(src, target)
            self.assertTrue(target.is_dir())

    def test_missing_main_database_is_held(self):
        mod = load_snapshot()
        with tempfile.TemporaryDirectory(prefix="UCIE_W16_DB_FIXTURE_") as temp:
            top = Path(temp)
            src = top / "runtime"
            src.mkdir()
            with sqlite3.connect(src / "unrelated.sqlite3") as c:
                c.execute("CREATE TABLE sample(i INTEGER)")
            c.close()
            target = top / "stage"
            with self.assertRaises(mod.PrivateSnapshotError):
                mod.snapshot_databases(src, target)
            self.assertFalse(target.exists())

    def test_new_root_localv1_launcher_and_app_both_gate_relocation(self):
        source = (ROOT / "src" / "ucie_miner" / "local_v1_app_v01.py"
                  ).read_text("utf-8")
        launcher = (ROOT / "scripts" / "run_ucie_local_v1_autostart.py"
                    ).read_text("utf-8")
        self.assertIn('parser.add_argument("--owner-relocated-runtime"', source)
        self.assertIn("require_owner_runtime_root(", source)
        self.assertIn("relocated=True, platform=os.name", source)
        self.assertIn("root.resolve() != Path(\"D:/UCIE\").resolve()", source)
        self.assertIn('app_argv.append("--owner-relocated-runtime")', launcher)
        self.assertIn('return app_main(app_argv)', launcher)

    def test_package_and_script_owner_gate_have_identical_critical_checks(self):
        # Future edits must not silently diverge the package's local app
        # gate from the W12 public-miner and scheduler entrypoint gate.
        pkg = (ROOT / "src" / "ucie_miner" /
               "owner_root_gate_v01.py").read_text("utf-8")
        script = (ROOT / "scripts" /
                  "ucie_owner_root_gate_v01.py").read_text("utf-8")
        for needle in (
            'LEGACY = PureWindowsPath(r"D:\\UCIE")',
            'TARGET = PureWindowsPath(r"D:\\UCIE_PROJECT\\UCIE")',
            "MARKER_BYTES = b",
            "def _direct(",
            "def require_owner_runtime_root(",
            'root.parent / "ARCHIVE" / MARKER',
        ):
            self.assertIn(needle, script)
            self.assertIn(needle, pkg)
        self.assertEqual(
            script[script.index("def classify_root("):],
            pkg[pkg.index("def classify_root("):],
        )

    def test_localv1_relocation_does_not_start_server_without_owner_root(self):
        from ucie_miner import local_v1_app_v01 as app
        with redirect_stdout(io.StringIO()) as out:
            result = app.main(["--port", "0", "--owner-relocated-runtime"])
        self.assertEqual(result, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"],
                         "UCIE_LOCAL_V1_EXACT_OWNER_ROOT_REQUIRED")

    def test_snapshot_script_has_no_task_or_c40_mutation_calls(self):
        source = BACKUP.read_text("utf-8")
        for token in (
            "Set-ScheduledTask", "Stop-ScheduledTask", "Start-ScheduledTask",
            "cloudflared.exe", "git clean", "git reset", "git pull",
            "shutil.move(", "shutil.copytree(", "unlink(", "rmtree(",
        ):
            self.assertNotIn(token, source)
        self.assertIn("mode=ro", source)
        self.assertIn("single_global_transaction", source)
        self.assertIn("cutover_data_freshness_accepted", source)


if __name__ == "__main__":
    unittest.main()
