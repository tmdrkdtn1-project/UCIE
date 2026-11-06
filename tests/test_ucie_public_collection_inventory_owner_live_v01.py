"""Owner-only UCIE public inventory live acceptance, read-only.

This is a deliberate single-file unittest, not a scheduled collector.
CI checkouts skip it unless the test ITSELF resides at exact D:/UCIE.
Only fixed public miner aggregate counts are returned, not record rows.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from ucie_miner.public_collection_inventory_v01 import (
    SCHEMA, NO_GO, OBSERVED, collection_inventory,
)


class OwnerReadOnlyCollectionInventoryTests(unittest.TestCase):
    def test_real_ucie_public_inventory_counts_only(self):
        root = Path(__file__).resolve().parents[1]
        if os.name != "nt" or root.is_symlink() or \
                root.resolve() != Path("D:/UCIE").resolve():
            self.skipTest("OWNER_D_UCIE_WINDOWS_ONLY")
        result = collection_inventory(root)
        # Intentionally print aggregate-only report even when status is NO_GO.
        clean = {
            "schema": result["schema"],
            "status": result["status"],
            "legacy_candidates": result["legacy_miner"]["candidates"],
            "legacy_run_count": result["legacy_miner"]["runs"],
            "legacy_latest_run_utc": result["legacy_miner"]["last_run_utc"],
            "legacy_per_source": result["legacy_miner"]["by_source"],
            "stage10_candidate_revisions": result[
                "stage10_public_candidate_staging"]["candidate_revisions"],
            "stage10_git_commit_revisions": result[
                "stage10_public_candidate_staging"]["git_commit_revisions"],
            "stage12_review_proposals": result[
                "stage12_unverified_review"]["review_proposals"],
            "recent_hourly_status": result["recent_hourly_activity"]["status"],
            "recent_hourly_finished_utc":
                result["recent_hourly_activity"]["last_finished_utc"],
            "recent_hourly_age_minutes":
                result["recent_hourly_activity"]["last_finished_age_minutes"],
            "latest_new_unverified_candidates":
                result["recent_hourly_activity"][
                    "latest_new_unverified_candidates"],
            "task_scheduler_verified": result[
                "current_windows_task_scheduler_events_verified"],
            "issues": result["issues"],
            "non_additive_ledgers": result[
                "totals_from_distinct_ledgers_are_not_additive"],
        }
        print("UCIE_OWNER_LIVE_COLLECTION_COUNTS_V01="
              + json.dumps(clean, ensure_ascii=True, sort_keys=True))
        self.assertEqual(result["schema"], SCHEMA)
        self.assertIn(result["status"], (NO_GO, OBSERVED))
        self.assertFalse(result["current_windows_task_scheduler_events_verified"])
        self.assertEqual(result["operating_database_writes"], 0)
        self.assertEqual(result["public_network_requests"], 0)
        self.assertFalse(result["scheduler_changed"])
        self.assertFalse(result["source_code_or_project_data_scanned"])


if __name__ == "__main__":
    unittest.main()
