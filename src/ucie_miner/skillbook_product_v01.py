"""UCIE SkillBook V0.1: fixed first-party technical chapter and W02 Library item.

The catalog is an in-memory product draft, not a live crawler, a signed
skill, a license verdict, or a deployment/auto-learning pathway.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy

from .library_entry import LibraryEntryError, build_library_entry

SCHEMA = "UCIE_SKILLBOOK_SCANDIR_PRODUCT_V01"
CATALOG_SCHEMA = "UCIE_SKILLBOOK_V01_READONLY_CATALOG"
SKILLBOOK_ID = "UCIE-SKILLBOOK-PY-SCANDIR-001"
TOPIC = "BOUNDED_SCANDIR_RESOURCE_LIFECYCLE"
EVIDENCE_URL = "https://docs.python.org/3/library/os.html"
# Actual SHA-256 of python/cpython Doc/library/os.rst at tag v3.15.0.
# The GitHub blob SHA1 is separately recorded, never passed off as SHA-256.
SOURCE_DOCUMENT_SHA256 = "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a"
SOURCE_GIT_BLOB_SHA1 = "74419ee7f3588f1baec83c85b05716e6388719e3"
SOURCE_TAG_OBJECT_SHA = "7212e49729737c864e3f17b69ed83c8443c75acf"
SOURCE_COMMIT_SHA = "d220409a13b77de7a6c30abe16ea90db01528edc"

CHAPTERS = (
    {
        "heading": "출처로 확인된 API 동작",
        "claim_type": "OFFICIAL_PYTHON_DOCUMENTED",
        "text": (
            "os.scandir()는 순서가 보장되지 않는 DirEntry 반복자를 반환한다. "
            "반복자는 close()와 context manager를 지원하며, 리소스 정리를 위해 "
            "명시적으로 종료하거나 with 구문을 사용하는 것이 권장된다."
        ),
    },
    {
        "heading": "UCIE 작성 안전 레시피",
        "claim_type": "UCIE_AUTHORED_RECIPE",
        "text": (
            "승인된 절대 디렉터리만 명시적으로 받고, 하위 탐색이나 파일 내용 열기는 "
            "하지 않는다. with os.scandir()로 수명 관리를 보장하며, 총 탐색 항목 "
            "128개 이하의 예산을 강제하고 링크를 따라가지 않는다. "
            "반환 파일 이름은 재현 가능한 비교를 위해 정렬한다."
        ),
    },
    {
        "heading": "반례와 실패 처리",
        "claim_type": "UCIE_AUTHORED_NEGATIVE_CASES",
        "text": (
            "상대 경로, 심볼릭 링크 경로, 존재하지 않는 디렉터리, 0 또는 129 이상의 "
            "예산, 파일과 링크를 포함한 탐색 항목 초과는 명시적 오류로 차단한다. "
            "도중 오류가 나더라도 scandir 반복자의 정리가 보장되어야 한다."
        ),
    },
    {
        "heading": "적용 범위와 한계",
        "claim_type": "LIMITATIONS_NOT_VERIFIED",
        "text": (
            "이 예제는 단일 디렉터리 메타데이터만 다룬다. 디렉터리 교체 경쟁 상태 "
            "(TOCTOU), 권한 분리, OS 보안 경계, 변동하는 파일시스템에서의 원자적 "
            "스냅샷, 전체 디렉터리 트리 처리, 보안 제품 성능은 보장하지 않는다. "
            "배포 라이선스·독립 제3자 QA·실제 외부 환경 효능은 미검증이다."
        ),
    },
)

SEARCH_TERMS = (
    "python", "scandir", "directory", "enumeration", "resource", "close",
    "파일", "디렉터리", "열거", "자원", "정리", "리소스", "안전", "보안",
    "bounded", "symlink", "version", "3.15", "3.13",
)
QUERY = re.compile(r"[\w .-]{0,80}\Z", re.UNICODE)


class SkillBookProductError(ValueError):
    pass


def _candidate() -> dict:
    return {
        "kind": "REUSABLE_SKILL",
        "source_id": "doc:python/cpython",
        "evidence_reference": EVIDENCE_URL,
        "evidence_sha256": SOURCE_DOCUMENT_SHA256,
        "purpose_code": TOPIC,
        "version_scope": "PYTHON_3_15",
        "dependencies": ["python3"],
    }


def build_skillbook() -> dict:
    """Bind UCIE-authored content to an existing W01/W02 approved-source record."""
    try:
        entry = build_library_entry(_candidate())
    except (LibraryEntryError, KeyError, TypeError, ValueError) as exc:
        raise SkillBookProductError("public source or LibraryEntry contract drift") from exc
    if (entry["source_id"] != "doc:python/cpython"
            or entry["evidence_sha256"] != SOURCE_DOCUMENT_SHA256
            or entry["entry_status"] != "UNVERIFIED_CANDIDATE_ONLY"
            or entry["approval_status"] != "NOT_APPROVED"
            or entry["export_allowed"] is not False):
        raise SkillBookProductError("SkillBook source or approval boundary mismatch")
    return {
        "schema": SCHEMA,
        "skillbook_id": SKILLBOOK_ID,
        "title": "Python os.scandir 자원 수명과 제한된 디렉터리 열거",
        "topic": TOPIC,
        "kind": "REUSABLE_SKILL",
        "domain": "PYTHON",
        "language": "Python",
        "target_interpreters_for_ci": ["3.13", "3.15"],
        "library_entry": entry,
        "source_evidence": {
            "publisher": "python/cpython",
            "official_document_registry_id": "doc:python/cpython",
            "official_document_url": EVIDENCE_URL,
            "source_file": "Doc/library/os.rst",
            "source_tag": "v3.15.0",
            "source_tag_object_sha1": SOURCE_TAG_OBJECT_SHA,
            "source_commit_sha1": SOURCE_COMMIT_SHA,
            "source_document_git_blob_sha1": SOURCE_GIT_BLOB_SHA1,
            "source_document_sha256": SOURCE_DOCUMENT_SHA256,
            "source_digest_scope": "ENTIRE_VERSION_PINNED_DOC_SOURCE_BYTES",
            "claims_only_official_api_contract_not_independent_runtime_verification": True,
        },
        "ucie_authored_chapters": deepcopy(CHAPTERS),
        "machine_skill_contract": {
            "id": "UCIE-SKILL-BOUNDED-SCANDIR-001",
            "callable": "ucie_miner.skillbook_scandir_recipe_v01.bounded_regular_file_names",
            "signature": "bounded_regular_file_names(approved_directory, *, max_entries=128)",
            "inputs": {
                "approved_directory": "EXPLICIT_OWNER_AUTHORIZED_ABSOLUTE_LOCAL_DIRECTORY",
                "max_entries": "INTEGER_1_TO_128_INCLUSIVE",
            },
            "outputs": {
                "on_success": "SORTED_TUPLE_OF_REGULAR_FILENAMES_ONLY",
                "on_failure": "BoundedScandirError_FAIL_CLOSED",
            },
            "dependencies": ["Python 3.13+ standard library os, pathlib"],
            "preconditions": [
                "DIRECTORY_SCOPE_INDEPENDENTLY_AUTHORIZED_BY_CALLER",
                "NO_UNTRUSTED_PRIVATE_PROJECT_SCAN",
                "NOT_A_SECURITY_SANDBOX",
            ],
            "negative_tests": [
                "RELATIVE_PATH_DENIED", "SYMLINK_ROOT_DENIED",
                "OVERSIZED_DIRECTORY_DENIED", "INVALID_LIMIT_DENIED",
                "ITERATOR_CLOSED_ON_EARLY_FAILURE",
            ],
            "runtime_execution_by_catalog": False,
            "external_code_execution": False,
            "portable_package_state": "DRAFT_SOURCE_ONLY_NOT_APPROVED",
        },
        "proof_gates": {
            "pinned_upstream_identity_recorded": True,
            "first_party_recipe_implemented": True,
            "first_party_test_receipt": "SEPARATE_EXACT_COMMIT_CI_REQUIRED",
            "independent_test_verified": False,
            "license_redistribution_approved": False,
            "security_review_approved": False,
            "human_approved": False,
            "signed": False,
            "published": False,
        },
        "status": "FIRST_PARTY_DRAFT_NOT_APPROVED",
        "export_allowed": False,
        "auto_promoted": False,
        "model_training_performed": False,
        "upstream_source_executed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "other_project_access": False,
    }


def search_skillbooks(*, query: str = "", language: str = "",
                      kind: str = "") -> dict:
    """W04 style in-memory search; never changes the existing candidate index."""
    if (type(query) is not str or QUERY.fullmatch(query) is None
            or type(language) is not str or language not in ("", "Python")
            or type(kind) is not str or kind not in ("", "REUSABLE_SKILL")):
        raise SkillBookProductError("unsafe or unsupported library search filter")
    book = build_skillbook()
    terms = tuple(w.casefold() for w in query.strip().split())
    haystack = " ".join((
        book["title"], book["topic"], book["kind"], book["language"],
        " ".join(SEARCH_TERMS),
    )).casefold()
    matches = all(term in haystack for term in terms)
    items = [{
        "skillbook_id": book["skillbook_id"],
        "library_item_id": book["library_entry"]["library_item_id"],
        "title": book["title"],
        "kind": book["kind"],
        "domain": book["domain"],
        "language": book["language"],
        "source_id": book["library_entry"]["source_id"],
        "version_scope_claim": book["library_entry"]["version_scope_claim"],
        "source_document_sha256": SOURCE_DOCUMENT_SHA256,
        "status": book["status"],
        "human_approved": False,
        "export_allowed": False,
    }] if matches and (not language or language == book["language"]) and (
        not kind or kind == book["kind"]) else []
    return {
        "schema": CATALOG_SCHEMA,
        "status": "READ_ONLY_FIRST_PARTY_DRAFT_CATALOG",
        "total": len(items),
        "items": items,
        "legacy_public_candidate_index_modified": False,
        "operating_database_writes": 0,
        "network_requests": 0,
        "approved_reusable_packages": 0,
    }


def get_skillbook(skillbook_id: str) -> dict:
    if type(skillbook_id) is not str or skillbook_id != SKILLBOOK_ID:
        raise SkillBookProductError("unknown fixed SkillBook identity")
    return build_skillbook()


def main() -> int:
    print(json.dumps(search_skillbooks(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
