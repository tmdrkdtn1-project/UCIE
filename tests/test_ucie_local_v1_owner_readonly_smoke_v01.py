"""Real owner-only UCIE Local V1 read-only consumer smoke.

Runs ONLY inside the exact D:/UCIE checkout on Windows. No mock public
evidence, no scheduler changes, no writes or independent owner user signoff.
CI on ephemeral cloud machines intentionally skips.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from ucie_miner import local_v1_app_v01 as app
from ucie_miner import local_v1_priority_v01 as policy


@unittest.skipUnless(
    os.name == "nt" and Path(__file__).resolve().parents[1] ==
    Path("D:/UCIE").resolve(),
    "OWNER_HOST_EXACT_D_UCIE_ONLY",
)
class RealOwnerPublicOnlyLocalV1Workflow(unittest.TestCase):
    def test_actual_existing_ucie_source_four_product_actions(self):
        root = Path("D:/UCIE")
        self.assertTrue((root / ".git").is_dir())
        self.assertTrue((root / "runtime").is_dir())
        home = app._home()
        self.assertIn('href="/local/error"', home)
        self.assertIn('href="/local/books"', home)
        engine = app._engine("purpose=SKILL_TEST_AUTOMATION")
        self.assertIn("TAGGED_TEST_CASE_LOOKUP_V1", engine)
        books = app._books("q=")
        self.assertIn("/skillbooks/", books)
        self.assertIn("미승인", books)
        error = app._error(root, "q=python")
        self.assertIn("오류 예방", error)
        self.assertTrue("UNVERIFIED_CANDIDATE_ONLY" in error or
                        "출처 연결이 불완전" in error or
                        "기존 공개 근거가 없습니다" in error)
        evolution = app._evolution(root, "q=python")
        self.assertIn("기존 공개 PR 후보:", evolution)
        self.assertIn("수동 검토", evolution)
        snapshot = policy.roadmap()
        self.assertFalse(snapshot["local_v1_accepted_by_owner"])
        self.assertFalse(snapshot["customer_distribution_authorized"])
        print("UCIE_LOCAL_V1_OWNER_READONLY_SMOKE=" + json.dumps({
            "status": "FOUR_PRODUCT_ACTION_RENDER_PATHS_OBSERVED_NOT_OWNER_UI_ACCEPTANCE",
            "error_public_link_displayed": "github.com/" in error,
            "evolution_public_link_displayed": "github.com/" in evolution,
            "existing_public_ledger_snapshot_displayed": True,
            "real_owner_browser_walkthrough_completed": False,
            "local_product_go": False,
            "customer_distribution_authorized": False,
            "scheduler_changes": 0,
            "operating_ledger_writes": 0,
            "other_projects_accessed": False,
        }, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
