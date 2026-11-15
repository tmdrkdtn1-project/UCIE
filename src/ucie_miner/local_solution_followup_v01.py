"""Owner-local one-question follow-up for four fixed UCIE problem guides.

Only a user's explicit yes/no/not-sure selection is interpreted. This is
not AI inference or observed system state. Selections are URL-safe bounded
non-sensitive labels; nothing is saved, uploaded, executed, learned or sent.
"""
from __future__ import annotations

from html import escape

from .local_v1_priority_v01 import require_local_work
from .local_error_actionable_workflow_v01 import CASE_IDS

SCHEMA = "UCIE_OWNER_LOCAL_FIXED_FOLLOWUP_V01"
STATUS = "FIRST_PARTY_HUMAN_ANSWER_GUIDANCE_NOT_VERIFIED_DIAGNOSIS"
ANSWERS = ("yes", "no", "unsure")
_LABELS = {
    "yes": "네, 확인했어요",
    "no": "아니요, 다릅니다",
    "unsure": "아직 모르겠어요",
}

# Each message describes a *hypothesis*, never a verified root cause.
# The questions relate to checks already present in the fixed official
# reference guide; no extra source or new command is introduced.
_CASES = {
    "python-env": (
        "실행 중인 Python 환경의 패키지 목록에 필요한 패키지가 보이나요?",
        {
            "yes": (
                "패키지가 표시되는데도 불러오지 못한다면",
                "패키지 설치 여부만으로 원인을 확정할 수 없습니다. "
                "실제로 실행한 Python 경로와 import 이름이 패키지 이름과 같은지 확인할 필요가 있습니다.",
                "먼저 기존 가이드의 '실행 Python 확인'과 패키지 목록을 같은 환경에서 비교하세요. "
                "확인 전에는 무작정 재설치하거나 가상환경을 삭제하지 마세요.",
            ),
            "no": (
                "현재 실행 환경에 패키지가 표시되지 않는다면",
                "다른 가상환경에 설치됐거나 아직 설치되지 않았을 가능성이 있습니다. "
                "패키지가 없는 사실만으로 설치 명령을 즉시 실행할 필요는 없습니다.",
                "실행 중인 Python 경로와 의도한 가상환경을 먼저 비교하세요. "
                "맞는 환경을 확인한 후 공식 설치 절차를 검토하세요.",
            ),
            "unsure": (
                "아직 패키지와 실행 환경을 비교하지 않았다면",
                "현재 정보만으로는 설치 위치의 불일치인지 다른 문제인지 구분할 수 없습니다.",
                "위의 두 가지 확인 방법부터 차례로 살펴보세요. "
                "명령을 실행하기 전에 내 환경에 적합한지 확인하세요.",
            ),
        },
    ),
    "powershell-command": (
        "오류가 난 명령을 Get-Command로 조회했을 때 결과가 나오나요?",
        {
            "yes": (
                "명령이 검색되는데 실행이 예상과 다르다면",
                "동일한 이름의 함수·별칭·명령이 다른 순서로 선택될 수 있습니다. "
                "검색되었다는 사실만으로 원하는 명령이 실행된다고 확정할 수 없습니다.",
                "Get-Command의 CommandType과 Source를 확인하고 공식 명령 우선순위 설명과 비교하세요. "
                "실행 정책을 해제하지 마세요.",
            ),
            "no": (
                "명령이 검색되지 않는다면",
                "오타, 모듈 미설치, 버전 차이 또는 경로 설정 등 여러 가능성이 있습니다.",
                "명령 이름과 PowerShell 버전을 먼저 확인하세요. "
                "확인되지 않은 외부 스크립트 설치나 실행은 피하세요.",
            ),
            "unsure": (
                "아직 해당 명령을 조회하지 않았다면",
                "실행 오류가 명령 부재 때문인지 이름 충돌 때문인지 구분할 수 없습니다.",
                "기존 가이드의 Get-Command 예시에서 실제 문제가 난 명령을 안전하게 확인하고, "
                "출력의 명령 유형을 살펴보세요.",
            ),
        },
    ),
    "git-repository": (
        "문제가 난 폴더에서 git rev-parse --show-toplevel이 성공하나요?",
        {
            "yes": (
                "Git 최상위 폴더를 찾는 데 성공했다면",
                "현재 셸에서는 Git 작업 트리를 인식합니다. "
                "원래 오류가 발생한 작업 위치나 실행 환경이 달랐을 가능성이 있습니다.",
                "기존 오류를 낸 작업과 같은 폴더·환경에서 다시 확인하세요. "
                "기존 변경 사항을 지우는 명령은 사용하지 마세요.",
            ),
            "no": (
                "Git 작업 트리를 찾을 수 없다면",
                "현재 폴더가 원래 의도한 저장소 밖일 수 있습니다. "
                "저장소가 손상됐다고 단정할 수는 없습니다.",
                "올바른 저장소 폴더인지 확인한 뒤 이동해 다시 조회하세요. "
                "git init, clean, reset을 해결책처럼 실행하지 마세요.",
            ),
            "unsure": (
                "작업 위치를 아직 확인하지 않았다면",
                "저장소 자체의 문제인지 실행 위치의 문제인지 판단할 수 없습니다.",
                "먼저 기존 가이드의 읽기 전용 Git 최상위 폴더 확인 방법을 사용하세요. "
                "작업 폴더의 내용을 삭제하지 마세요.",
            ),
        },
    ),
    "mcp-prompts": (
        "요청의 이름과 인수가 prompts/list의 정의와 일치하나요?",
        {
            "yes": (
                "요청 구조가 일치한다고 확인했다면",
                "입력 구조 외에도 SDK·서버 버전, 값 타입, 서버 내부 처리 등 다른 요인이 있을 수 있습니다. "
                "실제 오류의 원인은 아직 검증되지 않았습니다.",
                "공식 공개 자료의 요청 계약과 적용 버전부터 비교하세요. "
                "서버 비밀정보나 실제 요청 본문을 UCIE에 붙여 넣지 마세요.",
            ),
            "no": (
                "이름이나 인수가 일치하지 않는다면",
                "요청 계약 불일치가 입력 오류의 한 가지 원인일 수 있습니다.",
                "prompts/list 정의와 요청의 필수 필드·타입을 점검하세요. "
                "실제 서버에 무조건 재전송하지 마세요.",
            ),
            "unsure": (
                "아직 요청 계약을 비교하지 않았다면",
                "입력 계약 위반과 서버 내부 오류를 구분할 수 없습니다.",
                "기존 공식 자료의 프롬프트 목록·인수 설명 및 오류 코드부터 확인하세요. "
                "실제 요청 데이터는 입력하지 마세요.",
            ),
        },
    ),
}


