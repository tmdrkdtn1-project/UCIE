"""UCIE local signed review history: one synthetic append/inspect/revoke path."""
from contextlib import closing
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_miner.public_batch import build_public_batch
from ucie_miner.public_library_graph import preview_library_knowledge_graph
from ucie_miner.public_library_signed_review import EVENT_SCHEMA
from ucie_miner.public_library_review_store import (
    DB_NAME, ZERO_HEAD, inspect_local_library_review_history,
    append_local_library_review_history,
)
from test_ucie_stage9_batch import NOW, metadata, evidence

STAMP = datetime(2026, 10, 22, 5, 0, tzinfo=timezone.utc)


def public_batch():
    return build_public_batch(metadata_fetch=metadata, evidence_fetch=evidence,
                              now=NOW, max_enrich=2)


class LibrarySignedReviewStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "UCIE"
        (self.root / "runtime").mkdir(parents=True)
        self.batch = public_batch()
        self.owner = Ed25519PrivateKey.generate()
        self.qa = Ed25519PrivateKey.generate()
        nodes = preview_library_knowledge_graph(self.batch)["nodes"]
        self.card = next(n for n in nodes
                         if n["kind"] == "UNVERIFIED_PUBLIC_RESEARCH_REFERENCE")
        self.args = {
            "owner_trust": self.owner.public_key(),
            "qa_trust": self.qa.public_key(),
            "at_time": STAMP,
        }

    def event(self, action="REVIEW_ATTESTED", serial=1, *,
              owner=None, qa=None):
        review = action == "REVIEW_ATTESTED"
        issued = STAMP - timedelta(hours=1)
        claim = {
            "schema": EVENT_SCHEMA,
            "action": action,
            "public_url": self.card["public_url"],
            "pinned_revision_sha": self.card["pinned_revision_sha"],
            "evidence_sha256": self.card["evidence_fingerprint_sha256"],
            "version_claim": "3.15.0" if review else None,
            "review_evidence_sha256": "a" * 64 if review else None,
            "review_claims": {
                "source_license": True, "security": True,
                "regression": True, "release_version": True,
            } if review else None,
            "serial": serial,
            "issued_utc": issued.isoformat().replace("+00:00", "Z"),
            "expires_utc": ((issued + timedelta(days=7)).isoformat()
                            .replace("+00:00", "Z") if review else None),
        }
        blob = canonical_json(claim)
        return {
            "claim": claim,
            "owner_signature_hex": (owner or self.owner).sign(blob).hex(),
            "qa_signature_hex": (qa or self.qa).sign(blob).hex()
                                 if review else None,
        }

    def add(self, entries, head=ZERO_HEAD, **kwargs):
        return append_local_library_review_history(
            self.root, self.batch, entries,
            expected_head_sha256=head, allow_disk_write=True,
            **{**self.args, **kwargs})

    def inspect(self, **kwargs):
        return inspect_local_library_review_history(
            self.root, **{**self.args, **kwargs})

    def test_explicit_opt_in_and_readonly_missing_ledger(self):
        self.assertFalse((self.root / "runtime" / DB_NAME).exists())
        first = self.inspect(expected_head_sha256=ZERO_HEAD)
        self.assertEqual(first["event_count"], 0)
        self.assertTrue(first["caller_checkpoint_matched"])
        self.assertFalse((self.root / "runtime" / DB_NAME).exists())
        with self.assertRaises(PolicyError):
            append_local_library_review_history(
                self.root, self.batch, [self.event()],
                expected_head_sha256=ZERO_HEAD, **self.args)
        self.assertFalse((self.root / "runtime" / DB_NAME).exists())

    def test_append_reopen_and_owner_revocation_cannot_resurrect(self):
        first = self.add([self.event()])
        self.assertEqual(first["event_count"], 1)
        self.assertEqual(first["highest_serial"], 1)
        self.assertFalse(first["distribution_authorized"])
        self.assertFalse(first["external_rollback_protection_proven"])
        head = first["head_sha256"]
        self.assertNotEqual(head, ZERO_HEAD)
        observed = self.inspect(expected_head_sha256=head)
        self.assertEqual(observed["head_sha256"], head)
        self.assertTrue(observed["hash_chain_and_signatures_checked"])

        revoked = self.add([self.event(action="REVOKE", serial=2)], head)
        self.assertEqual(revoked["owner_revoked_reference_count"], 1)
        self.assertEqual(revoked["event_count"], 2)
        self.assertEqual(revoked["latest_reference_states"][0]["state"],
                         "OWNER_REVOKED_NO_GO")
        self.assertEqual(self.inspect()["head_sha256"],
                         revoked["head_sha256"])
        with self.assertRaises(PolicyError):
            self.add([self.event(serial=3)], revoked["head_sha256"])
        self.assertEqual(self.inspect()["head_sha256"], revoked["head_sha256"])

    def test_head_lease_and_global_serial_replay_rejected(self):
        first = self.add([self.event()])
        with self.assertRaises(PolicyError):
            self.add([self.event(action="REVOKE", serial=2)], ZERO_HEAD)
        with self.assertRaises(PolicyError):
            self.add([self.event(action="REVOKE", serial=1)],
                     first["head_sha256"])
        with self.assertRaises(PolicyError):
            self.inspect(expected_head_sha256=ZERO_HEAD)
        self.assertEqual(self.inspect()["event_count"], 1)

    def test_invalid_signatures_and_forged_claims_never_write(self):
        forged = self.event(owner=Ed25519PrivateKey.generate())
        with self.assertRaises(PolicyError):
            self.add([forged])
        unsigned = self.event()
        unsigned["claim"]["version_claim"] = "999"
        with self.assertRaises(PolicyError):
            self.add([unsigned])
        self.assertFalse((self.root / "runtime" / DB_NAME).exists())

    def test_sqlite_history_mutation_and_corruption_fail_closed(self):
        first = self.add([self.event()])
        db = self.root / "runtime" / DB_NAME
        # sqlite3.Connection.__exit__ commits but does not close the file.
        # Explicit close is required before TemporaryDirectory cleanup on Windows.
        with closing(sqlite3.connect(db)) as conn, conn:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("UPDATE review_history SET serial=99")
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("DELETE FROM review_history")
            # Simulate deliberate database corruption by an administrator
            # circumventing the append-only trigger (outside this API).
            conn.execute("DROP TRIGGER deny_review_history_update")
            conn.execute("DROP TRIGGER deny_review_history_delete")
            conn.execute("UPDATE review_history SET event_hash=?", ("f" * 64,))
        with self.assertRaises(PolicyError):
            self.inspect(expected_head_sha256=first["head_sha256"])

    def test_full_file_rollback_requires_external_head(self):
        original = self.add([self.event()])
        db = self.root / "runtime" / DB_NAME
        backup = db.read_bytes()
        second = self.add(
            [self.event(action="REVOKE", serial=2)],
            original["head_sha256"])
        # SQLite's file contents are never authoritative against restore.
        db.write_bytes(backup)
        with self.assertRaises(PolicyError):
            self.inspect(expected_head_sha256=second["head_sha256"])
        old = self.inspect()
        self.assertEqual(old["head_sha256"], original["head_sha256"])
        self.assertFalse(old["external_rollback_protection_proven"])

    def test_source_separation_and_symlink_blocked(self):
        with self.assertRaises(PolicyError):
            append_local_library_review_history(
                Path(self.temp.name) / "OtherProject", self.batch,
                [self.event()], allow_disk_write=True,
                expected_head_sha256=ZERO_HEAD, **self.args)
        elsewhere = Path(self.temp.name) / "out.sqlite3"
        elsewhere.write_bytes(b"not a database")
        try:
            self.root.joinpath("runtime", DB_NAME).symlink_to(elsewhere)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable on this CI host")
        with self.assertRaises(PolicyError):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
