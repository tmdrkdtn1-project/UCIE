"""UCIE V2 G0/G1: source-bound first-use links and actual synthetic results.

Review-only HTML fragment assembled from existing UCIE V04 GET routes, the
pre-existing three-task/4-case models, B1 Capsule, B3 no-change review and
B4 source-bound hypothesis. No V04 handler changes, new endpoint, customer
input, I/O, network, DB write, source collection or auto-promotion.
"""
from __future__ import annotations

from html import escape
from urllib.parse import quote

SCHEMA = "UCIE_V2_FIRST_USE_EXISTING_ACTION_JOIN_V01"
STATUS = "REVIEW_ONLY_EXISTING_OWNER_LOCAL_ROUTES_NOT_DEPLOYED"
FLOW_HREFS = {
    "solve": "/local/ask",
    "try": "/local/engine?purpose=SKILL_TEST_AUTOMATION",
    "learn": "/local/library?q=Git",
}
MCP_ROUTES = {
    "guide": "/local/guide/mcp-prompts",
    "library": "/local/library?q=MCP",
    "evolution": "/local/evolution?q=MCP",
    "example": "/local/engine?purpose=MCP_PROMPTS_CONTRACT",
}
MCP_CASE_ID = "mcp-prompts"
EXPECTED_CODES = {
    "mcp-prompts": ("CONTRACT_VIOLATION", "CONTRACT_MATCH"),
    "python-env": ("INTERPRETER_MISMATCH", "INTERPRETER_PATHS_MATCH"),
    "powershell-command": ("ALIAS_SHADOWS_COMMAND", "EXPECTED_CMDLET_CHOSEN"),
    "git-repository": ("OUTSIDE_WORKTREE", "INSIDE_WORKTREE"),
}
MCP_CAPSULE = "UCIE-CAPSULE-MCP-PROMPTS-GET-20261126-01"


class FirstUseJoinError(ValueError):
    """Fail closed on source, route, capsule, synthetic or rights drift."""


def _known_route(href: str) -> str:
    from .local_b2_connected_workbench_v01 import PUBLIC_QUERIES
    cases = frozenset(EXPECTED_CODES)
    allowed = {"/local/solve", *FLOW_HREFS.values(), *MCP_ROUTES.values()}
    for case in cases:
        allowed.add("/local/solve?case=" + case)
        for scenario in ("issue", "control"):
            allowed.add("/local/engine?purpose=B2_CONNECTED_TRIAGE&case=" +
                        case + "&scenario=" + scenario)
        allowed.add("/local/library?q=" + quote(PUBLIC_QUERIES[case], safe=""))
    if type(href) is not str or href not in allowed:
        raise FirstUseJoinError("unreviewed or unsafe local action")
    return href


def _link(href: str, label: str) -> str:
    if type(label) is not str or not label or len(label) > 110:
        raise FirstUseJoinError("invalid source-owned action label")
    return ('<a class="review-action" href="' +
            escape(_known_route(href), quote=True) + '">' +
            escape(label, quote=True) + '</a>')


