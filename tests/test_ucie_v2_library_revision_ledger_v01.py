"""Isolated first-party UCIE review history: tamper, revision, persistence."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from unittest import TestCase

from ucie_miner import ucie_v2_library_revision_ledger_v01 as ledger
from ucie_miner import ucie_v2_original_library_assets_v01 as asset
from ucie_miner import ucie_v2_revision_impact_v01 as b3
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5


def row(method):
    return {"study_id": b5.STUDY_ID, "case_id": b5.CASE_ID,
            "anonymous_trial_token": "F01", "method": method,
            "cohort": "FIRST_TIME_CODER", "first_safe_action_time_ms": 900,
            "correct_safe_action": True, "false_version_or_rights_claim": False,
            "evidence_detail_found": False, "origin": b5.SYNTHETIC_ORIGIN}


def changed(source):
    return {"source_id": source, "previous_pin": b3.PINS[source],
            "candidate_pin": "f"*len(b3.PINS[source])}


class ReviewHistoryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = tuple(row(m) for m in b5.METHODS)
        cls.clean = asset.assemble_original_library_assets(cls.records, ())
        cls.changed = asset.assemble_original_library_assets(
            cls.records, (changed("doc:git/git"),))
        cls.incomplete = asset.assemble_original_library_assets(
            (row(b5.METHODS[0]),), ())

    def test_empty_initial_history(self):
        h = ledger.new_review_history()
        self.assertEqual(ledger.validate_review_history(h)["record_count"], 0)

    def test_append_digest_and_idempotent_replay(self):
        h = ledger.append_review_bundle(ledger.new_review_history(), self.clean)
        self.assertEqual(h["record_count"], 1)
        self.assertEqual(ledger.append_review_bundle(h, self.clean), h)
        self.assertFalse(h["history_persisted"])

    def test_version_chain_records_holds_and_preserves_old(self):
        h = ledger.new_review_history()
        for b in (self.clean, self.changed, self.incomplete):
            h = ledger.append_review_bundle(h, b)
        self.assertEqual(h["record_count"], 3)
        states = [r["bundle"]["revision"]["review_status"] for r in h["events"]]
        self.assertEqual(states, ["REVIEW_ACTIVE_UNVERIFIED",
                                  "REVIEW_HOLD_CANDIDATE_SOURCE_CHANGE",
                                  "REVIEW_HOLD_INCOMPLETE_PAIRED_FIXTURE"])
        lessons = ledger.review_negative_lessons(h)
        self.assertEqual(lessons["negative_lessons_preserved"], 3)
        self.assertFalse(lessons["automatic_promotion"])
        self.assertTrue(all(not r["usable_as_proven_rule"]
                            for r in lessons["reusable_review_only_lessons"]))

    def test_old_history_unchanged_after_append(self):
        h = ledger.append_review_bundle(ledger.new_review_history(), self.clean)
        digest = h["content_sha256"]
        ledger.append_review_bundle(h, self.changed)
        self.assertEqual(h["content_sha256"], digest)
        self.assertEqual(h["record_count"], 1)

    def test_tampered_original_chapter_denied(self):
        h = ledger.append_review_bundle(ledger.new_review_history(), self.clean)
        h["events"][0]["bundle"]["chapter"]["text"] += "INJECTED"
        with self.assertRaises(ledger.ReviewHistoryError):
            ledger.validate_review_history(h)

    def test_forged_rights_even_with_recomputed_bundle_hash_denied(self):
        forged = deepcopy(self.clean)
        forged["rights_approved"] = True
        forged["content_sha256"] = asset._digest({k:v for k,v in forged.items()
                                                  if k != "content_sha256"})
        with self.assertRaises(ledger.ReviewHistoryError):
            ledger.append_review_bundle(ledger.new_review_history(), forged)

    def test_reordered_or_deleted_history_denied(self):
        h = ledger.append_review_bundle(ledger.new_review_history(), self.clean)
        h = ledger.append_review_bundle(h, self.changed)
        h["events"].pop(0)
        with self.assertRaises(ledger.ReviewHistoryError):
            ledger.validate_review_history(h)

    def test_max_capacity_fail_closed(self):
        h = ledger.new_review_history()
        # Bound is checked before adding 33rd record; synthetic snapshots below
        # are hypothetical code-review copies, each digest is distinct.
        for n in range(ledger.MAX_ENTRIES):
            b = deepcopy(self.clean)
            b["revision"]["revision_candidate_signal_sha256"] = f"{n:064x}"
            b["content_sha256"] = asset._digest({k:v for k,v in b.items()
                                                  if k != "content_sha256"})
            h = ledger.append_review_bundle(h, b)
        with self.assertRaises(ledger.ReviewHistoryError):
            ledger.append_review_bundle(h, self.changed)

    def test_private_field_rejected_even_if_rehashed(self):
        b = deepcopy(self.clean)
        b["customer_email"] = "private@example.invalid"
        b["content_sha256"] = asset._digest({k:v for k,v in b.items()
                                              if k != "content_sha256"})
        with self.assertRaises(ledger.ReviewHistoryError):
            ledger.append_review_bundle(ledger.new_review_history(), b)

    def test_wrong_repository_lineage_rejected(self):
        b = deepcopy(self.clean)
        b["chapter"]["source_lineage"][0]["source_id"] = "repo:unapproved"
        b["content_sha256"] = asset._digest({k:v for k,v in b.items()
                                              if k != "content_sha256"})
        with self.assertRaises(ledger.ReviewHistoryError):
            ledger.append_review_bundle(ledger.new_review_history(), b)

    def test_no_unmarked_directory_writes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "ucie_v2_review_store"
            root.mkdir()
            h = ledger.append_review_bundle(ledger.new_review_history(), self.clean)
            with self.assertRaises(ledger.ReviewHistoryError):
                ledger.write_review_store(root, h, expected_previous_sha256=
                                          ledger.new_review_history()["content_sha256"],
                                          approve_write=True)
            self.assertFalse((root/ledger.STORE_FILENAME).exists())

    def test_preview_then_explicit_persistent_roundtrip(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "ucie_v2_review_store"
            root.mkdir()
            (root / ledger.STORE_MARKER).write_text(ledger.STORE_MARKER_VALUE,
                                                    encoding="utf-8")
            original = ledger.read_review_store(root)
            newer = ledger.append_review_bundle(original, self.clean)
            preview = ledger.write_review_store(
                root, newer, expected_previous_sha256=original["content_sha256"])
            self.assertEqual(preview["status"], "PREVIEW_ONLY_NO_WRITE")
            self.assertFalse((root / ledger.STORE_FILENAME).exists())
            report = ledger.write_review_store(
                root, newer, expected_previous_sha256=original["content_sha256"],
                approve_write=True)
            self.assertEqual(report["status"], "REVIEW_STORE_WRITTEN_NOT_PRODUCTION")
            self.assertEqual(ledger.read_review_store(root), newer)
            second = ledger.append_review_bundle(newer, self.changed)
            ledger.write_review_store(root, second,
                                      expected_previous_sha256=newer["content_sha256"],
                                      approve_write=True)
            self.assertEqual(ledger.read_review_store(root)["record_count"], 2)

    def test_stale_writer_and_rewrite_denied(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t) / "ucie_v2_review_store"
            root.mkdir()
            (root / ledger.STORE_MARKER).write_text(ledger.STORE_MARKER_VALUE,
                                                    encoding="utf-8")
            empty = ledger.new_review_history()
            first = ledger.append_review_bundle(empty, self.clean)
            ledger.write_review_store(root, first,
                                      expected_previous_sha256=empty["content_sha256"],
                                      approve_write=True)
            with self.assertRaises(ledger.ReviewHistoryError):
                ledger.write_review_store(root, empty,
                                          expected_previous_sha256=empty["content_sha256"],
                                          approve_write=True)
            unrelated = ledger.append_review_bundle(empty, self.changed)
            with self.assertRaises(ledger.ReviewHistoryError):
                ledger.write_review_store(root, unrelated,
                                          expected_previous_sha256=first["content_sha256"],
                                          approve_write=True)

    def test_symlinked_store_denied(self):
        with tempfile.TemporaryDirectory() as t:
            target = Path(t) / "real"
            target.mkdir()
            root = Path(t) / "ucie_v2_review_store"
            try:
                root.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(ledger.ReviewHistoryError):
                ledger.read_review_store(root)
