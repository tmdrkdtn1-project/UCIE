"""Owner-local guided problem resolution: actual supported symptoms, not AI.

No arbitrary user text/code/logs, files, commands, network, SQL writes, POST,
training or release. These tests validate bounded existing first-party steps.
"""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
import unittest

from ucie_miner import local_problem_solver_v01 as solve
from ucie_miner import local_v1_app_v01 as app


class OwnerGuidedProblemSolverTests(unittest.TestCase):
    def test_01_home_primary_problem_action_is_real_local_route(self):
        html=app._home()
        self.assertIn("지금 겪는 문제부터 해결하고 싶어요", html)
        self.assertIn('href="/local/solve"', html)
        self.assertIn("내 문제 해결하기", html)
        self.assertLess(html.index('href="/local/solve"'),
                        html.index('data-first-use="v01"'))

    def test_02_start_has_four_real_distinct_symptom_choices(self):
        html=solve.render_guidance()
        self.assertEqual(html.count('data-problem-case="'),4)
        for case in ("python-env","powershell-command","git-repository","mcp-prompts"):
            with self.subTest(case=case):
                self.assertIn('href="/local/solve?case='+case+'"',html)
        self.assertIn("어떤 문제로 고민하고 있나요?",html)
        self.assertIn("AI가 자유 문장을 분석하는 기능은 아직 제공하지 않습니다",html)

    def test_03_four_selected_problems_have_reason_check_and_official_source(self):
        for name in ("python-env","powershell-command","git-repository","mcp-prompts"):
            with self.subTest(case=name):
                html=app._solve("case="+name)
                self.assertIn('data-problem-result="guided"',html)
                self.assertIn("1. 가능한 원인",html)
                self.assertIn("2. 확인해 볼 방법",html)
                self.assertIn("3. 안전한 다음 단계",html)
                self.assertIn("4. 확인할 공식 근거",html)
                self.assertEqual(html.count('class="problem-check"'),2)
                self.assertIn('data-problem-ai-scope="limited"',html)
                self.assertIn("사용자 PC를 실제 분석한 것은 아닙니다",html)
                self.assertIn("명령은 자동 실행되지 않습니다",html)
                self.assertIn('target="_blank" rel="noopener noreferrer"',html)

    def test_04_python_output_has_safe_specific_next_steps(self):
        html=app._solve("case=python-env")
        self.assertIn("실행 중인 Python과 설치 대상 환경",html)
        self.assertIn("python -m pip list",html)
        self.assertIn("실제로 실행되는 Python 경로",html)
        self.assertIn("https://docs.python.org/3/library/venv.html",html)
        self.assertIn("/local/library?q=Python",html)
        self.assertNotIn("자동 수정되었습니다",html)

    def test_05_no_ai_model_or_uploaded_user_file_misrepresentation(self):
        for case in ("python-env","git-repository"):
            html=solve.render_guidance(case)
            self.assertIn("AI 연결 기능은 아직 제공하지 않습니다",html)
            self.assertIn("비공개 코드·로그·비밀번호",html)
            self.assertNotIn('<input type="file"',html)
            self.assertNotIn('<textarea',html)
            self.assertNotIn("AI가 분석한 결과",html)

    def test_06_prohibits_any_arbitrary_user_input_and_unsanctioned_path(self):
        bad=("case=unknown","case=","case=python-env&path=%2Fprivate",
             "case=python-env&case=git-repository", "q=secret",
             "case=python-env&message=please%20read%20private%20files",
             "case=python-env&token=abc", "case=python-env%3Cscript%3E")
        for query in bad:
            with self.subTest(query=query),self.assertRaises(ValueError):
                app._solve(query)

    def test_07_runtime_has_no_network_or_private_files(self):
        with patch("urllib.request.urlopen",side_effect=AssertionError("network forbidden")):
            with patch("subprocess.run",side_effect=AssertionError("no commands")):
                for case in ("python-env","powershell-command","git-repository","mcp-prompts"):
                    self.assertIn("확인해 볼 방법",solve.render_guidance(case))

    def test_08_source_claim_and_approval_forgeries_fail_closed(self):
        from ucie_miner import local_error_actionable_workflow_v01 as catalog
        original=catalog.get_case
        for prop,value in (
            ("independent_fix_validated",True),
            ("commands_executed",True),
            ("operating_database_writes",1),
            ("official_url","https://unauthorized.invalid/try"),
            ("customer_distribution_authorized",True),
        ):
            with self.subTest(prop=prop):
                forged=original("python-env")
                forged[prop]=value
                with patch.object(solve,"get_case",return_value=forged):
                    with self.assertRaises(solve.ProblemGuidanceError):
                        solve.render_guidance("python-env")

    def test_09_real_loopback_get_and_post_host_boundaries(self):
        with TemporaryDirectory(prefix="UCIE_LOCAL_PROBLEM_GUIDE_") as tmp:
            root=Path(tmp)/"UCIE"
            (root/".git").mkdir(parents=True)
            with HTTPServer(("127.0.0.1",0),app.make_handler(root)) as server:
                thread=Thread(target=server.serve_forever,daemon=True)
                thread.start()
                try:
                    def send(path,method="GET",host=None):
                        with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=6)) as c:
                            c.request(method,path,headers={
                                "Host":host or "127.0.0.1:"+str(server.server_port)})
                            response=c.getresponse()
                            return response.status,response.read().decode("utf-8","replace"),dict(response.getheaders())
                    status,body,headers=send("/local/solve")
                    self.assertEqual(status,200)
                    self.assertIn("어떤 문제로 고민하고 있나요?",body)
                    self.assertIn("default-src 'none'",headers["Content-Security-Policy"])
                    for case in ("python-env","powershell-command","git-repository","mcp-prompts"):
                        with self.subTest(case=case):
                            code,result,_=send("/local/solve?case="+case)
                            self.assertEqual(code,200)
                            self.assertIn('data-problem-result="guided"',result)
                    self.assertEqual(send("/local/solve?case=../../private")[0],400)
                    self.assertEqual(send("/local/solve","POST")[0],405)
                    self.assertEqual(send("/local/solve",host="external.example")[0],403)
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())


if __name__=="__main__":
    unittest.main()