def build_existing_action_join(proof: dict) -> dict:
    from .local_first_use_plain_v01 import START_TASKS, FIXED_ROUTES
    from .local_error_actionable_workflow_v01 import (
        CASE_IDS, SCHEMA as CASE_SCHEMA, STATUS as CASE_STATUS, get_case,
    )
    from .local_b2_connected_workbench_v01 import (
        SCHEMA as TRIAL_SCHEMA, STATUS as TRIAL_STATUS, evaluate_case,
        PUBLIC_QUERIES,
    )
    from .ucie_v2_capsule_v01 import (
        SCHEMA as CAPSULE_SCHEMA, CASE_ID, CAPSULE_ID, SKILLBOOK_ID,
        PR as OFFICIAL_PR,
    )
    from .ucie_v2_revision_impact_v01 import assess_revision_impacts
    from .ucie_v2_generalization_transfer_v01 import build_hypothesis
    from .mcp_prompts_guide_v01 import (
        build_readonly_guide, SCHEMA as GUIDE_SCHEMA, STATUS as GUIDE_STATUS,
    )
    if (type(proof) is not dict or proof.get("schema") != CAPSULE_SCHEMA
            or proof.get("case_id") != CASE_ID
            or proof.get("capsule_id") != CAPSULE_ID
            or proof.get("decision") != "HOLD"
            or proof.get("applicability") != "UNKNOWN_NO_PROOF"
            or proof.get("rights") != "NOT_APPROVED"
            or proof.get("independent_qa") != "NOT_VERIFIED"
            or proof.get("customer_release") != "NOT_AUTHORIZED"
            or proof.get("customer_pc_tested") is not False
            or proof.get("sdk_reexecuted_now") is not False
            or proof.get("auto_promoted") is not False
            or proof.get("actual_code_repaired") is not False
            or proof.get("skillbook_id") != SKILLBOOK_ID
            or proof.get("official_source_url") != OFFICIAL_PR
            or proof.get("revision_status") !=
               "HISTORIC_PIN_REVIEWED_FRESH_REVALIDATION_PENDING"):
        raise FirstUseJoinError("B1 truth/rights/ID contract drift")
    if (type(START_TASKS) is not tuple or len(START_TASKS) != 3
            or set(CASE_IDS) != set(EXPECTED_CODES)
            or set(PUBLIC_QUERIES) != set(EXPECTED_CODES)
            or FIXED_ROUTES != frozenset(FLOW_HREFS.values())):
        raise FirstUseJoinError("existing first-use/triage contract drift")
    flows = {}
    for row in START_TASKS:
        if (type(row) is not tuple or len(row) != 6
                or row[0] not in FLOW_HREFS
                or row[0] in flows
                or row[4] != FLOW_HREFS[row[0]]
                or any(type(value) is not str or not value for value in row)):
            raise FirstUseJoinError("existing Local V04 first-use route drift")
        flows[row[0]] = {"href": _known_route(row[4]), "label": row[3]}
    if set(flows) != set(FLOW_HREFS):
        raise FirstUseJoinError("missing first-use choice")

    cases = {}
    for case_id in CASE_IDS:
        guidance = get_case(case_id)
        if (guidance.get("schema") != CASE_SCHEMA
                or guidance.get("status") != CASE_STATUS
                or guidance.get("case_id") != case_id
                or guidance.get("commands_executed") is not False
                or guidance.get("user_logs_or_files_read") is not False
                or guidance.get("independent_fix_validated") is not False
                or guidance.get("customer_distribution_authorized") is not False
                or guidance.get("network_requests") != 0
                or guidance.get("operating_database_writes") != 0
                or guidance.get("library_query") != PUBLIC_QUERIES[case_id]):
            raise FirstUseJoinError("source-owned guidance drift")
        trials = []
        for scenario in ("issue", "control"):
            result = evaluate_case(case_id, scenario)
            if (result.get("schema") != TRIAL_SCHEMA
                    or result.get("status") != TRIAL_STATUS
                    or result.get("case_id") != case_id
                    or result.get("scenario") != scenario
                    or result.get("result_code") !=
                        EXPECTED_CODES[case_id][len(trials)]
                    or result.get("official_source_url") !=
                        guidance["official_url"]
                    or result.get("fixture_origin") !=
                        "UCIE_AUTHORED_FIXED_SYNTHETIC"
                    or result.get("fixture_evaluated") is not True
                    or any(result.get(k) is not False for k in (
                        "actual_user_environment_inspected",
                        "third_party_code_executed",
                        "arbitrary_command_or_path_accepted",
                        "independent_fix_validated", "human_review_approved",
                        "rule_or_skillbook_promoted",
                        "customer_distribution_authorized",
                    ))
                    or result.get("network_requests") != 0
                    or result.get("operating_database_writes") != 0):
                raise FirstUseJoinError("source-owned synthetic trial drift")
            trials.append({
                "status": result["result_code"],
                "observation": result["observed_synthetic_result"],
                "limitation": result["limitation"],
                "href": _known_route(
                    "/local/engine?purpose=B2_CONNECTED_TRIAGE&case=" +
                    case_id + "&scenario=" + scenario),
            })
        cases[case_id] = {
            "case_id": case_id,
            "label": guidance["label"],
            "safe_next": guidance["safe_next"],
            "solve_href": _known_route("/local/solve?case=" + case_id),
            "library_href": _known_route("/local/library?q=" +
                                          quote(PUBLIC_QUERIES[case_id], safe="")),
            "issue": trials[0],
            "control": trials[1],
            "capsule_id": CAPSULE_ID if case_id == MCP_CASE_ID else None,
            "no_other_capsule_claimed": case_id != MCP_CASE_ID,
        }

    guide = build_readonly_guide()
    if (guide.get("schema") != GUIDE_SCHEMA
            or guide.get("status") != GUIDE_STATUS
            or guide.get("skillbook_id") != SKILLBOOK_ID
            or guide.get("export_allowed") is not False
            or guide.get("auto_promoted") is not False
            or guide.get("network_requests") != 0
            or guide.get("operating_database_writes") != 0
            or guide.get("source_evidence", {}).get("pr_url") != OFFICIAL_PR):
        raise FirstUseJoinError("MCP SkillBook draft/source drift")
    revision = assess_revision_impacts(())
    if (revision.get("status") != "NO_LINKED_RETEST_IN_BOUNDED_GRAPH"
            or revision.get("proposed_test_files") != []
            or revision.get("global_asset_coverage_verified") is not False
            or revision.get("tests_executed") is not False
            or revision.get("auto_promoted") is not False):
        raise FirstUseJoinError("B3 review or automatic QA drift")
    principle = build_hypothesis()
    if (principle.get("target_capsule_id") != CAPSULE_ID
            or principle.get("export_allowed") is not False
            or principle.get("model_trained") is not False
            or principle.get("cross_source_model_generalization_verified") is not False):
        raise FirstUseJoinError("B4 original hypothesis/rights drift")
    return {
        "schema": SCHEMA, "status": STATUS,
        "flows": flows, "cases": cases,
        "mcp_guide_href": _known_route(MCP_ROUTES["guide"]),
        "mcp_evolution_href": _known_route(MCP_ROUTES["evolution"]),
        "mcp_example_href": _known_route(MCP_ROUTES["example"]),
        "capsule_id": CAPSULE_ID, "skillbook_id": SKILLBOOK_ID,
        "b4_hypothesis_id": principle["hypothesis_id"],
        "revision_status": proof["revision_status"],
        "revalidation_still_pending": True,
        "actual_new_upstream_revision_authenticated": False,
        "independent_qa": "NOT_VERIFIED", "rights": "NOT_APPROVED",
        "customer_release": "NOT_AUTHORIZED",
        "owner_v04_route_added": False, "real_owner_browser_tested": False,
        "customer_code_read": False, "new_post_created": False,
        "network_requests": 0, "operating_database_writes": 0,
    }


