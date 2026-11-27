"""UCIE B1 immutable in-memory evidence capsules -> B4 draft, preview only.

Creates capsules from exact first-party pinned SkillBook sources, not from PR
candidate capsules, local troubleshooting cases, private projects or a database.
A content hash is identity/integrity, not upstream authentication.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json

from .skillbook_principle_composer_v01 import compose_bounded_metadata_principle
from .b4_skillbook_draft_v01 import build_b4_skillbook
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_B1_PINNED_SKILLBOOK_EVIDENCE_CAPSULE_V01"
JOURNEY_SCHEMA = "UCIE_B0_B1_B2_B4_SKILLBOOK_JOURNEY_V01"


class CapsuleLinkError(ValueError):
    pass


def _canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def build_pinned_b1_capsules() -> tuple[dict, dict]:
    """Derive content-addressed B1 draft capsules from the exact curated books."""
    require_local_work("VIRTUAL_LIBRARY")
    principle = compose_bounded_metadata_principle()
    if len(principle["sources"]) != 2:
        raise CapsuleLinkError("EXPECTED_TWO_CURATED_PARENTS")
    capsules = []
    for source in principle["sources"]:
        if (source["provenance_status"] != "SOURCE_ID_PINNED_NOT_INDEPENDENT_QA"
                or source["source_approved_for_research_not_redistribution"] is not True
                or source["source_id"] not in ("doc:python/cpython", "doc:git/git")):
            raise CapsuleLinkError("UNVERIFIED_SOURCE_LINEAGE")
        body = {
            "schema": SCHEMA,
            "case_id": source["skillbook_id"],  # existing first-party ID; not a local error case
            "case_kind": "EXISTING_CURATED_SKILLBOOK_CASE_NOT_USER_PROBLEM",
            "parent_principle_id": principle["principle_id"],
            "parent_principle_sha256": principle["content_sha256"],
            "source_id": source["source_id"],
            "source_tag": source["source_tag"],
            "source_document_sha256": source["document_sha256"],
            "official_url": source["public_url"],
            "callable": source["callable"],
            "budget": source["budget"],
            "data_disclosed": source["data_disclosed"],
            "source_provenance_status": source["provenance_status"],
            "upstream_authenticity": "NOT_INDEPENDENTLY_ATTESTED",
            "evidence_stage": "B1_FIRST_PARTY_DERIVED_SOURCE_PINNED_REVIEW_ONLY",
            "independent_qa_verified": False,
            "rights_approved": False, "owner_approved": False,
            "export_allowed": False, "operating_database_writes": 0,
        }
        digest = sha256(_canon(body)).hexdigest()
        capsules.append({**body, "capsule_id": "UCIE-B1-" + digest[:24].upper(),
                         "content_sha256": digest})
    if len({c["capsule_id"] for c in capsules}) != 2:
        raise CapsuleLinkError("DUPLICATE_CAPSULE_ID")
    return tuple(capsules)


def build_b4_capsule_journey(case_id: str) -> dict:
    """Link only actual curated SkillBook case IDs with exactly matching B4 pins."""
    require_local_work("VIRTUAL_LIBRARY")
    if type(case_id) is not str:
        raise CapsuleLinkError("INVALID_CASE")
    capsules = build_pinned_b1_capsules()
    matches = [c for c in capsules if c["case_id"] == case_id]
    if len(matches) != 1:
        raise CapsuleLinkError("CASE_HAS_NO_B1_SOURCE_PIN")
    capsule = matches[0]
    book = build_b4_skillbook()
    parents = [s for s in book["source_provenance"]
               if s["source_id"] == capsule["source_id"]]
    if (len(parents) != 1 or
            parents[0]["tag"] != capsule["source_tag"] or
            parents[0]["sha256"] != capsule["source_document_sha256"] or
            book["parent_principle_sha256"] != capsule["parent_principle_sha256"]):
        raise CapsuleLinkError("B4_SOURCE_OR_VERSION_DRIFT")
    result = {
        "schema": JOURNEY_SCHEMA,
        "case_id": case_id,
        "capsule_id": capsule["capsule_id"],
        "capsule_sha256": capsule["content_sha256"],
        "b4_skillbook_id": book["skillbook_id"],
        "b4_skillbook_sha256": book["content_sha256"],
        "source_id": capsule["source_id"],
        "source_tag": capsule["source_tag"],
        "stage_b0": "EXISTING_PINNED_FIRST_PARTY_SKILLBOOK_CASE",
        "stage_b1": "SOURCE_BOUND_DRAFT_CAPSULE_VERIFIED_AGAINST_B4_PARENT",
        "stage_b2": "OFFLINE_READ_ONLY_THREE_STEP_PREVIEW",
        "stage_b4": "LINKED_REVIEW_ONLY_UNVERIFIED",
        "independent_upstream_attestation": False,
        "independent_qa_verified": False,
        "rights_approved": False, "owner_approved": False,
        "export_allowed": False, "new_local_route_registered": False,
        "operating_database_writes": 0, "network_requests": 0,
    }
    return {**result, "receipt_sha256": sha256(_canon(result)).hexdigest()}


def render_b4_capsule_journey(case_id: str) -> str:
    """Three-step fragment, no route registration or runtime UI modification."""
    result = build_b4_capsule_journey(case_id)
    return (
        '<section class="search-panel" data-b4-capsule-journey="review-only">'
        '<h2>기술 원리 근거 연결 미리보기</h2><ol>'
        '<li>기존 SkillBook 사례: ' + escape(result["case_id"]) + '</li>'
        '<li>근거 Capsule: ' + escape(result["capsule_id"]) + '</li>'
        '<li>B4 원리 SkillBook: ' + escape(result["b4_skillbook_id"]) + '</li>'
        '</ol><p>근거 식별자 연결만 확인됐습니다. 출처의 독립 검증,'
        ' 실제 수정 효과, 배포 승인은 완료되지 않았습니다.</p></section>'
    )
