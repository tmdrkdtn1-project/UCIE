"""Stage 16 synthetic, local-only cross-ledger integrity regression."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from ucie_miner.public_discovery import DiscoveryError
from ucie_miner.public_external_history import _schema as init_history, DB_NAME as HISTORY_DB
from ucie_miner.public_fix_evidence import _check_schema as init_fix, DB_NAME as FIX_DB
from ucie_miner.public_evidence_chain_audit import audit_external_evidence_chain
from ucie_miner.skill_profiles import PROFILE

SOURCE = "python/cpython"
MERGE = "a" * 40
HISTORY_SHA = "b" * 64
EVIDENCE_SHA = "c" * 64
SKILL = "python-runtime-safety"


class ChainAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(parents=True)
        self.operational = self.runtime / "public_miner.sqlite3"
        self.operational.write_bytes(b"OPERATIONAL_NO_TOUCH")

    def history(self):
        with closing(sqlite3.connect(self.runtime / HISTORY_DB)) as db:
            db.execute("BEGIN IMMEDIATE")
            init_history(db, new=True)
            db.execute("INSERT INTO upstream_history VALUES (?,?,?,?,?,?,?,?,?)",
                       (SOURCE, 42, MERGE, "2026-10-01T10:00:00Z",
                        "d" * 64, HISTORY_SHA, SKILL, '["REGRESSION"]',
                        "UNVERIFIED_CANDIDATE_ONLY"))
            db.commit()

    def fix(self, *, merge=MERGE, historical=HISTORY_SHA, guidance=None,
            review="UNVERIFIED_REVIEW_CANDIDATE_ONLY"):
        profile = PROFILE[SKILL]
        with closing(sqlite3.connect(self.runtime / FIX_DB)) as db:
            db.execute("BEGIN IMMEDIATE")
            init_fix(db, new=True)
            db.execute("INSERT INTO fix_evidence VALUES (" + ",".join("?" * 21) + ")",
                       (SOURCE, 42, merge, historical, EVIDENCE_SHA, SKILL,
                        '["EXCEPTION_HANDLING"]', '["GENERIC_EXCEPTION"]',
                        '["THREAD_SERIALIZATION"]', 1, 1,
                        "BOUNDED_FIRST_PAGE_ONLY", 1,
                        '["advisory","document"]',
                        guidance if guidance is not None else profile["safe_call"],
                        profile["recommended_action"], "UNDETERMINED",
                        "UNVERIFIED", "PUBLIC_PATCH_RELEASE_HINTS_UNVERIFIED",
                        review, "2026-10-15T12:00:00+00:00"))
            db.commit()

    def test_missing_both_is_no_go_and_writes_nothing(self):
        actual = audit_external_evidence_chain(self.root)
        self.assertEqual(actual["status"], "STAGE16_INCOMPLETE_LOCAL_EVIDENCE_NO_GO")
        self.assertEqual(actual["missing_ledgers"], ["stage13", "stage15"])
        self.assertEqual(list(self.runtime.iterdir()), [self.operational])

    def test_exact_local_link_never_claims_external_verification(self):
        self.history()
        self.fix()
        before = {p.name: p.read_bytes() for p in self.runtime.iterdir()}
        result = audit_external_evidence_chain(self.root)
        self.assertEqual(result["status"], "STAGE16_LOCALLY_LINKED_BUT_UNVERIFIED_NO_GO")
        self.assertEqual(result["local_identity_links"], 1)
        self.assertEqual(result["orphaned_revision_refs"], 0)
        self.assertFalse(result["upstream_merge_independently_attested"])
        self.assertFalse(result["pr_file_pagination_complete"])
        self.assertFalse(result["production_approved"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.runtime.iterdir()})

    def test_orphaned_hash_is_rejected(self):
        self.history()
        self.fix(historical="e" * 64)
        actual = audit_external_evidence_chain(self.root)
        self.assertEqual(actual["orphaned_revision_refs"], 1)
        self.assertEqual(actual["status"], "STAGE16_LOCAL_EVIDENCE_MISMATCH_NO_GO")

    def test_merge_sha_conflict_is_rejected(self):
        self.history()
        self.fix(merge="f" * 40)
        actual = audit_external_evidence_chain(self.root)
        self.assertEqual(actual["merge_sha_mismatches"], 1)
        self.assertEqual(actual["local_identity_links"], 0)

    def test_noncanonical_safe_guidance_fails_closed(self):
        self.history()
        self.fix(guidance="UNTRUSTED_GENERATED_COMMAND")
        result = audit_external_evidence_chain(self.root)
        self.assertEqual(result["invalid_review_rows"], 1)
        self.assertNotIn("UNTRUSTED_GENERATED_COMMAND", str(result))

    def test_history_only_is_incomplete(self):
        self.history()
        result = audit_external_evidence_chain(self.root)
        self.assertEqual(result["missing_ledgers"], ["stage15"])
        self.assertEqual(result["stage13_unverified_revisions"], 1)

    def test_fix_only_is_incomplete_not_linked(self):
        self.fix()
        result = audit_external_evidence_chain(self.root)
        self.assertEqual(result["missing_ledgers"], ["stage13"])
        self.assertEqual(result["orphaned_revision_refs"], 1)

    def test_invalid_stage13_identity_is_rejected(self):
        self.history()
        with closing(sqlite3.connect(self.runtime / HISTORY_DB)) as db:
            db.execute("UPDATE upstream_history SET source='unapproved/private'")
            db.commit()
        with self.assertRaises(DiscoveryError):
            audit_external_evidence_chain(self.root)

    def test_reject_foreign_ledger(self):
        with closing(sqlite3.connect(self.runtime / HISTORY_DB)) as db:
            db.execute("CREATE TABLE unrelated(x TEXT)")
            db.commit()
        with self.assertRaises(DiscoveryError):
            audit_external_evidence_chain(self.root)


if __name__ == "__main__":
    unittest.main()
