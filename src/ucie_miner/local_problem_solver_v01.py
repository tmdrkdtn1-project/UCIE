"""UCIE owner-local bounded problem-solving entry, based on official references.

A real task-driven triage surface for the four currently supported known
symptoms. A selected case produces *possible* causes, human-read-only checks,
safe next actions and their existing approved source references. This is NOT
AI, arbitrary problem text analysis, customer code diagnosis or an automatic fix.

No submitted code, raw logs, free text, files, secrets, network, persistence,
tool execution, cross-project retrieval or author/release approval.
"""
from __future__ import annotations

from html import escape
from urllib.parse import quote

from .local_v1_priority_v01 import require_local_work
from .local_solution_followup_v01 import ANSWERS, render_followup
from .local_error_actionable_workflow_v01 import (
    CASE_IDS, SCHEMA as CASE_SCHEMA, STATUS as CASE_STATUS, get_case,
)

SCHEMA = "UCIE_OWNER_LOCAL_PROBLEM_GUIDANCE_V01"
STATUS = "FIXED_SYMPTOM_OFFICIAL_GUIDANCE_NOT_INDEPENDENT_DIAGNOSIS"

# Public-facing, bounded symptom selections. Do not treat as free-form text.
_SYMPTOMS = (
    ("python-env", "Python 실행", "설치한 모듈을 찾지 못해요",
     "패키지를 설치했는데 실행 시 모듈을 불러오지 못하는 경우"),
    ("powershell-command", "PowerShell", "명령을 찾지 못해요",
     "입력한 명령이 인식되지 않거나 예상한 명령이 실행되지 않는 경우"),
    ("git-repository", "Git", "Git 저장소가 아니라는 오류가 나요",
     "작업 폴더에서 Git 명령을 실행했지만 저장소를 인식하지 못하는 경우"),
    ("mcp-prompts", "MCP 연결", "요청 인수가 잘못됐다는 오류가 나요",
     "prompts/get 호출 후 입력 인수 관련 오류가 나타나는 경우"),
)
_ALLOWED_OFFICIAL = frozenset((
    "https://docs.python.org/3/library/venv.html",
    "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_command_precedence",
    "https://git-scm.com/docs/git-rev-parse",
    "https://github.com/modelcontextprotocol/python-sdk/pull/3696",
))


class ProblemGuidanceError(ValueError):
    """Reject scope drift rather than making a speculative problem diagnosis."""


def _validated_case(case_id: str) -> dict:
    require_local_work("LOCAL_APP")
    if (type(case_id) is not str or case_id not in CASE_IDS
            or len(CASE_IDS) != len(_SYMPTOMS)
            or tuple(item[0] for item in _SYMPTOMS) != CASE_IDS):
        raise ProblemGuidanceError("unreviewed problem type")
    case = get_case(case_id)
    if (case.get("schema") != CASE_SCHEMA
            or case.get("status") != CASE_STATUS
            or case.get("case_id") != case_id
            or case.get("official_url") not in _ALLOWED_OFFICIAL
            or type(case.get("cause")) is not str
            or not case["cause"]
            or type(case.get("safe_next")) is not str
            or not case["safe_next"]
            or type(case.get("checks")) is not tuple
            or len(case["checks"]) != 2
            or any(type(part) is not str or not part or len(part) > 260
                   for check in case["checks"] for part in check)
            or any(case.get(flag) is not False for flag in (
                "commands_executed", "user_logs_or_files_read",
                "independent_fix_validated", "automatic_rule_promotion",
                "customer_distribution_authorized"))
            or case.get("network_requests") != 0
            or case.get("operating_database_writes") != 0):
        raise ProblemGuidanceError("untrusted first-party issue guidance")
    return case


