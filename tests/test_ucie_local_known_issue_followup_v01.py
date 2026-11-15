"""Real UCIE owner-local self-check: selected facts, not inferred private state."""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
from urllib.parse import urlencode
import unittest

from ucie_miner import local_solution_followup_v01 as follow
from ucie_miner import local_problem_solver_v01 as guide
from ucie_miner import local_question_intake_v01 as question
from ucie_miner import local_v1_app_v01 as app


CASES = ("python-env", "powershell-command", "git-repository", "mcp-prompts")
ANSWERS = ("yes", "no", "unsure")


class LocalKnownIssueSelfCheckTests(unittest.TestCase):
    def test_01_known_symptoms_show_one_decision_with_three_safe_choices(self):
        for case in CASES:
            with self.subTest(case=case):
                html=app._solve("case="+case)
                self.assertIn('data-followup-question="'+case+'"',html)
                self.assertIn("한 가지 더 확인해 볼까요?",html)
                self.assertIn('aria-label="확인한 내용 선택"',html)
                for answer in ANSWERS:
                    self.assertIn('/local/solve?case='+case+'&amp;check='+answer,
                                  html)
                self.assertNotIn("data-followup-result=",html)
                self.assertIn("실제 PC를 자동으로 검사한 결과는 아닙니다.",html)

    def test_02_all_twelve_user_selected_outcomes_get_an_actual_next_action(self):
        messages=set()
        for case in CASES:
            for answer in ANSWERS:
                with self.subTest(case=case,answer=answer):
                    html=app._solve("case="+case+"&check="+answer)
                    self.assertIn('data-followup-result="'+answer+'"',html)
                    self.assertIn("가능한 설명:",html)
                    self.assertIn("다음 행동:",html)
                    self.assertIn("원인을 확인했거나 오류를 해결했다는 판정은 아닙니다",html)
                    self.assertIn('aria-current="true"',html)
                    self.assertIn("4. 확인할 공식 근거",html)
                    self.assertNotIn("검증된 해결책",html)
                    self.assertNotIn("사용자 환경 분석 완료",html)
                    messages.add(html[html.index('data-followup-result='):])
        self.assertEqual(len(messages),12)

    def test_03_python_and_git_paths_never_recommend_destructive_command(self):
        yes=guide.render_guidance("python-env",check="yes")
        no=guide.render_guidance("python-env",check="no")
        git=guide.render_guidance("git-repository",check="no")
        self.assertIn("import 이름",yes)
        self.assertIn("실행 중인 Python 경로",no)
        self.assertIn("저장소 밖",git)
        self.assertIn("git init, clean, reset을 해결책처럼 실행하지 마세요",git)
        self.assertIn("https://docs.python.org/3/library/venv.html",yes)
        self.assertIn("https://git-scm.com/docs/git-rev-parse",git)

    def test_04_other_domains_keep_first_party_official_source_and_caution(self):
        ps=guide.render_guidance("powershell-command",check="yes")
        mcp=guide.render_guidance("mcp-prompts",check="no")
        self.assertIn("CommandType과 Source",ps)
        self.assertIn("공식 명령 우선순위",ps)
        self.assertIn("prompts/list",mcp)
        self.assertIn("https://github.com/modelcontextprotocol/python-sdk/pull/3696",mcp)
        self.assertIn("실제 서버에 무조건 재전송하지 마세요",mcp)

    def test_05_unknown_case_answer_blank_duplicates_and_private_keys_rejected(self):
        invalid=(
            "check=yes", "case=", "case=python-env&check=",
            "case=python-env&check=both",
            "case=python-env&check=YES",
            "case=python-env&check=yes&check=no",
            "case=python-env&check=yes&path=C%3A%5CSecret",
            "case=python-env&check=token%3DPRIVATE",
            "case=unknown&check=yes",
            "case=python-env&check=yes&question=private",
        )
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                app._solve(raw)
        with self.assertRaises(follow.FollowupError):
            follow.render_followup("python-env","maybe")
        with self.assertRaises(guide.ProblemGuidanceError):
            guide.render_guidance("",check="yes")

    def test_06_user_question_result_connects_to_self_check_without_echo(self):
        payload=urlencode({
            "question":"Python 패키지 설치 이후 ModuleNotFoundError가 발생합니다."
        }).encode("ascii")
        receipt=question.triage_question(payload)
        self.assertEqual(receipt["predefined_case_id"],"python-env")
        html=question.render_question_result(receipt)
        self.assertIn('data-followup-question="python-env"',html)
        self.assertIn("네, 확인했어요",html)
        self.assertNotIn("Python 패키지 설치 이후 ModuleNotFoundError가 발생합니다.",html)
        self.assertFalse(receipt["question_retained"])

    def test_07_no_external_ai_network_private_file_or_command_execution(self):
        with patch("urllib.request.urlopen",side_effect=AssertionError("network")):
            with patch("subprocess.run",side_effect=AssertionError("execution")):
                for case in CASES:
                    for answer in ANSWERS:
                        self.assertIn("다음 행동:",guide.render_guidance(case,check=answer))
        self.assertFalse(hasattr(follow,"MODEL"))
        self.assertNotIn("<form",follow.render_followup("python-env"))

    def test_08_forged_official_reference_or_fix_flag_still_fails_closed(self):
        from ucie_miner import local_error_actionable_workflow_v01 as catalog
        original=catalog.get_case("git-repository")
        for field,forged in (
            ("independent_fix_validated",True),
            ("customer_distribution_authorized",True),
            ("operating_database_writes",1),
            ("official_url","https://unapproved.example/payload"),
        ):
            with self.subTest(field=field):
                case={**original,field:forged}
                with patch.object(guide,"get_case",return_value=case):
                    with self.assertRaises(guide.ProblemGuidanceError):
                        guide.render_guidance("git-repository",check="yes")

    def test_09_live_loopback_http_all_twelve_followup_urls(self):
        with TemporaryDirectory(prefix="UCIE_LOCAL_SELF_CHECK_") as temp:
            root=Path(temp)/"UCIE"
            (root/".git").mkdir(parents=True)
            with HTTPServer(("127.0.0.1",0),app.make_handler(root)) as server:
                thread=Thread(target=server.serve_forever,daemon=True)
                thread.start()
                try:
                    def send(url,method="GET"):
                        with closing(HTTPConnection(
                                "127.0.0.1",server.server_port,timeout=7)) as conn:
                            conn.request(method,url,headers={
                                "Host":"127.0.0.1:"+str(server.server_port)})
                            reply=conn.getresponse()
                            return reply.status,reply.read().decode("utf-8","replace"),dict(reply.getheaders())
                    for case in CASES:
                        for answer in ANSWERS:
                            with self.subTest(case=case,answer=answer):
                                status,html,headers=send(
                                    "/local/solve?case="+case+"&check="+answer)
                                self.assertEqual(status,200)
                                self.assertIn('data-followup-result="'+answer+'"',html)
                                self.assertEqual(headers["Cache-Control"],"no-store")
                                self.assertIn("default-src 'none'",
                                              headers["Content-Security-Policy"])
                    self.assertEqual(send("/local/solve?check=yes")[0],400)
                    self.assertEqual(send("/local/solve?case=python-env&check=wrong")[0],400)
                    self.assertEqual(send("/local/solve","POST")[0],405)
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())


if __name__=="__main__":
    unittest.main()
