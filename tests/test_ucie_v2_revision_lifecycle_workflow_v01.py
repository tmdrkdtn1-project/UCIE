"""UCIE-only actual B1-B3-B4 source-impact lifecycle in the B2 local page."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from ucie_miner import ucie_v2_revision_lifecycle_workflow_v01 as s
from ucie_miner import ucie_v2_revision_impact_v01 as b3


class LifecycleProductTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = s.build_revision_lifecycle()

    def test_real_pinned_mcp_capsule_used(self):
        self.assertEqual(self.report["capsule_id"], b3.MCP_ASSET)
        self.assertEqual(self.report["skillbook_id"], b3.MCP_SKILLBOOK)
        self.assertEqual(self.report["fixed_source_commit"],
                         b3.PINS["repo:modelcontextprotocol/python-sdk"])

    def test_mcp_hypothesis_holds_only_mcp_assets(self):
        a = self.report["review_workflows"][0]
        changed = [r["asset_id"] for r in a["asset_review_states"]
                   if r["affected_by_hypothesis"]]
        self.assertEqual(set(changed), {b3.MCP_ASSET, b3.MCP_SKILLBOOK})
        self.assertEqual(len(a["proposed_test_files_not_executed"]), 3)
        self.assertNotIn(b3.PRINCIPLE, changed)

    def test_git_hypothesis_holds_git_and_principle_not_mcp(self):
        a = self.report["review_workflows"][1]
        changed = [r["asset_id"] for r in a["asset_review_states"]
                   if r["affected_by_hypothesis"]]
        self.assertEqual(set(changed), {b3.GIT_BOOK, b3.PRINCIPLE})
        self.assertEqual(len(a["proposed_test_files_not_executed"]), 2)

    def test_unchanged_pin_does_not_invent_new_retest(self):
        a = self.report["review_workflows"][2]
        self.assertEqual(a["status"], "UNCHANGED_PIN_NO_RETEST")
        self.assertEqual(a["proposed_test_files_not_executed"], [])
        self.assertFalse(any(r["affected_by_hypothesis"]
                             for r in a["asset_review_states"]))

    def test_two_original_review_packages_linked_not_approved(self):
        for row in self.report["review_workflows"]:
            self.assertEqual(len(row["bounded_library_review_packages"]), 2)
            for p in row["bounded_library_review_packages"]:
                self.assertFalse(p["export_allowed"])
                self.assertFalse(p["independent_sdk_compatibility_proven"])

    def test_changed_mcp_requires_review_of_derived_packages(self):
        a = self.report["review_workflows"][0]
        self.assertTrue(all(p["review_state"] ==
            "HOLD_REASSESS_SOURCE_CHANGE_HYPOTHESIS"
            for p in a["bounded_library_review_packages"]))

    def test_other_change_does_not_fake_mcp_sdk_retest(self):
        for a in self.report["review_workflows"][1:]:
            self.assertTrue(all(p["review_state"] ==
                "HOLD_DRAFT_INDEPENDENT_QA_REQUIRED"
                for p in a["bounded_library_review_packages"]))

    def test_default_view_is_truthful_and_complete(self):
        html=s.render_revision_lifecycle(self.report)
        self.assertIn("기술이 바뀌면 예전 검증을 어떻게 다룰까요?",html)
        self.assertEqual(html.count('class="lifecycle-step"'),3)
        self.assertIn("실제 변경 미조회",html)
        self.assertIn("자동 시험/규칙 승격 없음",html)

    def test_owner_checklist_is_plain_human_not_signoff(self):
        html=s.render_owner_acceptance_checklist()
        self.assertIn("아직 미인수",html)
        self.assertIn("실제 사람의 수행 시간",html)
        self.assertEqual(html.count("<li>"),5)

    def test_source_change_not_authenticated_or_executed(self):
        self.assertFalse(self.report["real_source_changes_observed"])
        self.assertFalse(self.report["source_revision_independently_authenticated"])
        self.assertFalse(self.report["tests_executed_by_this_workflow"])
        self.assertFalse(self.report["customer_distribution_authorized"])
        self.assertEqual(self.report["operating_database_writes"], 0)
        self.assertEqual(self.report["network_requests"], 0)

    def test_deterministic_and_no_test_effects(self):
        self.assertEqual(self.report, s.build_revision_lifecycle())

    def test_forged_qa_with_valid_rehash_denied(self):
        r=deepcopy(self.report)
        r["independent_qa_verified"]=True
        r["content_sha256"]=s._digest({
            k:v for k,v in r.items() if k!="content_sha256"})
        with self.assertRaises(s.RevisionLifecycleError):
            s.render_revision_lifecycle(r)

    def test_forged_asset_release_with_valid_rehash_denied(self):
        r=deepcopy(self.report)
        r["review_workflows"][0]["asset_review_states"][0][
            "customer_release_authorized"]=True
        r["content_sha256"]=s._digest({
            k:v for k,v in r.items() if k!="content_sha256"})
        with self.assertRaises(s.RevisionLifecycleError):
            s.render_revision_lifecycle(r)

    def test_injected_external_case_with_valid_rehash_denied(self):
        r=deepcopy(self.report)
        r["review_workflows"][0]["source_id"]="repo:outside/private"
        r["content_sha256"]=s._digest({
            k:v for k,v in r.items() if k!="content_sha256"})
        with self.assertRaises(s.RevisionLifecycleError):
            s.render_revision_lifecycle(r)

    def test_source_pin_drift_fails_closed(self):
        with patch.dict(b3.PINS, {"doc:git/git":"b"*64}):
            with self.assertRaises(b3.RevisionImpactError):
                s.build_revision_lifecycle()

    def test_no_new_network_or_external_execution(self):
        with patch("urllib.request.urlopen",
                   side_effect=AssertionError("network")):
            with patch("subprocess.run",
                       side_effect=AssertionError("subprocess")):
                r=s.build_revision_lifecycle()
        self.assertEqual(r["operating_database_writes"],0)

    def test_history_is_not_rewritten_as_current_sdk_pass(self):
        self.assertFalse(self.report["real_customer_environment_tested"])
        self.assertFalse(self.report["real_owner_edge_retested_for_this_revision"])
        self.assertFalse(self.report["rights_approved"])
