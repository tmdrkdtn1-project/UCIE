"""UCIE V0.9: explicit-click public identity proof UI over V0.7.

No automatic network calls during search, audit, comparison or GET /health.
Only the exact owner-clicked /public-check/<source-bound sha> makes bounded
anonymous public lookups. Never stores external HTML or activates rules.
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
from urllib.parse import parse_qs, urlencode, urlsplit

from . import library_browser_v07 as v07
from .library_browser_v02 import _head, _foot, _t
from .library_public_proof_v09 import (
    SCHEMA as PROBE_SCHEMA, BatchError, perform_public_probe_batch,
)
from .library_public_probe_v08 import ProbeError
from .library_review_records_v05 import ClaimError
from .library_audit_v07 import AuditError
from .library_explore import ExploreError
from .public_discovery import DiscoveryError, SOURCES, SOURCE_SKILL
from .skill_profiles import PROFILE

SCHEMA = "UCIE_LOCAL_PUBLIC_SOURCE_CHECK_BROWSER_V09"
HEX = re.compile(r"[0-9a-f]{64}\Z")
STYLE = """<style>
.live-source-check{border-left:3px solid #4d78b0;background:#eff4fb;
padding:14px;margin:18px 0}
.probe-claim{background:#fff;border:1px solid #dce5f1;
border-radius:12px;padding:18px;margin:12px 0}
.probe-claim dt{font-size:12px;color:#536984;margin-top:9px}
.probe-claim dd{font-size:14px;margin-left:0;overflow-wrap:anywhere}
</style>"""


def _brand(html: str) -> str:
    text = html
    for previous in ("V0.2 ·", "V0.3 ·", "V0.4 ·",
                     "V0.5 ·", "V0.7 ·", "V0.8 ·"):
        text = text.replace(previous, "V0.9 ·")
    for old in (
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02",
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V03",
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V04",
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V05",
            v07.SCHEMA):
        text = text.replace(old, SCHEMA)
    if STYLE not in text:
        text = text.replace("</head>", STYLE + "</head>")
    return text


def render_public_source_probe(report: dict) -> str:
    if (type(report) is not dict or report.get("schema") != PROBE_SCHEMA
            or report.get("approved_rule_count") != 0
            or report.get("deployed_rule_count") != 0
            or report.get("auto_promoted") is not False
            or report.get("external_source_code_executed") is not False
            or report.get("operating_database_writes") != 0
            or type(report.get("results")) is not list
            or len(report["results"]) != 1):
        raise BatchError("untrusted source proof response")
    result = report["results"][0]
    item_id = result["item_id"]
    if type(item_id) is not str or HEX.fullmatch(item_id) is None:
        raise BatchError("invalid source proof identity")
    metadata = result["source_revision_metadata"]
    if (metadata.get("fix_verified") is not False
            or metadata.get("identity_matched") not in (True, False)):
        raise BatchError("unsafe source metadata classification")
    html = [
        _head("UCIE 공개 원본 대조 결과"),
        '<p><a href="/audit/item/' + item_id + '">'
        '후보별 검토 화면으로 돌아가기</a> · '
        '<a href="/audit">전체 감사 현황</a></p>',
        '<p class="live-source-check">이 화면은 명시적인 요청에 따라 '
        '승인된 공개 GitHub API와 기존 공식 문서 접수 URL을 익명으로 '
        '조회합니다. 공개 병합 SHA 일치나 HTTP 응답 해시 일치는 '
        '오류 수정 성공·지원 버전·라이선스·보안/회귀시험 PASS를 '
        '뜻하지 않습니다.</p>',
        '<section class="probe-claim"><h2>공개 소스 메타데이터</h2>',
        '<dl><dt>승인된 출처</dt><dd>' + _t(result["source_id"]) + '</dd>',
        '<dt>원장 후보 ID</dt><dd><code>' + item_id + '</code></dd>',
        '<dt>공개 원본 대조</dt><dd>' + _t(metadata["status"]) + '</dd>',
        '<dt>현재 메타데이터 확인</dt><dd>'
        + ("조회됨" if metadata["metadata_observed"] else "확인 불가") + '</dd>',
        '<dt>원장 개정 SHA 일치</dt><dd>'
        + ("일치" if metadata["identity_matched"] else "불일치 또는 확인 불가")
        + '</dd><dt>실제 오류 수정 검증</dt><dd>NOT_VERIFIED</dd>'
        '</dl></section>',
        '<section class="probe-claim"><h2>기존 공식 문서 SHA 주장 대조</h2>',
    ]
    docs = result["official_document_checks"]
    if type(docs) is not list or len(docs) > 2:
        raise BatchError("invalid official document check count")
    if not docs:
        html.append('<p>비교 대상인 공식 문서 접수 영수증이 없습니다.</p>')
    for doc in docs:
        if (doc.get("fix_verified") is not False
                or doc.get("claimed_sha_matched") not in (True, False)):
            raise BatchError("unsafe document proof status")
        html.append('<p>응답 바이트 대조 상태: <strong>'
                    + _t(doc["status"]) + '</strong></p>')
        if doc.get("public_content_checked"):
            sha = doc.get("actual_http_body_sha256")
            if type(sha) is not str or HEX.fullmatch(sha) is None:
                raise BatchError("invalid returned public digest")
            html.append('<p>실제 응답 SHA-256: <code>' + sha + '</code></p>')
    guide = result["inert_rule_review_draft"]
    if (guide.get("type") != "REVIEW_ONLY_INERT_PREVENTION_OUTLINE"
            or guide.get("code_generated") is not False
            or guide.get("executable_command") is not None
            or guide.get("signed") is not False):
        raise BatchError("unsafe inferred rule output")
    html += [
        '</section><section class="probe-claim"><h2>오류 예방 규칙 검토 초안</h2>',
        '<p>검토 질문: ' + _t(guide["question"]) + '</p>',
        '<p>다음 검토: ' + _t(guide["next_review"]) + '</p>',
        '<p>안전 검토: ' + _t(guide["safe_review"], 260) + '</p>',
        '<p>적용 버전: UNDETERMINED · 검증 완료 규칙: 0 · '
        '자동 생성 실행 코드: 없음 · 승인/배포 불가</p></section>',
        _foot(),
    ]
    return _brand("".join(html))



AUDIT_LIST_PAGE_SIZE = 20
AUDIT_LIST_MAX_PAGE = 50
AUDIT_LIST_MAX_QUERY = 300
AUDIT_LIST_FILTERS = frozenset(("source", "domain", "page"))
AUDIT_PICKER_STYLE = """<style>
.audit-picker{border:1px solid #cad7e9;background:#f7faff;border-radius:12px;padding:16px;margin:20px 0}
.audit-picker p{margin:8px 0}.audit-picker ul{padding-left:20px}
.audit-list-form{display:flex;gap:10px;flex-wrap:wrap;align-items:end;margin:16px 0}
.audit-list-form label{display:flex;flex-direction:column;gap:5px;font-size:13px}
.audit-list-form select,.audit-list-form button{padding:8px;border:1px solid #c5d3e4;border-radius:7px}
.audit-list-table{overflow-x:auto}.audit-list-table table{width:100%;border-collapse:collapse}
.audit-list-table td,.audit-list-table th{border:1px solid #dce5f1;padding:10px;font-size:13px;text-align:left}
.audit-pagination{display:flex;gap:15px;align-items:center;margin:16px 0}
</style>"""


def _audited_candidates(report: dict) -> list[dict]:
    """All source-linked candidates, including those with zero V0.5 receipts."""
    v07._ensure(report)
    rows = report["candidates"]
    if (report.get("source_linkage_checked") is not True
            or report.get("source_linked_candidates") != len(rows)):
        raise AuditError("incomplete or inconsistent audit source candidates")
    allowed = {"repo:" + repo for repo in SOURCES}
    checked = set()
    buckets = {source: [] for source in sorted(allowed)}
    for row in rows:
        if type(row) is not dict:
            raise AuditError("invalid candidate row")
        identity = row.get("item_id")
        source = row.get("source_id")
        skill = SOURCE_SKILL.get(
            source.removeprefix("repo:") if type(source) is str else None)
        profile = PROFILE.get(skill)
        if (type(identity) is not str or HEX.fullmatch(identity) is None
                or identity in checked or source not in allowed
                or profile is None or row.get("domain") != profile["domain"]
                or row.get("status") not in (
                    "NOT_VERIFIED", "RECEIPT_CONFLICT_REVIEW_REQUIRED_NO_GO")
                or row.get("owner_approved") is not False
                or row.get("independently_verified") is not False
                or type(row.get("claim_count")) is not int
                or row["claim_count"] < 0
                or type(row.get("purpose_code")) is not str
                or type(row.get("purpose_title")) is not str):
            raise AuditError("unsafe or ambiguous source-linked audit row")
        checked.add(identity)
        buckets[source].append(row)
    for source in buckets:
        buckets[source].sort(key=lambda x: (
            x["purpose_code"], x["item_id"]))
    # A blank filter should show representatives from different approved
    # sources rather than hiding small sources beneath hundreds of Python rows.
    result = []
    for offset in range(max((len(v) for v in buckets.values()), default=0)):
        for source in sorted(buckets):
            if offset < len(buckets[source]):
                result.append(buckets[source][offset])
    return result


def _audit_listing_query(query: str) -> tuple[str, str, int]:
    if type(query) is not str or len(query) > AUDIT_LIST_MAX_QUERY:
        raise AuditError("bounded audit browse query required")
    if not query:
        return "", "", 1
    try:
        parsed = parse_qs(
            query, keep_blank_values=True, strict_parsing=True,
            max_num_fields=3, encoding="utf-8", errors="strict")
    except (ValueError, UnicodeError) as exc:
        raise AuditError("invalid audit browse query") from exc
    if (not set(parsed).issubset(AUDIT_LIST_FILTERS)
            or any(len(values) != 1 for values in parsed.values())):
        raise AuditError("unknown or repeated audit browse query field")
    source = parsed.get("source", [""])[0]
    domain = parsed.get("domain", [""])[0]
    number = parsed.get("page", ["1"])[0]
    if (not re.fullmatch(r"[1-9][0-9]?", number)
            or int(number) > AUDIT_LIST_MAX_PAGE
            or len(source) > 72 or len(domain) > 42):
        raise AuditError("invalid bounded audit browse page")
    if source and source not in {"repo:" + x for x in SOURCES}:
        raise AuditError("unsupported audit source filter")
    if domain and domain not in {v["domain"] for v in PROFILE.values()}:
        raise AuditError("unsupported audit domain filter")
    return source, domain, int(number)


def _audit_browse_url(*, source: str = "", domain: str = "",
                      page: int = 1) -> str:
    return "/audit/candidates?" + urlencode(
        {"source": source, "domain": domain, "page": str(page)})


def render_audit_dashboard_with_picker(report: dict) -> str:
    """Place visible candidate choices ABOVE the statistics, even at 0 claims."""
    rows = _audited_candidates(report)
    preview = rows[:5]
    html = [
        '<section class="audit-picker"><h2>공개 후보 선택 · 전체 원장</h2>',
        '<p>접수 영수증이 없어도 원장에 결속된 후보 ',
        str(len(rows)),
        '건을 선택할 수 있습니다. 선택만으로 외부 조회가 발생하지 않습니다.</p>',
        '<p><strong><a href="/audit/candidates">전체 공개 후보 목록 열기 · '
        '출처/기술 분야 필터 및 페이지 이동</a></strong></p>',
        '<ul>',
    ]
    for row in preview:
        html.append(
            '<li><a href="/audit/item/' + row["item_id"] + '">'
            + _t(row["source_id"]) + " · "
            + _t(row["purpose_title"]) + "</a>"
            + ' · NOT_VERIFIED · 접수 ' + str(row["claim_count"]) + '건</li>')
    html.append('</ul></section>')
    existing = v07.render_audit_dashboard(report)
    needle = '<p><a href="/">검색으로 돌아가기</a></p>'
    if needle not in existing:
        raise AuditError("audit dashboard missing expected back-navigation anchor")
    return _brand(existing.replace(needle, needle + "".join(html), 1)
                  .replace("</head>", AUDIT_PICKER_STYLE + "</head>", 1))


def render_audit_candidate_listing(
        report: dict, *, source: str = "", domain: str = "",
        page: int = 1) -> str:
    rows = _audited_candidates(report)
    sources = sorted({"repo:" + x for x in SOURCES})
    domains = sorted({v["domain"] for v in PROFILE.values()})
    if (source not in ("", *sources) or domain not in ("", *domains)
            or type(page) is not int or not 1 <= page <= AUDIT_LIST_MAX_PAGE):
        raise AuditError("unsupported audit list filter")
    filtered = [row for row in rows
                if (not source or row["source_id"] == source)
                and (not domain or row["domain"] == domain)]
    pages = max(1, (len(filtered) + AUDIT_LIST_PAGE_SIZE - 1) // AUDIT_LIST_PAGE_SIZE)
    if page > pages:
        raise AuditError("audit page beyond available source-linked candidates")
    visible = filtered[(page - 1) * AUDIT_LIST_PAGE_SIZE:page * AUDIT_LIST_PAGE_SIZE]
    markup = [
        _head("UCIE 공개 후보 전체 목록"),
        '<p><a href="/audit">전체 감사 현황으로 돌아가기</a></p>',
        '<p class="audit-note">후보 목록은 접수 영수증이 0건이어도 표시합니다. '
        '아래 후보 선택은 원장 검토 화면만 열며, 외부 공개 GitHub 조회는 '
        '다음 화면에서 명시적으로 클릭해야 실행됩니다.</p>',
        '<section class="audit-box"><h2>후보 선택 · ',
        str(len(filtered)), '건 / 전체 ', str(len(rows)), '건</h2>',
        '<form class="audit-list-form" action="/audit/candidates" method="get">',
    ]
    for label, key, choices, current in (
        ("공개 저장소", "source", sources, source),
        ("기술 분야", "domain", domains, domain),
    ):
        markup.append('<label>' + label + '<select name="' + key + '">')
        markup.append('<option value="">전체</option>')
        for choice in choices:
            selected = ' selected' if current == choice else ''
            markup.append('<option value="' + _t(choice, 75) + '"'
                          + selected + '>' + _t(choice) + '</option>')
        markup.append('</select></label>')
    markup.append('<button type="submit">후보 검색</button></form>')
    markup.append('<div class="audit-list-table"><table><thead><tr>'
                  '<th>공개 출처</th><th>검토 유형</th><th>검증 상태</th>'
                  '<th>선택</th></tr></thead><tbody>')
    for row in visible:
        markup.append(
            '<tr><td>' + _t(row["source_id"]) + '</td><td>'
            + _t(row["purpose_title"]) + '</td><td>'
            + _t(row["status"]) + '</td><td><a href="/audit/item/'
            + row["item_id"] + '">후보 검토하기</a></td></tr>')
    if not visible:
        markup.append('<tr><td colspan="4">조건에 맞는 후보가 없습니다.</td></tr>')
    markup.append('</tbody></table></div><nav class="audit-pagination">')
    if page > 1:
        markup.append('<a href="' + _t(_audit_browse_url(
            source=source, domain=domain, page=page - 1), 250)
            + '">이전 페이지</a>')
    markup.append('<span>페이지 ' + str(page) + ' / ' + str(pages) + '</span>')
    if page < pages:
        markup.append('<a href="' + _t(_audit_browse_url(
            source=source, domain=domain, page=page + 1), 250)
            + '">다음 페이지</a>')
    markup.append('</nav></section>')
    markup.append(_foot())
    return _brand("".join(markup).replace("</head>",
        AUDIT_PICKER_STYLE + "</head>", 1))


def make_handler(root: Path, *, auditor=None, public_prober=None,
                 explorer=None, comparer=None, reviewer=None,
                 claims_loader=None):
    base = v07.make_handler(
        root, auditor=auditor, explorer=explorer,
        comparer=comparer, reviewer=reviewer, claims_loader=claims_loader)
    if public_prober is None:
        public_prober = perform_public_probe_batch
    audit_reader = v07.audit_existing_public_library if auditor is None else auditor

    class Handler(base):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            if status == 200 and mime == "text/html; charset=utf-8":
                content = _brand(content)
                parts = urlsplit(self.path)
                if parts.path.startswith("/audit/item/"):
                    identity = parts.path.removeprefix("/audit/item/")
                    if HEX.fullmatch(identity) is not None:
                        link = (
                            '<section class="live-source-check">'
                            '<p>외부 공개 원본을 확인하려면 아래 링크를 '
                            '직접 클릭하세요. 클릭 시 승인된 GitHub 공개 '
                            '메타데이터 및 접수된 공식 문서만 읽습니다.</p>'
                            '<p><a href="/public-check/' + identity
                            + '">공개 원본 SHA 대조 실행 (명시적 조회)</a></p>'
                            '</section>')
                        content = content.replace("</main>", link + "</main>")
            return super().reply(status, content, mime)

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path in ("/audit", "/audit/candidates"):
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY",
                                      "text/plain; charset=utf-8")
                if parts.fragment or len(self.path) > AUDIT_LIST_MAX_QUERY + 30:
                    return self.reply(400, "INVALID_AUDIT_NAVIGATION",
                                      "text/plain; charset=utf-8")
                if parts.path == "/audit" and parts.query:
                    return self.reply(400, "INVALID_AUDIT_NAVIGATION",
                                      "text/plain; charset=utf-8")
                try:
                    source, domain, page = _audit_listing_query(
                        parts.query if parts.path == "/audit/candidates" else "")
                except AuditError:
                    return self.reply(400, "INVALID_AUDIT_NAVIGATION",
                                      "text/plain; charset=utf-8")
                try:
                    report = audit_reader(root)
                    if parts.path == "/audit":
                        html = render_audit_dashboard_with_picker(report)
                    else:
                        html = render_audit_candidate_listing(
                            report, source=source, domain=domain, page=page)
                    return self.reply(200, html)
                except (AuditError, ClaimError, ExploreError,
                        DiscoveryError, ValueError, TypeError, KeyError):
                    return self.reply(503, "SOURCE_AUDIT_VALIDATION_FAILED_NO_GO",
                                      "text/plain; charset=utf-8")
                except (sqlite3.DatabaseError, OSError):
                    return self.reply(503, "SOURCE_AUDIT_STORAGE_UNAVAILABLE_NO_GO",
                                      "text/plain; charset=utf-8")
            if parts.path == "/health" and not parts.query and not parts.fragment:
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY",
                                      "text/plain; charset=utf-8")
                return self.reply(200, json.dumps({
                    "schema": SCHEMA,
                    "status": "LOCAL_READ_ONLY_UI_READY",
                    "external_requests_without_explicit_click": 0,
                    "operating_db_writes": 0,
                    "review_receipt_writes": 0,
                    "scheduler_changes": 0,
                    "auto_promoted": False,
                }), "application/json; charset=utf-8")
            if not parts.path.startswith("/public-check/"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY",
                                  "text/plain; charset=utf-8")
            if parts.query or parts.fragment or len(self.path) > 105:
                return self.reply(400, "EXACT_PUBLIC_SOURCE_REQUEST_ONLY",
                                  "text/plain; charset=utf-8")
            item_id = parts.path.removeprefix("/public-check/")
            if HEX.fullmatch(item_id) is None:
                return self.reply(404, "PUBLIC_SOURCE_ITEM_NOT_FOUND",
                                  "text/plain; charset=utf-8")
            try:
                report = public_prober(root, item_id=item_id, top=1)
                return self.reply(200, render_public_source_probe(report))
            except (BatchError, AuditError, ProbeError, ClaimError,
                    ExploreError, DiscoveryError,
                    ValueError, TypeError, KeyError):
                return self.reply(503, "PUBLIC_SOURCE_PROOF_NO_GO",
                                  "text/plain; charset=utf-8")
            except (sqlite3.DatabaseError, OSError):
                return self.reply(503, "PUBLIC_SOURCE_STORAGE_NO_GO",
                                  "text/plain; charset=utf-8")
    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE V0.9 owner-clicked approved public source checks")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if (root.is_symlink() or root.name.casefold() != "ucie"
            or not root.is_dir() or not 0 <= args.port <= 65535
            or (os.name == "nt" and root.resolve() != Path("D:/UCIE").resolve())):
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED"}))
        return 2
    try:
        with HTTPServer(("127.0.0.1", args.port), make_handler(root)) as server:
            print(json.dumps({
                "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_LISTENING",
                "url": "http://127.0.0.1:" + str(server.server_port) + "/",
                "database_writes": 0, "scheduler_changes": 0,
                "public_fetch_requires_owner_click": True,
                "production_approved": False,
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
