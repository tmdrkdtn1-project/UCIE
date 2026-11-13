"""Actionable, read-only UCIE Local V1 error triage for four approved domains.

Only fixed UCIE-authored text backed by official public technical documentation.
Does not accept logs, credentials, snippets or paths. Does not execute suggested
commands or read files; a displayed diagnosis is never a verified customer fix.
The owner-priority/Local V04 GET-only policy remains the authoritative gate.
"""
from __future__ import annotations

SCHEMA = "UCIE_LOCAL_ERROR_ACTIONABLE_WORKFLOW_V01"
STATUS = "OFFICIAL_DOC_REFERENCED_HUMAN_CHECK_ONLY_NOT_ATTESTED"
CASE_IDS = ("python-env", "powershell-command", "git-repository", "mcp-prompts")

# Source URLs are fixed official docs/allowed upstream only, not user supplied.
_CASES = {
    "python-env": {
        "label": "Python · ModuleNotFoundError",
        "symptom": "ModuleNotFoundError / 설치한 모듈을 찾지 못함",
        "cause": "모듈 자체의 부재뿐 아니라 실행 중인 Python과 설치 대상 환경이 다를 수 있습니다.",
        "checks": (
            ("실행 Python 확인", 'python -c "import sys; print(sys.executable)"',
             "실제로 실행되는 Python 경로가 예상한 가상환경인지 확인"),
            ("현재 Python의 설치 목록만 확인", "python -m pip list",
             "필요한 패키지가 같은 Python 환경에 표시되는지 확인"),
        ),
        "safe_next": "인터프리터가 다르면 올바른 가상환경을 먼저 선택하세요. 원인을 확인하기 전 임의 설치·환경 초기화 금지.",
        "official_url": "https://docs.python.org/3/library/venv.html",
        "official_title": "Python 공식 가상환경 문서",
        "doc_scope": "공식 개념·점검 절차; 개별 환경 원인과 적용 버전은 현장에서 확인 필요",
        "library_query": "Python",
    },
    "powershell-command": {
        "label": "PowerShell · 명령을 찾지 못함",
        "symptom": "CommandNotFoundException / 명령 이름을 인식하지 못함",
        "cause": "명령 오타 외에 세션의 함수·별칭·cmdlet 우선순위와 PATH가 영향을 줄 수 있습니다.",
        "checks": (
            ("명령 이름 확인", "Get-Command -Name Get-Date -All",
             "예시 명령의 실행 후보와 유형 표시; 실제 오류 명령명으로 바꿔 재확인"),
            ("PowerShell 위치 확인", "$PSVersionTable.PSVersion",
             "현재 세션 버전을 확인하고 공식 문서의 해당 버전을 비교"),
        ),
        "safe_next": "명령이 실제로 없는지·가려졌는지 먼저 확인하세요. 무단 스크립트 실행이나 실행 정책 해제는 해결책이 아닙니다.",
        "official_url": "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_command_precedence",
        "official_title": "Microsoft 공식 PowerShell 명령 우선순위",
        "doc_scope": "공식 명령 탐색 설명; 현재 설치 모듈·PATH·권한 문제는 미진단",
        "library_query": "PowerShell",
    },
    "git-repository": {
        "label": "Git · 저장소를 찾지 못함",
        "symptom": "fatal: not a git repository (or any of the parent directories)",
        "cause": "현재 작업 위치가 의도한 Git 저장소의 작업 트리가 아닐 수 있습니다.",
        "checks": (
            ("현재 작업 위치 확인", "git rev-parse --show-toplevel",
             "성공하면 실제 Git 최상위 작업 트리 경로가 반환됨"),
            ("현재 변경 사항 조회", "git status --short",
             "저장소가 맞는 경우에만 기존 변경 여부를 확인; 삭제·reset 금지"),
        ),
        "safe_next": "잘못된 디렉터리라면 의도한 저장소로 이동한 뒤 다시 확인하세요. 무작정 git init/clean/reset 하지 마세요.",
        "official_url": "https://git-scm.com/docs/git-rev-parse",
        "official_title": "Git 공식 rev-parse 매뉴얼",
        "doc_scope": "공식 저장소 위치 점검; 현재 사용자 저장소 접근·상태는 미확인",
        "library_query": "Git",
    },
    "mcp-prompts": {
        "label": "MCP · prompts/get 입력 오류",
        "symptom": "JSON-RPC -32602 / prompts/get 인수 오류와 서버 예외 구분",
        "cause": "필수 인수 누락/타입 불일치와 서버 내부 실행 예외를 동일 원인으로 취급하지 않아야 합니다.",
        "checks": (
            ("호출 계약 확인", "prompts/get",
             "이름·arguments 구조가 서버의 prompts/list 정의와 일치하는지 확인"),
            ("오류 분류", "-32602",
             "입력 인수 오류의 코드인지 우선 판별, 내부 예외는 별도 기록"),
        ),
        "safe_next": "서버나 API에 임의 재전송하지 말고 UCIE 자체 작성된 정적 계약 가이드와 예제부터 검토하세요.",
        "official_url": "https://github.com/modelcontextprotocol/python-sdk/pull/3696",
        "official_title": "승인 범위 MCP Python SDK 공식 변경 PR #3696",
        "doc_scope": "고정 공개 소스의 사례 연결; 실제 배포 버전·개별 서버 수정 여부는 미확인",
        "library_query": "MCP",
    },
}


def get_case(case_id: str) -> dict:
    """Return bounded fresh data for exact fixed identifiers, never raw logs."""
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise ValueError("unregistered UCIE local error triage case")
    entry = _CASES[case_id]
    if (set(entry) != {
            "label", "symptom", "cause", "checks", "safe_next",
            "official_url", "official_title", "doc_scope", "library_query"
        } or type(entry["checks"]) is not tuple
            or len(entry["checks"]) != 2
            or any(len(check) != 3 or any(type(part) is not str or
                        not part or len(part) > 260 for part in check)
                   for check in entry["checks"])):
        raise ValueError("untrusted UCIE authored triage catalog")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "case_id": case_id,
        **{key: tuple(tuple(z for z in row) for row in value)
           if key == "checks" else value
           for key, value in entry.items()},
        "commands_executed": False,
        "user_logs_or_files_read": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "independent_fix_validated": False,
        "automatic_rule_promotion": False,
        "customer_distribution_authorized": False,
    }
