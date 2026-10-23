"""Offline durable-claim tests, confined to fresh temporary UCIE fixtures."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ucie_public.policy import PolicyError
from ucie_public.rulepack import canonical_json
from ucie_public.unattended_journal import DB_NAME, claim_owner_grant_once
from ucie_public.unattended_ops import SCHEMA

NOW = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)


def payload(*, serial=1, task="UCIE-JOB-ONE-20261023", nonce="a"*32):
    return {
        "schema": SCHEMA, "project_id": "UCIE",
        "audience": "UCIE_OWNER_ONLY",
        "operation": "GIT_BRANCH_PUBLISH",
        "target": "tmdrkdtn1-project/UCIE",
        "task_id": task, "sequence": serial, "nonce": nonce,
        "revision_sha": "a"*40,
        "issued_at": "2026-10-23T09:59:00Z",
        "expires_at": "2026-10-23T10:09:00Z",
    }


class UCIEJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ucie_ops_synthetic_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.key = Ed25519PrivateKey.generate()
        self.trust = self.key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

    def claim(self, obj):
        raw = canonical_json(obj)
        return claim_owner_grant_once(
            self.root, raw, self.key.sign(raw), self.trust, at_time=NOW)

    def test_exactly_one_claim_and_no_execution(self):
        grant = payload()
        receipt = self.claim(grant)
        self.assertEqual(receipt["status"], "UCIE_OWNER_OPERATION_CLAIMED_NO_EXECUTION")
        self.assertTrue(receipt["local_atomic_sqlite_claimed"])
        self.assertFalse(receipt["host_owner_acl_verified"])
        self.assertFalse(receipt["external_rollback_anchor_verified"])
        self.assertFalse(receipt["git_push_performed"])
        self.assertFalse(receipt["service_restarted"])
        self.assertFalse(receipt["rule_promoted"])
        with self.assertRaises(PolicyError):
            self.claim(grant)
        with sqlite3.connect(self.root / DB_NAME) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM grants").fetchone()[0], 1)

    def test_ascending_serial_and_uniqueness(self):
        self.claim(payload())
        with self.assertRaises(PolicyError):
            self.claim(payload(serial=1, task="UCIE-JOB-TWO-20261023", nonce="b"*32))
        with self.assertRaises(PolicyError):
            self.claim(payload(serial=2, task="UCIE-JOB-ONE-20261023", nonce="b"*32))
        with self.assertRaises(PolicyError):
            self.claim(payload(serial=2, task="UCIE-JOB-TWO-20261023", nonce="a"*32))
        self.assertEqual(self.claim(payload(
            serial=2, task="UCIE-JOB-TWO-20261023", nonce="b"*32))["sequence"], 2)
        with sqlite3.connect(self.root / DB_NAME) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM grants").fetchone()[0], 2)

    def test_forgery_never_advances_sequence(self):
        raw = canonical_json(payload())
        with self.assertRaises(PolicyError):
            claim_owner_grant_once(self.root, raw, b"0"*64,
                                   self.trust, at_time=NOW)
        result = self.claim(payload())
        self.assertEqual(result["sequence"], 1)

    def test_untrusted_root_and_linked_database_denied(self):
        raw = canonical_json(payload())
        with self.assertRaises(PolicyError):
            claim_owner_grant_once(Path("relative"), raw, self.key.sign(raw),
                                   self.trust, at_time=NOW)
        self.claim(payload())
        if hasattr(Path, "symlink_to"):
            link = self.root / "link"
            try:
                link.symlink_to(self.root / DB_NAME)
            except (OSError, NotImplementedError):
                return
            # Safe regular filename is required, never a symlink.
            target = self.root / DB_NAME
            backup = self.root / "snapshot"
            target.rename(backup)
            target.symlink_to(backup)
            with self.assertRaises(PolicyError):
                self.claim(payload(serial=2, task="UCIE-JOB-TWO-20261023", nonce="b"*32))


if __name__ == "__main__":
    unittest.main()
