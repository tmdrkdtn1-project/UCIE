"""UCIE owner-local home: usable links into ALL FOUR already implemented pillars.

This is not a separate dashboard, customer entitlement, install flow, or
synthetic substitute for real published evidence. It creates links into the
existing real owner Local V1 app; fixed synthetic engine outcomes are always
marked as synthetic, not as a user's code result. No input, files or network.
"""
from __future__ import annotations

from html import escape
from urllib.parse import quote

from .local_v1_priority_v01 import require_local_work
from .local_error_actionable_workflow_v01 import (
    CASE_IDS, SCHEMA as TRIAGE_SCHEMA, STATUS as TRIAGE_STATUS, get_case,
)
from .local_b2_connected_workbench_v01 import (
    PURPOSE, SCHEMA as B2_SCHEMA, STATUS as B2_STATUS,
    evaluate_case,
)

SCHEMA = "UCIE_OWNER_LOCAL_FOUR_PILLAR_PLAY_FIRST_V01"
STATUS = "LOCAL_OWNER_FOUR_CONNECTED_PATHS_READONLY_NO_CUSTOMER_RELEASE"
OWNER_CASES = (
    "python-env", "powershell-command", "git-repository", "mcp-prompts",
)
FORBIDDEN_FLAGS = (
    "actual_user_environment_inspected", "third_party_code_executed",
    "arbitrary_command_or_path_accepted", "independent_fix_validated",
    "human_review_approved", "rule_or_skillbook_promoted",
    "customer_distribution_authorized",
)


class OwnerPlayError(ValueError):
    """Never turn a future unreviewed scenario into owner approval."""


def owner_journeys() -> dict:
    """All four genuine existing routes for each pinned UCIE-authored case."""
    require_local_work("LOCAL_APP")
    if tuple(CASE_IDS) != OWNER_CASES:
        raise OwnerPlayError("reviewed owner local four-case contract changed")
    cases = []
    for case_id in OWNER_CASES:
        triage = get_case(case_id)
        issue = evaluate_case(case_id, "issue")
        control = evaluate_case(case_id, "control")
        if (triage.get("schema") != TRIAGE_SCHEMA
                or triage.get("status") != TRIAGE_STATUS
                or triage.get("case_id") != case_id
                or triage.get("commands_executed") is not False
                or triage.get("user_logs_or_files_read") is not False
                or triage.get("independent_fix_validated") is not False
                or triage.get("customer_distribution_authorized") is not False
                or triage.get("network_requests") != 0
                or triage.get("operating_database_writes") != 0):
            raise OwnerPlayError("untrusted owner error scenario")
        for item, scenario in ((issue, "issue"), (control, "control")):
            if (item.get("schema") != B2_SCHEMA
                    or item.get("status") != B2_STATUS
                    or item.get("case_id") != case_id
                    or item.get("scenario") != scenario
                    or item.get("fixture_origin") != "UCIE_AUTHORED_FIXED_SYNTHETIC"
                    or item.get("fixture_evaluated") is not True
                    or any(item.get(key) is not False for key in FORBIDDEN_FLAGS)
                    or item.get("network_requests") != 0
                    or item.get("operating_database_writes") != 0):
                raise OwnerPlayError("unreviewed or non-synthetic owner scenario")
        query = issue.get("public_library_query")
        evolution = issue.get("evolution_query")
        if (type(query) is not str or query != triage.get("library_query")
                or type(evolution) is not str or evolution != query
                or control.get("public_library_query") != query
                or control.get("evolution_query") != evolution
                or not 1 <= len(query) <= 32):
            raise OwnerPlayError("four-pillar evidence link drift")
        safe_case = quote(case_id, safe="")
        safe_query = quote(query, safe="")
        cases.append({
            "case_id": case_id,
            "label": triage["label"],
            "issue_result": issue["result_code"],
            "control_result": control["result_code"],
            "limitation": issue["limitation"],
            "error_url": "/local/error?case=" + safe_case,
            "engine_issue_url": ("/local/engine?purpose=" + PURPOSE +
                                 "&case=" + safe_case + "&scenario=issue"),
            "engine_control_url": ("/local/engine?purpose=" + PURPOSE +
                                   "&case=" + safe_case + "&scenario=control"),
            "library_url": "/local/library?q=" + safe_query,
            "evolution_url": "/local/evolution?q=" + safe_query,
        })
    return {
        "schema": SCHEMA, "status": STATUS,
        "owner_local_only": True, "case_count": len(cases),
        "cases": cases,
        "uses_existing_owner_routes": True,
        "actual_user_project_read": False,
        "network_requests": 0, "operating_database_writes": 0,
        "third_party_code_executed": False,
        "independent_user_fix_verified": False,
        "customer_distribution_authorized": False,
    }


def render_owner_play() -> str:
    """Accessible first-party links; no GET side effects or JS required."""
    report = owner_journeys()
    if (report.get("status") != STATUS
            or report.get("case_count") != 4
            or report.get("customer_distribution_authorized") is not False):
        raise OwnerPlayError("owner play access contract invalid")

    def a(href: str, label: str) -> str:
        if (type(href) is not str or not href.startswith("/local/")
                or any(symbol in href for symbol in ('"', "'", "<", ">", "#"))
                or type(label) is not str or not label):
            raise OwnerPlayError("unsafe owner local journey link")
        return ('<a href="' + escape(href, quote=True) + '">' +
                escape(label, quote=True) + '</a>')

    cards = []
    for case in report["cases"]:
        cards.append(
            '<article class="shelf-entry" data-owner-case="' +
            escape(case["case_id"], quote=True) + '">'
            '<h3>' + escape(case["label"], quote=True) + '</h3>'
            '<p>UCIE 자체 합성 오류 결과: <code>' +
            escape(case["issue_result"], quote=True) +
            '</code>. 실제 사용자 환경을 진단한 것이 아닙니다.</p>'
            '<div class="page-controls" aria-label="' +
            escape(case["label"], quote=True) + ' · 4대 기능">'
            + a(case["error_url"], "1. 오류 점검") +
            a(case["engine_issue_url"], "2. 엔진 실행") +
            a(case["library_url"], "3. 도서관 탐색") +
            a(case["evolution_url"], "4. 개선 근거") +
            a(case["engine_control_url"], "대조 시험") +
            '</div></article>'
        )
    return (
        '<section class="section-heading" aria-labelledby="owner-play-title">'
        '<span class="eyebrow">FOUR PILLARS · EXPERIENCE</span>'
        '<h2 id="owner-play-title">내 PC에서 바로 사용해보기</h2>'
        '<p>네 가지 실제 UCIE 화면을 연결해 살펴보세요. '
        '결제·고객 설치·로그 업로드 없이 작동합니다.</p></section>'
        '<section class="workbench-note" data-owner-playground="true" '
        'aria-label="소유자 전용 연결형 기능 체험">'
        + ''.join(cards) +
        '<p class="customer-note">엔진 판정은 UCIE 작성 합성 시험입니다. '
        '도서관·개선 탭은 현재 보유한 공개 기술 근거를 읽으며, '
        '미검증 후보를 승인된 수정 또는 상용 제품으로 표시하지 않습니다.</p>'
        '</section>'
    )
