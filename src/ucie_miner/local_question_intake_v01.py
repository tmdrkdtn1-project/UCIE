"""UCIE owner-local question intake: brief in-memory non-AI triage.

A loopback-only short description can match four fixed official-source UCIE
guides. No submitted text is displayed, logged, saved, used as a search,
transmitted to AI, executed or promoted. Not independent customer diagnosis.
"""
from __future__ import annotations
import re
from urllib.parse import parse_qs
from .local_v1_priority_v01 import require_local_work
from .local_problem_solver_v01 import render_guidance

SCHEMA = "UCIE_OWNER_LOCAL_TEXT_QUESTION_PREVIEW_V01"
STATUS = "BOUNDED_TEXT_CLASSIFICATION_NOT_AI_NOT_CUSTOMER_DIAGNOSIS"
MAX_BODY_BYTES = 1400
MIN_CHARS, MAX_CHARS = 12, 360
_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.ASCII)
_URL = re.compile(r"(?:https?://|www\.)", re.I)
_WIN_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|\\\\)", re.ASCII)
_UNIX_PATH = re.compile(r"(?:^|[\s\"'])(?:/(?:home|Users|etc|var|mnt|private|root|opt|srv)/)", re.I)
_PHONE = re.compile(r"(?<!\d)(?:01[016789][- ]?\d{3,4}[- ]?\d{4}|\+?\d{1,3}[- ]?\d{2,4}[- ]?\d{3,4}[- ]?\d{4})(?!\d)")
_CREDENTIAL = re.compile(
    r"(?:\b(?:api[_-]?key|bearer|authorization|password|passwd|secret|token|"
    r"private[_-]?key|ssh-rsa)\b|비밀번호|인증\s*토큰|개인\s*키|접속\s*키)", re.I)
_CODE = re.compile(
    r"(?:\x00|\x60{3}|<[/!]?[A-Za-z][^>]*>|(?:^|\n)\s*(?:import\s+\w+|"
    r"from\s+\w+\s+import|def\s+\w+\s*\(|class\s+\w+\s*[:(]|"
    r"function\s+\w+\s*\(|(?:\$|PS>)\s+)|[{};])", re.I)
_CASES = frozenset(("python-env", "powershell-command", "git-repository", "mcp-prompts"))

class QuestionInputError(ValueError):
    """Never attach submitted text or sensitive excerpts to errors."""


def _privacy_gate(value: str) -> str:
    if (type(value) is not str
            or not MIN_CHARS <= len(value.strip()) <= MAX_CHARS
            or len(value.splitlines()) > 3
            or any(ord(ch) < 32 and ch not in "\n\r\t" for ch in value)
            or any(ord(ch) in (127, 0x2028, 0x2029) for ch in value)
            or _EMAIL.search(value) or _URL.search(value)
            or _WIN_PATH.search(value) or _UNIX_PATH.search(value)
            or _PHONE.search(value) or _CREDENTIAL.search(value)
            or _CODE.search(value)):
        raise QuestionInputError("unapproved or potentially sensitive input")
    return " ".join(value.casefold().split())


def parse_bounded_question(body: bytes) -> str:
    """One ASCII-encoded form body containing percent-encoded UTF-8 only."""
    if type(body) is not bytes or not 0 < len(body) <= MAX_BODY_BYTES:
        raise QuestionInputError("invalid bounded form body")
    try:
        fields = parse_qs(body.decode("ascii", errors="strict"),
                          keep_blank_values=True, strict_parsing=True,
                          max_num_fields=1, encoding="utf-8", errors="strict")
    except (ValueError, UnicodeError) as exc:
        raise QuestionInputError("invalid form encoding") from exc
    if set(fields) != {"question"} or len(fields["question"]) != 1:
        raise QuestionInputError("one question field required")
    return _privacy_gate(fields["question"][0])


def _classify(text: str) -> str | None:
    python = (
        ("modulenotfounderror" in text or "no module named" in text
         or "module not found" in text
         or ("모듈" in text and any(x in text for x in ("찾", "없", "인식", "불러"))))
        and any(x in text for x in ("python", "파이썬", "pip", "module"))
    )
    ps = (any(x in text for x in ("powershell", "파워셸", "파워쉘"))
          and any(x in text for x in ("명령", "commandnotfoundexception", "get-command"))
          and any(x in text for x in ("찾", "없", "인식", "notfound")))
    git = (any(x in text for x in ("git", "깃"))
           and any(x in text for x in (
               "not a git repository", "저장소가 아니라",
               "저장소가 아니", "저장소를 찾", "repository not found")))
    mcp = (any(x in text for x in ("mcp", "prompts/get"))
           and any(x in text for x in ("prompts/get", "프롬프트"))
           and any(x in text for x in (
               "-32602", "인수", "arguments", "invalid params", "입력 오류", "매개변수")))
    matches = [case for match, case in (
        (python, "python-env"), (ps, "powershell-command"),
        (git, "git-repository"), (mcp, "mcp-prompts")) if match]
    return matches[0] if len(matches) == 1 else None


