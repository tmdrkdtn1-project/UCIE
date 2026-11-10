"""Safety and equivalence tests for Stage15 one-read audited snapshots.

All records are UCIE-authored synthetic public-only metadata; no operational
DB, private project, network, scheduler, C40 or customer UI is accessed.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ucie_miner import public_candidate_learning as stage12
from ucie_miner import public_evidence_chain_audit as chain
from ucie_miner import public_fix_evidence as stage15
from ucie_miner.public_discovery import DiscoveryError, SOURCE_SKILL
from ucie_miner.skill_profiles import PROFILE


class Stage15AuditedSnapshotTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "UCIE"
        self.root.mkdir()
        self.fix_path = self.root / "synthetic_public_fix_metadata.sqlite3"
        self.fix_path.touch()
        self.source = "python/cpython"
        self.number = 101
        self.merge = "a" * 40
        self.history_digest = "b" * 64
        self.evidence_digest = "c" * 64
        self.skill = SOURCE_SKILL[self.source]
        profile = PROFILE[self.skill]
        self.row = (
            self.source, self.number, self.merge, self.history_digest,
            self.evidence_digest, self.skill, "[]", "[]", "[]",
            0, 0, "BOUNDED_FIRST_PAGE_ONLY", 0, "[]",
            profile["safe_call"], profile["recommended_action"],
            "UNDETERMINED", "UNVERIFIED",
            stage15.EVIDENCE_STATE, stage15.UNVERIFIED,
        )
        self.history = {(self.source, self.number, self.history_digest):
                        (self.merge, self.skill)}

    def test_exact_stage16_audit_payload_and_status_still_available(self):
        with patch.object(chain, "_history", return_value=self.history) as h:
            with patch.object(chain, "_fix", return_value=[self.row]) as f:
                proof = chain.audit_external_evidence_chain(self.root)
        self.assertEqual((h.call_count, f.call_count), (1, 1))
        self.assertEqual(proof["status"],
                         "STAGE16_LOCALLY_LINKED_BUT_UNVERIFIED_NO_GO")
        self.assertEqual(proof["stage13_unverified_revisions"], 1)
        self.assertEqual(proof["stage15_unverified_revisions"], 1)
        self.assertEqual(proof["local_identity_links"], 1)
        self.assertEqual(proof["invalid_review_rows"], 0)
        self.assertEqual(proof["orphaned_revision_refs"], 0)
        self.assertEqual(proof["merge_sha_mismatches"], 0)
        self.assertEqual(proof["persistent_writes"], 0)
        self.assertFalse(proof["license_approved"])
        self.assertFalse(proof["production_approved"])
        self.assertFalse(proof["independent_regression_verified"])

    def test_stage15_single_source_read_preserves_unverified_rows(self):
        with patch.object(stage15, "_marker_enabled", return_value=True):
            with patch.object(stage15, "_path", return_value=self.fix_path):
                with patch.object(chain, "_history",
                                  return_value=self.history) as h:
                    with patch.object(chain, "_fix",
                                      return_value=[self.row]) as f:
                        items = stage12._rows_from_stage15(self.root)
        self.assertEqual((h.call_count, f.call_count), (1, 1))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0], (
            self.source,
            f"fix-pr:{self.number}:{self.merge}:{self.history_digest}",
            self.skill, self.evidence_digest, [], None,
        ))

    def test_snapshot_is_read_only_and_not_promoted(self):
        with patch.object(chain, "_history", return_value=self.history):
            with patch.object(chain, "_fix", return_value=[self.row]):
                history, fixes = chain.read_audited_public_evidence_snapshot(
                    self.root)
        self.assertIsInstance(fixes, tuple)
        self.assertEqual(fixes[0], self.row)
        with self.assertRaises(TypeError):
            history["forged"] = ("x", "y")
        self.assertEqual(history, self.history)

    def test_rejected_orphan_revision_no_unverified_handoff(self):
        bad = list(self.row)
        bad[3] = "e" * 64
        self._expect_rejection(self.history, [tuple(bad)])

    def test_rejected_merge_mismatch_no_unverified_handoff(self):
        bad = list(self.row)
        bad[2] = "f" * 40
        self._expect_rejection(self.history, [tuple(bad)])

    def test_rejected_fake_approval_or_untrusted_tags(self):
        for idx, value in ((19, "OWNER_APPROVED"),
                           (17, "RIGHTS_APPROVED"),
                           (6, "not-json")):
            with self.subTest(index=idx):
                bad = list(self.row)
                bad[idx] = value
                self._expect_rejection(self.history, [tuple(bad)])

    def test_missing_history_or_fix_ledger_fails_closed(self):
        self._expect_rejection(None, [self.row])
        self._expect_rejection(self.history, None)

    def test_reader_integrity_error_not_bypassed(self):
        with patch.object(chain, "_history",
                          side_effect=DiscoveryError("synthetic corruption")):
            with patch.object(chain, "_fix") as f:
                with self.assertRaises(DiscoveryError):
                    chain.read_audited_public_evidence_snapshot(self.root)
                self.assertEqual(f.call_count, 0)

    def test_opt_in_disabled_never_reads_ledgers(self):
        with patch.object(stage15, "_marker_enabled", return_value=False):
            with patch.object(chain, "_history") as h:
                with patch.object(chain, "_fix") as f:
                    self.assertEqual(
                        stage12._rows_from_stage15(self.root), [])
        self.assertEqual((h.call_count, f.call_count), (0, 0))

    def test_opt_in_with_missing_fix_path_is_inert(self):
        missing = self.fix_path.with_name("absent-synthetic-public.sqlite3")
        with patch.object(stage15, "_marker_enabled", return_value=True):
            with patch.object(stage15, "_path", return_value=missing):
                with patch.object(chain, "_history") as h:
                    with patch.object(chain, "_fix") as f:
                        self.assertEqual(
                            stage12._rows_from_stage15(self.root), [])
        self.assertEqual((h.call_count, f.call_count), (0, 0))

    def test_mutation_between_source_reads_rejected(self):
        changed = list(self.row)
        changed[2] = "d" * 40
        # A source that changed independently cannot be linked to the
        # immutable history in the one in-memory audited snapshot.
        with patch.object(chain, "_history", return_value=self.history):
            with patch.object(chain, "_fix", return_value=[tuple(changed)]):
                with self.assertRaises(DiscoveryError):
                    chain.read_audited_public_evidence_snapshot(self.root)

    def _expect_rejection(self, history, fixes):
        with patch.object(chain, "_history", return_value=history):
            with patch.object(chain, "_fix", return_value=fixes):
                with self.assertRaises(DiscoveryError):
                    chain.read_audited_public_evidence_snapshot(self.root)


if __name__ == "__main__":
    unittest.main()
