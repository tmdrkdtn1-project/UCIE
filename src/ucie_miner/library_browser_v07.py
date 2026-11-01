"""UCIE V0.7: one integrated read-only audit dashboard over V0.5 browser.

Adds cross-candidate proof-triage and inert prevention review guides without
changing the existing V0.5 search, compare, selection and six review gates.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import HTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from . import library_browser_v05 as v05
from .library_browser_v02 import _head, _foot, _t
from .library_audit_v07 import (
    SCHEMA as AUDIT_SCHEMA, STATUS, INCOMPLETE, CONFLICT,
    AuditError, audit_existing_public_library, summarize_audit,
)
from .library_review_records_v05 import ClaimError
from .library_explore import ExploreError
from .public_discovery import DiscoveryError

SCHEMA = "UCIE_LOCAL_PUBLIC_LIBRARY_AUDIT_BROWSER_V07"
HEX = re.compile(r"[0-9a-f]{64}\Z")
CARDS = re.compile(r'<a href="/item/([0-9a-f]{64})">상세보기</a>')
STYLE = """<style>
.audit-nav{margin-top:12px;padding:12px 0}
.audit-box{border:1px solid #dce5f1;border-radius:12px;background:white;padding:18px}
.audit-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:12px;margin:18px 0}
.audit-num{font-size:23px;font-weight:750}
.audit-note{background:#eaf1fa;border-left:3px solid #4076b3;padding:13px;margin:20px 0}
.audit-table{overflow-x:auto;margin:20px 0}
.audit-table table{width:100%;border-collapse:collapse;background:white}
.audit-table th,.audit-table td{padding:10px;border:1px solid #dce5f1;text-align:left;overflow-wrap:anywhere;font-size:13px}
.audit-gates{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin:20px 0}
</style>"""


def _brand(html: str) -> str:
    # Normalize the full inherited v0.2-v0.5 chain before its send hooks
    # run, so the owner-facing footer accurately reports the V0.7 schema.
    for previous in ("V0.2 ·", "V0.3 ·", "V0.4 ·", "V0.5 ·"):
        html = html.replace(previous, "V0.7 ·")
    for old in (
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02",
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V03",
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V04",
            v05.SCHEMA):
        html = html.replace(old, SCHEMA)
    if STYLE not in html:
        html = html.replace("</head>", STYLE + "</head>")
    return html


def _chrome(html: str) -> str:
    html = _brand(html)
    if 'href="/audit"' not in html:
        html = html.replace(
            "</header>", '</header><nav class="audit-nav">'
            '<a href="/audit">전체 공개 근거 검증·감사 현황</a>'
            '</nav>', 1)
    html = CARDS.sub(
        lambda match: match.group(0) + ' · <a href="/audit/item/'
        + match.group(1) + '">검증 상태·오류 예방 검토 가이드</a>', html)
    return html


def _ensure(report: dict):
    if (type(report) is not dict
            or report.get("schema") != AUDIT_SCHEMA
            or report.get("status") not in (STATUS, INCOMPLETE, CONFLICT)
            or report.get("auto_promoted") is not False
            or report.get("approved_candidates") != 0
            or report.get("exportable_rules") != 0
            or report.get("operating_database_writes") != 0
            or type(report.get("candidates")) is not list
            or len(report["candidates"]) > 1000):
        raise AuditError("untrusted public audit data")


def render_audit_dashboard(report: dict) -> str:
    _ensure(report)
    summary = summarize_audit(report, limit=10)
    counts = (
        ("원장에 결속된 공개 후보", summary["source_linked_candidates"]),
        ("무결성 검사된 접수 영수증", summary["claim_receipts_integrity_checked"]),
        ("접수 근거가 있는 후보", summary["candidate_count_with_claims"]),
        ("출처 미연결 접수", summary["orphaned_claim_count"]),
        ("원장 SHA 불일치", summary["source_sha_conflicts"]),
        ("동일 근거 주장 충돌", summary["conflicting_claim_groups"]),
        ("검증 완료 규칙", summary["approved_candidates"]),
        ("자동 배포 가능 규칙", summary["exportable_rules"]),
    )
    html = [
        _head("UCIE 공개 근거 감사·검토 현황"),
        '<p><a href="/">검색으로 돌아가기</a></p>',
        '<p class="audit-note">이 화면은 제출된 공개 근거의 원장 결속과 '
        '형식·중복·충돌을 감사합니다. 외부 문서 내용, 실제 회귀시험 결과, '
        '지원 버전, 라이선스 적법성은 확인하지 않았습니다. '
        '수집된 주장은 규칙 승인·자동학습에 반영되지 않습니다.</p>',
        '<p><strong>원장 검사 상태:</strong> ' + _t(summary["status"]) + '</p>',
        '<section class="audit-grid">',
    ]
    for label, value in counts:
        if type(value) is not int or not 0 <= value <= 1000:
            raise AuditError("invalid audit count")
        html.append('<article class="audit-box"><div class="audit-num">'
                    + str(value) + '</div><p>' + _t(label) + '</p></article>')
    html.append('</section>')
    for heading, key in (
        ("기술 분야별 공개 후보", "per_domain"),
        ("승인된 공개 저장소별 후보", "per_source"),
        ("검증 관문별 제출 건수", "per_gate_claim_counts"),
        ("공개 자료 인용 형식", "citation_shape_counts"),
        ("추가 확인 필요 유형", "evidence_review_class_counts"),
    ):
        lines = summary[key]
        html.append('<section class="audit-box"><h2>' + _t(heading)
                    + '</h2><div class="audit-table"><table><tbody>')
        for name, value in sorted(lines.items()):
            if type(name) is not str or type(value) is not int:
                raise AuditError("invalid audit facet")
            html.append("<tr><th>" + _t(name, 110) + "</th><td>"
                        + str(value) + "</td></tr>")
        if not lines:
            html.append('<tr><td colspan="2">접수된 자료 없음</td></tr>')
        html.append("</tbody></table></div></section>")
    html.append('<section class="audit-box"><h2>우선 검토 대상 · 미검증</h2>')
    queue = summary["review_queue"]
    if not queue:
        html.append('<p>접수된 후보가 없습니다. 현재 원장 후보는 모두 '
                    '미검증 상태입니다.</p>')
    for item in queue:
        identity = item["item_id"]
        if HEX.fullmatch(identity) is None:
            raise AuditError("invalid review item identity")
        html.append('<p><a href="/audit/item/' + identity + '">'
                    + _t(item["source_id"]) + " · "
                    + _t(item["purpose_code"]) + "</a> · 제출 "
                    + str(item["claim_count"]) + "건 · 충돌 "
                    + str(item["conflicting_claim_groups"]) + "건</p>")
    html.append('</section><p class="subtitle">감사 요약 SHA-256: <code>'
                + summary["report_sha256"] + '</code> · 출처 기록의 서명 아님'
                '</p>')
    html.append(_foot())
    return _chrome("".join(html))


def render_audit_candidate(report: dict, item_id: str) -> str:
    _ensure(report)
    if type(item_id) is not str or HEX.fullmatch(item_id) is None:
        raise AuditError("invalid item identity")
    rows = [x for x in report["candidates"] if x["item_id"] == item_id]
    if len(rows) != 1:
        raise AuditError("unknown or ambiguous audited public candidate")
    row = rows[0]
    guide = row["review_guide"]
    if (guide.get("type") != "INERT_UCIE_REVIEW_GUIDE_NOT_RULE"
            or guide.get("generated_executable_rule") is not False
            or row.get("owner_approved") is not False
            or row.get("independently_verified") is not False):
        raise AuditError("unsafe executable or approved review draft")
    html = [
        _head("UCIE 후보별 검증 상태·오류 예방 검토"),
        '<p><a href="/audit">전체 감사 현황으로 돌아가기</a> · '
        '<a href="/">검색으로 돌아가기</a></p>',
        '<p class="audit-note">출처 연결이 확인된 공개 후보입니다. '
        '검토 가이드는 UCIE의 사전 정의된 고정 문구이며 실행 가능한 '
        '방지 규칙이나 검증 완료 결과가 아닙니다.</p>',
        '<section class="audit-box"><h2>' + _t(row["purpose_title"])
        + '</h2><p>' + _t(row["purpose_description"]) + '</p>'
        '<p>출처: ' + _t(row["source_id"])
        + '</p><p>후보 SHA-256: <code>' + item_id
        + '</code></p><p>원장 SHA-256: <code>'
        + _t(row["source_sha256"]) + '</code></p>'
        '<p>제출된 근거: ' + str(row["claim_count"])
        + '건 · 서로 충돌하는 주장: ' + str(row["claim_conflicts"])
        + '건</p><p><strong>후보 상태: '
        + _t(row["status"]) + '</strong></p></section>',
        '<h2>검증 관문</h2><div class="audit-gates">',
    ]
    for gate in row["gates"]:
        if gate["status"] not in (
                "NOT_VERIFIED", "SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED"):
            raise AuditError("false proof status in gate")
        html.append('<article class="audit-box"><h3>' + _t(gate["gate"])
                    + '</h3><p>' + _t(gate["status"])
                    + '</p><p>접수된 주장: '
                    + str(gate["received_unverified_claims"])
                    + '건</p><p>다음 확인: ' + _t(gate["next_check"])
                    + '</p></article>')
    html.append('</div><section class="audit-box"><h2>오류 예방 검토 초안</h2>'
                '<p>유형: ' + _t(guide["type"])
                + '</p><p>검토 질문: ' + _t(guide["question"], 260)
                + '</p><p>권장 검토: ' + _t(guide["safe_review"], 260)
                + '</p><p>다음 작업: ' + _t(guide["required_next_check"])
                + '</p><p>적용 버전: UNDETERMINED · 자동 생성 코드 없음 · '
                '독립 재현 미완료 · 승인/배포 불가</p></section>')
    html.append(_foot())
    return _chrome("".join(html))


def make_handler(root: Path, *, auditor=None, explorer=None,
                 comparer=None, reviewer=None, claims_loader=None):
    base = v05.make_handler(
        root, explorer=explorer, comparer=comparer, reviewer=reviewer,
        claims_loader=claims_loader)
    if auditor is None:
        auditor = audit_existing_public_library

    class Handler(base):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            if status == 200 and mime == "text/html; charset=utf-8":
                content = _chrome(content)
            return super().reply(status, content, mime)

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path == "/health" and not parts.query and not parts.fragment:
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY",
                                      "text/plain; charset=utf-8")
                return self.reply(200, json.dumps({
                    "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_READY",
                    "operating_db_writes": 0, "claim_receipt_writes": 0,
                    "scheduler_changes": 0, "auto_promoted": False,
                    "production_approved": False,
                }), "application/json; charset=utf-8")
            if parts.path != "/audit" and not parts.path.startswith("/audit/item/"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY",
                                  "text/plain; charset=utf-8")
            if parts.query or parts.fragment or len(self.path) > 110:
                return self.reply(400, "BOUNDED_AUDIT_ROUTES_ONLY",
                                  "text/plain; charset=utf-8")
            if parts.path.startswith("/audit/item/"):
                identity = parts.path.removeprefix("/audit/item/")
                if HEX.fullmatch(identity) is None:
                    return self.reply(404, "AUDIT_ITEM_NOT_FOUND",
                                      "text/plain; charset=utf-8")
            try:
                report = auditor(root)
                if parts.path == "/audit":
                    html = render_audit_dashboard(report)
                else:
                    if not any(row["item_id"] == identity
                               for row in report["candidates"]):
                        return self.reply(404, "AUDIT_ITEM_NOT_FOUND",
                                          "text/plain; charset=utf-8")
                    html = render_audit_candidate(report, identity)
                return self.reply(200, html)
            except (AuditError, ClaimError, ExploreError,
                    DiscoveryError, ValueError, TypeError, KeyError):
                return self.reply(503, "SOURCE_AUDIT_VALIDATION_FAILED_NO_GO",
                                  "text/plain; charset=utf-8")
            except (sqlite3.DatabaseError, OSError):
                return self.reply(503, "SOURCE_AUDIT_STORAGE_UNAVAILABLE_NO_GO",
                                  "text/plain; charset=utf-8")

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE V0.6+V0.7 source-bound read-only audit browser")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if (root.is_symlink() or root.name.casefold() != "ucie"
            or not root.is_dir() or not 0 <= args.port <= 65535
            or (os.name == "nt" and root.resolve() != Path("D:/UCIE").resolve())):
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED"}))
        return 2
    try:
        with HTTPServer(("127.0.0.1", args.port),
                        make_handler(root)) as server:
            print(json.dumps({
                "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_LISTENING",
                "url": "http://127.0.0.1:" + str(server.server_port) + "/",
                "database_writes": 0, "review_receipt_writes": 0,
                "scheduler_changes": 0, "production_approved": False,
            }), flush=True)
            server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except OSError:
        print(json.dumps({"schema": SCHEMA, "status": "LOCAL_BIND_FAILED_NO_GO"}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