def triage_question(body: bytes) -> dict:
    require_local_work("LOCAL_APP")
    normalized = parse_bounded_question(body)
    case = _classify(normalized)
    if case is not None and case not in _CASES:
        raise QuestionInputError("unregistered case")
    return {
        "schema": SCHEMA, "status": STATUS,
        "matched_known_issue": case is not None,
        "predefined_case_id": case,
        "question_retained": False, "question_echoed": False,
        "external_ai_called": False, "independent_customer_fix_verified": False,
        "network_requests": 0, "persistent_writes": 0,
        "customer_distribution_authorized": False,
    }


def render_question_form() -> str:
    require_local_work("LOCAL_APP")
    return (
        '<section class="start-here" data-question-entry="local">'
        '<span class="eyebrow">내 문제 설명하기</span>'
        '<h2>어떤 코딩 문제로 막혀 있나요?</h2>'
        '<p>일반적인 증상을 짧게 적으면, UCIE가 알고 있는 문제 유형과'
        ' 비교해 가능한 원인과 확인 방법을 안내합니다.</p>'
        '<form action="/local/ask" method="post" autocomplete="off">'
        '<label for="owner-question">문제 설명 (12~360자)</label>'
        '<textarea id="owner-question" name="question" minlength="12"'
        ' maxlength="360" rows="4" required'
        ' placeholder="예: Python에서 패키지를 설치했는데'
        ' ModuleNotFoundError가 발생합니다."></textarea>'
        '<button type="submit">확인 방법 찾아보기 →</button></form>'
        '<p class="customer-note"><strong>주의:</strong> 비공개 코드·로그·'
        '파일 경로·이메일·비밀번호·토큰·개인정보는 입력하지 마세요.'
        ' 작성한 글은 이 PC에서만 임시 처리하고 저장하거나'
        ' 외부 AI로 보내지 않습니다.</p>'
        '<p class="customer-note">현재는 AI 모델이 아니라 네 가지'
        ' 알려진 문제를 구분하는 초기 기능입니다.'
        ' 일치하지 않는 문제는 추측해서 답하지 않습니다.</p>'
        '<p><a href="/local/solve">대표 문제에서 직접 선택하기 →</a></p>'
        '</section>'
    )


def render_question_result(receipt: dict) -> str:
    require_local_work("LOCAL_APP")
    if (type(receipt) is not dict or receipt.get("schema") != SCHEMA
            or receipt.get("status") != STATUS
            or receipt.get("question_retained") is not False
            or receipt.get("question_echoed") is not False
            or receipt.get("external_ai_called") is not False
            or receipt.get("independent_customer_fix_verified") is not False
            or receipt.get("customer_distribution_authorized") is not False
            or receipt.get("persistent_writes") != 0
            or receipt.get("network_requests") != 0
            or receipt.get("matched_known_issue") is not
            (receipt.get("predefined_case_id") in _CASES)):
        raise QuestionInputError("untrusted question result")
    case = receipt["predefined_case_id"]
    if case is None:
        return (
            '<section class="search-panel" data-question-result="unmatched">'
            '<h2>이 질문에 대한 확인된 안내를 찾지 못했습니다</h2>'
            '<p>현재 UCIE는 네 가지 대표 상황만 안전하게 구분합니다.'
            ' 맞지 않는 문제에 답을 지어내지 않겠습니다.</p>'
            '<p><a href="/local/solve">지원하는 문제 유형 보기 →</a></p>'
            '<p><a href="/local/ask">다른 질문 입력하기 →</a></p>'
            '<p class="customer-note">작성한 내용은 결과 화면에 표시하거나'
            ' 저장하지 않습니다. AI 분석 기능은 아직 구현되지 않았습니다.'
            '</p></section>'
        )
    return (
        '<section class="search-panel" data-question-result="known">'
        '<h2>비슷한 공개 기술 문제를 찾았습니다</h2>'
        '<p>질문의 일부 표현이 기존 UCIE 문제 유형과'
        ' 일치했습니다. <strong>실제 PC나 코드의 원인을'
        ' 확인한 것은 아닙니다.</strong></p>'
        '<p><a href="/local/ask">다른 질문 입력하기 →</a></p>'
        '</section>' + render_guidance(case)
    )
