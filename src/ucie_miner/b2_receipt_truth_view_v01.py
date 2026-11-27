"""B2 truthful presentation of an optional B1 first-party synthetic receipt.

This never runs a test on page rendering, never registers HTTP endpoints, and
never claims SDK, customer runtime, upstream provenance or distribution proof.
"""
from __future__ import annotations

from html import escape

from .b1_b2_b3_truth_journey_v01 import build_truth_journey
from .b1_first_party_receipt_link_v01 import (
    FirstPartyReceiptError, render_receipt_guidance,
)

SCHEMA = "UCIE_V2_B2_RECEIPT_TRUTH_VIEW_V01"


class ReceiptTruthViewError(ValueError):
    pass


def render_b2_receipt_truth_view(case_id: str, *,
                                 source_tag: str | None = None,
                                 receipt: dict | None = None) -> str:
    """Build one bounded view with separate observed and unobserved axes.

    Receipt is an explicitly supplied existing result, not generated here.
    A mismatched declared revision remains HOLD even with a valid synthetic
    receipt; a 'passed example' does not mean an approved customer fix.
    """
    journey = build_truth_journey(case_id, source_tag)
    e = lambda v: escape(str(v), quote=True)
    if receipt is not None:
        if type(receipt) is not dict:
            raise ReceiptTruthViewError("INVALID_RECEIPT")
        if (receipt.get("case_id") != journey["case_id"]
                or receipt.get("capsule_id") != journey["capsule_id"]
                or receipt.get("capsule_sha256") != journey["capsule_sha256"]
                or receipt.get("source_document_sha256")
                    != journey["source_document_sha256"]
                or receipt.get("source_revision_decision")
                    != journey["source_revision_decision"]):
            raise ReceiptTruthViewError("RECEIPT_CASE_OR_VERSION_MISMATCH")
        try:
            checked = render_receipt_guidance(receipt)
        except FirstPartyReceiptError as exc:
            raise ReceiptTruthViewError("RECEIPT_NOT_VERIFIED_FOR_DISPLAY") from exc
    else:
        checked = (
            '<section aria-label="자체 시험 상태"><h3>UCIE 예제 시험</h3>'
            '<p>이 화면에서는 아직 자체 시험 기록이 연결되지 않았습니다.</p>'
            '</section>'
        )
    if journey["b3_retest_proposal_count"]:
        revision = ("제시된 출처 버전이 달라 재확인을 제안합니다. "
                    "실제 공식 변경은 확인하지 않았습니다.")
    else:
        revision = "공식 자료 변경 여부는 현재 확인하지 않았습니다."
    body = (
        '<section data-ucie-b2-receipt-truth="review-only" '
        'aria-label="검증 범위 읽기 전용 안내">'
        '<h2>지금 확인된 내용과 아직 모르는 내용</h2>'
        '<ol><li>준비된 기술 사례 선택</li>'
        '<li>예제에서 확인한 내용과 한계 읽기</li>'
        '<li>안전한 다음 확인 단계 선택</li></ol>'
        '<p>' + e(journey["plain_next_step"]) + '</p>'
        '<p>' + e(revision) + '</p>'
        + checked +
        '<section aria-label="검증 및 사용 허가 상태">'
        '<h3>아직 확인되지 않은 내용</h3>'
        '<p>현재 사용 중인 프로그램 버전에서 작동하는지는 미확인입니다.</p>'
        '<p>독립적인 품질 검증은 미완료입니다.</p>'
        '<p>고객용 배포와 사용권 승인은 완료되지 않았습니다.</p>'
        '</section>'
        '<details><summary>왜 이렇게 안내하나요?</summary>'
        '<p>사례: ' + e(journey["case_id"]) + '</p>'
        '<p>근거 Capsule: ' + e(journey["capsule_id"]) + '</p>'
        '<p>출처 SHA-256: ' + e(journey["source_document_sha256"]) + '</p>'
        '<p>SkillBook: ' + e(journey["skillbook_id"]) + '</p>'
        '<p>개정 제안 식별 SHA-256: ' + e(journey["b3_proposal_sha256"]) + '</p>'
        '</details></section>'
    )
    if any(x in body.lower() for x in ("<form", "onclick=", "fetch(", "type=\"file\"")):
        raise ReceiptTruthViewError("UNSAFE_PAGE_CONTENT")
    return body
