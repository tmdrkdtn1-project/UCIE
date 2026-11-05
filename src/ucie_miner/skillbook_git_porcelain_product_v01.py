"""UCIE SkillBook 002: Git porcelain v1 -z, source-linked draft product.

Git official documentation is trusted only as factual public evidence.
We never execute upstream code or inspect any working repository.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json

from .library_entry import LibraryEntryError, build_library_entry
from .skillbook_git_porcelain_recipe_v01 import (
    PorcelainSummaryError, summarize_porcelain_v1_z,
)

SCHEMA = "UCIE_SKILLBOOK_GIT_PORCELAIN_PRODUCT_V01"
SKILLBOOK_ID = "UCIE-SKILLBOOK-GIT-PORCELAIN-002"
TOPIC = "BOUNDED_GIT_PORCELAIN_V1_Z_SUMMARY"
SOURCE_DOC_SHA256 = "1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325"
SOURCE_DOC_BLOB_SHA1 = "9a376886a5867a63d173d85162c57027f336f915"
SOURCE_TAG = "v2.51.0"
EVIDENCE_REFERENCE = "https://git-scm.com/docs/git"
PUBLIC_DOC_URL = "https://git-scm.com/docs/git-status"
SEARCH_TERMS = (
    "git", "porcelain", "status", "nul", "rename", "copy", "repository",
    "changes", "파일", "상태", "개수", "요약", "리네임", "경로", "비공개",
)
DEMO_SCHEMA = "UCIE_SKILLBOOK_002_GIT_CONSUMER_PILOT_V01"
DEMO_OBSERVED = "FIRST_PARTY_SYNTHETIC_GIT_CONSUMER_OBSERVED_NO_RELEASE"
DEMO_PREVIEW = "GIT_CONSUMER_DEMO_NOT_RUN_NO_RELEASE"
DEMO_NO_GO = "GIT_CONSUMER_CONTRACT_NO_GO"

CHAPTERS = (
    {
        "heading": "Git 공식 파싱 계약",
        "claim_type": "OFFICIAL_GIT_DOCUMENTED",
        "text": (
            "git status --porcelain=v1 -z는 기계 판독용 NUL 종료 레코드를 "
            "제공한다. rename/copy에서는 -z 형식에 따라 경로 필드가 역순으로 "
            "배치되며, 원본/대상은 두 개의 NUL 구분 필드를 사용한다."
        ),
    },
    {
        "heading": "UCIE 작성 제한형 요약 레시피",
        "claim_type": "UCIE_AUTHORED_RECIPE",
        "text": (
            "실행자가 이미 별도로 승인해 제공한 최대 8KiB의 원시 bytes만 "
            "해석하며 레코드는 최대 64개까지만 허용한다. 각 경로는 검증한 뒤 "
            "버리고, 변경 분류별 개수만 결과로 돌려준다. Git 호출은 없다."
        ),
    },
    {
        "heading": "실패·오해 방지",
        "claim_type": "UCIE_AUTHORED_NEGATIVE_CASES",
        "text": (
            "NUL 누락, 잘못된 XY 상태, 불완전한 rename/copy 두 번째 경로, "
            "경로 탈출 형태, 초과 입력은 모두 명시적 오류로 거부한다. "
            "이 예시는 유효한 Git 원본 여부를 인증하지 않는다."
        ),
    },
    {
        "heading": "실제 사용 경계",
        "claim_type": "LIMITATIONS_NOT_VERIFIED",
        "text": (
            "실제 저장소 접근·사용자 경로 스캔·git 실행·리포지터리 상태 검증을 "
            "수행하지 않는다. 작업 복구·보안 검사·명령 실행 허가에 쓸 수 없고 "
            "독립 QA·라이선스·재배포 승인은 아직 없다."
        ),
    },
)


class GitSkillBookError(ValueError):
    """Unknown source, forged approval, or invalid fixed SkillBook identity."""


def build_skillbook() -> dict:
    candidate = {
        "kind": "REUSABLE_SKILL",
        "source_id": "doc:git/git",
        "evidence_reference": EVIDENCE_REFERENCE,
        "evidence_sha256": SOURCE_DOC_SHA256,
        "purpose_code": TOPIC,
        "version_scope": "GIT_2_51_0",
        "dependencies": ["python3"],
    }
    try:
        entry = build_library_entry(candidate)
    except (LibraryEntryError, TypeError, KeyError, ValueError) as exc:
        raise GitSkillBookError("Git official source not properly registered") from exc
    if (entry.get("source_id") != "doc:git/git"
            or entry.get("source_kind") != "OFFICIAL_PUBLIC_DOCUMENT"
            or entry.get("evidence_sha256") != SOURCE_DOC_SHA256
            or entry.get("entry_status") != "UNVERIFIED_CANDIDATE_ONLY"
            or entry.get("approval_status") != "NOT_APPROVED"
            or entry.get("export_allowed") is not False):
        raise GitSkillBookError("Git source or approval boundary drift")
    return {
        "schema": SCHEMA,
        "skillbook_id": SKILLBOOK_ID,
        "title": "Git porcelain v1 -z 변경사항 개수 요약(경로 비공개)",
        "topic": TOPIC,
        "kind": "REUSABLE_SKILL",
        "domain": entry["domain"],
        "language": "Python",
        "target_interpreters_for_ci": ["3.13", "3.15"],
        "library_entry": entry,
        "source_evidence": {
            "publisher": "git/git",
            "official_document_registry_id": "doc:git/git",
            "official_document_url": PUBLIC_DOC_URL,
            "registry_document_url": EVIDENCE_REFERENCE,
            "source_file": "Documentation/git-status.adoc",
            "source_tag": SOURCE_TAG,
            "source_document_git_blob_sha1": SOURCE_DOC_BLOB_SHA1,
            "source_document_sha256": SOURCE_DOC_SHA256,
            "source_digest_scope": "ENTIRE_GIT_TAG_PINNED_DOCUMENT_BYTES",
            "runtime_git_binary_version_verified": False,
            "upstream_code_executed": False,
        },
        "ucie_authored_chapters": deepcopy(CHAPTERS),
        "machine_skill_contract": {
            "id": "UCIE-SKILL-GIT-PORCELAIN-V1-Z-002",
            "callable": (
                "ucie_miner.skillbook_git_porcelain_recipe_v01."
                "summarize_porcelain_v1_z"
            ),
            "signature": "summarize_porcelain_v1_z(payload: bytes, *, max_entries=64)",
            "inputs": {
                "payload": "CALLER_SUPPLIED_GIT_PORCELAIN_V1_Z_BYTES_ONLY",
                "max_entries": "INTEGER_1_TO_64_INCLUSIVE",
            },
            "outputs": {
                "on_success": "BOUNDED_INTEGER_COUNTS_WITH_NO_PATH_BYTES",
                "on_failure": "PorcelainSummaryError_FAIL_CLOSED",
            },
            "preconditions": [
                "CALLER_VERIFIES_GIT_SOURCE_AND_PERMISSION_SEPARATELY",
                "GIT_PORCELAIN_V1_Z_WITHOUT_BRANCH_HEADER_ONLY",
                "NOT_A_SECURITY_SANDBOX",
            ],
            "negative_tests": [
                "UNTERMINATED_NUL_DENIED",
                "UNKNOWN_XY_DENIED",
                "RENAME_SECOND_PATH_REQUIRED",
                "TRAVERSAL_DENIED",
                "EXCESS_INPUT_DENIED",
                "OPAQUE_FILENAMES_NEVER_DISCLOSED",
            ],
            "runtime_execution_by_catalog": False,
            "external_code_execution": False,
            "portable_package_state": "DRAFT_SOURCE_ONLY_NOT_APPROVED",
        },
        "consumer_pilot": {
            "module": "ucie_miner.skillbook_git_porcelain_product_v01",
            "manual_opt_in": "--run-synthetic-demo",
            "mode": "UCIE_AUTHORED_IN_MEMORY_BYTES_EXAMPLE_ONLY",
            "uses_real_first_party_recipe": True,
            "accepts_repository_or_path_parameter": False,
            "executes_from_browser": False,
            "independent_qa_verified": False,
            "package_export_allowed": False,
        },
        "revision_history": [{
            "version": "0.1.0-draft",
            "state": "FIRST_PARTY_DRAFT_NOT_APPROVED",
            "evidence_sha256": SOURCE_DOC_SHA256,
            "scope": "GIT_PORCELAIN_SOURCE_ANCHORED_BOUNDED_COUNTS",
            "supersedes": None,
            "independently_verified": False,
            "published": False,
        }],
        "proof_gates": {
            "pinned_upstream_identity_recorded": True,
            "first_party_recipe_implemented": True,
            "first_party_test_receipt": "EXACT_COMMIT_CI_NOT_SELF_ATTESTED",
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


def preview_consumer() -> dict:
    return {
        "schema": DEMO_SCHEMA,
        "skillbook_id": SKILLBOOK_ID,
        "status": DEMO_PREVIEW,
        "demo_executed": False,
        "real_repository_inspected": False,
        "git_subprocess_invoked": False,
        "operating_database_writes": 0,
        "external_project_access": False,
        "export_allowed": False,
    }


def demonstrate_in_memory_consumer() -> dict:
    book = build_skillbook()
    if (book["status"] != "FIRST_PARTY_DRAFT_NOT_APPROVED"
            or book["export_allowed"] is not False
            or book["machine_skill_contract"]["callable"] !=
            "ucie_miner.skillbook_git_porcelain_recipe_v01.summarize_porcelain_v1_z"
            or book["proof_gates"]["independent_test_verified"] is not False
            or book["proof_gates"]["human_approved"] is not False):
        raise GitSkillBookError("untrusted Git SkillBook consumer contract")
    # Literal UCIE-authored fake Git output; NO git binary or repository access.
    payload = (b" M changed.txt\x00"
               b"?? new.txt\x00"
               b"R  new-name.txt\x00old-name.txt\x00"
               b"UU conflict.txt\x00")
    outcome = summarize_porcelain_v1_z(payload, max_entries=4)
    refused = False
    try:
        summarize_porcelain_v1_z(payload, max_entries=3)
    except PorcelainSummaryError:
        refused = True
    if (outcome.get("total_entries") != 4 or
            outcome["counts"] != {
                "tracked_changed": 1, "renamed": 1, "copied": 0,
                "conflicted": 1, "untracked": 1, "ignored": 0,
            } or refused is not True
            or outcome.get("filenames_or_content_returned") is not False
            or outcome.get("git_process_executed") is not False):
        raise GitSkillBookError("real Git summary recipe result drift")
    return {
        "schema": DEMO_SCHEMA,
        "skillbook_id": SKILLBOOK_ID,
        "status": DEMO_OBSERVED,
        "source_document_sha256": SOURCE_DOC_SHA256,
        "real_ucie_recipe_executed": True,
        "demo_entries": outcome["total_entries"],
        "safe_summary_counts": outcome["counts"],
        "budget_3_rejected": refused,
        "only_static_ucie_authored_bytes_used": True,
        "filename_or_private_data_returned": False,
        "real_repository_inspected": False,
        "git_subprocess_invoked": False,
        "independent_qa_verified": False,
        "security_review_approved": False,
        "license_redistribution_approved": False,
        "owner_release_approved": False,
        "export_allowed": False,
        "package_created": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "task_scheduler_mutations": 0,
        "other_project_access": False,
        "model_training_performed": False,
    }


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(
        description="UCIE SkillBook 002 Git porcelain offline bytes-only pilot")
    cli.add_argument("--run-synthetic-demo", action="store_true")
    args = cli.parse_args(argv)
    if not args.run_synthetic_demo:
        print(json.dumps(preview_consumer(), ensure_ascii=True, sort_keys=True))
        return 0
    try:
        report = demonstrate_in_memory_consumer()
    except (GitSkillBookError, PorcelainSummaryError, ValueError, KeyError, TypeError):
        print(json.dumps({"schema": DEMO_SCHEMA, "status": DEMO_NO_GO,
                          "export_allowed": False, "git_subprocess_invoked": False},
                         ensure_ascii=True, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
