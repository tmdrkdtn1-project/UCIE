"""UCIE-only B1/B2 real module linkage and fail-closed unit regression.

No external SDK run: historic pinned CI remains a prior first-party receipt.
All calls to source modules operate on deterministic UCIE-owned fixtures.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import re
import unittest

from ucie_miner import ucie_v2_capsule_v01 as c
from ucie_miner import ucie_v2_beginner_preview_v01 as b
from ucie_miner.mcp_prompts_guide_v01 import build_readonly_guide
from ucie_miner.local_b2_connected_workbench_v01 import evaluate_case


def inputs():
    return (build_readonly_guide(), evaluate_case("mcp-prompts", "issue"),
            evaluate_case("mcp-prompts", "control"))


class V2CapsuleTests(unittest.TestCase):
    def setUp(self):
        self.guide, self.issue, self.control = inputs()

    def reject(self, change):
        data = [deepcopy(self.guide), deepcopy(self.issue),
                deepcopy(self.control)]
        change(*data)
        with self.assertRaises(c.CapsuleContractError):
            c.build_capsule(*data)

    def test_actual_preexisting_modules_join_one_case(self):
        x = c.build_from_existing_ucie()
        self.assertEqual(x.case_id, "mcp-prompts")
        self.assertEqual(x.capsule_id, c.CAPSULE_ID)
        self.assertEqual(x.skillbook_id, c.SKILLBOOK_ID)
        self.assertEqual(x.first_party_sdk_ci_url, c.REAL_SDK_CI)
        self.assertEqual(x.historic_sdk_calls, 16)
        self.assertEqual(x.synthetic_issue, "CONTRACT_VIOLATION")
        self.assertEqual(x.synthetic_control, "CONTRACT_MATCH")
        self.assertEqual(x.independent_qa, "NOT_VERIFIED")
        self.assertEqual(x.customer_release, "NOT_AUTHORIZED")

    def test_capsule_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            c.build_from_existing_ucie().rights = "APPROVED"

    def test_draft_status_forgery_rejected(self):
        self.reject(lambda g, i, q: g.__setitem__("status", "APPROVED"))
        self.reject(lambda g, i, q: g.__setitem__("auto_promoted", True))

    def test_guide_network_or_db_write_forgery_rejected(self):
        self.reject(lambda g, i, q: g.__setitem__("network_requests", 1))
        self.reject(lambda g, i, q: g.__setitem__("operating_database_writes", 1))
        self.reject(lambda g, i, q: g.__setitem__("other_project_access", True))

    def test_synthetic_state_forgery_rejected(self):
        self.reject(lambda g, i, q: i.__setitem__("status", "INDEPENDENTLY_VERIFIED"))

    def test_wrong_source_repo_rejected(self):
        self.reject(lambda g, i, q: g["source_evidence"].__setitem__(
            "official_repository", "unapproved/repo"))

    def test_wrong_sha_commit_rejected(self):
        self.reject(lambda g, i, q: g["source_evidence"].__setitem__(
            "patch_merge_commit", "0" * 40))

    def test_wrong_source_pr_rejected(self):
        self.reject(lambda g, i, q: g["source_evidence"].__setitem__(
            "pr_url", "https://example.invalid"))

    def test_wrong_fixed_release_claim_rejected(self):
        self.reject(lambda g, i, q: g["source_evidence"].__setitem__(
            "first_published_fixed_version", "2.3.1"))

    def test_historic_real_sdk_run_id_forgery_rejected(self):
        self.reject(lambda g, i, q: g["source_evidence"].__setitem__(
            "isolated_real_sdk_in_memory_ci", "https://example.invalid"))

    def test_fake_historic_sdk_call_count_rejected(self):
        self.reject(lambda g, i, q: g["source_evidence"].__setitem__(
            "observed_cases", 17))

    def test_bool_as_integer_rights_forgery_rejected(self):
        self.reject(lambda g, i, q: g.__setitem__("export_allowed", 0))
        self.reject(lambda g, i, q: g["review_gates"].__setitem__(
            "published", 0))

    def test_reviewer_permission_forgery_rejected(self):
        self.reject(lambda g, i, q: g["review_gates"].__setitem__(
            "human_approved", True))
        self.reject(lambda g, i, q: g["review_gates"].__setitem__(
            "customer_release_authorized", True))

    def test_wrong_machine_recipe_rejected(self):
        self.reject(lambda g, i, q: g["machine_skill_contract"].__setitem__(
            "callable", "os.system"))

    def test_invalid_protocol_modes_rejected(self):
        self.reject(lambda g, i, q: g["machine_skill_contract"].__setitem__(
            "protocols", ["unknown"]))

    def test_cross_case_false_join_rejected(self):
        self.reject(lambda g, i, q: i.__setitem__("case_id", "git-repository"))

    def test_synthetic_as_real_fix_rejected(self):
        self.reject(lambda g, i, q: i.__setitem__(
            "actual_user_environment_inspected", True))
        self.reject(lambda g, i, q: i.__setitem__(
            "independent_fix_validated", True))

    def test_wrong_control_rejected(self):
        self.reject(lambda g, i, q: q.__setitem__(
            "result_code", "CONTRACT_VIOLATION"))

    def test_synthetic_record_type_forgery_rejected(self):
        self.reject(lambda g, i, q: i.__setitem__("fixture_evaluated", 1))
        self.reject(lambda g, i, q: q.__setitem__("network_requests", False))

    def test_unknown_customer_version_holds(self):
        r = c.evaluate_applicability(c.build_from_existing_ucie())
        self.assertEqual(r["decision"], "HOLD")
        self.assertEqual(r["applicability"], "UNKNOWN_NO_PROOF")
        self.assertFalse(r["customer_pc_tested"])

    def test_exact_historic_in_memory_scope_not_customer_pass(self):
        x = c.build_from_existing_ucie()
        for v in c.SDK_BUILDS:
            r = c.evaluate_applicability(
                x, version=v, transport="in_memory", protocol_mode="legacy")
            self.assertEqual(r["applicability"], "EXACT_TESTED")
            self.assertEqual(r["decision"], "REFERENCE_ONLY_NOT_CUSTOMER_APPROVED")
            self.assertFalse(r["may_claim_fixed"])

    def test_unsupported_version_and_transport_hold(self):
        x = c.build_from_existing_ucie()
        for kwargs in (
            {"version":"2.3.1", "transport":"in_memory", "protocol_mode":"legacy"},
            {"version":"2.3.0", "transport":"http", "protocol_mode":"legacy"},
            {"version":"2.3.0", "transport":"stdio", "protocol_mode":"2026-07-28"},
            {"version":"2.3.0", "transport":"in_memory", "protocol_mode":"unknown"},
        ):
            self.assertEqual(c.evaluate_applicability(x, **kwargs)["decision"], "HOLD")

    def test_bounded_environment_and_type_reject(self):
        with self.assertRaises(c.CapsuleContractError):
            c.evaluate_applicability(c.build_from_existing_ucie(), version={})
        with self.assertRaises(c.CapsuleContractError):
            c.evaluate_applicability(c.build_from_existing_ucie(), version="x" * 100)

    def test_wrong_applicability_rejected_in_explanation(self):
        x = c.build_from_existing_ucie()
        r = c.evaluate_applicability(x)
        r["decision"] = "REFERENCE_ONLY_NOT_CUSTOMER_APPROVED"
        with self.assertRaises(c.CapsuleContractError):
            c.explain_for_beginner(x, r)

    def test_fake_exact_test_rejected_in_explanation(self):
        x = c.build_from_existing_ucie()
        r = c.evaluate_applicability(x)
        r["decision"] = "REFERENCE_ONLY_NOT_CUSTOMER_APPROVED"
        r["applicability"] = "EXACT_TESTED"
        with self.assertRaises(c.CapsuleContractError):
            c.explain_for_beginner(x, r)

    def test_false_customer_rights_rejected(self):
        x = c.build_from_existing_ucie()
        r = c.evaluate_applicability(x)
        r["rights"] = "LICENSED_FOR_SCOPED_RECIPIENT"
        with self.assertRaises(c.CapsuleContractError):
            c.explain_for_beginner(x, r)

    def test_additional_unverified_status_rejected(self):
        x = c.build_from_existing_ucie()
        r = c.evaluate_applicability(x)
        r["verified_by_customer"] = True
        with self.assertRaises(c.CapsuleContractError):
            c.explain_for_beginner(x, r)

    def test_read_only_default_preserves_four_pillars_and_hold(self):
        p = c.read_only_default()
        self.assertEqual(p["capsule_id"], c.CAPSULE_ID)
        self.assertEqual(p["case_id"], c.CASE_ID)
        self.assertEqual(p["skillbook_id"], c.SKILLBOOK_ID)
        self.assertIn("HISTORIC", p["revision_status"])
        self.assertFalse(p["sdk_reexecuted_now"])
        self.assertFalse(p["auto_promoted"])
        self.assertFalse(p["actual_code_repaired"])


class V2BeginnerPreviewTests(unittest.TestCase):
    def test_actual_b1_evidence_embedded_not_mock(self):
        html = b.render_preview()
        match = re.search(
            r'<script type="application/json" id="ucie-b1-evidence">(.*?)</script>',
            html, re.S)
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(data, c.read_only_default())
        self.assertEqual(data["decision"], "HOLD")

    def test_three_choices_four_supported_cases_and_unmatched(self):
        html = b.render_preview()
        self.assertEqual(html.count('data-flow="'), 3)
        self.assertEqual(html.count('data-issue="'), 5)
        self.assertIn('data-issue="mcp-prompts"', html)
        self.assertIn("기존 라이브러리", html)

    def test_no_new_post_customer_upload_or_model_action(self):
        html = b.render_preview()
        for forbidden in ("<form", 'method="post"', "fetch(", "XMLHttpRequest",
                          "localStorage", "sessionStorage", "innerHTML",
                          "sendBeacon", "WebSocket"):
            self.assertNotIn(forbidden, html)

    def test_evidence_optional_and_no_copied_wrong_case(self):
        html = b.render_preview()
        self.assertIn('<details id="proof" hidden>', html)
        self.assertIn("MCP의 증거를 잘못 적용하지 않습니다", html)
        self.assertIn("독립 QA", html)

    def test_accessibility_basics(self):
        html = b.render_preview()
        self.assertIn("focus-visible", html)
        self.assertIn('lang="ko"', html)
        self.assertIn('tabindex="-1"', html)
        self.assertIn("prefers-reduced-motion", html)


if __name__ == "__main__":
    unittest.main()
