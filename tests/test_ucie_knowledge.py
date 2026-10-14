"""Offline Stage 4 knowledge isolation and backup tests."""
from pathlib import Path
import hashlib
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from ucie_miner.knowledge import import_miner_candidates,open_knowledge,propose_rule,backup_knowledge


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        runtime=self.root/"runtime"
        runtime.mkdir()
        with sqlite3.connect(runtime/"public_miner.sqlite3") as db:
            db.execute("""CREATE TABLE candidates(
               source TEXT, pr_number INTEGER, public_url TEXT, merged_at TEXT,
               evidence_sha256 TEXT, status TEXT)""")
            db.execute("INSERT INTO candidates VALUES(?,?,?,?,?,?)",
                ("python/cpython",42,"https://github.com/python/cpython/pull/42",
                 "2026-10-01T00:00:00Z","a"*64,"UNVERIFIED_CANDIDATE_ONLY"))

    def test_import_idempotent_and_original_unchanged(self):
        db=self.root/"runtime"/"public_miner.sqlite3"
        digest=hashlib.sha256(db.read_bytes()).hexdigest()
        a=import_miner_candidates(self.root)
        b=import_miner_candidates(self.root)
        self.assertEqual(a["new_rows"],1)
        self.assertEqual(b["new_rows"],0)
        self.assertEqual(b["knowledge_rows"],1)
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),digest)

    def test_rule_requires_matching_evidence_and_cannot_promote(self):
        import_miner_candidates(self.root)
        result=propose_rule(self.root,source="python/cpython",number=42,
                            pattern_code="BAD_API_CALL",proposal_digest="b"*64)
        self.assertFalse(result["auto_promoted"])
        with open_knowledge(self.root) as db:
            self.assertEqual(db.execute("SELECT status FROM rule_candidates").fetchone()[0],
                             "UNVERIFIED_CANDIDATE_ONLY")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE rule_candidates SET status='VERIFIED'")

    def test_unapproved_source_rejected(self):
        with sqlite3.connect(self.root/"runtime"/"public_miner.sqlite3") as db:
            db.execute("INSERT INTO candidates VALUES(?,?,?,?,?,?)",
                ("private/secret",11,"https://github.com/private/secret/pull/11",
                 "2026-10-01T00:00:00Z","a"*64,"UNVERIFIED_CANDIDATE_ONLY"))
        with self.assertRaises(ValueError):
            import_miner_candidates(self.root)

    def test_backup_restore_offline(self):
        import_miner_candidates(self.root)
        dest=self.root/"runtime"/"knowledge_snapshot.sqlite3"
        backup_knowledge(self.root,dest)
        with sqlite3.connect(dest) as db:
            self.assertEqual(db.execute("PRAGMA quick_check").fetchone()[0],"ok")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],1)
        with self.assertRaises(ValueError):
            backup_knowledge(self.root,dest)

    def test_missing_legacy_database_denied(self):
        (self.root/"runtime"/"public_miner.sqlite3").unlink()
        with self.assertRaises(ValueError):
            import_miner_candidates(self.root)


if __name__=="__main__":
    unittest.main()
