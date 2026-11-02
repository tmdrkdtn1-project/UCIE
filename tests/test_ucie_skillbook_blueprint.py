"""Focused inert SkillBook blueprint regression; NOT external skill QA."""
from __future__ import annotations

import copy
import re
import unittest
from unittest.mock import patch

from ucie_miner import product_plan as plan
from ucie_miner.skillbook_blueprint import compose_blueprint, SkillBookBlueprintError

SHA = "a" * 64
ONE = {
    "kind": "REUSABLE_SKILL",
    "source_id": "repo:python/cpython",
    "evidence_reference": "pr:12345:" + "b" * 40,
    "evidence_sha256": SHA,
    "purpose_code": "SKILL_TEST_AUTOMATION",
    "version_scope": "3.15",
    "dependencies": [],
}
TWO = {
    "kind": "DEVELOPMENT_ENGINE",
    "source_id": "repo:PowerShell/PowerShell",
    "evidence_reference": "pr:9876:" + "c" * 40,
    "evidence_sha256": "d" * 64,
    "purpose_code": "ENGINE_WORKFLOW_ORCHESTRATION",
    "version_scope": "7.0",
    "dependencies": [],
}


class SkillBookBlueprintTests(unittest.TestCase):
    def test_product_contract_preserves_core_pipeline(self):
        self.assertTrue(plan.validate_product_plan())
        preview = plan.preview_next_work()
        self.assertEqual(preview["skillbook_mission"]["state"], "PLANNED_NOT_ACCEPTED")
        self.assertEqual(len(preview["skillbook_mission"]["pipeline"]), 8)
        self.assertIn("REPROCESS_AND_GENERALIZE_TECHNICAL_PRINCIPLES", preview["skillbook_mission"]["pipeline"])
        self.assertIn("RECLASSIFY_AND_COMPOSE_SKILLBOOK_CHAPTERS", preview["skillbook_mission"]["pipeline"])
        self.assertFalse(preview["skillbook_mission"]["paid_demand_verified"])

    def test_sorts_and_reconstructs_verified_scope_without_export(self):
        a = compose_blueprint("WINDOWS_AUTOMATION", [ONE, TWO])
        b = compose_blueprint("WINDOWS_AUTOMATION", [TWO, ONE])
        self.assertEqual(a, b)
        self.assertEqual(a["chapter_count"], 2)
        self.assertRegex(a["blueprint_id"], r"^[0-9a-f]{64}$")
        self.assertEqual(a["status"], "UNVERIFIED_METADATA_ONLY")
        self.assertTrue(all(not row["export_allowed"] for row in a["chapters"]))
        for key in ("human_readable_skillbook_created", "machine_readable_skill_implemented",
                    "independent_qa_passed", "rights_cleared", "human_approved",
                    "export_allowed", "auto_promoted", "model_trained"):
            self.assertIs(a[key], False)

    def test_rejects_duplicate_evidence_and_forged_approval(self):
        with self.assertRaises(SkillBookBlueprintError):
            compose_blueprint("WINDOWS_AUTOMATION", [ONE, copy.deepcopy(ONE)])
        forged = dict(ONE, export_allowed=True, approval_status="APPROVED")
        with self.assertRaises(SkillBookBlueprintError):
            compose_blueprint("WINDOWS_AUTOMATION", [forged])

    def test_rejects_unapproved_source_and_bad_topic(self):
        candidate = dict(ONE, source_id="repo:unknown/unknown")
        with self.assertRaises(SkillBookBlueprintError):
            compose_blueprint("WINDOWS_AUTOMATION", [candidate])
        with self.assertRaises(SkillBookBlueprintError):
            compose_blueprint("../unsafe", [ONE])

    def test_rejects_invalid_data_shape_and_empty(self):
        for data in ([], [ONE] * 21, [None], [{"kind": "REUSABLE_SKILL"}]):
            with self.assertRaises(SkillBookBlueprintError):
                compose_blueprint("WINDOWS_AUTOMATION", data)
        with self.assertRaises(SkillBookBlueprintError):
            compose_blueprint("WINDOWS_AUTOMATION", dict(ONE))

    def test_cannot_remove_required_skillbook_stage_or_deliverable(self):
        with patch.object(plan, "SKILLBOOK_PIPELINE", plan.SKILLBOOK_PIPELINE[:-1]):
            with self.assertRaises(ValueError):
                plan.validate_product_plan()
        with patch.object(plan, "SKILLBOOK_DELIVERABLES", plan.SKILLBOOK_DELIVERABLES[:-1]):
            with self.assertRaises(ValueError):
                plan.validate_product_plan()


if __name__ == "__main__":
    unittest.main()
