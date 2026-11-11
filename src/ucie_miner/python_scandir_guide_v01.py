"""UCIE Python os.scandir: first-party, read-only HUMAN+MACHINE guide.

Official documentation is referenced but NOT version-pinned, and the source
licence is NOT attested per revision. This is a draft, not a certified rule,
approved SkillBook, upstream regression, customer deliverable or auto-fix.
Building the guide never runs the synthetic trial or scans caller files.
"""
from __future__ import annotations

from .python_scandir_review_v01 import (
    PURPOSE, SOURCE_ID, SCHEMA as TRIAL_SCHEMA, _source_bound_entry,
)

SCHEMA = "UCIE_PYTHON_SCANDIR_SKILLBOOK_REVIEW_V01"
GUIDE_ID = "UCIE-PYTHON-SCANDIR-REVIEW-004"
STATUS = "FIRST_PARTY_OFFICIAL_REFERENCE_DRAFT_NOT_APPROVED"
DOC_URL = "https://docs.python.org/3/library/os.html"
CHAPTERS = (
    ("오류 위험과 적용 조건",
     "여러 스레드가 동일한 os.scandir 반복자의 next()와 close()를 독립적으로 호출하는 사용 방식은 "
     "순서와 종료 상태를 관리하기 어렵습니다. 여러 작업자가 필요하면 반복자의 소비와 종료를 "
     "하나의 잠금으로 직렬화하거나 단일 소비자로 항목을 수집한 다음 분배하도록 설계합니다.",
     "UCIE_AUTHORED_PRACTICE_NOT_UPSTREAM_FIX_PROOF"),
    ("재현 가능한 제한된 확인",
     "UCIE가 임시 디렉터리에 직접 만든 파일 4개만 사용합니다. GuardedScandir을 두 소비자 "
     "스레드가 공유하되 잠금으로 직렬화하고, 중복·누락·종료 뒤 StopIteration을 확인한 뒤 "
     "별도 순차 결과와 비교합니다. 위험한 원본 race를 의도적으로 실행하지 않습니다.",
     "FIRST_PARTY_DISPOSABLE_SYNTHETIC_ONLY"),
    ("안전한 호출과 부정 예",
     "허용 예는 동일한 GuardedScandir 인스턴스의 next()/close()를 보호하는 단일 잠금과 "
     "with 블록을 사용하는 방식입니다. 피할 예는 동일한 원본 os.scandir 반복자를 두 스레드가 "
     "각자의 잠금 없이 동시에 next()하거나 한쪽에서 close()하는 방식입니다. "
     "부정 예는 설명일 뿐 실행되는 시험 코드가 아닙니다.",
     "UCIE_AUTHORED_REVIEW_GUIDANCE_ONLY"),
    ("재사용 가능한 기계 계약",
     "ucie_miner.python_scandir_review_v01.run_python_scandir_review()는 "
     "사용자 입력이나 디렉터리 경로를 받지 않습니다. UCIE 자체 임시 파일에서만 "
     "두 스레드 합성시험을 실행하며 소스·시험 상태·미검증 게이트를 구조화해 반환합니다. "
     "가이드 페이지와 JSON 조회는 이 함수를 실행하지 않습니다.",
     "FIRST_PARTY_ZERO_USER_INPUT_SYNTHETIC_INTERFACE"),
    ("버전·출처·사용권·승인 한계",
     "공식 Python os 문서의 URL만 승인된 참고 출처이며 문서의 정확한 개정 SHA는 고정되지 "
     "않았습니다. 특정 CPython 릴리스의 race 존재 또는 수정 효과는 독립 재현되지 않았고 "
     "해당 문서 개정의 재배포 사용권도 검증되지 않았습니다. 공개 PR 후보는 다른 종류의 "
     "근거로 취급합니다. 사람 검수·보안·권리·고객 배포 승인 모두 미완료입니다.",
     "SOURCE_REVISION_RIGHTS_INDEPENDENT_QA_RELEASE_NO_GO"),
)


class PythonScandirGuideError(ValueError):
    """A source, review gate or draft contract is not trustworthy."""


def build_readonly_guide() -> dict:
    """Return independent first-party guide data without triggering any trial."""
    source, entry = _source_bound_entry()
    if (SOURCE_ID != "doc:python/cpython"
            or PURPOSE != "SCANDIR_SERIALIZED_ITERATION"
            or source.get("source_id") != SOURCE_ID
            or source.get("source_kind") != "OFFICIAL_PUBLIC_DOCUMENT"
            or source.get("public_url") != DOC_URL
            or source.get("license_verdict") != "NOT_ATTESTED_PER_REVISION"
            or source.get("fetch_authorized_by_this_registry") is not False
            or entry.get("kind") != "TEST_RECIPE"
            or entry.get("source_id") != SOURCE_ID
            or entry.get("purpose_code") != PURPOSE
            or entry.get("revision_hint") != "PUBLIC_DOCUMENT_REVISION_NOT_PINNED"
            or entry.get("version_scope_claim") != "UNDETERMINED"
            or entry.get("approval_status") != "NOT_APPROVED"
            or entry.get("human_approved") is not False
            or entry.get("export_allowed") is not False
            or entry.get("auto_promoted") is not False):
        raise PythonScandirGuideError("unverified official Python reference drift")
    return {
        "schema": SCHEMA,
        "skillbook_id": GUIDE_ID,
        "title": "Python os.scandir 반복자 안전 사용 · 검토용 기술 가이드",
        "status": STATUS,
        "source_evidence": {
            "source_id": SOURCE_ID,
            "kind": "OFFICIAL_PUBLIC_DOCUMENT_REFERENCE",
            "official_url": DOC_URL,
            "document_revision": "PUBLIC_DOCUMENT_REVISION_NOT_PINNED",
            "version_scope": "UNDETERMINED",
            "source_license_status": "NOT_ATTESTED_PER_REVISION",
            "reference_digest_scope": "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES",
            "upstream_race_fix_independently_reproduced": False,
            "public_pr_equivalent_to_document": False,
            "upstream_code_executed": False,
        },
        "chapters": [
            {"heading": heading, "text": text, "claim_scope": scope}
            for heading, text, scope in CHAPTERS
        ],
        "machine_skill_contract": {
            "callable": "ucie_miner.python_scandir_review_v01.run_python_scandir_review",
            "result_schema": TRIAL_SCHEMA,
            "inputs": "NO_USER_FILES_PATHS_OR_NETWORK",
            "synthetic_files": 4,
            "guarded_consumers": 2,
            "trial_requires_explicit_engine_click": True,
            "trial_executed_on_guide_view": False,
            "arbitrary_customer_code_access": False,
            "automatic_patch_applied": False,
        },
        "review_gates": {
            "human_approved": False,
            "source_revision_pinned": False,
            "per_revision_rights_cleared": False,
            "independent_upstream_qa": False,
            "release_signed": False,
            "customer_release_authorized": False,
        },
        "export_allowed": False,
        "auto_promoted": False,
        "other_project_access": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "customer_release_authorized": False,
    }
