"""B1 capsule + B4 original review assets -> truthful B2 isolated journey."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from ucie_miner import ucie_v2_library_capsule_journey_v01 as subject
from ucie_miner import ucie_v2_original_reusable_review_package_v01 as packages
from ucie_miner import ucie_v2_revision_review_history_v01 as reviews
from ucie_miner import ucie_v2_feedback_registry_v01 as feedback
from ucie_miner import ucie_v2_library_revision_ledger_v01 as library
from ucie_miner import ucie_v2_original_library_assets_v01 as original
from ucie_miner import ucie_v2_b5_comparison_contract_v01 as b5


SHA="a"*64

def study(m):
    return {"study_id":b5.STUDY_ID,"case_id":b5.CASE_ID,
            "anonymous_trial_token":"F01","method":m,
            "cohort":"FIRST_TIME_CODER","first_safe_action_time_ms":900,
            "correct_safe_action":True,"false_version_or_rights_claim":False,
            "evidence_detail_found":False,"origin":b5.SYNTHETIC_ORIGIN}

def case(tag,i,wrong=False):
    truth="RISK" if i<4 else "SAFE"
    return {"case_id":f"{tag}_{i}","ground_truth":truth,
            "baseline_prediction":truth,
            "challenger_prediction":"SAFE" if wrong and i==1 else truth,
            "origin":"UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY","source_sha256":SHA}


class LibraryCapsuleJourneyTests(TestCase):
    @classmethod
    def setUpClass(cls):
        bundle=original.assemble_original_library_assets(
            tuple(study(m) for m in b5.METHODS),())
        cls.h=library.append_review_bundle(library.new_review_history(),bundle)
        cls.f=feedback.append_feedback_evidence(
            cls.h,feedback.empty_feedback_registry(cls.h),
            execute_synthetic=True)
        cls.r=reviews.new_revision_history(cls.h)
        ids=[x["candidate_id"] for x in feedback.prioritize_review_experiments(
            cls.h,cls.f)["priority_queue"]]
        cls.before={ids[0]:[case("a",i,True) for i in range(8)],
                    ids[1]:[case("b",i) for i in range(8)]}
        cls.after={ids[0]:[case("a",i) for i in range(8)],
                   ids[1]:[case("b",i) for i in range(8)]}

    def build(self,**kwargs):
        params=dict(fixture_sha256=SHA,
                    expected_revision_head_sha256=self.r["content_sha256"])
        params.update(kwargs)
        return subject.build_review_journey(
            self.h,self.f,self.r,self.before,self.after,**params)

    def test_real_capsule_and_related_library_artifacts_join(self):
        r=self.build()
        self.assertEqual(r["case_id"],"mcp-prompts")
        self.assertEqual(r["capsule_id"],
                         "UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01")
        self.assertEqual(len(r["related_review_packages"]),2)
        self.assertTrue(all(x["connected_via"]==
            "MCP_TARGET_AND_PIN_ONLY_NOT_SAME_EXPERIMENT"
            for x in r["related_review_packages"]))

    def test_three_readable_steps_and_optional_proof(self):
        html=subject.render_isolated_journey(self.build())
        for step in ("1. 어떤 도움이 필요하세요?",
                     "2. 확인된 범위는 어디까지인가요?",
                     "3. 지금 확인할 일",
                     "왜 이렇게 안내하나요?"):
            self.assertIn(step,html)
        self.assertNotIn("<form",html)
        self.assertNotIn("type=\"submit\"",html)

    def test_unknown_environment_defaults_to_hold(self):
        r=self.build()
        self.assertEqual(r["applicability"],"UNKNOWN_NO_PROOF")
        self.assertEqual(r["decision"],"HOLD")

    def test_exact_historical_test_environment_still_not_release(self):
        r=self.build(version="2.3.0",transport="in_memory",
                     protocol_mode="legacy")
        self.assertEqual(r["applicability"],"EXACT_TESTED")
        self.assertFalse(r["customer_distribution_authorized"])
        self.assertIn("배포 미승인",subject.render_isolated_journey(r))

    def test_unapproved_sdk_version_does_not_autopass(self):
        r=self.build(version="999.0.0",transport="http",
                     protocol_mode="legacy")
        self.assertEqual(r["decision"],"HOLD")

    def test_wrong_related_capsule_denied(self):
        original_builder=packages.build_original_review_packages
        fake=deepcopy(original_builder(
            self.h,self.f,self.r,self.before,self.after,fixture_sha256=SHA,
            expected_revision_head_sha256=self.r["content_sha256"]))
        fake["review_packages"][0]["engine_test_contract"]["target_capsule_id"]="other"
        with patch.object(subject,"build_original_review_packages",return_value=fake):
            with self.assertRaises(subject.LibraryJourneyError):
                self.build()

    def test_false_rights_even_rehashed_denied(self):
        r=self.build()
        r["related_review_packages"][0]["rights_approved"]=True
        r["content_sha256"]=subject._sha({
            k:v for k,v in r.items() if k!="content_sha256"})
        with self.assertRaises(subject.LibraryJourneyError):
            subject.render_isolated_journey(r)

    def test_customer_code_is_never_required_or_echoed(self):
        html=subject.render_isolated_journey(self.build())
        self.assertNotIn("textarea",html)
        self.assertNotIn("고객 코드 입력",html)
        self.assertFalse(self.build()["private_question_text_retained"])

    def test_original_inputs_unchanged_and_deterministic(self):
        old=deepcopy((self.h,self.f,self.r,self.before,self.after))
        x=self.build()
        self.assertEqual(x,self.build())
        self.assertEqual(old,(self.h,self.f,self.r,self.before,self.after))

    def test_stale_review_head_denied(self):
        with self.assertRaises(ValueError):
            self.build(expected_revision_head_sha256="f"*64)

    def test_hidden_new_endpoint_denied(self):
        r=self.build()
        r["new_post_endpoint_created"]=True
        r["content_sha256"]=subject._sha({
            k:v for k,v in r.items() if k!="content_sha256"})
        with self.assertRaises(subject.LibraryJourneyError):
            subject.render_isolated_journey(r)


class ExistingQuestionToEvidenceTests(LibraryCapsuleJourneyTests):
    """Actual existing /local/ask result feeds the isolated B1/B2/B4 flow."""

    @staticmethod
    def body(s):
        from urllib.parse import urlencode
        return urlencode({"question": s}).encode("ascii")

    def build_flow(self, text):
        return subject.build_isolated_question_flow(
            self.body(text), self.h,self.f,self.r,self.before,self.after,
            fixture_sha256=SHA,
            expected_revision_head_sha256=self.r["content_sha256"])

    def test_existing_mcp_question_joins_same_capsule_and_reviewed_assets(self):
        result=self.build_flow("MCP prompts/get 호출에서 인수 오류 -32602가 발생합니다.")
        self.assertEqual(result["case_id"],"mcp-prompts")
        self.assertEqual(result["linked_capsule_id"],subject.CAPSULE_ID)
        html=subject.render_isolated_question_flow(result)
        self.assertIn("왜 이렇게 안내하나요?",html)
        self.assertIn("고객 환경에서 수정 효과",html)
        self.assertNotIn("MCP prompts/get 호출에서 인수 오류",html)

    def test_other_three_supported_cases_do_not_invent_mcp_proof(self):
        samples=(
            ("Python에서 패키지를 설치했는데 ModuleNotFoundError가 발생합니다.","python-env"),
            ("PowerShell에서 명령을 입력했는데 명령을 찾을 수 없습니다.","powershell-command"),
            ("Git 명령을 실행했는데 not a git repository 오류가 납니다.","git-repository"),
        )
        for text,case in samples:
            with self.subTest(case=case):
                result=self.build_flow(text)
                self.assertEqual(result["case_id"],case)
                self.assertIsNone(result["linked_capsule_id"])
                self.assertIsNone(result["mcp_evidence_journey"])
                self.assertIn("UCIE가 만든 예제",
                    subject.render_isolated_question_flow(result))

    def test_unsupported_question_fails_closed_without_fake_source(self):
        result=self.build_flow("프로그램 화면이 너무 느려서 확인 방법을 알고 싶습니다.")
        self.assertIsNone(result["case_id"])
        self.assertIsNone(result["linked_skillbook_id"])
        self.assertIn("아직 이 문제에 맞는 안내가 없어요",
            subject.render_isolated_question_flow(result))

    def test_sensitive_text_rejected_and_not_echoed(self):
        from ucie_miner.local_question_intake_v01 import QuestionInputError
        secret="MCP prompts/get 오류인데 token=MY_PRIVATE_VALUE 이 보입니다."
        with self.assertRaises(QuestionInputError) as caught:
            self.build_flow(secret)
        self.assertNotIn("MY_PRIVATE_VALUE",str(caught.exception))

    def test_false_release_after_rehash_denied(self):
        flow=self.build_flow("MCP prompts/get 호출에서 인수 오류 -32602가 발생합니다.")
        flow["customer_export_authorized"]=True
        flow["content_sha256"]=subject._sha({
            k:v for k,v in flow.items() if k != "content_sha256"})
        with self.assertRaises(subject.LibraryJourneyError):
            subject.render_isolated_question_flow(flow)

    def test_wrong_mcp_capsule_after_rehash_denied(self):
        flow=self.build_flow("MCP prompts/get 호출에서 인수 오류 -32602가 발생합니다.")
        flow["linked_capsule_id"]="forged"
        flow["content_sha256"]=subject._sha({
            k:v for k,v in flow.items() if k != "content_sha256"})
        with self.assertRaises(subject.LibraryJourneyError):
            subject.render_isolated_question_flow(flow)

    def test_no_new_route_or_background_effect(self):
        result=self.build_flow("MCP prompts/get 호출에서 인수 오류 -32602가 발생합니다.")
        self.assertFalse(result["new_http_endpoint_created"])
        self.assertFalse(result["question_retained"])
        self.assertFalse(result["automatic_ai_called"])
        self.assertEqual(result["network_requests"],0)
        self.assertEqual(result["operating_database_writes"],0)
