"""UCIE owner-local short question intake, private and deterministic (not AI)."""
from __future__ import annotations

from contextlib import closing
from http.client import HTTPConnection
from http.server import HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urlencode
from unittest.mock import patch
import unittest

from ucie_miner import local_question_intake_v01 as q
from ucie_miner import local_v1_app_v01 as app


EXAMPLES = (
    ("Python에서 패키지를 설치했는데 ModuleNotFoundError가 발생합니다.", "python-env"),
    ("PowerShell에서 명령을 입력했는데 명령을 찾을 수 없습니다.", "powershell-command"),
    ("Git 명령을 실행했는데 not a git repository 오류가 납니다.", "git-repository"),
    ("MCP prompts/get 호출에서 인수 오류 -32602가 발생합니다.", "mcp-prompts"),
)


def body(text: str) -> bytes:
    return urlencode({"question": text}).encode("ascii")


class LocalQuestionIntakeTests(unittest.TestCase):
    def test_01_form_says_what_can_be_entered_and_denies_ai_claims(self):
        html = app._ask()
        self.assertIn('action="/local/ask" method="post"', html)
        self.assertIn('name="question"', html)
        self.assertIn("문제 설명 (12~360자)", html)
        self.assertIn("비공개 코드·로그", html)
        self.assertIn("저장하거나", html)
        self.assertIn("외부 AI로 보내지 않습니다", html)
        self.assertIn("AI 모델이 아니라", html)
        self.assertNotIn('type="file"', html)

    def test_02_four_general_text_symptoms_link_approved_existing_guidance(self):
        for question, case in EXAMPLES:
            with self.subTest(case=case):
                receipt = q.triage_question(body(question))
                self.assertEqual(receipt["predefined_case_id"], case)
                self.assertTrue(receipt["matched_known_issue"])
                self.assertFalse(receipt["question_retained"])
                self.assertFalse(receipt["question_echoed"])
                self.assertFalse(receipt["external_ai_called"])
                html = q.render_question_result(receipt)
                self.assertIn('data-question-result="known"', html)
                self.assertIn("1. 가능한 원인", html)
                self.assertIn("4. 확인할 공식 근거", html)
                self.assertNotIn(question, html)

    def test_03_unsupported_or_ambiguous_text_does_not_forge_ai_answer(self):
        for question in (
            "Python 코드를 실행하면 속도가 너무 느린 것 같아요.",
            "Python 모듈을 못 찾고 Git 저장소가 아니라는 오류도 나타납니다.",
            "프로그램 실행 후 그래픽 화면이 멈추는 이유가 궁금합니다.",
        ):
            with self.subTest(question=question):
                receipt = q.triage_question(body(question))
                self.assertIsNone(receipt["predefined_case_id"])
                html = q.render_question_result(receipt)
                self.assertIn('data-question-result="unmatched"', html)
                self.assertIn("답을 지어내지 않겠습니다", html)
                self.assertNotIn(question, html)

    def test_04_sensitive_or_structured_inputs_rejected_without_echo(self):
        private = (
            "Python 오류가 납니다. my.name@example.com 으로 확인해 주세요.",
            r"Python에서 C:\Users\user\private\secrets.txt 에 오류가 납니다.",
            "Python에서 https://private.example.local/files 를 확인해 주세요.",
            "Python ModuleNotFoundError이고 password: hunter2 를 입력했습니다.",
            "Python ModuleNotFoundError import os; print(123)",
            "Python에서 다음 코드가 오류납니다: " + chr(96)*3 + "python",
            "Python 모듈 오류와 제 번호는 010-1234-5678 입니다.",
            "Python 오류의 api_key = abc123 값을 참고해주세요.",
        )
        for value in private:
            with self.subTest(case=private.index(value)):
                with self.assertRaises(q.QuestionInputError) as caught:
                    q.triage_question(body(value))
                self.assertNotIn(value, str(caught.exception))

    def test_05_duplicate_blank_invalid_encoding_and_oversize_denied(self):
        invalid = (
            b"question=", b"other=hello",
            b"question=abc&question=xyz",
            b"question=%FF%FF%FF",
            b"question=%00%00",
            b"question=short",
            b"question=" + b"x" * 2000,
        )
        for data in invalid:
            with self.subTest(length=len(data)), self.assertRaises(q.QuestionInputError):
                q.triage_question(data)

    def test_06_response_receipt_never_accepts_fake_ai_or_approval(self):
        r=q.triage_question(body(EXAMPLES[0][0]))
        for key,value in (
            ("external_ai_called",True),
            ("independent_customer_fix_verified",True),
            ("persistent_writes",1),
            ("question_retained",True),
            ("customer_distribution_authorized",True),
        ):
            with self.subTest(key=key), self.assertRaises(q.QuestionInputError):
                q.render_question_result({**r,key:value})

    def test_07_no_network_or_code_execution_during_analysis(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            with patch("subprocess.run", side_effect=AssertionError("execution")):
                for question,_ in EXAMPLES:
                    result=q.triage_question(body(question))
                    self.assertIn("공식 근거", q.render_question_result(result))

    def test_08_single_loopback_get_post_and_privacy_boundaries(self):
        with TemporaryDirectory(prefix="UCIE_OWNER_QUESTION_") as tmp:
            root=Path(tmp)/"UCIE"
            (root/".git").mkdir(parents=True)
            with HTTPServer(("127.0.0.1",0), app.make_handler(root)) as server:
                thread=Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    origin="http://127.0.0.1:"+str(server.server_port)
                    def send(path, *, method="GET", text=None,
                             headers=None, content=None):
                        payload=body(text) if text is not None else content
                        hdr={"Host":"127.0.0.1:"+str(server.server_port)}
                        if method=="POST":
                            hdr.update({"Origin":origin,
                                        "Content-Type":"application/x-www-form-urlencoded"})
                        if headers:
                            hdr.update(headers)
                        with closing(HTTPConnection("127.0.0.1",server.server_port,timeout=7)) as c:
                            c.request(method,path,body=payload,headers=hdr)
                            response=c.getresponse()
                            return (response.status,
                                    response.read().decode("utf-8","replace"),
                                    dict(response.getheaders()))
                    status,html,hdr=send("/local/ask")
                    self.assertEqual(status,200)
                    self.assertIn('data-question-entry="local"',html)
                    self.assertIn("default-src 'none'",hdr["Content-Security-Policy"])
                    self.assertEqual(hdr["Cache-Control"],"no-store")
                    for question,case in EXAMPLES:
                        with self.subTest(case=case):
                            code,page,headers=send("/local/ask",method="POST",text=question)
                            self.assertEqual(code,200)
                            self.assertIn('data-question-result="known"',page)
                            self.assertNotIn(question,page)
                            self.assertIn("no-store",headers["Cache-Control"])
                    secret="Python ModuleNotFoundError, token=do_not_echo"
                    code,page,_=send("/local/ask",method="POST",text=secret)
                    self.assertEqual(code,422)
                    self.assertIn('data-question-rejected="true"',page)
                    self.assertNotIn("do_not_echo",page)
                    self.assertEqual(send("/local/ask?question=abc")[0],400)
                    self.assertEqual(send("/local/solve",method="POST",text=EXAMPLES[0][0])[0],405)
                    self.assertEqual(send("/local/ask",method="POST",text=EXAMPLES[0][0],
                                          headers={"Origin":"https://evil.example"})[0],403)
                    self.assertEqual(send("/local/ask",method="POST",text=EXAMPLES[0][0],
                                          headers={"Origin":""})[0],403)
                    # Existing GET Host boundary tests cover hostile Host headers.
                    # Some Windows socket guards abort crafted POST Host requests
                    # before a portable HTTP status can be observed.
                    self.assertEqual(send("/local/ask",method="POST",text=EXAMPLES[0][0],
                                          headers={"Content-Type":"application/json"})[0],400)
                    self.assertEqual(send("/local/ask",method="POST",
                                          content=b"question="+b"a"*1401)[0],413)
                finally:
                    server.shutdown()
                    thread.join(timeout=6)
                    self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
