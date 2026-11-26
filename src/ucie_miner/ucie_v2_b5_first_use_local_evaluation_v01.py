"""UCIE V2 B5 source-linked comparable method dry run and owner evaluation card.

This strictly reuses existing B5 synthetic comparator and the real source-
locked B1-B4 local proof. Nothing here observes or accepts actual participants,
user-entered code, external apps, passwords, telemetry or customer files.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json

from .local_v1_priority_v01 import require_local_work
from .ucie_v2_b5_comparison_contract_v01 import (
    build_comparison_protocol, summarize_synthetic_comparison,
    STUDY_ID, CASE_ID, METHODS, SYNTHETIC_ORIGIN, SCHEMA as PROTOCOL_SCHEMA,
)
from .ucie_v2_revision_lifecycle_workflow_v01 import build_revision_lifecycle

SCHEMA = "UCIE_V2_B5_OFFLINE_EVALUATION_WALKTHROUGH_V01"
LABELS = {
    "OFFICIAL_DOCS_ONLY": "공식 문서만 보는 방식",
    "GENERAL_TOOL": "일반 도구로 확인하는 방식",
    "UCIE_V2_REVIEW_ONLY": "UCIE V2 검토용 화면",
}


class B5WalkthroughError(ValueError):
    """Reject protocol drift, invented people or external test claims."""


def _sha(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def fixed_synthetic_comparison_records() -> tuple[dict, ...]:
    """Nine first-party artificial rows to exercise original B5 math only.

    Same synthetic timing and outcome per comparison arm to avoid a fabricated
    performance advantage; these are a parser/review smoke test, not an A/B.
    """
    records = []
    for method in METHODS:
        for index, time_ms in enumerate((13000, 10000, 11000), 1):
            records.append({
                "study_id": STUDY_ID, "case_id": CASE_ID,
                "anonymous_trial_token": f"F{index:02d}",
                "method": method, "cohort": "FIRST_TIME_CODER",
                "first_safe_action_time_ms": time_ms,
                "correct_safe_action": index != 2,
                "false_version_or_rights_claim": index == 3,
                "evidence_detail_found": index == 1,
                "origin": SYNTHETIC_ORIGIN,
            })
    return tuple(records)


def build_b5_readonly_evaluation() -> dict:
    require_local_work("LOCAL_ACCEPTANCE")
    protocol = build_comparison_protocol()
    lifecycle = build_revision_lifecycle()
    if (protocol.get("schema") != PROTOCOL_SCHEMA
            or protocol.get("study_id") != STUDY_ID
            or protocol.get("status") !=
                "METHOD_DEFINED_REAL_OBSERVATIONS_NOT_COLLECTED"
            or protocol.get("comparators") != list(METHODS)
            or protocol.get("task", {}).get("case_id") != CASE_ID
            or protocol.get("task", {}).get("required_safe_outcome") !=
                "RECOGNIZE_VERSION_UNKNOWN_HOLD_AND_ONE_SAFE_CHECK"
            or protocol.get("actual_human_study_completed") is not False
            or protocol.get("baseline_comparison_completed") is not False
            or protocol.get("real_novice_observed") != 0
            or protocol.get("real_technical_reviewer_observed") != 0
            or protocol.get("real_prospective_buyers_observed") != 0
            or protocol.get("customer_export_authorized") is not False
            or lifecycle.get("case_id") != CASE_ID
            or lifecycle.get("customer_distribution_authorized") is not False
            or lifecycle.get("real_source_changes_observed") is not False):
        raise B5WalkthroughError("source-linked B5 comparator or rights drift")
    summary = summarize_synthetic_comparison(fixed_synthetic_comparison_records())
    if (summary["case_id"] != lifecycle["case_id"]
            or summary["study_id"] != STUDY_ID
            or summary["status"] != "SYNTHETIC_METRICS_AGGREGATED_NOT_HUMAN_STUDY"
            or summary["total_synthetic_records"] != 9
            or summary["human_comparison_valid"] is not False
            or summary["real_novice_observed"] != 0
            or summary["real_baseline_or_competitor_tested"] is not False
            or summary["customer_willingness_measured"] is not False
            or summary["operating_database_writes"] != 0
            or summary["network_requests"] != 0):
        raise B5WalkthroughError("synthetic statistics misclassified")
    for method in METHODS:
        row = summary["methods"][method]
        if (row["synthetic_count"] != 3
                or row["synthetic_correct_safe_action_count"] != 2
                or row["synthetic_false_claim_count"] != 1
                or row["synthetic_evidence_found_count"] != 1
                or row["synthetic_first_action_median_ms"] != 11000
                or row["synthetic_safe_action_fraction"] != round(2/3, 6)):
            raise B5WalkthroughError("review comparator fixture drift")
    core = {
        "schema": SCHEMA,
        "study_id": STUDY_ID,
        "case_id": CASE_ID,
        "capsule_id": lifecycle["capsule_id"],
        "skillbook_id": lifecycle["skillbook_id"],
        "lifecycle_sha256": lifecycle["content_sha256"],
        "scenario": protocol["task"]["scenario"],
        "safe_outcome": protocol["task"]["required_safe_outcome"],
        "comparison_methods": [
            {"method": method, "label": LABELS[method],
             "illustrative_synthetic_only": summary["methods"][method]}
            for method in METHODS
        ],
        "target_first_safe_action_under_10_seconds_fraction":
            protocol["first_action_under_10_seconds_target_fraction"],
        "material_overclaim_count_target":
            protocol["material_overclaim_count_target"],
        "human_recruitment_and_consent_required": True,
        "owner_edge_browser_acceptance_pending": True,
        "actual_human_trials_collected": 0,
        "actual_purchasing_interviews_collected": 0,
        "actual_comparative_ux_effect_verified": False,
        "synthetic_comparison_is_not_product_performance": True,
        "independent_source_qa_verified": False,
        "customer_distribution_authorized": False,
        "raw_user_data_stored": False,
        "data_upload_or_post_created": False,
        "tests_or_trials_auto_executed_on_owner_pc": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**core, "content_sha256": _sha(core)}


def render_b5_evaluation_panel(report: dict) -> str:
    """Stable no-script HTML: independent first-use study card + dry-run data."""
    if (type(report) is not dict or report.get("schema") != SCHEMA
            or report.get("content_sha256") != _sha({
                k: v for k, v in report.items() if k != "content_sha256"})
            or report.get("study_id") != STUDY_ID
            or report.get("case_id") != CASE_ID
            or report.get("comparison_methods") is None
            or type(report["comparison_methods"]) is not list
            or len(report["comparison_methods"]) != len(METHODS)
            or tuple(r.get("method") for r in report["comparison_methods"]) != METHODS
            or report.get("actual_human_trials_collected") != 0
            or report.get("actual_purchasing_interviews_collected") != 0
            or report.get("human_recruitment_and_consent_required") is not True
            or report.get("owner_edge_browser_acceptance_pending") is not True
            or report.get("actual_comparative_ux_effect_verified") is not False
            or report.get("synthetic_comparison_is_not_product_performance") is not True
            or report.get("independent_source_qa_verified") is not False
            or report.get("customer_distribution_authorized") is not False
            or report.get("raw_user_data_stored") is not False
            or report.get("data_upload_or_post_created") is not False
            or report.get("tests_or_trials_auto_executed_on_owner_pc") is not False
            or report.get("network_requests") != 0
            or report.get("operating_database_writes") != 0):
        raise B5WalkthroughError("tampered comparison or false human approval")
    e = lambda v: escape(str(v), quote=True)
    rows = []
    for r in report["comparison_methods"]:
        method = r["method"]
        data = r["illustrative_synthetic_only"]
        if (r.get("label") != LABELS[method] or type(data) is not dict
                or data.get("synthetic_count") != 3
                or data.get("synthetic_first_action_median_ms") != 11000
                or data.get("synthetic_correct_safe_action_count") != 2
                or data.get("synthetic_false_claim_count") != 1):
            raise B5WalkthroughError("misleading illustrative comparison")
        rows.append(
            '<tr><th scope="row">' + e(r["label"]) + '</th>'
            '<td>인공 3건</td><td>11초</td><td>2/3</td><td>1건</td></tr>'
        )
    return (
        '<section id="b5-first-use-evaluation" aria-labelledby="b5-evaluation-title">'
        '<h2 id="b5-evaluation-title">어떤 안내가 처음 사용자에게 더 안전할까요?</h2>'
        '<p><strong>실제 비교시험은 아직 수행하지 않았습니다.</strong> '
        '아래 수치는 기존 UCIE B5 계산기를 시험하기 위한 '
        '세 방식의 동일한 인공 입력값이며 제품 성능을 뜻하지 않습니다.</p>'
        '<div role="region" aria-label="인공 비교시험 결과" tabindex="0">'
        '<table><caption>검토용 인공 데이터 · 실사용 결과 아님</caption>'
        '<thead><tr><th scope="col">방법</th><th scope="col">입력</th>'
        '<th scope="col">중앙값</th><th scope="col">올바른 행동</th>'
        '<th scope="col">허위 확신</th></tr></thead><tbody>' +
        ''.join(rows) + '</tbody></table></div>'
        '<h3>실제 검수 시 같은 과제를 비교할 기준</h3>'
        '<p>공식 문서만 보기, 일반 도구, UCIE V2 세 방법 모두 '
        'MCP 프롬프트 인수 오류에서 미확인 버전을 HOLD하고 '
        '안전한 첫 확인 행동을 선택하는 동일한 과제를 사용합니다.</p>'
        '<ol><li>버전 미확인 상태를 정확히 구분했는가?</li>'
        '<li>첫 안전 행동까지의 실제 시간은 얼마인가?</li>'
        '<li>잘못된 수정 성공·권리 주장이나 위험한 실행 권고가 있었는가?</li>'
        '<li>공식 출처와 과거 시험/현재 미검증을 구분했는가?</li>'
        '<li>설명 없이도 첫 행동과 검증 범위를 이해했는가?</li></ol>'
        '<p>목표: 10초 이내 첫 안전 행동 비율 '
        + e(int(report["target_first_safe_action_under_10_seconds_fraction"]*100))
        + '% 이상, 중대한 허위 주장 0건. '
        '이는 목표값이며 실제 달성 결과가 아닙니다.</p>'
        '<p>실제 초보자 시험과 경쟁 방법 비교는 별도 모집·동의·'
        '주관적 해석 배제·독립 검수가 필요합니다. '
        '참가자 기록·개인정보·구매 의사는 수집하지 않았습니다.</p>'
        '</section>'
    )