def render_existing_action_sections(proof: dict) -> str:
    """Render fixed URLs and UCIE-owned test results, never customer input."""
    model = build_existing_action_join(proof)
    native_links = "".join(
        _link(model["flows"][key]["href"], model["flows"][key]["label"])
        for key in ("solve", "try", "learn")
    )
    parts = [
        '<nav id="direct-start-actions" aria-label="기존 UCIE 기능 바로가기">'
        '<p>선택 화면을 사용할 수 없어도 기존 기능을 바로 열 수 있습니다.'
        ' 다만 UCIE 소유자 로컬 서버에서 제공되는 경우에만 연결됩니다.</p>'
        + native_links + '</nav>',
        '<div id="existing-actions" hidden aria-live="polite" '
        'data-ucie-join="review-only">',
        '<p id="route-scope" class="subtle">기존 UCIE 로컬 서버가 같은 주소에서'
        ' 화면을 제공할 때만 아래 링크가 실제 서비스로 연결됩니다. '
        '별도 HTML 파일에서는 이동하지 않습니다.</p>',
    ]
    for key in ("solve", "try", "learn"):
        flow = model["flows"][key]
        parts.append(
            '<div data-route-flow="' + key + '" hidden>'
            + _link(flow["href"], flow["label"]))
        if key == "solve":
            parts.append(_link("/local/solve", "네 가지 대표 상황에서 고르기"))
        elif key == "try":
            parts.append(_link(model["mcp_example_href"],
                               "UCIE 자체 MCP 입력 오류 계약 예제"))
        else:
            parts.append(_link(model["mcp_guide_href"],
                               "MCP 기술 가이드 003 미승인 초안 읽기"))
        parts.append("</div>")
    for case_id in EXPECTED_CODES:
        row = model["cases"][case_id]
        parts.append(
            '<section data-route-case="' + escape(case_id) + '" hidden>'
            '<h4>' + escape(row["label"]) + ' · 기존 UCIE 예제</h4>'
            '<p>합성 입력에 대해서만 실행된 결과입니다. '
            '사용하시는 PC나 개인 코드는 확인하지 않았습니다.</p>'
            '<dl><dt>오류 예제</dt><dd>' +
            escape(row["issue"]["observation"]) + ' ('
            + escape(row["issue"]["status"]) +
            ')</dd><dt>대조 예제</dt><dd>' +
            escape(row["control"]["observation"]) + ' ('
            + escape(row["control"]["status"]) +
            ')</dd></dl><p>먼저 확인할 일: ' +
            escape(row["safe_next"]) + '</p>'
        )
        parts.append(_link(row["solve_href"], "기존 안내에서 확인 순서 보기"))
        parts.append(_link(row["issue"]["href"], "UCIE 오류 합성 예제 실행"))
        parts.append(_link(row["control"]["href"], "UCIE 대조 합성 예제 실행"))
        parts.append(_link(row["library_href"], "관련 공개 기술 자료 보기"))
        if case_id == MCP_CASE_ID:
            parts.append(
                '<p>기술 확인 기록: <code>' +
                escape(model["capsule_id"]) + '</code></p>'
                '<p>개정 상태: 이전 고정 시험 근거는 있지만 '
                '최신 공식 원본 재확인은 아직 필요합니다.</p>'
                '<p>가상도서관의 제한형 원리 가설: <code>' +
                escape(model["b4_hypothesis_id"]) +
                '</code> · 다른 환경까지 자동 적용 가능하다는 뜻이 아닙니다.</p>'
            )
            parts.append(_link(model["mcp_guide_href"],
                               "근거와 기술서적 003 읽기"))
            parts.append(_link(model["mcp_evolution_href"],
                               "공개 기술의 변경 정보 살펴보기"))
        else:
            parts.append('<p>이 항목의 B1 기술 확인 기록은 현재 연결되지 '
                         '않았습니다. MCP의 증거를 잘못 적용하지 않습니다.</p>')
        parts.append("</section>")
    parts.append(
        '<div data-route-case="unmatched" hidden>'
        '<p>지원하는 대표 상황 외에는 원인이나 수정 성공을 추측하지 않습니다.</p>' +
        _link("/local/solve", "지원하는 네 가지 상황 보기") + '</div>'
        "</div>"
    )
    return "".join(parts)
