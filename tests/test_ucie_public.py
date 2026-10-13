"""Self-contained offline, synthetic-only regression checks."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ucie_public.policy import PolicyError, validate_entry, load_curated
from ucie_public.rulepack import generate_keys, publish_demo, verify_demo, run_probe

class PublicOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = load_curated(ROOT)[0]

    def entry(self):
        return copy.deepcopy(self.example)

    def test_example_exists(self):
        self.assertEqual(len(load_curated(ROOT)), 1)

    def test_safe_syntax(self):
        self.assertEqual(run_probe(self.entry())["result"], "PASS_SYNTAX_ONLY")

    def test_private_field(self):
        entry = self.entry()
        entry["project_id"] = "other"
        with self.assertRaises(PolicyError):
            validate_entry(entry)

    def test_private_description(self):
        entry = self.entry()
        entry["guidance"] = "Read internal_workroom first"
        with self.assertRaises(PolicyError):
            validate_entry(entry)

    def test_private_path(self):
        entry = self.entry()
        entry["problem"] = "Refer to C:\\Users\\owner\\file.py"
        with self.assertRaises(PolicyError):
            validate_entry(entry)

    def test_token_marker(self):
        entry = self.entry()
        entry["guidance"] = "Bearer abcdefghijklmnop"
        with self.assertRaises(PolicyError):
            validate_entry(entry)

    def test_nonpublic_source(self):
        entry = self.entry()
        entry["source"]["kind"] = "private_incident"
        with self.assertRaises(PolicyError):
            validate_entry(entry)

    def test_fake_official_host(self):
        entry = self.entry()
        entry["source"]["url"] = "https://docs.python.org.invalid/3/"
        with self.assertRaises(PolicyError):
            validate_entry(entry)

    def test_no_shell_execution(self):
        entry = self.entry()
        entry["probe"]["snippet"] = "import os\nos.system('whoami')"
        with self.assertRaises(PolicyError):
            run_probe(entry)

    def test_bad_syntax(self):
        entry = self.entry()
        entry["probe"]["snippet"] = "def broken("
        with self.assertRaises(PolicyError):
            run_probe(entry)

class RulepackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "build").mkdir()
        (self.root / "curated_public").mkdir()
        source = ROOT / "curated_public" / "PUB-PY-AST-SYNTAX.json"
        (self.root / "curated_public" / source.name).write_bytes(source.read_bytes())
        self.private, self.public = generate_keys(self.root / "keys")
        self.package = publish_demo(self.root, self.private, self.root / "build" / "test.zip", serial=5)

    def test_signed_demo(self):
        self.assertEqual(verify_demo(self.package, self.public)["result"], "DEMO_VERIFIED")

    def test_not_production(self):
        self.assertFalse(verify_demo(self.package, self.public)["production_approved"])

    def test_serial_rollback(self):
        with self.assertRaises(PolicyError):
            verify_demo(self.package, self.public, min_serial=6)

    def test_expired(self):
        future = datetime.now(timezone.utc) + timedelta(days=90)
        with self.assertRaises(PolicyError):
            verify_demo(self.package, self.public, at_time=future)

    def test_wrong_key(self):
        _, other_pub = generate_keys(self.root / "other")
        with self.assertRaises(PolicyError):
            verify_demo(self.package, other_pub)

    def test_refuse_overwrite(self):
        with self.assertRaises(PolicyError):
            publish_demo(self.root, self.private, self.package)

    def test_reject_unexpected_archive_entries(self):
        altered = self.root / "build" / "bad.zip"
        with zipfile.ZipFile(self.package) as source, zipfile.ZipFile(altered, "w") as dest:
            for name in source.namelist():
                dest.writestr(name, source.read(name))
            dest.writestr("../unexpected.txt", "no")
        with self.assertRaises(PolicyError):
            verify_demo(altered, self.public)

if __name__ == "__main__":
    unittest.main()