def render_guidance(case_id: str = "", *, check: str = "") -> str:
    """First select a known symptom, then complete a bounded human self-check."""
    require_local_work("LOCAL_APP")
    if (type(case_id) is not str or type(check) is not str
            or (check and (not case_id or check not in ANSWERS))):
        raise ProblemGuidanceError("unregistered symptom or self-check")
    if case_id:
        case = _validated_case(case_id)
        _, domain, symptom, summary = next(
            item for item in _SYMPTOMS if item[0] == case_id)
        checks = []
        for title, command, expected in case["checks"]:
            checks.append(
                '<li class="problem-check"><strong>' +
                escape(title) + '</strong>'
                '<p>확인할 명령 또는 항목</p>'
                '<pre><code>' + escape(command) + '</code></pre>'
                '<p>확인 기준: ' + escape(expected) + '</p></li>'
            )
        library = "/local/library?q=" + quote(case["library_query"], safe="")
        return (
            '<section class="search-panel" data-problem-result="guided">'
            '<p><a href="/local/solve">← 다른 문제 선택</a></p>'
            '<span class="eyebrow">해결 순서 안내 · ' + escape(domain) + '</span>'
            '<h2>' + escape(symptom) + '</h2>'
            '<p>' + escape(summary) + '</p>'
            '<p><strong>확인된 사실:</strong> 선택한 증상 유형을'
            ' UCIE의 공식 문서 기반 점검 안내와 연결했습니다.'
            ' 사용자 PC를 실제 분석한 것은 아닙니다.</p>'
            '</section>'
            '<section class="shelf-entry" data-problem-possible-cause="true">'
            '<h2>1. 가능한 원인</h2><p>' + escape(case["cause"]) + '</p>'
            '<p class="customer-note">가능성에 대한 설명이며'
            ' 개별 환경의 원인을 확정한 것은 아닙니다.</p></section>'
            '<section class="shelf-entry" data-problem-checks="2">'
            '<h2>2. 확인해 볼 방법</h2>'
            '<p>명령은 자동 실행되지 않습니다. 내 작업 환경에 맞는지'
            ' 먼저 확인하고 필요한 경우 직접 실행하세요.</p>'
            '<ol class="review-steps">' + "".join(checks) +
            '</ol></section>'
            '<section class="shelf-entry" data-problem-next="true">'
            '<h2>3. 안전한 다음 단계</h2><p>' +
            escape(case["safe_next"]) + '</p>'
            '<h3>4. 확인할 공식 근거</h3>'
            '<p><a href="' + escape(case["official_url"], quote=True) +
            '" target="_blank" rel="noopener noreferrer">' +
            escape(case["official_title"]) + ' →</a></p>'
            '<p><a href="' + escape(library, quote=True) +
            '">관련 공개 자료 더 찾아보기 →</a></p>'
            '</section>'
            '<section class="workbench-note" data-problem-ai-scope="limited">'
            '<h2>내 문제를 직접 적어 AI에게 물어보려면?</h2>'
            '<p>자유로운 질문을 이해해 맞춤 답을 생성하는 AI 연결 기능은'
            ' 아직 제공하지 않습니다. 이 화면에서는 고른 증상에'
            ' 맞춰 기존 공식 자료의 점검 방법을 안내합니다.</p>'
            '<p>비공개 코드·로그·비밀번호·개인정보는 입력하거나'
            ' 업로드하지 마세요. 현재 화면에는 업로드 기능이 없고,'
            ' 문제 내용을 외부로 보내지 않습니다.</p></section>' +
            render_followup(case_id, check)
        )
    cards = []
    for case_id, domain, symptom, summary in _SYMPTOMS:
        case = _validated_case(case_id)
        if not case.get("official_url") in _ALLOWED_OFFICIAL:
            raise ProblemGuidanceError("missing approved public reference")
        cards.append(
            '<article class="start-task" data-problem-case="' +
            escape(case_id, quote=True) + '">'
            '<span class="start-task-kind">' + escape(domain) + '</span>'
            '<h3>' + escape(symptom) + '</h3>'
            '<p>' + escape(summary) + '</p>'
            '<a class="start-task-link" href="/local/solve?case=' +
            quote(case_id, safe="") + '">확인 방법과 해결 방향 보기 '
            '<span aria-hidden="true">→</span></a></article>'
        )
    return (
        '<section class="start-here" data-problem-entry="v01">'
        '<span class="eyebrow">문제 해결 시작</span>'
        '<h2>어떤 문제로 고민하고 있나요?</h2>'
        '<p>현재 지원하는 문제 유형 중 가장 가까운 것을 선택하면'
        ' 가능한 원인, 확인 방법, 안전한 다음 단계와 공식 근거를 보여줍니다.</p>'
        '<div class="start-task-grid" aria-label="문제 증상 선택">' +
        "".join(cards) + '</div>'
        '<p class="customer-note">현재는 네 가지 대표 상황에 대한'
        ' 안내 기능입니다. 사용자의 코드를 자동 검사하거나'
        ' AI가 자유 문장을 분석하는 기능은 아직 제공하지 않습니다.</p>'
        '</section>'
    )
