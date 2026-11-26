"""UCIE B4 original chapter and B3 revision impact linking regression."""
from __future__ import annotations

from unittest import TestCase

from ucie_miner import ucie_v2_revision_impact_v01 as b3
from ucie_miner import ucie_v2_generalization_review_v01 as review


def signal(source_id: str, value: str | None = None) -> dict:
    prior = b3.PINS.get(source_id)
    n = len(prior or "a" * 40)
    return {
        "source_id": source_id,
        "previous_pin": prior,
        "candidate_pin": value if value is not None else "f" * n,
    }


class B4ReviewAndRevisionTests(TestCase):
    def test_original_chapter_includes_two_real_source_pins_and_status(self):
        text = review.render_hypothesis_chapter()
        self.assertIn("9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a", text)
        self.assertIn("1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325", text)
        self.assertIn("UCIE 자체 가설", text)
        self.assertIn("배포 불가", text)
        self.assertIn("공식 사실 아님", text)

    def test_chapter_shows_specific_untransferable_output_privacy(self):
        text = review.render_hypothesis_chapter()
        self.assertIn("파일명 자체를 호출자에게 반환", text)
        self.assertIn("개수만 반환", text)
        self.assertIn("거부한 주장", text)

    def test_chapter_marks_real_sdk_qa_training_and_rights_unproven(self):
        text = review.render_hypothesis_chapter()
        self.assertIn("외부 MCP SDK를 이번에 재실행한 것이 아닙니다", text)
        self.assertIn("권리", text)
        self.assertIn("자동 추론 모델", text)

    def test_python_changed_retains_parent_and_b4_rerun(self):
        x = review.assess_hypothesis_revision((signal("doc:python/cpython"),))
        self.assertTrue(x["b4_hypothesis_impacted"])
        self.assertIn(review.B4_TEST, x["bounded_proposed_test_files"])
        self.assertIn(b3.PRINCIPLE, x["affected_assets"])
        self.assertEqual(x["candidate_hypothesis_sha256"], "NOT_COMPUTED")

    def test_git_changed_retains_parent_and_b4_rerun(self):
        x = review.assess_hypothesis_revision((signal("doc:git/git"),))
        self.assertTrue(x["b4_hypothesis_impacted"])
        self.assertIn(review.B4_TEST, x["bounded_proposed_test_files"])
        self.assertNotIn(b3.PY_BOOK, x["affected_assets"])

    def test_mcp_changed_triggers_target_transfer_retest(self):
        x = review.assess_hypothesis_revision((
            signal("repo:modelcontextprotocol/python-sdk"),))
        self.assertTrue(x["b4_hypothesis_impacted"])
        self.assertIn(review.B4_TEST, x["bounded_proposed_test_files"])
        self.assertNotIn(b3.GIT_BOOK, x["affected_assets"])

    def test_two_parents_trigger_one_deduplicated_retest(self):
        x = review.assess_hypothesis_revision((
            signal("doc:git/git"), signal("doc:python/cpython")))
        self.assertEqual(x["bounded_proposed_test_files"].count(review.B4_TEST), 1)

    def test_unlinked_approved_source_does_not_trigger_b4(self):
        x = review.assess_hypothesis_revision((
            signal("repo:PowerShell/PowerShell"),))
        self.assertFalse(x["b4_hypothesis_impacted"])
        self.assertEqual(x["bounded_proposed_test_files"], [])
        self.assertFalse(x["global_asset_coverage_verified"])

    def test_identical_source_pin_does_not_trigger_b4(self):
        x = review.assess_hypothesis_revision((
            signal("doc:git/git", b3.PINS["doc:git/git"]),))
        self.assertFalse(x["b4_hypothesis_impacted"])
        self.assertEqual(x["bounded_proposed_test_files"], [])

    def test_no_source_changes_yields_no_retest(self):
        x = review.assess_hypothesis_revision(())
        self.assertEqual(x["bounded_proposed_test_files"], [])
        self.assertFalse(x["b4_hypothesis_impacted"])

    def test_stale_source_pin_raises_without_plan(self):
        bad = signal("doc:git/git")
        bad["previous_pin"] = "0" * 64
        with self.assertRaises(b3.RevisionImpactError):
            review.assess_hypothesis_revision((bad,))

    def test_unapproved_source_denied(self):
        with self.assertRaises(b3.RevisionImpactError):
            review.assess_hypothesis_revision((
                signal("repo:unapproved/vendor"),))

    def test_review_is_never_release_or_automatic_schedule(self):
        x = review.assess_hypothesis_revision((signal("doc:python/cpython"),))
        for key in ("source_revision_authenticated",
                    "global_asset_coverage_verified", "source_or_test_auto_executed",
                    "retest_auto_scheduled", "auto_promoted", "model_trained",
                    "customer_release_authorized"):
            self.assertIs(x[key], False)
        self.assertEqual(x["network_requests"], 0)
        self.assertEqual(x["operating_database_writes"], 0)
