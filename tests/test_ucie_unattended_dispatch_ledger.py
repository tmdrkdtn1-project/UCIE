"""UCIE append-only unattended state receipts, ephemeral SQLite only."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from contextlib import closing
import tempfile
import unittest

from ucie_public.policy import PolicyError
from ucie_public.unattended_dispatch_ledger import (
    GENESIS, append_operation_receipt, inspect_lifecycle,
)

NOW = datetime(2026, 10, 24, 0, 30, tzinfo=timezone.utc)
TASK = "UCIE-P3-OPERATION-TEST-20261024"
GRANT = "a" * 64
DETAIL = "b" * 64


class UCIEOperationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ucie_dispatch_fixture_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.head = GENESIS

    def add(self, state, *, old_head=None, task=TASK, grant=GRANT):
        result = append_operation_receipt(
            self.root, task_id=task, grant_sha256=grant,
            operation="GIT_BRANCH_PUBLISH", next_state=state,
            detail_sha256=DETAIL,
            expected_previous_head=self.head if old_head is None else old_head,
            at_time=NOW)
        self.head = result["event_sha256"]
        return result

    def test_happy_git_path_ends_in_review_not_automerge(self):
        for state in (
            "CLAIMED", "REMOTE_MUTATION_STARTED", "DRAFT_PR_API_RESPONSE",
            "CI_PENDING", "CI_PASS_REVIEW_REQUIRED",
        ):
            result = self.add(state)
            self.assertEqual(result["state"], state)
            self.assertFalse(result["external_anchor_advanced"])
            self.assertFalse(result["operation_executed"])
            self.assertFalse(result["rule_auto_promoted"])
        inspection = inspect_lifecycle(self.root, expected_external_head=self.head)
        self.assertEqual(inspection["event_count"], 5)
        self.assertFalse(inspection["external_anchor_independent"])
        with self.assertRaises(PolicyError):
            self.add("REMOTE_MUTATION_STARTED")

    def test_ambiguous_remote_path_requires_independent_reconciliation(self):
        self.add("CLAIMED")
        self.add("REMOTE_MUTATION_STARTED")
        self.add("AMBIGUOUS_REMOTE_STATE")
        self.add("OPERATOR_RECONCILIATION_REQUIRED")
        with self.assertRaises(PolicyError):
            self.add("REMOTE_MUTATION_STARTED")

    def test_rejects_duplicate_task_stale_head_and_wrong_operation(self):
        self.add("CLAIMED")
        with self.assertRaises(PolicyError):
            self.add("CLAIMED")
        with self.assertRaises(PolicyError):
            self.add("REMOTE_MUTATION_STARTED", old_head=GENESIS)
        with self.assertRaises(PolicyError):
            self.add("REMOTE_MUTATION_STARTED", grant="c" * 64)
        with self.assertRaises(PolicyError):
            append_operation_receipt(
                self.root, task_id=TASK, grant_sha256=GRANT,
                operation="FOREIGN_SERVICE", next_state="RECOVERY_STARTED",
                detail_sha256=DETAIL, expected_previous_head=self.head,
                at_time=NOW)

    def test_unapproved_external_rollback_snapshot_is_detected_by_head(self):
        self.add("CLAIMED")
        first = self.head
        self.add("REMOTE_MUTATION_STARTED")
        self.assertNotEqual(first, self.head)
        with self.assertRaises(PolicyError):
            inspect_lifecycle(self.root, expected_external_head=first)
        with self.assertRaises(PolicyError):
            inspect_lifecycle(self.root, expected_external_head=GENESIS)

    def test_tampered_record_fails_integrity_check(self):
        self.add("CLAIMED")
        db = self.root / "ucie_unattended_claims.sqlite3"
        with closing(sqlite3.connect(db)) as conn:
            conn.execute("UPDATE operation_events SET state='CI_PASS_REVIEW_REQUIRED'")
            conn.commit()
        with self.assertRaises(PolicyError):
            inspect_lifecycle(self.root, expected_external_head=self.head)

    def test_foreign_new_task_cannot_skip_claim(self):
        self.add("CLAIMED")
        with self.assertRaises(PolicyError):
            self.add("CI_PASS_REVIEW_REQUIRED", task="UCIE-P3-OTHER-TEST-20261024")

    def test_missing_database_not_equal_to_non_genesis_head(self):
        self.assertEqual(
            inspect_lifecycle(self.root, expected_external_head=GENESIS)["event_count"], 0)
        with self.assertRaises(PolicyError):
            inspect_lifecycle(self.root, expected_external_head="a" * 64)
        db = self.root / "ucie_unattended_claims.sqlite3"
        with closing(sqlite3.connect(db)) as conn:
            conn.execute("CREATE TABLE grants(sequence INTEGER PRIMARY KEY)")
            conn.commit()
        self.assertEqual(
            inspect_lifecycle(self.root, expected_external_head=GENESIS)["event_count"], 0)
        with self.assertRaises(PolicyError):
            inspect_lifecycle(self.root, expected_external_head="a" * 64)


if __name__ == "__main__":
    unittest.main()
