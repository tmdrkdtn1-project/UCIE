"""Synthetic-only UCIE Stage 4-7 integration. No production DB access."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ucie_miner.integration import preview_knowledge_rules
from ucie_miner.knowledge import import_miner_candidates
from ucie_miner.patterns import PatternError


class Stage4To7IntegrationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        runtime = self.root / "runtime"
        curated = self.root / "curated_public"
        runtime.mkdir()
        curated.mkdir()
        manifest_text = (ROOT / "curated_public" /
                         "pr_review_evidence_v1.json").read_text("utf-8")
        (curated / "pr_review_evidence_v1.json").write_text(
            manifest_text, encoding="utf-8")
        self.entries = json.loads(manifest_text)["entries"]
        self.miner = runtime / "public_miner.sqlite3"
        self.knowledge = runtime / "knowledge.sqlite3"
        with closing(sqlite3.connect(self.miner)) as db, db:
            db.execute("""CREATE TABLE candidates (
                source TEXT NOT NULL, pr_number INTEGER NOT NULL,
                public_url TEXT NOT NULL, merged_at TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL, status TEXT NOT NULL)""")
            for row in self.entries:
                self._insert(db, row["source"], row["pr_number"],
                             row["merged_at"])
        import_miner_candidates(self.root)

    @staticmethod
    def _insert(db, source, number, merged):
        db.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?)",
                   (source, number, f"https://github.com/{source}/pull/{number}",
                    merged, hashlib.sha256(str(number).encode()).hexdigest(),
                    "UNVERIFIED_CANDIDATE_ONLY"))

    def test_nine_prs_map_to_eight_unverified_ruleplans(self):
        prior_miner = self.miner.read_bytes()
        prior_knowledge = self.knowledge.read_bytes()
        preview = preview_knowledge_rules(self.root)
        self.assertEqual(preview["miner_count"], 9)
        self.assertEqual(preview["knowledge_count"], 9)
        self.assertEqual(preview["pattern_preview"]["family_count"], 8)
        self.assertEqual(len(preview["rulepack_preview"]["proposals"]), 8)
        self.assertEqual(preview["database_writes"], 0)
        self.assertFalse(preview["production_approved"])
        self.assertFalse(preview["approval_gate"]["deploy_allowed"])
        self.assertTrue(all(x["executable_command"] is None
                            for x in preview["rulepack_preview"]["proposals"]))
        self.assertEqual(self.miner.read_bytes(), prior_miner)
        self.assertEqual(self.knowledge.read_bytes(), prior_knowledge)

    def test_unmapped_candidate_remains_unverified(self):
        with closing(sqlite3.connect(self.miner)) as db, db:
            self._insert(db, "python/cpython", 999998,
                         "2026-10-01T00:00:00Z")
        import_miner_candidates(self.root)
        result = preview_knowledge_rules(self.root)
        self.assertEqual(result["unmapped_count"], 1)
        self.assertEqual(result["pattern_preview"]["family_count"], 8)

    def test_stale_knowledge_digest_fails_closed(self):
        with closing(sqlite3.connect(self.knowledge)) as db, db:
            db.execute("UPDATE evidence SET evidence_sha256=? WHERE pr_number=153462",
                       ("f" * 64,))
        with self.assertRaises(PatternError):
            preview_knowledge_rules(self.root)

    def test_missing_import_fails_closed(self):
        self.knowledge.unlink()
        with self.assertRaises(PatternError):
            preview_knowledge_rules(self.root)

    def test_quarantined_backport_excluded(self):
        with closing(sqlite3.connect(self.knowledge)) as db, db:
            db.execute("""UPDATE evidence SET disposition='QUARANTINED'
                           WHERE source='python/cpython' AND pr_number=159365""")
        result = preview_knowledge_rules(self.root)
        self.assertEqual(result["quarantined_or_retracted_count"], 1)
        self.assertEqual(result["pattern_preview"]["family_count"], 8)
        self.assertFalse(result["production_approved"])

    def test_missing_canonical_fails_closed(self):
        with closing(sqlite3.connect(self.knowledge)) as db, db:
            db.execute("""UPDATE evidence SET disposition='RETRACTED'
                           WHERE source='python/cpython' AND pr_number=153462""")
        with self.assertRaises(PatternError):
            preview_knowledge_rules(self.root)


if __name__ == "__main__":
    unittest.main()
