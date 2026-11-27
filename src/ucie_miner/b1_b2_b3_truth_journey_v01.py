"""UCIE-only B1/B2/B3 single-case, read-only preview; never a V04 route.

Accepts only an existing pinned first-party SkillBook case and a declared
source revision. Revision declarations are NOT authenticated observations.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json

from .b1_version_truth_gate_v01 import evaluate_b1_source_revision
from .b1_b4_skillbook_capsule_link_v01 import (
    build_b4_capsule_journey, build_pinned_b1_capsules,
)
from .b4_revision_impact_v01 import propose_affected_retests
from .b4_skillbook_draft_v01 import build_b4_skillbook
from .local_first_use_plain_v01 import START_TASKS
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_V2_B1_B2_B3_TRUTH_JOURNEY_V01"


class TruthJourneyError(ValueError):
    pass


def build_truth_journey(case_id: str, source_tag: str | None = None) -> dict:
    """Show the same capsule and source across B1, B2 and B3, without writes."""
    require_local_work("VIRTUAL_LIBRARY")
    verdict = evaluate_b1_source_revision(case_id, source_tag)
    journey = build_b4_capsule_journey(case_id)
    capsules = build_pinned_b1_capsules()
    matches = [cap for cap in capsules if cap["case_id"] == case_id]
    if len(matches) != 1:
        raise TruthJourneyError("CASE_MISSING")
    capsule = matches[0]
    if (journey["case_id"] != verdict["case_id"]
            or journey["capsule_id"] != verdict["capsule_id"]
            or journey["capsule_sha256"] != verdict["capsule_sha256"]
            or capsule["source_document_sha256"] != verdict["source_document_sha256"]
            or journey["source_id"] != verdict["source_id"]):
        raise TruthJourneyError("CASE_CAPSULE_PROOF_DRIFT")
    book = build_b4_skillbook()
    if (book["content_sha256"] != journey["b4_skillbook_sha256"]
            or book["skillbook_id"] != journey["b4_skillbook_id"]):
        raise TruthJourneyError("SKILLBOOK_DRIFT")
    matches = [p for p in book["source_provenance"]
               if p["source_id"] == verdict["source_id"]]
    if (len(matches) != 1
            or matches[0]["sha256"] != verdict["source_document_sha256"]
            or matches[0]["tag"] != verdict["pinned_source_tag"]):
        raise TruthJourneyError("SOURCE_LINEAGE_DRIFT")
    # A mismatched declared tag is only a hypothesis requiring re-review.
    # An unknown requested tag is NOT evidence that upstream changed.
    proposed_tag = (verdict["requested_source_tag"]
                    if verdict["source_revision_decision"] == "SOURCE_REVISION_MISMATCH_HOLD"
                    else verdict["pinned_source_tag"])
    impact = propose_affected_retests([{
        "source_id": verdict["source_id"],
        "expected_sha256": verdict["source_document_sha256"],
        "observed_sha256": verdict["source_document_sha256"],
        "observed_tag": proposed_tag,
        "independently_verified": False,
    }])
    expected_impact = 1 if proposed_tag != verdict["pinned_source_tag"] else 0
    if (impact["retests_proposed"] != expected_impact
            or impact["revision_claims_authenticated"] is not False
            or impact["test_execution"] != "NOT_RUN"):
        raise TruthJourneyError("B3_IMPACT_DRIFT")
    # Reuse the existing three first-use destinations only as disclosed links;
    # they remain the frozen V04-owned routes and are NOT mounted here.
    if (len(START_TASKS) != 3
            or {x[0] for x in START_TASKS} != {"solve", "try", "learn"}
            or any(not x[4].startswith("/local/") for x in START_TASKS)):
        raise TruthJourneyError("FIRST_USE_CONTRACT_DRIFT")
    result = {
        "schema": SCHEMA, "case_id": case_id,
        "capsule_id": verdict["capsule_id"],
        "capsule_sha256": verdict["capsule_sha256"],
        "skillbook_id": journey["b4_skillbook_id"],
        "skillbook_sha256": journey["b4_skillbook_sha256"],
        "source_id": verdict["source_id"],
        "source_document_sha256": verdict["source_document_sha256"],
        "source_tag": verdict["pinned_source_tag"],
        "source_revision_decision": verdict["source_revision_decision"],
        "runtime_version_applicability": "UNKNOWN_NO_PROOF",
        "plain_next_step": verdict["human_next_step"],
        "step_1": "기술 사례 선택",
        "step_2": "확인된 범위와 아직 모르는 점 읽기",
        "step_3": "안전한 다음 확인 방법",
        "b3_retest_proposal_count": impact["retests_proposed"],
        "b3_proposal_sha256": impact["proposal_sha256"],
        "b3_revision_authenticated": False,
        "b3_retest_executed": False,
        "independent_qa": "NOT_VERIFIED",
        "rights_approved": False,
        "export_allowed": False,
        "owner_approved": False,
        "first_use_destinations": {x[0]: x[4] for x in START_TASKS},
        "first_use_routes_modified": False,
        "new_local_route_registered": False,
        "customer_code_executed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "status": "ISOLATED_REVIEW_ONLY",
    }
    digest = sha256(json.dumps(result, ensure_ascii=True, sort_keys=True,
                               allow_nan=False, separators=(",", ":")).encode("ascii")).hexdigest()
    return {**result, "receipt_sha256": digest}


def render_truth_journey(case_id: str, source_tag: str | None = None) -> str:
    """Safe standalone HTML fragment, not a new endpoint or embedded script."""
    result = build_truth_journey(case_id, source_tag)
    show_impact = result["b3_retest_proposal_count"] > 0
    statement = ("제시한 출처 버전이 달라 관련 자료의 재검토를 제안합니다. "
                 "실제 공식 변경은 아직 확인하지 않았습니다."
                 if show_impact else
                 "공식 자료의 변경 여부는 아직 조사하지 않았습니다.")
    e = lambda s: escape(str(s), quote=True)
    return (
        '<section aria-label="UCIE 근거 연결 미리보기" data-ucie-review="true">'
        '<h2>어떤 도움이 필요하세요?</h2>'
        '<p>이미 준비된 기술 사례 한 개를 확인합니다. 사용 중인 PC나 코드는 검사하지 않습니다.</p>'
        '<ol><li>' + e(result["step_1"]) + '</li>'
        '<li>' + e(result["step_2"]) + '</li>'
        '<li>' + e(result["step_3"]) + '</li></ol>'
        '<h3>지금 확인해 볼 일</h3><p>' + e(result["plain_next_step"]) + '</p>'
        '<p>' + e(statement) + '</p>'
        '<p>이 기술 설명과 예제는 검토 중이며 고객용 배포는 승인되지 않았습니다.</p>'
        '<details><summary>왜 이렇게 안내하나요?</summary>'
        '<dl><dt>근거 연결 식별자</dt><dd>' + e(result["capsule_id"]) + '</dd>'
        '<dt>출처 버전</dt><dd>' + e(result["source_tag"]) + '</dd>'
        '<dt>근거 SHA-256</dt><dd>' + e(result["source_document_sha256"]) + '</dd>'
        '<dt>SkillBook</dt><dd>' + e(result["skillbook_id"]) + '</dd>'
        '<dt>검증 범위</dt><dd>실제 환경 동작·독립 시험·사용권 미확인</dd>'
        '</dl></details></section>'
    )
