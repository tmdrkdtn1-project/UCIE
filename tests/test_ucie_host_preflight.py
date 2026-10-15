"""Stage 8 UCIE host preflight synthetic read-only checks."""
from contextlib import closing
from pathlib import Path
import hashlib
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.host_preflight import inspect_ucie_host


class HostPreflightTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        self.miner = self.runtime / "public_miner.sqlite3"
        self.knowledge = self.runtime / "knowledge.sqlite3"
        with closing(sqlite3.connect(self.miner)) as db, db:
            db.execute("CREATE TABLE candidates (number INTEGER)")
            db.execute("INSERT INTO candidates VALUES(42)")
        with closing(sqlite3.connect(self.knowledge)) as db, db:
            db.execute("CREATE TABLE evidence (number INTEGER)")
            db.execute("INSERT INTO evidence VALUES(42)")

    def test_read_only_observation_not_production_pass(self):
        digest = hashlib.sha256(self.miner.read_bytes()).hexdigest()
        knowledge = hashlib.sha256(self.knowledge.read_bytes()).hexdigest()
        result = inspect_ucie_host(self.root, is_windows=True,
                                   python_version=(3, 15))
        self.assertEqual(result["status"], "READ_ONLY_PRECHECK_COMPLETE")
        self.assertEqual(result["miner"]["records"], 1)
        self.assertEqual(result["knowledge"]["records"], 1)
        self.assertEqual(hashlib.sha256(self.miner.read_bytes()).hexdigest(),
                         digest)
        self.assertEqual(hashlib.sha256(self.knowledge.read_bytes()).hexdigest(),
                         knowledge)
        self.assertFalse(result["production_approved"])
        self.assertEqual(result["scheduler_registration"], "NOT_INSPECTED")
        self.assertEqual(result["database_writes"], 0)

    def test_absent_knowledge_denies_completion(self):
        self.knowledge.unlink()
        result = inspect_ucie_host(self.root, is_windows=True,
                                   python_version=(3, 15))
        self.assertEqual(result["status"], "READ_ONLY_PRECHECK_INCOMPLETE")
        self.assertEqual(result["knowledge"]["state"], "ABSENT_OR_UNSAFE")

    def test_python_version_requires_windows_315(self):
        for windows, version in [(False, (3, 15)), (True, (3, 13))]:
            with self.subTest(version=version):
                result = inspect_ucie_host(self.root, is_windows=windows,
                                           python_version=version)
                self.assertEqual(result["status"], "READ_ONLY_PRECHECK_INCOMPLETE")

    def test_malformed_or_missing_sqlite_is_not_pass(self):
        self.knowledge.write_bytes(b"not a database")
        result = inspect_ucie_host(self.root, is_windows=True,
                                   python_version=(3, 15))
        self.assertNotEqual(result["knowledge"]["state"], "READ_ONLY_INSPECTED")
        self.assertNotEqual(result["status"], "READ_ONLY_PRECHECK_COMPLETE")

    def test_missing_table_is_not_pass(self):
        self.knowledge.unlink()
        with closing(sqlite3.connect(self.knowledge)) as db, db:
            db.execute("CREATE TABLE not_evidence (n INTEGER)")
        result = inspect_ucie_host(self.root, is_windows=True,
                                   python_version=(3, 15))
        self.assertEqual(result["knowledge"]["state"], "SCHEMA_MISSING")

    def test_invalid_metadata_rejected(self):
        with self.assertRaises(ValueError):
            inspect_ucie_host(self.root, is_windows="yes",
                              python_version=(3, 15))


if __name__ == "__main__":
    unittest.main()
