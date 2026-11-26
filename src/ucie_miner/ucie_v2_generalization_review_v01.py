"""UCIE B4 original Korean chapter and B3-informed bounded revision advice.

Only already reviewed UCIE source pins and bounded synthetic trials.
No network, customer data, upstream execution, scheduling, training or release.
"""
from __future__ import annotations

from . import ucie_v2_revision_impact_v01 as b3
from .ucie_v2_generalization_transfer_v01 import (
    B4HypothesisError, SCHEMA as HYPOTHESIS_SCHEMA,
    build_hypothesis, run_bounded_transfer,
)

SCHEMA = "UCIE_V2_B4_GENERALIZATION_REVIEW_AND_REVISION_V01"
B4_TEST = "test_ucie_v2_generalization_transfer_v01.py"


def render_hypothesis_chapter() -> str:
    """Create an original fact-vs-inference Korean chapter from exact contracts."""
    h = build_hypothesis()
    trial = run_bounded_transfer(h)
    if (h.get("schema") != HYPOTHESIS_SCHEMA
            or trial.get("hypothesis_id") != h.get("hypothesis_id")
            or trial.get("content_sha256") != h.get("content_sha256")
            or trial.get("positive_negative_control") !=
                ["CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"]
            or trial.get("real_upstream_sdk_rerun") is not False
            or trial.get("independent_qa_verified") is not False
            or h.get("export_allowed") is not False
            or h.get("model_trained") is not False):
        raise B4HypothesisError("draft source/trial/status drift")
    parents = h["parents"]
    if (len(parents) != 2 or
            {p["source_id"] for p in parents} !=
                {"doc:python/cpython", "doc:git/git"}):
        raise B4HypothesisError("invalid original chapter provenance")
    lines = [
        "# UCIE V2 가상도서관 - 일반화 가설 검토 초안",
        "",
        "- 상태: **UCIE 자체 가설, 검토 전. 배포 불가.**",
        "- 가설 ID: " + h["hypothesis_id"],
        "- 내용 SHA-256: " + h["content_sha256"],
        "",
        "## 1. 원본 기술 근거와 UCIE의 추론 분리",
    ]
    for parent in parents:
        lines.extend([
            "- SkillBook: " + parent["skillbook_id"],
            "  - 출처: " + parent["source_id"],
            "  - 근거 SHA-256: " + parent["document_sha256"],
            "  - 제한된 함수: " + parent["original_machine_callable"],
            "  - 자원 한도: " + parent["input_budget_contract"],
            "  - 실제 출력 계약: " + parent["observed_output_contract"],
        ])
    lines.extend([
        "",
        "## 2. 공통 원리: UCIE의 원본 가설 (공식 사실 아님)",
        "",
        h["hypothesis"],
        "",
        "추출한 공통 조건: " + ", ".join(h["shared_candidate_facets"]),
        "",
        "## 3. 일반화할 수 없는 반례",
        "",
        "- 거부한 주장: " + h["nontransferable_privacy_claim"]["claim"],
        "- Python 제한형 디렉터리 열거는 파일명 자체를 호출자에게 반환합니다.",
        "- Git 제한형 상태 요약은 파일명 대신 개수만 반환합니다.",
        "- 두 기술 모두 입력 예산을 제한해도 정보 노출 범위까지 같지는 않습니다.",
        "",
        "## 4. 세 번째 기술(MCP)로의 제한된 전이 시험",
        "",
        "- 대상: " + h["target_case"],
        "- SDK 출처 고정 커밋: " + h["target_upstream_commit"],
        "- UCIE 작성 검사기: " + h["target_ucie_recipe"],
        "- 합성 시험: 정상 계약 일치 / 의도적 오류 계약 위반 / 실행 오류 통제군",
        "- 관측 상태: " + ", ".join(trial["positive_negative_control"]),
        "- 실제 외부 MCP SDK를 이번에 재실행한 것이 아닙니다.",
        "",
        "## 5. 적용 금지와 승인 보류",
        "",
        *("- " + reason for reason in h["explicit_exclusions"]),
        "- 독립 QA, 실제 고객환경, 권리, 보안, 서명, 배포: 미완료 또는 미승인",
        "- 범용 자동 추론 모델 및 모델 학습: 구현·수행되지 않음",
        "- 변경 영향 검사는 B3의 독립 재시험 제안으로 연결할 수 있습니다.",
        "",
        "## 6. 기술 자산의 현재 단계",
        "",
        "- 사람이 읽는 UCIE 원본 초안: 작성됨",
        "- 기계가 읽는 한정형 시험 계약: 작성됨",
        "- 독립 검증·상품화 배포: 불가",
    ])
    return "\n".join(lines) + "\n"


def assess_hypothesis_revision(signals: tuple[dict, ...]) -> dict:
    """Plan only relevant B3/B4 tests; candidate digests are unverified signals."""
    hypothesis = build_hypothesis()
    plan = b3.assess_revision_impacts(signals)
    affected = set(plan["affected_assets"])
    parent_or_target = {b3.PY_BOOK, b3.GIT_BOOK, b3.PRINCIPLE, b3.MCP_ASSET}
    needs_review = bool(parent_or_target & affected)
    files = sorted(set(plan["proposed_test_files"]) |
                   ({B4_TEST} if needs_review else set()))
    return {
        "schema": SCHEMA,
        "status": ("SOURCE_CANDIDATE_CHANGED_HYPOTHESIS_REVIEW_REQUIRED"
                   if needs_review else "NO_LINKED_CHANGE_IN_BOUNDED_GRAPH"),
        "hypothesis_id": hypothesis["hypothesis_id"],
        "previous_hypothesis_sha256": hypothesis["content_sha256"],
        "candidate_hypothesis_sha256": "NOT_COMPUTED",
        "changed_candidate_source_ids": plan["candidate_changed_source_ids"],
        "affected_assets": sorted(affected),
        "b4_hypothesis_impacted": needs_review,
        "bounded_proposed_test_files": files,
        "source_revision_authenticated": False,
        "global_asset_coverage_verified": False,
        "source_or_test_auto_executed": False,
        "retest_auto_scheduled": False,
        "auto_promoted": False,
        "model_trained": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
