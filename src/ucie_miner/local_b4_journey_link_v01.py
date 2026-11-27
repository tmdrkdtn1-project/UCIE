"""UCIE local B0/B1/B2 to B4 review journey, read-only and fail-closed.

No synthetic B1 capsule IDs. A known local case is never assumed to share
the B4 source just because both mention Python or Git.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .local_error_actionable_workflow_v01 import CASE_IDS, get_case
from .local_v1_priority_v01 import require_local_work
from .b4_skillbook_draft_v01 import build_b4_skillbook

SCHEMA = "UCIE_LOCAL_B0_B1_B2_B4_LINK_REVIEW_V01"


class LocalB4LinkError(ValueError):
    pass


def build_local_b4_journey(case_id: str) -> dict:
    """Return a truthful local case-to-B4 decision without fictitious capsules."""
    require_local_work("VIRTUAL_LIBRARY")
    if type(case_id) is not str or case_id not in CASE_IDS:
        raise LocalB4LinkError("UNKNOWN_CASE_ID")
    case = get_case(case_id)
    if type(case) is not dict or case.get("case_id") != case_id:
        raise LocalB4LinkError("CASE_ID_DRIFT")
    url = case.get("official_url")
    if type(url) is not str or not url.startswith("https://"):
        raise LocalB4LinkError("CASE_SOURCE_NOT_VERIFIED")
    book = build_b4_skillbook()
    # The current B4 source parents describe CPython scandir and Git porcelain,
    # not the local problem-case venv, rev-parse or MCP prompts reference.
    # Neither a shared language label nor a URL domain proves capsule identity.
    result = {
        "schema": SCHEMA,
        "case_id": case_id,
        "case_official_url": url,
        "case_source_status": "EXISTING_LOCAL_OFFICIAL_GUIDANCE_ONLY",
        "b4_skillbook_id": book["skillbook_id"],
        "b4_skillbook_sha256": book["content_sha256"],
        "b4_source_refs": book["source_provenance"],
        "capsule_id": None,
        "capsule_identity_verified": False,
        "case_to_b4_link": "HOLD_NO_VERIFIED_B1_CAPSULE",
        "b4_linked_to_case": False,
        "user_step_1": "KNOWN_CASE_SELECTED",
        "user_step_2": "SOURCE_GUIDANCE_READ_ONLY",
        "user_step_3": "B4_REFERENCE_HOLD_NO_CAPSULE_LINK",
        "can_browse_b4_draft_separately": True,
        "b4_draft_status": book["status"],
        "owner_approved": False,
        "rights_approved": False,
        "export_allowed": False,
        "customer_project_read": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    result["receipt_sha256"] = sha256(json.dumps(
        result, sort_keys=True, ensure_ascii=True,
        separators=(",", ":")).encode("ascii")).hexdigest()
    return result


def render_local_b4_journey(case_id: str) -> str:
    """Render existing four known issue types, no new endpoint or action."""
    from html import escape
    r = build_local_b4_journey(case_id)
    return (
        '<section class="search-panel" data-ucie-b4-journey="review-only">'
        '<h2>기술 사례와 재사용 지식 연결 상태</h2>'
        '<ol><li>기존 문제 유형 선택: ' + escape(r["case_id"]) + '</li>'
        '<li>공식 기술 안내 확인: 기존 읽기 전용 근거</li>'
        '<li>B4 SkillBook 연결: 검증된 Capsule ID가 없어 보류</li></ol>'
        '<p>B4 초안은 별도로 열람할 수 있으나 이 문제에 대한'
        ' 검증된 해결책으로 연결된 것은 아닙니다.</p>'
        '<p>식별되지 않은 Capsule을 임의로 만들거나 고객 파일을'
        ' 조사하지 않습니다.</p></section>'
    )
