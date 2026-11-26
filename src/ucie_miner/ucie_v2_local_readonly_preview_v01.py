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
    return {
        **receipt, "content_sha256": _hash(receipt),
        "preview_html": rendered,
    }


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
            or args[0] != "--case" or args[1] not in EXAMPLES):
        print("UCIE_LOCAL_DEMO_USAGE: --case <predefined-safe-case-id>",
              file=sys.stderr)
        return 2
    try:
        output = render_fixed_demo_page(args[1])
    except (ValueError, KeyError, TypeError):
        print("UCIE_LOCAL_DEMO_HOLD: source evidence unavailable",
              file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