class FollowupError(ValueError):
    """No unreviewed symptoms, answer values or invented conclusions."""


def render_followup(case_id: str, answer: str = "") -> str:
    """Bounded self-check linked only from known UCIE first-party guides."""
    require_local_work("LOCAL_APP")
    if (type(case_id) is not str or case_id not in CASE_IDS
            or set(_CASES) != set(CASE_IDS)
            or type(answer) is not str or answer not in ("", *ANSWERS)):
        raise FollowupError("unknown fixed followup")
    question, choices = _CASES[case_id]
    if (type(question) is not str or not question or len(question) > 140
            or set(choices) != set(ANSWERS)
            or any(type(v) is not tuple or len(v) != 3
                   or any(type(p) is not str or not p or len(p) > 260
                          for p in v) for v in choices.values())):
        raise FollowupError("unreviewed followup content")
    links = []
    for selected in ANSWERS:
        href = "/local/solve?case=" + case_id + "&check=" + selected
        links.append(
            '<a href="' + escape(href, quote=True) + '"' +
            (' aria-current="true"' if selected == answer else '') + '>' +
            escape(_LABELS[selected]) + '</a>'
        )
    intro = (
        '<section class="workbench-note" data-followup-question="' +
        escape(case_id, quote=True) + '" aria-labelledby="self-check-title">'
        '<h2 id="self-check-title">한 가지 더 확인해 볼까요?</h2>'
        '<p>' + escape(question) + '</p>'
        '<div class="page-controls" role="group" aria-label="확인한 내용 선택">' +
        "".join(links) + '</div>'
        '<p class="customer-note">선택은 저장하거나 외부로 보내지 않습니다. '
        '실제 PC를 자동으로 검사한 결과는 아닙니다.</p></section>'
    )
    if not answer:
        return intro
    title, possible, next_step = choices[answer]
    result = (
        '<section class="shelf-entry" data-followup-result="' +
        escape(answer, quote=True) + '" aria-labelledby="followup-result-title">'
        '<h2 id="followup-result-title">선택한 내용에 따른 확인 안내</h2>'
        '<h3>' + escape(title) + '</h3>'
        '<p><strong>가능한 설명:</strong> ' + escape(possible) + '</p>'
        '<p><strong>다음 행동:</strong> ' + escape(next_step) + '</p>'
        '<p class="customer-note">사용자 선택을 바탕으로 한 참고 안내입니다. '
        '원인을 확인했거나 오류를 해결했다는 판정은 아닙니다.</p>'
        '</section>'
    )
    return intro + result
