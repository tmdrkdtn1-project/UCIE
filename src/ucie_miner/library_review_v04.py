"""UCIE V0.4: read-only, source-anchored per-candidate review preparation.

This module does NOT independently reproduce upstream fixes, establish a
released-version range, grant a license, attest a reviewer, approve a rule or
persist a review. It exposes precisely which required proof is still missing
from the existing Stage10/12/15 source-linked review handoff.
"""
from __future__ import annotations

from pathlib import Path
import re

from .automated_candidate_qa import _checked_handoff
from .library_explore import _candidate_rows, describe_purpose
from .public_discovery import SOURCE_SKILL
from .skill_profiles import PROFILE
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_PUBLIC_SOURCE_LINKED_REVIEW_DOSSIER_V04"
READY = "SOURCE_LINKED_REVIEW_PREPARATION_ONLY_NO_GO"
INCOMPLETE = "SOURCE_LINKAGE_INCOMPLETE_NO_GO"
NOT_FOUND = "UNKNOWN_OR_AMBIGUOUS_CANDIDATE_NO_GO"
HEX = re.compile(r"[0-9a-f]{64}\Z")

# Fixed UCIE-authored review requirements, NEVER upstream PR instructions.
REQUIREMENTS = (
    ("SOURCE_PROVENANCE", "공개 출처·개정·해시 연결",
     "원장 출처·개정·SHA 연결만 확인. 수정 효과를 증명하지 않습니다."),
    ("VERSION_APPLICABILITY", "적용 버전",
     "공식 릴리스와 해당 패치 포함 여부를 대조하고 버전 범위를 재현 시험하세요."),
    ("LICENSE", "라이선스·재배포 권한",
     "원본의 정확한 라이선스와 수정본의 재사용 조건을 법적 검토로 확인하세요."),
    ("INDEPENDENT_REGRESSION", "독립 회귀시험",
     "후보별 독립 재현과 수정 전후 회귀시험을 승인된 격리된 테스트 입력으로 확인하세요."),
    ("SECURITY_REVIEW", "보안 영향",
     "외부 코드 실행 없이 보안 영향과 관련 회귀 위험을 별도로 검토하세요."),
    ("OWNER_SIGNOFF", "담당자 승인·배포",
     "명시적인 담당자 검수와 서명·승인 전 자동 적용 및 배포를 금지합니다."),
)
KNOWN_BLOCKERS = {
    "VERIFICATION_NOT_PERFORMED": "후보별 독립 검증 미수행",
    "MULTIPLE_EVIDENCE_REVISIONS_REQUIRE_SELECTION": "복수 근거 개정 중 검토 대상 확정 필요",
    "NO_EXACT_PINNED_RULE_TEMPLATE": "원본에 정확히 결속된 규칙 템플릿 부재",
}


class ReviewDossierError(ValueError):
    pass


def _id(item_id: object) -> str:
    if type(item_id) is not str or HEX.fullmatch(item_id) is None:
        raise ReviewDossierError("exact public candidate SHA-256 ID required")
    return item_id


def dossier_from_linked_handoff(handoff: object, *, item_id: str) -> dict:
    """Read metadata only after current W04 source/revision/fingerprint checks."""
    _id(item_id)
    complete, tasks = _checked_handoff(handoff)
    empty = {
        "schema": SCHEMA, "status": INCOMPLETE, "item": None,
        "requirements": [], "blocking_reasons": [],
        "source_linkage_checked": False,
        "independently_verified": False,
        "owner_approved": False, "auto_promoted": False,
        "production_approved": False, "export_allowed": False,
        "operating_database_writes": 0, "network_requests": 0,
        "scheduler_changes": 0,
    }
    if not complete:
        return empty
    again, rows = _candidate_rows(handoff)
    if not again:
        return empty
    found = [row for row in rows if row["library_item_id"] == item_id]
    if len(found) != 1:
        return dict(empty, status=NOT_FOUND)
    row = found[0]
    hashes = row["review_candidate_sha256s"]
    if (type(hashes) is not list or not hashes
            or any(type(x) is not str or HEX.fullmatch(x) is None for x in hashes)
            or len(set(hashes)) != len(hashes)):
        raise ReviewDossierError("invalid grouped candidate revisions")
    matched = [task for task in tasks if task["candidate_id_sha256"] in hashes]
    if len(matched) != len(hashes) or set(
            task["candidate_id_sha256"] for task in matched) != set(hashes):
        raise ReviewDossierError("review rows do not match source-linked revisions")
    blockers = set()
    for task in matched:
        reasons = task["blocking_reasons"]
        if type(reasons) is not list or any(type(x) is not str for x in reasons):
            raise ReviewDossierError("malformed verification blockers")
        blockers.update(reasons)
    # Unknown future blockers are conservatively labeled, never echoed.
    reasons = [KNOWN_BLOCKERS[x] for x in sorted(blockers) if x in KNOWN_BLOCKERS]
    if blockers - KNOWN_BLOCKERS.keys():
        reasons.append("추가 검증 사유가 존재하며 개별 검토가 필요합니다")
    repo = row["source_id"].removeprefix("repo:")
    profile = PROFILE.get(SOURCE_SKILL.get(repo))
    if profile is None or profile["domain"] != row["domain"]:
        raise ReviewDossierError("public source skill profile mismatch")
    if (row["human_approved"] is not False or row["export_allowed"] is not False
            or row["lifecycle"] != "UNVERIFIED_CANDIDATE_ONLY"):
        raise ReviewDossierError("unapproved candidate falsely marked approved")
    label, description = describe_purpose(row["purpose_code"])
    requirements = []
    for code, name, instruction in REQUIREMENTS:
        requirements.append({
            "gate": code, "label": name,
            "status": ("SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED"
                       if code == "SOURCE_PROVENANCE" else "NOT_VERIFIED"),
            "next_action": instruction,
        })
    return dict(
        empty,
        status=READY, source_linkage_checked=True,
        item={
            "library_item_id": row["library_item_id"],
            "source_id": row["source_id"],
            "domain": row["domain"],
            "kind": row["kind"],
            "purpose_code": row["purpose_code"],
            "purpose_label": label,
            "purpose_description": description,
            "public_url": row["public_url"],
            "revision_hint": row["revision_hint"],
            "evidence_sha256": row["evidence_sha256"],
            "evidence_revision_count": row["evidence_revision_count"],
            "evidence_revision_sha256s": list(row["evidence_revision_sha256s"]),
            "version_scope": "UNDETERMINED",
            "license_status": row["license_status"],
            "review_question": profile["review_question"],
            "next_review_action": profile["recommended_action"],
            "safe_review_guidance": profile["safe_call"],
            "status": "UNVERIFIED_CANDIDATE_ONLY",
        },
        requirements=requirements, blocking_reasons=reasons,
    )


def dossier_existing_public_candidate(root: Path, *, item_id: str) -> dict:
    _id(item_id)
    root = Path(root)
    if root.is_symlink() or root.name.casefold() != "ucie" or not root.is_dir():
        raise ReviewDossierError("dedicated UCIE-only checkout required")
    return dossier_from_linked_handoff(
        prepare_verification_handoff(root), item_id=item_id)
