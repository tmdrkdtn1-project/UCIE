"""UCIE owner-local first-use guidance: actions, limits and plain Korean labels.

This is pure, offline UI. It does not change evidence review, approval, source
selection, engine results, private data, membership or customer distribution.
Existing detailed technical provenance stays accessible behind native <details>.
"""
from __future__ import annotations

from html import escape

from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_LOCAL_FIRST_USE_PLAIN_LANGUAGE_V01"
STATUS = "OWNER_LOCAL_PURPOSE_FIRST_NO_RELEASE_CLAIM"

# These are already implemented, fixed Local V1 GET routes, not new actions.
START_TASKS = (
    (
        "solve",
        "지금 겪는 문제부터 해결하고 싶어요",
        "대표 오류 증상 중 하나를 선택해 원인과 확인 방법을 알아보세요.",
        "내 문제 해결 시작하기",
        "/local/solve",
        "문제 해결 시작",
    ),
    (
        "try",
        "직접 실행해 보고 싶어요",
        "UCIE가 만든 안전한 예제의 숫자를 바꿔 결과를 비교해 보세요.",
        "예제 직접 체험하기",
        "/local/engine?purpose=SKILL_TEST_AUTOMATION",
        "예제 실행",
    ),
    (
        "learn",
        "사용법과 기술 자료를 찾고 싶어요",
        "기존 Git 기술 가이드와 공개 자료를 한곳에서 살펴보세요.",
        "기술 사용 가이드 찾아보기",
        "/local/library?q=Git",
        "가이드·자료 읽기",
    ),
)
FIXED_ROUTES = frozenset(task[4] for task in START_TASKS)
PATTERN_LABELS = {
    "API_CONTRACT": "프로그램 입력값과 사용 규칙 확인",
    "EXCEPTION_HANDLING": "오류가 발생했을 때 안전하게 처리",
    "EXPLICIT_ENCODING": "글자 깨짐을 예방하는 문자 처리",
    "DEPENDENCY_VERSION": "프로그램 버전 호환성 확인",
    "RESOURCE_CLEANUP": "사용한 파일과 자원을 안전하게 정리",
    "PS_SSH_PATH_WITHOUT_RUNSPACE": "PowerShell 원격 연결 경로 확인",
    "PS_FUZZY_GET_COMMAND_DUPLICATES": "PowerShell 명령 검색 중복 확인",
    "PS_RESOLVE_PATH_DOT_PREFIX": "PowerShell 상대 경로와 파일명 확인",
    "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO": "Python 디버그 설정 오타 확인",
    "PY_SCANDIR_SHARED_ITERATOR_RACE": "Python 폴더 목록을 함께 사용할 때 주의할 점",
    "PY_QSBR_THREADSTATE_SLOT_LEAK": "Python 스레드 자원 정리 확인",
    "PY_COMPREHENSION_COMPILER_ERROR_CLEANUP": "Python 문법 오류 후 자원 정리",
    "PY_AST_REPR_FIELDS_LOOKUP": "Python 코드 구조 표시 오류 확인",
    "PY_WEAKREF_FREE_THREADED_RACE": "Python 동시 실행 중 참조 관리 확인",
}


class FirstUseError(ValueError):
    """Reject invented or unsafe first-use action destinations."""


def human_pattern(pattern: object) -> str:
    """Translate known review codes; never invent an approved fix."""
    return (PATTERN_LABELS.get(pattern, "검토 중인 공개 기술 사례")
            if type(pattern) is str else "검토 중인 공개 기술 사례")


def render_first_use() -> str:
    require_local_work("LOCAL_APP")
    if (len(START_TASKS) != 3
            or {t[0] for t in START_TASKS} != {"solve", "try", "learn"}
            or len({t[4] for t in START_TASKS}) != 3):
        raise FirstUseError("reviewed three-action journey contract changed")
    rows = []
    for task in START_TASKS:
        if (type(task) is not tuple or len(task) != 6
                or any(type(x) is not str or not x or len(x) > 145 for x in task)
                or task[4] not in FIXED_ROUTES
                or not task[4].startswith("/local/")
                or any(ch in task[4] for ch in ('"', "'", "<", ">", "#"))):
            raise FirstUseError("unsafe or unreviewed first-use action")
        key, heading, detail, label, href, scope = task
        rows.append(
            '<article class="start-task" data-start-task="' + escape(key, quote=True) +
            '"><span class="start-task-kind">' + escape(scope, quote=True) +
            '</span><h3>' + escape(heading, quote=True) + '</h3>'
            '<p>' + escape(detail, quote=True) + '</p>'
            '<a class="start-task-link" href="' + escape(href, quote=True) + '">' +
            escape(label, quote=True) + ' <span aria-hidden="true">→</span></a>'
            '</article>'
        )
    return (
        '<section class="start-here" data-first-use="v01" '
        'aria-labelledby="first-use-title">'
        '<span class="eyebrow">처음 사용하는 분을 위한 안내</span>'
        '<h2 id="first-use-title">내 PC에서 바로 사용해보기</h2>'
        '<p>무엇을 해야 할지 모르겠다면 아래 세 가지 중 하나를'
        ' 선택하세요. 어려운 설정 없이 바로 둘러볼 수 있습니다.</p>'
        '<div class="start-task-grid" aria-label="하고 싶은 일 선택">' +
        "".join(rows) + '</div>'
        '<div class="start-truth" aria-label="현재 할 수 있는 일과 제한">'
        '<p><strong>지금 가능한 것:</strong> 대표 문제의 확인 방법 안내, '
        '공개 기술 자료 검색, UCIE 자체 예제 실행, 기술 가이드 읽기.</p>'
        '<p><strong>아직 확인이 필요한 것:</strong> 외부 공개 자료의 '
        '실제 수정 효과와 적용 가능한 버전.</p>'
        '<p><strong>아직 제공하지 않는 것:</strong> 자유 문장을 이해하는'
        ' AI 맞춤 답변, 사용자 프로젝트 파일 자동 검사 또는 코드 자동 수정.</p>'
        '</div>'
        '<details class="technical-details" data-plain-glossary="true">'
        '<summary>낯선 용어 쉽게 알아보기</summary>'
        '<dl class="start-glossary">'
        '<div><dt>기술 사용 가이드 (SkillBook)</dt>'
        '<dd>한 가지 기술을 이해하고 예제를 따라 해보는 안내 자료</dd></div>'
        '<div><dt>공개 변경 기록 (PR)</dt>'
        '<dd>다른 개발자가 공개 저장소에 제안한 코드 변경 기록</dd></div>'
        '<div><dt>검토 전 자료</dt>'
        '<dd>출처는 표시되지만 실제 효과와 적용 버전은 확인이 더 필요한 자료</dd></div>'
        '<div><dt>예제 체험</dt>'
        '<dd>UCIE가 자체 제작한 안전한 입력으로 동작을 비교하는 시험</dd></div>'
        '</dl></details></section>'
    )
