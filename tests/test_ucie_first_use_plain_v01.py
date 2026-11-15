"""Owner Local V04 first-use UX: plain Korean, true claims, navigable actions.

Only public/first-party synthetic cases; no outside project, cloud service,
operating SQLite write, customer release, subscription, or hidden JS.
"""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from ucie_miner import local_first_use_plain_v01 as simple
from ucie_miner import local_v1_app_v01 as app
from ucie_miner import local_v1_design_v04 as design
from test_ucie_local_v1_product_v01 import public_rows
from test_ucie_local_v1_design_v04 import visible_text


class FirstUsePlainKoreanTests(unittest.TestCase):
    def test_01_three_clear_job_to_action_choices_before_expert_navigation(self):
        html=app._home()
        self.assertIn('data-first-use="v01"',html)
        self.assertEqual(html.count('class="start-task"'),3)
        self.assertLess(html.index('data-first-use="v01"'),
                        html.index('data-more-functions="true"'))
        for intent in ("지금 겪는 문제부터 해결하고 싶어요","직접 실행해 보고 싶어요",
                       "사용법과 기술 자료를 찾고 싶어요"):
            self.assertIn(intent,visible_text(html))
        self.assertEqual(html.count('class="pillar-card"'),4)

    def test_02_existing_real_routes_have_descriptive_action_labels(self):
        html=simple.render_first_use()
        expected={
            "/local/ask":"내 문제 직접 설명하기",
            "/local/engine?purpose=SKILL_TEST_AUTOMATION":"예제 직접 체험하기",
            "/local/library?q=Git":"기술 사용 가이드 찾아보기",
        }
        for url, label in expected.items():
            with self.subTest(url=url):
                self.assertIn('href="'+url+'"',html)
                self.assertIn(label,visible_text(html))
        self.assertNotIn("https://",html)
        self.assertNotIn("<script",html)
        self.assertNotIn('method="post"',html.lower())

    def test_03_clear_available_pending_and_not_available_truth(self):
        text=visible_text(app._home())
        for sentence in ("지금 가능한 것:", "아직 확인이 필요한 것:",
                         "아직 제공하지 않는 것:",
                         "사용자 프로젝트 파일 자동 검사"):
            self.assertIn(sentence,text)
        self.assertNotIn("고객 출시",text)
        self.assertNotIn("진단 완료",text)
        self.assertNotIn("검증 완료된 수정본",text)

    def test_04_optional_advanced_navigation_and_examples_start_closed(self):
        html=app._home()
        self.assertIn('<details class="technical-details more-functions" '
                      'data-more-functions="true">',html)
        self.assertIn('data-more-examples="true"',html)
        self.assertIn('data-owner-playground="true"',html)
        self.assertNotIn('data-more-examples="true" open',html)
        self.assertIn("<summary>다른 기능과 메뉴도 살펴보기</summary>",html)
        self.assertIn("<summary>Python · PowerShell · Git · MCP 예제 더 보기</summary>",html)

    def test_05_plain_language_status_and_glossary_are_optional(self):
        html=simple.render_first_use()
        text=visible_text(html)
        self.assertIn("<summary>낯선 용어 쉽게 알아보기</summary>",html)
        self.assertNotIn("공개 변경 기록 (PR)",text)
        self.assertIn("공개 변경 기록 (PR)",html)
        self.assertIn("기술 사용 가이드 (SkillBook)",html)
        self.assertIn("검토 전 자료",html)

    def test_06_public_candidate_cards_hide_codes_and_show_useful_language(self):
        report=public_rows()
        html=app._evidence_rows(report,guidance=True,query="Python")
        text=visible_text(html)
        self.assertIn("Python 폴더 목록을 함께 사용할 때 주의할 점",text)
        self.assertIn("무엇을 얻나요?",text)
        self.assertIn("검토 전",text)
        self.assertNotIn("PY_SCANDIR_SHARED_ITERATOR_RACE",text)
        self.assertIn("PY_SCANDIR_SHARED_ITERATOR_RACE",html)
        self.assertIn("UNVERIFIED_CANDIDATE_ONLY",html)

    def test_07_unknown_public_pattern_never_fabricates_a_cure(self):
        self.assertEqual(simple.human_pattern("API_CONTRACT"),
                         "프로그램 입력값과 사용 규칙 확인")
        self.assertEqual(simple.human_pattern("SOMETHING_NEW"),
                         "검토 중인 공개 기술 사례")
        self.assertEqual(simple.human_pattern(None),
                         "검토 중인 공개 기술 사례")
        report=public_rows()
        report["items"][0]["purpose_code"]="SOMETHING_NEW"
        html=app._evidence_rows(report,query="API")
        self.assertIn("검토 중인 공개 기술 사례",visible_text(html))
        self.assertIn("SOMETHING_NEW",html)

    def test_08_review_starts_with_a_purpose_and_collapses_developer_details(self):
        with patch.object(app,"_search",return_value=public_rows()):
            html=app._review(Path("UCIE"),
                             "q=scandir&page=1&id="+"a"*64+"&from=library")
        text=visible_text(html)
        self.assertIn("이 자료를 통해 알 수 있는 것",text)
        self.assertIn("원본 공개 기록 열어보기",text)
        self.assertIn("안전한 예제 실행해 보기",text)
        self.assertIn("<summary>개발자용 수정 방향과 시험 계획 보기</summary>",html)
        self.assertNotIn("Never concurrently share a raw scandir iterator",text)
        self.assertIn("Never concurrently share a raw scandir iterator",html)
        self.assertIn("실제 회귀시험: NOT_EXECUTED",html)
        self.assertIn("NOT_VERIFIED",html)

    def test_09_untrusted_start_destination_rejected_not_substituted(self):
        real=simple.START_TASKS
        forged=(real[0][:4]+("https://other.example/private",real[0][5]),)+real[1:]
        with patch.object(simple,"START_TASKS",forged):
            with self.assertRaises(simple.FirstUseError):
                simple.render_first_use()

    def test_10_existing_v04_dark_theme_and_a11y_responsive_floor(self):
        css=design.STYLE
        for token in (".start-task-grid","@media(max-width:900px)",
                      "@media(max-width:580px)","start-task-link:focus-visible",
                      "prefers-reduced-motion:reduce","grid-template-columns:1fr"):
            self.assertIn(token,css)
        self.assertNotIn("@import",css)
        self.assertNotIn("url(http",css)
        self.assertNotIn("<script",css)
        html=app._home()
        self.assertIn('aria-labelledby="first-use-title"',html)
        self.assertIn('aria-label="하고 싶은 일 선택"',html)
        self.assertIn('href="#workspace"',html)

    def test_11_live_localhost_first_choice_and_engine_clickable_no_post(self):
        with TemporaryDirectory(prefix="UCIE_FIRST_USE_") as temp:
            root=Path(temp)/"UCIE"
            (root/".git").mkdir(parents=True)
            with HTTPServer(("127.0.0.1",0),app.make_handler(root)) as server:
                thread=Thread(target=server.serve_forever,daemon=True)
                thread.start()
                try:
                    def request(route,method="GET",host=None):
                        with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=8)) as conn:
                            conn.request(method,route,headers={
                                "Host":host or "127.0.0.1:"+str(server.server_port)})
                            response=conn.getresponse()
                            return response.status,response.read().decode("utf-8","replace"),dict(response.getheaders())
                    code,page,headers=request("/local")
                    self.assertEqual(code,200)
                    self.assertIn('data-first-use="v01"',page)
                    self.assertIn("default-src 'none'",headers["Content-Security-Policy"])
                    code,body,_=request("/local/engine?purpose=SKILL_TEST_AUTOMATION")
                    self.assertEqual(code,200)
                    self.assertIn('data-owner-workload="true"',body)
                    self.assertEqual(request("/local","POST")[0],405)
                    self.assertEqual(request("/local",host="external.example")[0],403)
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())


if __name__=="__main__":
    unittest.main()
