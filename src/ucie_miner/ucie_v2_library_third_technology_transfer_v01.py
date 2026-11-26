"""UCIE Virtual Library third-technology transfer falsification, review only.

Reuses the existing real source-pinned Python/Git curated original principle
and MCP Capsule. Tests a bounded original *claim classifier* on a held-out MCP
contract, NOT on an actual SDK or arbitrary downloaded text. This is a real
first-party negative-control run, not independent technical validation.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json

from .local_v1_priority_v01 import require_local_work
from .skillbook_principle_composer_v01 import (
    compose_bounded_metadata_principle, PRINCIPLE_ID, PYTHON_ID, GIT_ID,
)
from .ucie_v2_capsule_v01 import build_from_existing_ucie
from .ucie_v2_revision_impact_v01 import PINS, MCP_ASSET, MCP_SKILLBOOK

SCHEMA = "UCIE_V2_VLIB_HELDOUT_MCP_TRANSFER_FALSIFICATION_V01"
CANDIDATE = "UCIE-VLIB-GENERALIZATION-BOUNDARY-003"
CASES = (
    ("explicit-input-and-bounds", "BOUNDED_INPUT_AND_EXPLICIT_SCOPE", True),
    ("all-outputs-hide-names", "ALL_OUTPUTS_ANONYMIZED", False),
    ("historic-sdk-means-current-customer-fix", "UNIVERSAL_SDK_COMPATIBILITY", False),
)


class TransferReviewError(ValueError):
    """Never silently promote historical/synthetic source facts to universal."""


def _hash(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def _bounded_transfer_check(claim: str) -> bool:
    """First-party exhaustive allowlisted scope test; no external execution."""
    if type(claim) is not str or claim not in {row[1] for row in CASES}:
        raise TransferReviewError("unknown transfer hypothesis")
    return claim == "BOUNDED_INPUT_AND_EXPLICIT_SCOPE"


def build_heldout_transfer_review() -> dict:
    require_local_work("VIRTUAL_LIBRARY")
    principle = compose_bounded_metadata_principle()
    capsule = build_from_existing_ucie()
    sources = principle.get("sources")
    if (principle.get("principle_id") != PRINCIPLE_ID
            or principle.get("generalization_method") !=
               "FIRST_PARTY_CURATED_EXPLICIT_COMPARISON"
            or principle.get("independent_qa_verified") is not False
            or principle.get("export_allowed") is not False
            or type(sources) is not list or len(sources) != 2
            or {s.get("skillbook_id") for s in sources}
               != {PYTHON_ID, GIT_ID}
            or {s.get("source_id"): s.get("document_sha256")
                for s in sources} != {
                "doc:python/cpython": PINS["doc:python/cpython"],
                "doc:git/git": PINS["doc:git/git"]}
            or capsule.capsule_id != MCP_ASSET
            or capsule.skillbook_id != MCP_SKILLBOOK
            or capsule.fixed_commit != PINS["repo:modelcontextprotocol/python-sdk"]
            or capsule.independent_qa != "NOT_VERIFIED"
            or capsule.rights != "NOT_APPROVED"
            or capsule.customer_release != "NOT_AUTHORIZED"
            or capsule.fixed_published_version != "NOT_VERIFIED"):
        raise TransferReviewError("unreviewed source or claimed approval")
    trials = []
    for scenario, claim, expected in CASES:
        result = _bounded_transfer_check(claim)
        if result is not expected:
            raise TransferReviewError("positive or negative control mismatch")
        trials.append({
            "scenario": scenario,
            "claim_code": claim,
            "expected_transfer": expected,
            "observed_first_party_review_result": result,
            "status": "BOUNDED_DRAFT_ACCEPTABLE" if result else
                      "REJECT_OVERBROAD_OR_UNTESTED_TRANSFER",
            "trial_origin": "UCIE_AUTHORED_HELDOUT_MCP_CONTRACT_FIXTURE",
        })
    chapter = (
        "UCIE 독립 초안: Python의 제한된 디렉터리 열거와 Git의 "
        "NUL 종료 상태 데이터 파싱은 모두 호출자가 범위를 정하고 "
        "예산을 제한하는 원리를 공유한다. MCP 입력과 오류 처리를 "
        "설계할 때는 경계 정의라는 추상적 원리만 후보로 옮길 수 있다. "
        "그러나 Python 레시피는 파일명을 노출하고 Git 레시피는 "
        "경로를 버리므로 모든 결과가 익명이라는 일반화는 거부한다. "
        "역사적 MCP SDK 메모리 시험은 현재 SDK와 고객 환경의 수정 "
        "효과를 증명하지 않는다. 세 기술의 API/프로토콜 호환성은 "
        "각각 다른 시험으로 검증해야 한다."
    )
    recipe = {
        "kind": "UCIE_FIRST_PARTY_ORIGINAL_ENGINE_TEST_CONTRACT_DRAFT",
        "principle_id": PRINCIPLE_ID,
        "target_capsule_id": MCP_ASSET,
        "supported_claims": ["BOUNDED_INPUT_AND_EXPLICIT_SCOPE"],
        "rejected_claims": ["ALL_OUTPUTS_ANONYMIZED",
                            "UNIVERSAL_SDK_COMPATIBILITY"],
        "reproducible_test_module":
            "tests/test_ucie_v2_library_third_technology_transfer_v01.py",
        "external_source_execution": False,
        "runtime_execution_enabled": False,
        "model_training_performed": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "export_allowed": False,
    }
    core = {
        "schema": SCHEMA, "candidate_id": CANDIDATE,
        "origin_principle_id": PRINCIPLE_ID,
        "origin_principle_sha256": principle["content_sha256"],
        "parents": [{
            "skillbook_id": s["skillbook_id"],
            "source_id": s["source_id"],
            "source_sha256": s["document_sha256"],
        } for s in sources],
        "third_technology": {
            "capsule_id": capsule.capsule_id,
            "skillbook_id": capsule.skillbook_id,
            "approved_source_id": "repo:modelcontextprotocol/python-sdk",
            "source_commit": capsule.fixed_commit,
        },
        "generalized_hypothesis":
            "INPUT_SCOPE_AND_PROCESSING_BUDGET_TRANSFERS_ONLY_AS_DESIGN_CANDIDATE",
        "heldout_trials": trials,
        "original_human_skillbook_chapter": chapter,
        "human_chapter_sha256": sha256(chapter.encode("utf-8")).hexdigest(),
        "machine_test_contract": recipe,
        "candidate_status": "REVIEW_ONLY_UNVERIFIED_THIRD_TECH_TRANSFER",
        "autonomous_semantic_discovery_verified": False,
        "actual_mcp_sdk_reexecuted_now": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**core, "content_sha256": _hash(core)}


def render_heldout_transfer_review(review: dict) -> str:
    """No user input/host operation; display test counterexamples explicitly."""
    if (type(review) is not dict or review != build_heldout_transfer_review()
            or review["customer_release_authorized"] is not False):
        raise TransferReviewError("altered or unapproved inference")
    e = lambda s: escape(str(s), quote=True)
    cases = "".join(
        "<li>" + e(x["claim_code"]) + " — " + e(x["status"]) + "</li>"
        for x in review["heldout_trials"])
    return (
        '<section id="vlib-heldout-generalization" '
        'aria-labelledby="heldout-title">'
        '<h2 id="heldout-title">가상도서관: 세 번째 기술로 일반화 경계 검토</h2>'
        '<p>Python·Git 원리의 MCP 전이 가능성을 UCIE 고정 입력으로 '
        '제한 검토합니다. 실제 SDK 시험이나 자율적 기술 발견은 아닙니다.</p>'
        '<h3>UCIE가 재구성한 원리</h3><p>' +
        e(review["original_human_skillbook_chapter"]) + '</p>'
        '<details><summary>긍정·반증·통제 결과</summary><ul>' +
        cases + '</ul></details>'
        '<p>출처 고정: ' + e(review["origin_principle_id"]) +
        ' · ' + e(review["third_technology"]["capsule_id"]) + '</p>'
        '<p>기계용 엔진/시험 계약: 초안 · 독립 QA 미완료 · '
        '사용권 미승인 · 고객 배포 불가</p></section>'
    )
