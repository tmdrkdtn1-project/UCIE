"""B4 real documented delta addendum: same Capsule and no unearned approval."""
import unittest
from unittest.mock import patch

from ucie_miner import b4_python315_revision_addendum_v01 as module


class B4Python315RevisionAddendumTests(unittest.TestCase):
    def test_original_addendum_joins_pinned_b1_b3_b4(self):
        r = module.build_python315_revision_addendum()
        self.assertEqual(r["case_id"], "UCIE-SKILLBOOK-PY-SCANDIR-001")
        self.assertIn("os.scandir(-1)", r["official_change_note"])
        self.assertEqual(r["static_local_callsite_verdict"],
                         "NO_DIRECT_NEGATIVE_FD_PATTERN_IN_AUDITED_FUNCTION")
        self.assertEqual(r["machine_check"]["observed_ucie_call"],
                         "os.scandir(directory)")
        self.assertEqual(r["actual_customer_callsite"], "UNKNOWN_NOT_INSPECTED")
        self.assertFalse(r["documentation_sha_attested"])
        self.assertFalse(r["official_change_commit_authenticated"])
        self.assertFalse(r["owner_approved"])
        self.assertFalse(r["export_allowed"])

    def test_mismatched_capsule_id_is_blocked(self):
        audit = module.audit_trusted_scandir_recipe()
        with patch.object(module, "audit_trusted_scandir_recipe",
                          return_value={**audit, "capsule_id": "FORGED"}):
            with self.assertRaisesRegex(
                module.RevisionAddendumError, "PROOF_DRIFT"):
                module.build_python315_revision_addendum()

    def test_false_official_commit_authentication_is_blocked(self):
        from ucie_miner.b3_documented_scandir_315_delta_v01 import (
            PYTHON_CASE, evaluate_documented_scandir_delta,
        )
        delta = evaluate_documented_scandir_delta(PYTHON_CASE,
                                                   proposed_runtime="3.15")
        with patch.object(module, "evaluate_documented_scandir_delta",
                          return_value={**delta, "official_revision_commit_verified": True}):
            with self.assertRaisesRegex(module.RevisionAddendumError, "PROOF_DRIFT"):
                module.build_python315_revision_addendum()

    def test_source_mismatch_fails_closed(self):
        from ucie_miner.b1_b4_skillbook_capsule_link_v01 import (
            build_b4_capsule_journey,
        )
        joined = build_b4_capsule_journey(
            "UCIE-SKILLBOOK-PY-SCANDIR-001")
        with patch.object(module, "build_b4_capsule_journey",
                          return_value={**joined, "case_id": "OTHER"}):
            with self.assertRaisesRegex(module.RevisionAddendumError, "PROOF_DRIFT"):
                module.build_python315_revision_addendum()

    def test_review_only_markdown_and_deterministic_receipt(self):
        a = module.build_python315_revision_addendum()
        b = module.build_python315_revision_addendum()
        self.assertEqual(a, b)
        self.assertEqual(len(a["content_sha256"]), 64)
        text = module.render_python315_addendum_markdown()
        self.assertIn(a["capsule_id"], text)
        self.assertIn(a["skillbook_id"], text)
        self.assertIn("고객 환경 검증/독립 QA/권리 승인: 미완료", text)
        self.assertNotIn("고객 코드 수정 완료", text)


if __name__ == "__main__":
    unittest.main()
