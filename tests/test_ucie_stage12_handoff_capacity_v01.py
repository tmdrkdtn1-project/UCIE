"""UCIE Stage12 -> W04 source-bound candidate capacity regression.

Prove the actual Stage10/12 bounded capacity (10,000) and the W04
verification handoff agree. Synthetic data is UCIE-authored and inert;
live owner test is read-only, exact D:/UCIE only. No approvals, writes,
network, local services, scheduler, or access to other projects.
"""
from __future__ import annotations

import os
from pathlib import Path
import unittest

from ucie_miner.automated_candidate_qa import _checked_handoff
from ucie_miner.public_candidate_staging import MAX_ROWS
from ucie_miner.library_search import (
    search_existing_public_library, search_linked_public_candidates,
)
from ucie_miner.verification_handoff import prepare_verification_handoff
from ucie_public.policy import PolicyError

ROOT = Path(__file__).resolve().parents[1]


def _synthetic_handoff(count: int) -> dict:
    rows = [{
        "candidate_id_sha256": f"{i:064x}",
        "evidence_sha256": f"{i + 1:064x}",
        "stage6_candidate": None,
        "status": "UNVERIFIED_CANDIDATE_ONLY",
        "approval": False,
        "blocking_reasons": ["VERIFICATION_NOT_PERFORMED"],
    } for i in range(count)]
    return {
        "schema": "UCIE_PUBLIC_CANDIDATE_VERIFICATION_HANDOFF_V1",
        "status": "LINKED_UNVERIFIED_NO_GO",
        "source_revisions": count,
        "linked_revisions": count,
        "pending_source_revisions": 0,
        "tasks": rows,
        "auto_promoted": False,
        "production_approved": False,
        "deploy_allowed": False,
    }


class Stage12ConsistentCapacity(unittest.TestCase):
    def test_1008_linked_unverified_candidates_are_not_invalid(self):
        # First real owner failure occurred at 1,008 verified source links.
        handoff = _synthetic_handoff(1008)
        complete, tasks = _checked_handoff(handoff)
        self.assertTrue(complete)  # linked, NOT approved or released
        self.assertEqual(len(tasks), 1008)
        self.assertTrue(all(x["approval"] is False for x in tasks))
        self.assertFalse(handoff["production_approved"])

    def test_max_rows_boundary_is_accepted_as_unverified_only(self):
        self.assertEqual(MAX_ROWS, 10_000)
        handoff = _synthetic_handoff(MAX_ROWS)
        linked, tasks = _checked_handoff(handoff)
        self.assertTrue(linked)
        self.assertEqual(len(tasks), MAX_ROWS)
        self.assertFalse(handoff["auto_promoted"])

    def test_above_stage12_max_rows_still_fails_closed(self):
        handoff = _synthetic_handoff(MAX_ROWS + 1)
        with self.assertRaisesRegex(
                PolicyError, "invalid public candidate review ledger"):
            _checked_handoff(handoff)

    def test_duplicate_fingerprint_and_forged_approval_are_rejected(self):
        handoff = _synthetic_handoff(1008)
        handoff["tasks"][1]["candidate_id_sha256"] = (
            handoff["tasks"][0]["candidate_id_sha256"])
        with self.assertRaises(PolicyError):
            _checked_handoff(handoff)
        handoff = _synthetic_handoff(1008)
        handoff["tasks"][-1]["approval"] = True
        with self.assertRaises(PolicyError):
            _checked_handoff(handoff)
        handoff = _synthetic_handoff(1008)
        handoff["tasks"][-1]["blocking_reasons"] = []
        with self.assertRaises(PolicyError):
            _checked_handoff(handoff)

    def test_pending_linkage_does_not_authorize_search_results(self):
        handoff = _synthetic_handoff(1008)
        handoff["status"] = "SOURCE_REVISIONS_PENDING_NO_GO"
        handoff["source_revisions"] = 1009
        handoff["pending_source_revisions"] = 1
        linked, _ = _checked_handoff(handoff)
        self.assertFalse(linked)
        search = search_linked_public_candidates(
            handoff, query="python", limit=5)
        self.assertEqual(search["status"], "SOURCE_LINKAGE_INCOMPLETE_NO_GO")
        self.assertEqual(search["items"], [])
        self.assertFalse(search["auto_promoted"])


@unittest.skipUnless(
    os.name == "nt" and ROOT == Path("D:/UCIE").resolve(),
    "LIVE_UCIE_OWNER_WINDOWS_READ_ONLY_ONLY",
)
class ActualStage12LedgerAndSearch(unittest.TestCase):
    def test_source_linked_owner_ledger_stays_readonly_and_unapproved(self):
        handoff = prepare_verification_handoff(ROOT)
        complete, tasks = _checked_handoff(handoff)
        self.assertLessEqual(len(tasks), MAX_ROWS)
        self.assertFalse(handoff["production_approved"])
        self.assertFalse(handoff["auto_promoted"])
        self.assertTrue(all(x["approval"] is False for x in tasks))
        search = search_existing_public_library(
            ROOT, query="python", limit=10, offset=0)
        self.assertEqual(search["operating_database_writes"], 0)
        self.assertEqual(search["approved_or_exportable_items"], 0)
        self.assertFalse(search["auto_promoted"])
        if complete:
            self.assertEqual(
                handoff["status"], "LINKED_UNVERIFIED_NO_GO")
            self.assertEqual(
                search["status"], "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO")
            self.assertEqual(search["source_linked_count"], len(tasks))
            self.assertTrue(all(
                row["human_approved"] is False
                and row["export_allowed"] is False
                for row in search["items"]))
        else:
            self.assertEqual(
                search["status"], "SOURCE_LINKAGE_INCOMPLETE_NO_GO")
            self.assertEqual(search["items"], [])


if __name__ == "__main__":
    unittest.main()
