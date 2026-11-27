"""UCIE original B4 revision addendum composed from bounded B1/B3/B4 proof.

No copy of upstream code, no customer data, no release; validated same-case
joins plus explicit source-authenticity and non-impact limitations.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .b1_b4_skillbook_capsule_link_v01 import build_b4_capsule_journey
from .b3_documented_scandir_315_delta_v01 import (
    PYTHON_CASE, evaluate_documented_scandir_delta,
)
from .b3_first_party_callsite_audit_v01 import audit_trusted_scandir_recipe
from .b4_skillbook_draft_v01 import build_b4_skillbook

SCHEMA = "UCIE_B4_PYTHON315_SCANDIR_REVISION_ADDENDUM_V01"


class RevisionAddendumError(ValueError):
    pass


def build_python315_revision_addendum() -> dict:
    """Compose a machine-readable original safety note with strict join gates."""
    joined = build_b4_capsule_journey(PYTHON_CASE)
    book = build_b4_skillbook()
    delta = evaluate_documented_scandir_delta(
        PYTHON_CASE, proposed_runtime="3.15", uses_negative_one=None)
    audit = audit_trusted_scandir_recipe()
    if (
        joined["case_id"] != delta["case_id"]
        or joined["case_id"] != audit["case_id"]
        or joined["capsule_id"] != delta["capsule_id"]
        or joined["capsule_id"] != audit["capsule_id"]
        or joined["capsule_sha256"] != delta["capsule_sha256"]
        or joined["b4_skillbook_id"] != book["skillbook_id"]
        or joined["b4_skillbook_sha256"] != book["content_sha256"]
        or audit["actual_runtime_compatibility"] != "NOT_VERIFIED"
        or delta["official_revision_commit_verified"] is not False
        or delta["documentation_content_sha256_attested"] is not False
        or delta["retest_executed"] is not False
        or book["released"] is not False
    ):
        raise RevisionAddendumError("B1_B3_B4_PROOF_DRIFT")
    if not audit["explicit_directory_argument"]:
        local_verdict = "UNKNOWN_HOLD"
    else:
        local_verdict = "NO_DIRECT_NEGATIVE_FD_PATTERN_IN_AUDITED_FUNCTION"
    result = {
        "schema": SCHEMA,
        "status": "REVIEW_ONLY_NO_RELEASE",
        "case_id": PYTHON_CASE,
        "capsule_id": joined["capsule_id"],
        "capsule_sha256": joined["capsule_sha256"],
        "skillbook_id": book["skillbook_id"],
        "skillbook_sha256": book["content_sha256"],
        "official_api_reference_before": delta["older_official_document"],
        "official_api_reference_after": delta["newer_official_document"],
        "official_change_note": delta["documented_change"],
        "documentation_sha_attested": False,
        "official_change_commit_authenticated": False,
        "audited_first_party_function": audit["function_name"],
        "first_party_function_source_sha256": audit["source_sha256"],
        "static_audit_receipt_sha256": audit["receipt_sha256"],
        "static_local_callsite_verdict": local_verdict,
        "actual_customer_callsite": "UNKNOWN_NOT_INSPECTED",
        "customer_python_version": "UNKNOWN_NOT_INSPECTED",
        "actual_customer_fix": "NOT_PERFORMED",
        "human_explanation": (
            "Python 3.15 문서에는 os.scandir(-1)의 변경이 기재되어 있습니다. "
            "UCIE 예제의 직접 호출은 승인된 절대 경로 변수로 나타나지만, "
            "사용자 코드와 다른 호출 경로는 확인하지 않았습니다."
        ),
        "machine_check": {
            "gate": "OS_SCANDIR_NEGATIVE_FILE_DESCRIPTOR",
            "scope": "ONLY_PINNED_UCIE_SCANDIR_FUNCTION",
            "positive_risk_example": "os.scandir(-1)",
            "observed_ucie_call": "os.scandir(directory)" if audit[
                "explicit_directory_argument"] else "UNKNOWN",
            "safe_call_pattern": "explicit_authorized_absolute_directory",
            "decision": local_verdict,
            "executes_external_code": False,
            "automatically_repairs_customer_code": False,
        },
        "allowed_next_action": (
            "For a separately authorized caller: confirm actual os.scandir "
            "arguments and exact Python version before targeted tests."
        ),
        "independent_qa": "NOT_VERIFIED",
        "usage_rights": "NOT_APPROVED",
        "export_allowed": False,
        "owner_approved": False,
        "automatic_promotion": False,
        "operating_database_writes": 0,
        "network_requests_at_runtime": 0,
    }
    result["content_sha256"] = sha256(json.dumps(
        result, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")).encode("ascii")).hexdigest()
    return result


def render_python315_addendum_markdown() -> str:
    """Bounded original explanatory draft; no verbatim upstream article."""
    r = build_python315_revision_addendum()
    return (
        "# UCIE SkillBook B4 — Python 3.15 scandir 변경 검토 노트\n\n"
        "상태: 검토 초안, 배포 미승인, 외부 코드 미실행\n\n"
        "## 문서에서 확인된 변화\n"
        + r["official_change_note"] + "\n"
        + r["official_api_reference_before"] + "\n"
        + r["official_api_reference_after"] + "\n\n"
        "## UCIE 작성 분석\n"
        + r["human_explanation"] + "\n\n"
        "## 근거와 적용 경계\n"
        "Capsule: " + r["capsule_id"] + "\n"
        "SkillBook: " + r["skillbook_id"] + "\n"
        "정적 함수 SHA-256: " + r["first_party_function_source_sha256"] + "\n"
        "문서 원본 바이트 인증: 미완료\n"
        "고객 환경 검증/독립 QA/권리 승인: 미완료\n"
        "안전한 다음 행동: 실제 버전과 호출 인자를 확인한 뒤 필요한 범위만 시험\n"
    )
