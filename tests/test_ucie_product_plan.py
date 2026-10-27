"""Offline focused tests for UCIE V1 four-pillar plan metadata (not product QA)."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from ucie_miner import product_plan as plan


class UcieFinalProductPlanTests(unittest.TestCase):
    def test_four_equal_end_goals_are_not_bugs_only(self):
        result = plan.preview_next_work()
        self.assertEqual(len(result["pillars"]), 4)
        self.assertEqual(
            [x["id"] for x in result["pillars"]],
            ["G1", "G2", "G3", "G4"])
        goals = " ".join(x["goal"] for x in result["pillars"])
        self.assertIn("VIRTUAL_KNOWLEDGE_LIBRARY", goals)
        self.assertIn("LEARNING_LOGIC", goals)
        self.assertIn("EXPERIENCE_DRIVEN", goals)

    def test_acquisition_and_source_selection_are_mandatory(self):
        result = plan.preview_next_work()
        self.assertEqual(
            result["foundations"],
            ["APPROVED_PUBLIC_SOURCE_SELECTION",
             "MODULAR_AUTOMATIC_PUBLIC_ACQUISITION"])
        self.assertEqual(result["immediate_parallel_work"], ["W01", "W02"])
        self.assertEqual(result["next_contract_work"], ["W05"])
        self.assertEqual(result["foundation_code_available"], ["W01", "W02"])

    def test_p0_p9_exact_and_not_falsely_completed(self):
        out = plan.preview_next_work()
        self.assertEqual([r["id"] for r in out["milestones"]],
                         [f"P{i}" for i in range(10)])
        self.assertEqual(out["current_phase"],
                         "P0_BASELINE_OBSERVED__P1_AND_P3_NEXT")
        self.assertEqual(out["status"], "PLAN_DEFINED_IMPLEMENTATION_INCOMPLETE")
        self.assertFalse(out["v1_accepted"])
        self.assertTrue(all(x["planning_state"] != "V1_ACCEPTED"
                            for x in out["milestones"]))

    def test_dependencies_are_ordered_and_work_never_reports_done(self):
        self.assertTrue(plan.validate_product_plan())
        out = plan.preview_next_work()
        order = out["work_order"]
        self.assertEqual([r["id"] for r in order],
                         [f"W{i:02d}" for i in range(1, 11)])
        seen = set()
        for work in order:
            self.assertEqual(work["execution_state"],
                             ("FOUNDATION_CODE_IMPLEMENTED_NOT_HOST_VERIFIED"
                              if work["id"] in {"W01", "W02"}
                              else "PLANNED_NOT_EXECUTED"))
            self.assertTrue(set(work["depends_on"]) <= seen)
            self.assertTrue(work["acceptance"])
            seen.add(work["id"])

    def test_only_five_previously_approved_independent_sources(self):
        out = plan.preview_next_work()
        self.assertEqual(set(out["approved_public_repositories"]), {
            "python/cpython", "PowerShell/PowerShell", "git/git",
            "modelcontextprotocol/python-sdk", "actions/runner-images"})
        self.assertNotIn("GH Archive", out["approved_public_repositories"])
        self.assertIn("GH Archive", out["research_only_source_candidates"])
        self.assertFalse(out["source_allowlist_changed"])

    def test_unapproved_repo_mutation_rejected_in_plan_validation(self):
        with patch.object(plan, "APPROVED_REPOSITORIES",
                          plan.APPROVED_REPOSITORIES + ("other/repository",)):
            with self.assertRaises(ValueError):
                plan.validate_product_plan()

    def test_invalid_dependency_or_status_is_rejected(self):
        altered = list(plan.WORK)
        original = altered[1]
        altered[1] = (original[0], original[1], original[2],
                      ("W09",), original[4])
        with patch.object(plan, "WORK", tuple(altered)):
            with self.assertRaises(ValueError):
                plan.validate_product_plan()
        bad = list(plan.MILESTONES)
        original = bad[-1]
        bad[-1] = (original[0], original[1], "V1_ACCEPTED", original[3])
        with patch.object(plan, "MILESTONES", tuple(bad)):
            with self.assertRaises(ValueError):
                plan.validate_product_plan()

    def test_planning_preview_never_changes_runtime_or_approval(self):
        out = plan.preview_next_work()
        for flag in (
            "source_allowlist_changed", "runtime_modified",
            "scheduled_task_registered", "other_projects_accessed",
            "candidate_auto_promoted", "rulepacks_signed", "v1_accepted"):
            self.assertIs(out[flag], False)
        self.assertEqual(out["network_requests"], 0)
        self.assertEqual(out["operating_database_writes"], 0)

    def test_cli_is_inert_deterministic_json(self):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "ucie_miner.product_plan"],
            capture_output=True, text=True, check=False, timeout=12)
        self.assertEqual(result.returncode, 0, result.stderr[:300])
        self.assertEqual(json.loads(result.stdout), plan.preview_next_work())


if __name__ == "__main__":
    unittest.main()
