"""UCIE V2 B1-B4 source revision lifecycle, actual first-party code, offline.

Three fixed *hypothetical* source states reuse original B3 impact analysis,
B1 MCP Capsule, B2 known-case journey and B4 generated review packages.
This is review-only state TRANSFORMATION, not observation of a real change,
authentic source authentication, revalidation, approval or live mutation.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json

from .local_v1_priority_v01 import require_local_work
from .ucie_v2_capsule_v01 import build_from_existing_ucie
from .ucie_v2_revision_impact_v01 import (
    ASSETS, PINS, MCP_ASSET, MCP_SKILLBOOK, GIT_BOOK, PRINCIPLE,
    build_current_graph,
)
from .ucie_v2_local_readonly_preview_v01 import (
    build_fixed_demo, build_fixed_revision_impact_study,
)

SCHEMA = "UCIE_V2_B1_B4_REVISION_LIFECYCLE_REVIEW_V01"
SCENARIOS = (
    "mcp-change-hypothesis",
    "git-change-hypothesis",
    "git-original-unchanged",
)


class RevisionLifecycleError(ValueError):
    """Evidence or authority drift must not produce a false safe outcome."""


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def build_revision_lifecycle() -> dict:
    """Recompute exact UCIE source graph + actual fixed revision study + B4.

    Missing/incorrect source pins fail closed. Never accept candidate source
    blobs, filenames, customer input, URLs or runnable commands from users.
    """
    require_local_work("VIRTUAL_LIBRARY")
    graph = build_current_graph()
    study = build_fixed_revision_impact_study()
    capsule = build_from_existing_ucie()
    preview = build_fixed_demo("mcp-prompts")
    if (graph.get("source_pins") != dict(sorted(PINS.items()))
            or graph.get("graph_scope") != "FIRST_FIVE_PINNED_ASSETS_ONLY"
            or set(graph.get("assets", ())) != set(ASSETS)
            or graph.get("autonomous_generalization_verified") is not False
            or graph.get("operating_database_writes") != 0
            or study.get("actual_public_changes_observed") is not False
            or study.get("source_network_requests") != 0
            or study.get("operating_database_writes") != 0
            or capsule.capsule_id != MCP_ASSET
            or capsule.skillbook_id != MCP_SKILLBOOK
            or capsule.fixed_commit != PINS["repo:modelcontextprotocol/python-sdk"]
            or capsule.rights != "NOT_APPROVED"
            or capsule.independent_qa != "NOT_VERIFIED"
            or capsule.customer_release != "NOT_AUTHORIZED"
            or preview.get("customer_distribution_authorized") is not False
            or preview.get("actual_customer_sdk_tested_now") is not False):
        raise RevisionLifecycleError("source, Capsule, approval or study drift")
    review_rows = preview["linked_review_rows"]
    if (type(review_rows) is not list or len(review_rows) != 2
            or len({r["review_package_id"] for r in review_rows}) != 2
            or any(r["connected_via"] !=
                   "MCP_TARGET_AND_PIN_ONLY_NOT_SAME_EXPERIMENT"
                   or r["related_capsule_id"] != MCP_ASSET
                   or r["independent_sdk_compatibility_proven"] is not False
                   or r["rights_approved"] is not False
                   or r["export_allowed"] is not False for r in review_rows)):
        raise RevisionLifecycleError("unapproved library candidates")
    records = study.get("records")
    if (type(records) is not list or len(records) != len(SCENARIOS)
            or tuple(x.get("scenario") for x in records) != SCENARIOS):
        raise RevisionLifecycleError("review scenario order drift")
    workflow = []
    for record in records:
        sid = record["approved_source_id"]
        changed = record["changed_in_hypothesis"]
        impacted = record["affected_asset_ids"]
        unaffected = record["unaffected_asset_ids"]
        tests = record["proposed_test_names_not_executed"]
        if (sid not in PINS or record["pinned_original_sha256"] != PINS[sid]
                or record["candidate_pin_independently_authenticated"] is not False
                or record["actual_retest_executed"] is not False
                or record["automatic_scheduling"] is not False
                or record["candidate_is_hypothetical_only"] is not changed
                or type(changed) is not bool
                or type(impacted) is not list
                or type(unaffected) is not list
                or sorted(impacted + unaffected) != sorted(ASSETS)
                or len(impacted + unaffected) != len(ASSETS)
                or sorted(set(tests)) != tests
                or tests != sorted({f for a in impacted for f in ASSETS[a]["tests"]})
                or bool(impacted) is not changed):
            raise RevisionLifecycleError("source revision impact contract drift")
        if record["scenario"] == "mcp-change-hypothesis":
            if sid != "repo:modelcontextprotocol/python-sdk" or set(impacted) != {
                    MCP_ASSET, MCP_SKILLBOOK}:
                raise RevisionLifecycleError("MCP change scope drift")
        elif record["scenario"] == "git-change-hypothesis":
            if sid != "doc:git/git" or set(impacted) != {GIT_BOOK, PRINCIPLE}:
                raise RevisionLifecycleError("Git principle closure drift")
        elif record["scenario"] == "git-original-unchanged":
            if sid != "doc:git/git" or impacted:
                raise RevisionLifecycleError("unchanged source retest drift")
        else:
            raise RevisionLifecycleError("unreviewed source scenario")
        asset_rows = []
        for asset in sorted(ASSETS):
            selected = asset in impacted
            asset_rows.append({
                "asset_id": asset,
                "review_state": (
                    "HOLD_PROPOSED_RETEST_NOT_EXECUTED" if selected
                    else "HISTORIC_PIN_ONLY_NO_NEW_EVIDENCE"),
                "affected_by_hypothesis": selected,
                "independent_qa_verified": False,
                "customer_release_authorized": False,
            })
        mcp_changed = MCP_ASSET in impacted
        library = [{
            "review_package_id": row["review_package_id"],
            "package_sha256": row["package_sha256"],
            "scope": "MCP_HISTORIC_PIN_LINKED_SYNTHETIC_DRAFT",
            "review_state": (
                "HOLD_REASSESS_SOURCE_CHANGE_HYPOTHESIS" if mcp_changed
                else "HOLD_DRAFT_INDEPENDENT_QA_REQUIRED"),
            "source_change_independently_authenticated": False,
            "independent_sdk_compatibility_proven": False,
            "export_allowed": False,
        } for row in sorted(review_rows, key=lambda r:r["review_package_id"])]
        workflow.append({
            "scenario": record["scenario"],
            "source_id": sid,
            "source_baseline_pin": PINS[sid],
            "status": "HYPOTHETICAL_CHANGE_ONLY" if changed else
                      "UNCHANGED_PIN_NO_RETEST",
            "asset_review_states": asset_rows,
            "proposed_test_files_not_executed": tests,
            "bounded_library_review_packages": library,
            "safe_next_action": (
                "공식 출처와 변경 SHA를 독립 확인한 뒤 영향받는 시험만 검토하세요."
                if changed else "변경 증거가 없으므로 새 시험을 예약하지 마세요."),
            "actual_official_change_authenticated": False,
            "tests_executed_now": False,
            "rights_approved": False,
            "automatic_promotion": False,
        })
    core = {
        "schema": SCHEMA,
        "case_id": capsule.case_id,
        "capsule_id": capsule.capsule_id,
        "skillbook_id": capsule.skillbook_id,
        "fixed_source_commit": capsule.fixed_commit,
        "historical_first_party_ci_url": capsule.first_party_sdk_ci_url,
        "source_graph_scope": graph["graph_scope"],
        "review_workflows": workflow,
        "review_package_count": len(review_rows),
        "real_source_changes_observed": False,
        "real_owner_edge_retested_for_this_revision": False,
        "real_customer_environment_tested": False,
        "source_revision_independently_authenticated": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_distribution_authorized": False,
        "tests_executed_by_this_workflow": False,
        "scheduler_modified": False,
        "signed_rulepack_modified": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }
    return {**core, "content_sha256": _digest(core)}


def render_revision_lifecycle(report: dict) -> str:
    """One original novice-facing B1->B3->B4 decision with explicit HOLD."""
    if (type(report) is not dict
            or report.get("schema") != SCHEMA
            or report.get("content_sha256") != _digest({
                k: v for k, v in report.items() if k != "content_sha256"})
            or report.get("capsule_id") != MCP_ASSET
            or report.get("skillbook_id") != MCP_SKILLBOOK
            or report.get("fixed_source_commit") !=
               PINS["repo:modelcontextprotocol/python-sdk"]
            or report.get("source_graph_scope") != "FIRST_FIVE_PINNED_ASSETS_ONLY"
            or type(report.get("review_workflows")) is not list
            or len(report["review_workflows"]) != 3
            or any(report.get(key) is not False for key in (
                "real_source_changes_observed", "real_owner_edge_retested_for_this_revision",
                "real_customer_environment_tested", "source_revision_independently_authenticated",
                "independent_qa_verified", "rights_approved",
                "customer_distribution_authorized", "tests_executed_by_this_workflow",
                "scheduler_modified", "signed_rulepack_modified"))
            or report.get("operating_database_writes") != 0
            or report.get("network_requests") != 0):
        raise RevisionLifecycleError("unsafe lifecycle or false approval")
    e = lambda value: escape(str(value), quote=True)
    sections = []
    for i, record in enumerate(report["review_workflows"]):
        if (type(record) is not dict
                or record.get("scenario") != SCENARIOS[i]
                or record.get("source_id") not in PINS
                or record.get("source_baseline_pin") != PINS[record["source_id"]]
                or record.get("actual_official_change_authenticated") is not False
                or record.get("tests_executed_now") is not False
                or record.get("rights_approved") is not False
                or record.get("automatic_promotion") is not False):
            raise RevisionLifecycleError("tampered lifecycle step")
        assets = record.get("asset_review_states")
        tests = record.get("proposed_test_files_not_executed")
        packages = record.get("bounded_library_review_packages")
        if (type(assets) is not list or len(assets) != len(ASSETS)
                or type(tests) is not list or type(packages) is not list
                or len(packages) != 2 or
                any(type(row) is not dict or
                    row.get("independent_qa_verified") is not False or
                    row.get("customer_release_authorized") is not False or
                    row.get("review_state") not in (
                        "HOLD_PROPOSED_RETEST_NOT_EXECUTED",
                        "HISTORIC_PIN_ONLY_NO_NEW_EVIDENCE") for row in assets)
                or any(p.get("export_allowed") is not False or
                       p.get("independent_sdk_compatibility_proven") is not False
                       for p in packages)):
            raise RevisionLifecycleError("forged release or lost assets")
        held = [a for a in assets if a["review_state"] ==
                "HOLD_PROPOSED_RETEST_NOT_EXECUTED"]
        sections.append(
            '<article class="lifecycle-step" data-source-scenario="' +
            e(record["scenario"]) + '">'
            '<h3>' + e(("MCP 변경 가정", "Git 변경 가정", "Git 변경 없음")[i]) +
            '</h3><p>대상 출처: <code>' + e(record["source_id"]) + '</code></p>'
            '<p>재확인이 필요한 자산: ' + str(len(held)) + '개</p>'
            '<ul>' + ''.join('<li><code>' + e(row["asset_id"]) +
            '</code> · 보류 중</li>' for row in held) + '</ul>'
            '<p>재시험 제안: ' + str(len(tests)) + '개</p>'
            '<details><summary>제안된 시험 목록</summary><ul>' +
            ''.join('<li><code>' + e(x) + '</code></li>' for x in tests) +
            '</ul></details>'
            '<p>가상도서관 검토 자료: ' + str(len(packages)) +
            '건 · 서명/배포 미승인</p>'
            '<p><strong>다음 행동:</strong> ' + e(record["safe_next_action"]) +
            '</p><p>실제 변경 미조회 · 공식 SHA 독립 확인 전 · '
            '자동 시험/규칙 승격 없음</p></article>'
        )
    return (
        '<section class="lifecycle-workflow" id="revision-lifecycle" '
        'aria-labelledby="lifecycle-title">'
        '<h2 id="lifecycle-title">기술이 바뀌면 예전 검증을 어떻게 다룰까요?</h2>'
        '<p>기존 UCIE Capsule과 SkillBook을 기준으로 '
        '출처 변경을 <strong>가정</strong>해 새로 확인할 범위만 추립니다. '
        '변경된 자료는 재검토 대상으로 보류하지만, 이 결과는 실제 업데이트 '
        '발견이나 자동 재검증을 뜻하지 않습니다.</p>'
        + ''.join(sections) +
        '<p>기존 공식 시험 결과는 역사적 기록으로 유지합니다. '
        '새 버전의 효과·독립 QA·배포 권리는 아직 승인되지 않았습니다.</p>'
        '</section>'
    )


def render_owner_acceptance_checklist() -> str:
    """Read-only owner review instructions, never fabricate signoff."""
    return (
        '<section id="owner-acceptance" aria-labelledby="acceptance-title">'
        '<h2 id="acceptance-title">실제 사용자 확인 항목 (아직 미인수)</h2>'
        '<ol><li>네 가지 대표 사례의 제목과 안내를 찾을 수 있는가?</li>'
        '<li>어떤 내용이 합성 예제이고 어떤 내용이 과거 SDK 시험인가?</li>'
        '<li>기술이 변경됐다는 가정과 실제 변경 증거를 구별하는가?</li>'
        '<li>잘못된 SDK 버전이나 배포 승인 주장이 없는가?</li>'
        '<li>문제를 해결하기 전에 안전한 첫 행동을 이해할 수 있는가?</li>'
        '</ol>'
        '<p>실제 사람의 수행 시간·성공률·반응은 수집하지 않았습니다. '
        '별도 동의와 승인 없이 사용자 실험 기록을 만들지 않습니다.</p>'
        '</section>'
    )
