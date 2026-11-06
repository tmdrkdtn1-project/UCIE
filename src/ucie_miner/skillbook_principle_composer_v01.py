"""UCIE-only source-bound principle composer for two authored SkillBooks.

This is a *curated, deterministic cross-technique synthesis* of fixed first-
party books. It is not a model, arbitrary web-text summarizer, auto-training
pipeline, general-purpose approved skill, export path or legal verdict.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .skillbook_product_v01 import build_skillbook as python_skillbook
from .skillbook_git_porcelain_product_v01 import build_skillbook as git_skillbook
from .skillbook_scandir_recipe_v01 import bounded_regular_file_names
from .skillbook_git_porcelain_recipe_v01 import summarize_porcelain_v1_z

SCHEMA = "UCIE_SKILLBOOK_CROSS_SOURCE_PRINCIPLE_V01"
DEMO_SCHEMA = "UCIE_SKILLBOOK_CROSS_SOURCE_SYNTHETIC_DEMO_V01"
PRINCIPLE_CODE = "BOUNDED_METADATA_OBSERVATION"
PRINCIPLE_ID = "UCIE-PRINCIPLE-PYTHON-GIT-BOUNDED-METADATA-001"
REVISION = "0.1.0-draft"
PYTHON_ID = "UCIE-SKILLBOOK-PY-SCANDIR-001"
GIT_ID = "UCIE-SKILLBOOK-GIT-PORCELAIN-002"
SUPPORT = {
    PYTHON_ID: {
        "source_id": "doc:python/cpython",
        "source_tag": "v3.15.0",
        "document_sha256": "9d78f43c4d521c1adfe339731628feadc834728ff09112c29e63ebc09406c45a",
        "purpose_code": "BOUNDED_SCANDIR_RESOURCE_LIFECYCLE",
        "callable": "ucie_miner.skillbook_scandir_recipe_v01.bounded_regular_file_names",
        "budget": "max_entries=128",
        "data_disclosed": "SORTED_REGULAR_FILENAMES",
        "risk_note": "File names are disclosed to the explicitly authorized caller; not counts-only",
    },
    GIT_ID: {
        "source_id": "doc:git/git",
        "source_tag": "v2.51.0",
        "document_sha256": "1cdd1c7339dfc64093687b6e072d59feee584b8639c0203ece0a1150ce23d325",
        "purpose_code": "BOUNDED_GIT_PORCELAIN_V1_Z_SUMMARY",
        "callable": "ucie_miner.skillbook_git_porcelain_recipe_v01.summarize_porcelain_v1_z",
        "budget": "max_entries=64, max_payload_bytes=8192",
        "data_disclosed": "COUNTS_ONLY_NO_FILENAMES",
        "risk_note": "Input Git records are caller-supplied and never independently authenticated",
    },
}
CLAIMS = (
    {
        "heading": "공통 원리: 관측할 대상과 입력의 권한을 먼저 고정",
        "claim_type": "UCIE_AUTHORED_CROSS_SOURCE_INFERENCE_NOT_UPSTREAM_FACT",
        "text": (
            "제한된 메타데이터 처리의 첫 번째 설계 원리는 암묵적 주변 환경 탐색을 "
            "배제하고 입력에 대한 권한·형태를 호출 경계에서 분리하는 것이다. "
            "Python 방식은 별도로 승인된 절대 디렉터리만 받으며, Git 방식은 "
            "실행자가 제공한 bytes만 파싱한다. 둘 다 외부 프로젝트 자동 탐색을 하지 않는다."
        ),
    },
    {
        "heading": "공통 원리: 처리 예산과 수명·종료 규칙을 먼저 정한다",
        "claim_type": "UCIE_AUTHORED_CROSS_SOURCE_INFERENCE_NOT_UPSTREAM_FACT",
        "text": (
            "디렉터리 열거는 파일 외 디렉터리·링크까지 총 128개 이하의 항목 예산과 "
            "컨텍스트 관리자 종료를 강제한다. Git 상태 파서는 8192바이트와 "
            "64개 레코드, NUL 종료 형식을 요구한다. 예산 초과와 불완전한 입력은 "
            "부분 성공이 아니라 예외로 종결한다. 제한값을 두 기술 사이에서 혼용하지 않는다."
        ),
    },
    {
        "heading": "비교·기술 분류: 결과의 공개 범위는 다르다",
        "claim_type": "UCIE_AUTHORED_PRIVACY_AND_LIMITATION_ANALYSIS",
        "text": (
            "두 레시피 모두 원본 파일 내용을 읽지 않지만 출력은 같지 않다. "
            "scandir 레시피는 실제 파일명 목록을 반환하므로 사용자 지정 디렉터리의 "
            "이름이 노출된다. Git 레시피는 검증 뒤 경로를 버리고 개수만 반환한다. "
            "따라서 필요 최소한의 노출 수준을 작업별로 별도 선택해야 한다."
        ),
    },
    {
        "heading": "반례와 안전한 중지 조건",
        "claim_type": "UCIE_AUTHORED_NEGATIVE_DESIGN_CASES",
        "text": (
            "권한을 확인하지 않은 디렉터리, 상대 경로, 링크·junction을 통한 리디렉션, "
            "실시간 파일 교체 경쟁 상태를 보안 격리로 해결했다고 주장하지 않는다. "
            "잘못된 Git XY 상태와 NUL 누락, 초과 입력으로부터 임의 경로·내용·"
            "사용 허가를 도출하지 않는다. 이 패턴은 악성코드 검사기나 보안 샌드박스가 아니다."
        ),
    },
    {
        "heading": "적용·개정·시험 경계",
        "claim_type": "UCIE_AUTHORED_VERSION_AND_QA_LIMITATIONS",
        "text": (
            "공식 Python 3.15.0 문서 및 Git 2.51.0 태그의 API 계약을 참조하되 "
            "다른 버전 전체의 실제 호환성·고객 업무 성능을 단정하지 않는다. "
            "UCIE 자체 합성 입력·실행은 두 실제 레시피의 제한된 동작만 시험한다. "
            "독립 QA·소스 사용권·보안·소유자 승인·서명/배포는 별도 조건이다."
        ),
    },
)


class PrincipleCompositionError(ValueError):
    """Unapproved input, modified claim, or inconsistent source lineage."""


def _canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":")).encode("ascii")


def _books() -> tuple[dict, dict]:
    return (python_skillbook(), git_skillbook())


def compose_bounded_metadata_principle(
    books: tuple[dict, dict] | None = None,
) -> dict:
    """Build one *original* cross-source chapter from two exact curated books.

    A caller may reorder the two books. Nothing else is accepted, especially
    injected claims, mutable approval flags, third sources or third-party code.
    The original chapter wording is authored in this UCIE module, never lifted
    from public source text or fabricated by a model.
    """
    baseline = {b["skillbook_id"]: b for b in _books()}
    if books is None:
        books = tuple(deepcopy(b) for b in baseline.values())
    if type(books) is not tuple or len(books) != 2 or any(
            type(b) is not dict or len(b) > 25 for b in books):
        raise PrincipleCompositionError("exact two curated authored books required")
    seen = set()
    sources = []
    for b in books:
        book_id = b.get("skillbook_id")
        if (type(book_id) is not str or book_id not in baseline
                or book_id in seen or b != baseline[book_id]):
            raise PrincipleCompositionError("source book changed or falsely approved")
        seen.add(book_id)
        expected = SUPPORT[book_id]
        entry, source = b.get("library_entry"), b.get("source_evidence")
        machine, gates = b.get("machine_skill_contract"), b.get("proof_gates")
        history = b.get("revision_history")
        if (type(entry) is not dict or type(source) is not dict
                or type(machine) is not dict or type(gates) is not dict
                or type(history) is not list or len(history) != 1
                or entry.get("source_id") != expected["source_id"]
                or entry.get("purpose_code") != expected["purpose_code"]
                or entry.get("evidence_sha256") != expected["document_sha256"]
                or entry.get("approval_status") != "NOT_APPROVED"
                or entry.get("export_allowed") is not False
                or source.get("source_tag") != expected["source_tag"]
                or source.get("source_document_sha256")
                   != expected["document_sha256"]
                or machine.get("callable") != expected["callable"]
                or any(gates.get(k) is not False for k in (
                    "independent_test_verified", "security_review_approved",
                    "license_redistribution_approved", "human_approved",
                    "signed", "published"))
                or history[0].get("published") is not False):
            raise PrincipleCompositionError("public source or approval gate drift")
        sources.append({
            "skillbook_id": book_id,
            "source_id": entry["source_id"],
            "library_item_id": entry["library_item_id"],
            "public_url": source["official_document_url"],
            "source_tag": source["source_tag"],
            "document_sha256": expected["document_sha256"],
            "provenance_status": "SOURCE_ID_PINNED_NOT_INDEPENDENT_QA",
            "callable": expected["callable"],
            "budget": expected["budget"],
            "data_disclosed": expected["data_disclosed"],
            "risk_note": expected["risk_note"],
            "license_state": entry["source_license_status"],
            "source_approved_for_research_not_redistribution": True,
        })
    if seen != set(SUPPORT):
        raise PrincipleCompositionError("missing cross-source evidence")
    sources.sort(key=lambda x: x["skillbook_id"])
    chapters = [dict(chapter) for chapter in CLAIMS]
    basis = {
        "schema": SCHEMA, "principle_code": PRINCIPLE_CODE,
        "principle_version": REVISION, "sources": sources, "chapters": chapters,
    }
    checksum = sha256(_canon(basis)).hexdigest()
    return {
        **basis,
        "principle_id": PRINCIPLE_ID,
        "content_sha256": checksum,
        "status": "UCIE_CURATED_CROSS_SOURCE_CHAPTER_DRAFT_NO_GO",
        "classification": "REUSABLE_SKILL_DESIGN_PRINCIPLE",
        "human_readable_original_chapter_created": True,
        "generalization_method": "FIRST_PARTY_CURATED_EXPLICIT_COMPARISON",
        "arbitrary_untrusted_source_synthesis_supported": False,
        "upstream_technical_assertions_verified_independently": False,
        "first_party_recipe_invocation": "SEPARATE_OPT_IN_SYNTHETIC_TEST",
        "machine_consumer": {
            "scandir": SUPPORT[PYTHON_ID]["callable"],
            "git_summary": SUPPORT[GIT_ID]["callable"],
            "real_external_directory_allowed": False,
            "real_repository_examined": False,
        },
        "revision_history": [{
            "version": REVISION,
            "source_content_sha256": checksum,
            "supersedes": None,
            "status": "DRAFT_NOT_APPROVED",
            "independently_verified": False,
            "owner_approved": False,
            "published": False,
        }],
        "independent_qa_verified": False, "security_approved": False,
        "rights_approved": False, "owner_approved": False,
        "signed": False, "export_allowed": False, "released": False,
        "automatic_promotion": False, "model_trained": False,
        "network_requests": 0, "operating_database_writes": 0,
        "other_project_access": False,
    }


def render_principle_markdown(principle: dict) -> str:
    """Render only the exact bound first-party authored result."""
    canonical = compose_bounded_metadata_principle()
    if type(principle) is not dict or principle != canonical:
        raise PrincipleCompositionError("unknown or altered principle manuscript")
    lines = [
        "# UCIE 교차 기술 원리 001 — 제한된 메타데이터 관측",
        "",
        "> UCIE가 직접 작성한 Python/Git 비교 원리입니다. 공식 문서의 직접 인용이나",
        "> 독립 검증된 일반 법칙·보안 인증·배포 승인이 아닙니다.",
        "",
    ]
    for row in principle["sources"]:
        lines.extend([
            "## 근거 — " + row["skillbook_id"],
            "",
            "공식 공개 주소: " + row["public_url"],
            "고정 근거 태그: " + row["source_tag"],
            "원본 문서 SHA-256: `" + row["document_sha256"] + "`",
            "실행 계약: `" + row["callable"] + "`",
            "항목 제한: " + row["budget"],
            "출력 노출: " + row["data_disclosed"],
            "주의: " + row["risk_note"],
            "",
        ])
    for chapter in principle["chapters"]:
        lines.extend([
            "## " + chapter["heading"],
            "",
            "저작 구분: `" + chapter["claim_type"] + "`",
            "",
            chapter["text"], "",
        ])
    lines.extend([
        "## 버전·승인 상태", "",
        "UCIE 자체 개정: `" + REVISION + "`",
        "합성/비교 초안 상태: `" + principle["status"] + "`",
        "독립 검증: 미완료 · 법적 권리: 미승인 · 외부 반출: 금지", "",
    ])
    result = "\n".join(lines)
    if len(result.encode("utf-8")) > 16000:
        raise PrincipleCompositionError("bounded manuscript size exceeded")
    return result


def run_first_party_synthetic_comparison() -> dict:
    """Actual existing recipes, synthetic-only in OS disposable directory.

    Directory names never escape. No owner-selected paths, public calls or
    automatic learn/update/promotion. Real feature evidence, not independent QA.
    """
    compose_bounded_metadata_principle()
    with TemporaryDirectory(prefix="UCIE_FIRST_PARTY_PRINCIPLE_") as folder:
        d = Path(folder)
        (d / "beta.txt").write_bytes(b"ucie first-party synthetic\n")
        (d / "alpha.txt").write_bytes(b"ucie first-party synthetic\n")
        names = bounded_regular_file_names(d, max_entries=2)
        if names != ("alpha.txt", "beta.txt"):
            raise PrincipleCompositionError("scandir synthetic result differs")
    git_data = b" M first.txt\x00?? second.txt\x00"
    summary = summarize_porcelain_v1_z(git_data, max_entries=2)
    if (summary["total_entries"] != 2
            or summary["counts"]["tracked_changed"] != 1
            or summary["counts"]["untracked"] != 1
            or summary["filenames_or_content_returned"] is not False):
        raise PrincipleCompositionError("Git synthetic summary differs")
    return {
        "schema": DEMO_SCHEMA,
        "principle_id": PRINCIPLE_ID,
        "status": "FIRST_PARTY_COMPARISON_RECIPE_OBSERVED_NO_RELEASE",
        "scandir_regular_file_count": len(names),
        "scandir_names_returned_to_external_consumer": False,
        "git_parsed_status_entries": summary["total_entries"],
        "git_counts": summary["counts"],
        "git_names_returned": False,
        "directory_origin": "SELF_CREATED_TEMPORARY_ONLY",
        "git_input_origin": "UCIE_AUTHOR_SYNTHETIC_BYTES_ONLY",
        "independent_qa_verified": False, "rights_approved": False,
        "export_allowed": False, "operating_database_writes": 0,
        "external_project_access": False, "network_requests": 0,
    }
