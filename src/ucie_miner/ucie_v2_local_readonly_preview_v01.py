"""UCIE V2 local-first offline product walkthrough (not live V04).

Invokes the exact preexisting bounded question classifier, B1 MCP Capsule,
UCIE-authored B4 original review packages, and the isolated B2 three-step
renderer. Only four fixed, public-safe demonstration phrases can be used.
There is NO server, new route, user-code input, file write, source fetch,
external SDK invocation, promotion, signing, deployment, or owner-host change.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json
import sys
from urllib.parse import urlencode

from .local_v1_priority_v01 import require_local_work
from .ucie_v2_library_capsule_journey_v01 import (
    build_isolated_question_flow, render_isolated_question_flow,
)
from .ucie_v2_library_revision_ledger_v01 import (
    new_review_history, append_review_bundle,
)
from .ucie_v2_original_library_assets_v01 import assemble_original_library_assets
from .ucie_v2_feedback_registry_v01 import (
    empty_feedback_registry, append_feedback_evidence,
)
from .ucie_v2_revision_review_history_v01 import new_revision_history
from .ucie_v2_b5_comparison_contract_v01 import (
    STUDY_ID, CASE_ID, METHODS, SYNTHETIC_ORIGIN,
)

SCHEMA = "UCIE_V2_ISOLATED_LOCAL_PRODUCT_WALKTHROUGH_V01"
EXAMPLES = {
    "python-env": "Python에서 패키지를 설치했는데 ModuleNotFoundError가 발생합니다.",
    "powershell-command": "PowerShell에서 명령을 입력했는데 명령을 찾을 수 없습니다.",
    "git-repository": "Git 명령을 실행했는데 not a git repository 오류가 납니다.",
    "mcp-prompts": "MCP prompts/get 호출에서 인수 오류 -32602가 발생합니다.",
}
EXAMPLE_IDS = tuple(EXAMPLES)
PINNED_SYNTHETIC_FIXTURE_SHA256 = "a" * 64


class PreviewError(ValueError):
    """Fail closed without echoing unsupported or sensitive command arguments."""


def _hash(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def _first_party_study_record(method: str) -> dict:
    return {
        "study_id": STUDY_ID, "case_id": CASE_ID,
        "anonymous_trial_token": "F01",
        "method": method, "cohort": "FIRST_TIME_CODER",
        "first_safe_action_time_ms": 900, "correct_safe_action": True,
        "false_version_or_rights_claim": False, "evidence_detail_found": False,
        "origin": SYNTHETIC_ORIGIN,
    }


def _first_party_case(prefix: str, index: int, *, old_wrong: bool) -> dict:
    truth = "RISK" if index < 4 else "SAFE"
    return {
        "case_id": f"{prefix}_{index}", "ground_truth": truth,
        "baseline_prediction": truth,
        "challenger_prediction": "SAFE" if old_wrong and index == 1 else truth,
        "origin": "UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY",
        "source_sha256": PINNED_SYNTHETIC_FIXTURE_SHA256,
    }


def build_fixed_demo(case_id: str) -> dict:
    """Execute the same existing UCIE B1/B2/B4 code, not a mock webpage."""
    require_local_work("LOCAL_APP")
    if type(case_id) is not str or case_id not in EXAMPLES:
        raise PreviewError("only predefined UCIE public-safe cases allowed")
    question = urlencode({"question": EXAMPLES[case_id]}).encode("ascii")
    if case_id == "mcp-prompts":
        bundle = assemble_original_library_assets(
            tuple(_first_party_study_record(m) for m in METHODS), ())
        history = append_review_bundle(new_review_history(), bundle)
        reg = append_feedback_evidence(
            history, empty_feedback_registry(history), execute_synthetic=True)
        prior = new_revision_history(history)
        from .ucie_v2_feedback_registry_v01 import prioritize_review_experiments
        candidates = [x["candidate_id"] for x in
                      prioritize_review_experiments(history, reg)["priority_queue"]]
        if len(candidates) != 2:
            raise PreviewError("source-pinned review candidate count drift")
        before = {
            candidates[0]: [_first_party_case("a", i, old_wrong=True)
                            for i in range(8)],
            candidates[1]: [_first_party_case("b", i, old_wrong=False)
                            for i in range(8)],
        }
        after = {
            candidates[0]: [_first_party_case("a", i, old_wrong=False)
                            for i in range(8)],
            candidates[1]: [_first_party_case("b", i, old_wrong=False)
                            for i in range(8)],
        }
        flow = build_isolated_question_flow(
            question, history, reg, prior, before, after,
            fixture_sha256=PINNED_SYNTHETIC_FIXTURE_SHA256,
            expected_revision_head_sha256=prior["content_sha256"],
        )
    else:
        # This is the real original classifier and fixed synthetic workbench.
        # Never attach an unverified B1 MCP Capsule to unrelated cases.
        flow = build_isolated_question_flow(question)
    if (flow["case_id"] != case_id
            or flow["matched_known_issue"] is not True
            or flow["question_retained"] is not False
            or flow["customer_export_authorized"] is not False
            or flow["network_requests"] != 0
            or flow["operating_database_writes"] != 0):
        raise PreviewError("walkthrough evidence drift")
    rendered = render_isolated_question_flow(flow)
    receipt = {
        "schema": SCHEMA,
        "case_id": case_id,
        "case_evidence_sha256": flow["content_sha256"],
        "flow_kind": flow["technical_evidence_state"],
        "rendered_html_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
        "actual_owner_edge_browser_tested": False,
        "actual_customer_sdk_tested_now": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_distribution_authorized": False,
        "persistent_writes": 0,
        "network_requests": 0,
    }
    # For UI proof inspection, only the bounded validated review links.
    linked_rows = (
        flow["mcp_evidence_journey"]["related_review_packages"]
        if case_id == "mcp-prompts" else []
    )
    if len(linked_rows) > 2:
        raise PreviewError("too many review records")
    return {
        **receipt, "content_sha256": _hash(receipt),
        "preview_html": rendered,
        "linked_review_rows": linked_rows,
    }


def render_evidence_details(case_id: str) -> str:
    """Display inspectable *existing* evidence, without inventing verdicts.

    All values are produced by the pinned UCIE case assembly, never supplied
    by a browser field, customer source, URL parameter, or untrusted text.
    """
    from .ucie_v2_capsule_v01 import build_from_existing_ucie
    from .local_b2_connected_workbench_v01 import evaluate_case
    if type(case_id) is not str or case_id not in EXAMPLES:
        raise PreviewError("unsupported evidence case")
    e = lambda value: escape(str(value), quote=True)
    if case_id != "mcp-prompts":
        issue = evaluate_case(case_id, "issue")
        control = evaluate_case(case_id, "control")
        if (issue["case_id"] != case_id or control["case_id"] != case_id
                or issue["fixture_origin"] != "UCIE_AUTHORED_FIXED_SYNTHETIC"
                or control["fixture_origin"] != "UCIE_AUTHORED_FIXED_SYNTHETIC"
                or issue["actual_user_environment_inspected"] is not False
                or control["actual_user_environment_inspected"] is not False
                or issue["independent_fix_validated"] is not False
                or control["independent_fix_validated"] is not False):
            raise PreviewError("invalid first-party example proof")
        return (
            '<details class="proof" data-proof-kind="synthetic-only">'
            '<summary>예제에서 실제로 비교한 결과</summary>'
            '<p>문제 상황: ' + e(issue["observed_synthetic_result"]) + '</p>'
            '<p>정상 통제 예제: ' + e(control["observed_synthetic_result"]) + '</p>'
            '<p>시험의 한계: ' + e(issue["limitation"]) + '</p>'
            '<p>상태: UCIE가 만든 고정 예제에서만 확인했습니다.'
            ' 실제 사용자 PC나 제품 버전은 시험하지 않았습니다.</p>'
            '</details>'
        )
    capsule = build_from_existing_ucie()
    preview = build_fixed_demo("mcp-prompts")
    if (capsule.case_id != case_id
            or preview["flow_kind"] !=
              "HISTORIC_FIRST_PARTY_MCP_CAPSULE_RELATED_LIBRARY_REVIEW"
            or capsule.independent_qa != "NOT_VERIFIED"
            or capsule.rights != "NOT_APPROVED"
            or capsule.customer_release != "NOT_AUTHORIZED"):
        raise PreviewError("MCP source or review boundary drift")
    # Resolve actual B4 review only through the already-computed fixed case.
    # The returned panel carries only the source-linked summarized rows.
    rows = preview["linked_review_rows"]
    if (type(rows) is not list or len(rows) != 2
            or any(type(row) is not dict for row in rows)):
        raise PreviewError("missing review evidence")
    cards = []
    for row in rows:
        if (row.get("connected_via") !=
              "MCP_TARGET_AND_PIN_ONLY_NOT_SAME_EXPERIMENT"
                or row.get("rights_approved") is not False
                or row.get("export_allowed") is not False
                or row.get("independent_sdk_compatibility_proven") is not False):
            raise PreviewError("unapproved review evidence")
        cards.append(
            '<article class="review-card">'
            '<h3>개정 후보 (검토 중)</h3>'
            '<p>자산 ID: ' + e(row["review_package_id"]) + '</p>'
            '<p>후보 SHA: <code>' + e(row["package_sha256"]) + '</code></p>'
            '<p>판정: ' + e(row["review_status"]) + '</p>'
            '<p>다음 검토: ' + e(row["next_test_kind"]) + '</p>'
            '<p>고객 사용·배포 불가, 실제 SDK 독립시험 미확인</p>'
            '</article>'
        )
    return (
        '<details class="proof" data-proof-kind="historic-sdk">'
        '<summary>왜 이렇게 안내하나요? · 공식 근거와 시험 확인</summary>'
        '<p>공식 공개 변경: <a href="' + e(capsule.official_source_url) +
        '" rel="noopener noreferrer">MCP SDK 변경 기록</a></p>'
        '<p>공식 기술 규격: <a href="' + e(capsule.official_spec_url) +
        '" rel="noopener noreferrer">MCP 오류 처리 규격</a></p>'
        '<p>기존 UCIE 시험: <a href="' + e(capsule.first_party_sdk_ci_url) +
        '" rel="noopener noreferrer">과거 첫-party CI 확인</a></p>'
        '<p>검토 대상 SDK 커밋: <code>' + e(capsule.fixed_commit) + '</code></p>'
        '<p>SkillBook: ' + e(capsule.skillbook_id) + '</p>'
        '<p>시험 범위: 기존 메모리 내 제한 조건의 역사적 관측입니다.'
        ' 현재 SDK, 실제 고객 PC, 다른 전송 방식은 재검증하지 않았습니다.</p>'
        '<p>독립 QA: 미확인 · 사용권: 미승인 · 고객 배포: 불가</p>'
        '</details>'
        '<section aria-label="가상도서관 개정 후보 비교" '
        'data-review-comparison="review-only">'
        '<h2>가상도서관에서 검토 중인 개정 후보</h2>'
        '<p>아래 후보는 위 과거 SDK 시험과 같은 시험이 아닙니다.'
        ' 원본 근거를 참조해 새로 만든 UCIE 합성시험 검토 자료입니다.</p>'
        + ''.join(cards) + '</section>'
    )


def build_fixed_revision_impact_study() -> dict:
    """Real existing B3 dependency algorithm on three UCIE-authored cases.

    Candidate digests are deliberately FAKE hypotheticals, not observed
    upstream updates. Only bounded test *proposals*; no test scheduling.
    """
    from .ucie_v2_revision_impact_v01 import (
        PINS, ASSETS, assess_revision_impacts, SCHEMA as B3_SCHEMA,
        MCP_ASSET, MCP_SKILLBOOK, GIT_BOOK, PRINCIPLE,
    )
    cases = (
        ("mcp-change-hypothesis", "repo:modelcontextprotocol/python-sdk", True),
        ("git-change-hypothesis", "doc:git/git", True),
        ("git-original-unchanged", "doc:git/git", False),
    )
    records = []
    for scenario, sid, changed in cases:
        pinned = PINS[sid]
        hypothetical = ("a" if pinned[0] != "a" else "b") * len(pinned)
        report = assess_revision_impacts(({
            "source_id": sid, "previous_pin": pinned,
            "candidate_pin": hypothetical if changed else pinned,
        },))
        if (report.get("schema") != B3_SCHEMA
                or report.get("candidate_pin_independently_authenticated") is not False
                or report.get("tests_executed") is not False
                or report.get("independent_qa_verified") is not False
                or report.get("automatic_scheduling") is not False
                or report.get("customer_release_authorized") is not False
                or report.get("network_requests") != 0
                or report.get("operating_database_writes") != 0
                or report.get("graph_scope") != "FIRST_FIVE_PINNED_ASSETS_ONLY"):
            raise PreviewError("revision proposal cannot claim real upstream change")
        impacted = report["affected_assets"]
        expected = ([MCP_ASSET, MCP_SKILLBOOK] if scenario ==
                    "mcp-change-hypothesis" else [GIT_BOOK, PRINCIPLE]
                    if scenario == "git-change-hypothesis" else [])
        tests = sorted({test for asset in expected for test in ASSETS[asset]["tests"]})
        if (impacted != sorted(expected)
                or report["proposed_test_files"] != tests
                or not set(impacted).issubset(ASSETS)):
            raise PreviewError("affected-only algorithm drift")
        records.append({
            "scenario": scenario,
            "approved_source_id": sid,
            "pinned_original_sha256": pinned,
            "candidate_is_hypothetical_only": changed,
            "changed_in_hypothesis": changed,
            "affected_asset_ids": impacted,
            "unaffected_asset_ids": report["unaffected_assets"],
            "proposed_test_names_not_executed": tests,
            "candidate_pin_independently_authenticated": False,
            "actual_retest_executed": False,
            "automatic_scheduling": False,
        })
    return {
        "schema": "UCIE_V2_LOCAL_B3_FIXED_IMPACT_STUDY_V01",
        "records": records,
        "actual_public_changes_observed": False,
        "source_network_requests": 0,
        "operating_database_writes": 0,
        "customer_release_authorized": False,
    }


def render_fixed_revision_impact_panel() -> str:
    """Explain B3 affected-only review using validated first-party algorithm."""
    study = build_fixed_revision_impact_study()
    if (study["actual_public_changes_observed"] is not False
            or study["source_network_requests"] != 0
            or study["customer_release_authorized"] is not False
            or study["operating_database_writes"] != 0
            or len(study["records"]) != 3):
        raise PreviewError("unreviewed source impact study")
    title = {
        "mcp-change-hypothesis": "MCP SDK 변경을 가정했을 때",
        "git-change-hypothesis": "Git 문서 변경을 가정했을 때",
        "git-original-unchanged": "Git 문서가 그대로일 때",
    }
    e = lambda s: escape(str(s), quote=True)
    panels = []
    for r in study["records"]:
        if (r["scenario"] not in title
                or r["candidate_pin_independently_authenticated"] is not False
                or r["actual_retest_executed"] is not False
                or r["automatic_scheduling"] is not False):
            raise PreviewError("B3 proposal reviewed as executed")
        def li(seq):
            return "<ul>" + "".join("<li><code>" + e(x) +
                                     "</code></li>" for x in seq) + "</ul>"
        panels.append(
            '<article class="impact-case">'
            '<h3>' + title[r["scenario"]] + '</h3>'
            '<p>기존 출처: <code>' + e(r["approved_source_id"]) + '</code></p>'
            '<p>영향받는 기술 자산: ' + str(len(r["affected_asset_ids"])) + '개</p>'
            + li(r["affected_asset_ids"]) +
            '<p>재시험을 제안한 파일: ' +
            str(len(r["proposed_test_names_not_executed"])) + '개</p>'
            + li(r["proposed_test_names_not_executed"]) +
            '<p>실제 공식 변경을 확인한 결과가 아니며 재시험을 실행하지 않았습니다.</p>'
            '</article>'
        )
    return (
        '<section class="impact-review" id="source-revision-study" '
        'aria-labelledby="revision-title">'
        '<h2 id="revision-title">공식 자료가 바뀌면 무엇을 다시 확인할까요?</h2>'
        '<p><strong>가정 실험:</strong> UCIE가 승인된 두 기술 출처의 변경을 '
        '가정하여 기존 의존성 그래프로 영향받는 자료와 시험을 추려 봅니다. '
        '원본이 실제 바뀌었는지는 조회하지 않았습니다.</p>'
        + "".join(panels) +
        '<p>범위: UCIE에 연결된 5개 고정 자산만 해당 · '
        '자동 시험/일정 등록 없음 · 고객 배포 미승인</p>'
        '</section>'
    )


def _render_integrated_revision_lifecycle() -> str:
    """One original B1->B3->B4 decision shown in the actual offline Local view.

    Import inside the entrypoint: the lifecycle recomputes the original B4
    evidence through this preview module; no new route or circular import at
    module load.
    """
    from .ucie_v2_revision_lifecycle_workflow_v01 import (
        build_revision_lifecycle, render_revision_lifecycle,
        render_owner_acceptance_checklist,
    )
    return (render_revision_lifecycle(build_revision_lifecycle()) +
            render_owner_acceptance_checklist())


def render_all_cases_page() -> str:
    """One offline accessible page that compares all four fixed cases.

    No search endpoint, dynamic input, client-side code, network request,
    filesystem inspection or changes to the existing owner Local V04.
    """
    require_local_work("LOCAL_APP")
    navigation = ''.join(
        '<li><a href="#case-' + escape(case, quote=True) + '">' +
        escape(case, quote=True) + '</a></li>' for case in EXAMPLE_IDS
    )
    panels = []
    for case in EXAMPLE_IDS:
        rendered = build_fixed_demo(case)
        if rendered["customer_distribution_authorized"] is not False:
            raise PreviewError("unexpected approval state")
        panels.append(
            '<section class="case-panel" id="case-' +
            escape(case, quote=True) + '">'
            '<h2>대표 상황: ' + escape(case, quote=True) + '</h2>'
            + rendered["preview_html"]
            + render_evidence_details(case) + '</section>'
        )
    return (
        '<!doctype html><html lang="ko"><head>'
        '<meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width,initial-scale=1">'
        '<title>UCIE V2 — 근거 연결 비교 미리보기</title>'
        '<style>body{font:16px/1.7 system-ui,sans-serif;'
        'max-width:800px;margin:auto;padding:18px;color:#172a43;'
        'background:#f8fafc}header,.case-panel,footer{background:#fff;'
        'padding:18px;margin:14px 0;border-radius:12px}'
        'section{padding:10px 0;border-bottom:1px solid #d8e1e8}'
        'h1{font-size:1.5rem}h2{font-size:1.15rem}'
        'h3{font-size:1rem}nav ul{display:flex;gap:12px;flex-wrap:wrap}'
        'details{padding:12px;background:#f1f5f9;margin:12px 0}'
        'p,code{overflow-wrap:anywhere}a:focus-visible,summary:focus-visible'
        '{outline:3px solid #2563eb;outline-offset:3px}'
        '@media(max-width:400px){body{padding:8px}'
        '.case-panel,header,footer{padding:12px}}</style></head>'
        '<body><header><h1>UCIE V2 — 알려진 문제와 기술 근거</h1>'
        '<p>네 가지 고정된 사례입니다. 실제 PC 자동 진단이나'
        ' 자동 수정 기능이 아닙니다.</p>'
        '<nav aria-label="대표 문제 선택"><ul>' + navigation +
        '</ul></nav></header><main>' + ''.join(panels) +
        render_fixed_revision_impact_panel() +
        _render_integrated_revision_lifecycle() + '</main>'
        '<footer>검토용 실행 화면 · 독립 검증과 권리 검토 전 배포 금지 ·'
        ' 기존 V04 서비스 미변경</footer></body></html>'
    )


def render_fixed_demo_page(case_id: str) -> str:
    """Make a self-contained accessible HTML document; no V04 modifications."""
    preview = build_fixed_demo(case_id)
    if preview["rendered_html_sha256"] != sha256(
            preview["preview_html"].encode("utf-8")).hexdigest():
        raise PreviewError("render receipt mismatch")
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        '<title>UCIE V2 — 읽기 전용 첫 사용자 검토</title>'
        '<style>body{font:16px/1.7 system-ui,sans-serif;'
        'max-width:760px;margin:0 auto;padding:22px;background:#f8fafc;'
        'color:#172a43}header,main,footer{background:white;'
        'padding:20px;border-radius:14px;margin:12px 0}'
        'section{padding:15px 0;border-bottom:1px solid #d8e1e8}'
        'h1{font-size:1.55rem}h2{font-size:1.16rem}'
        'details{padding:12px;background:#f1f5f9;border-radius:9px}'
        'p{overflow-wrap:anywhere}summary{cursor:pointer}</style>'
        '</head><body><header><h1>UCIE V2 첫 사용자 미리보기</h1>'
        '<p>고정 공개 예제: ' + escape(case_id, quote=True) + '</p>'
        '<p>실제 PC를 분석하거나 코드를 수정하지 않습니다.</p></header>'
        + preview["preview_html"] +
        '<footer><p>개발 검토용 · 실제 수정/버전/권리 검증 미완료 · '
        '배포 불가 · 원본 V04 미변경</p></footer></body></html>'
    )


def main(argv: list[str] | None = None) -> int:
    """CLI writes only generated HTML to stdout; no automatic file creation."""
    args = sys.argv[1:] if argv is None else argv
    if (type(args) is not list or len(args) != 2
            or args[0] != "--case"
            or args[1] not in (*EXAMPLE_IDS, "all")):
        print("UCIE_LOCAL_DEMO_USAGE: --case <predefined-safe-case-id>",
              file=sys.stderr)
        return 2
    try:
        output = (render_all_cases_page() if args[1] == "all"
                  else render_fixed_demo_page(args[1]))
    except (ValueError, KeyError, TypeError):
        print("UCIE_LOCAL_DEMO_HOLD: source evidence unavailable",
              file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
