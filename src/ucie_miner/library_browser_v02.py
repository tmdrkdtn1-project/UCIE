"""UCIE V0.2 local, loopback-only public candidate explorer.

Pages and detail are rendered only after the existing W04 Stage10/12/15
source-linkage checks succeed. This is NOT an approved/usable Rulepack index.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlencode, urlsplit

from .library_explore import (
    READY, INCOMPLETE, ExploreError, describe_purpose,
    explore_existing_public_library,
)
from .library_search import ALLOWED_DOMAINS, ALLOWED_KINDS, LibrarySearchError, _filters
from .library_browser import APPROVED_SOURCES, PUBLIC_LINK
from .public_discovery import DiscoveryError

SCHEMA = "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02"
PARAMS = frozenset(("q", "source", "domain", "kind", "limit", "page"))
MAX_URL = 640
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class UIError(ValueError):
    pass


def read_filters(qs: str) -> dict:
    if type(qs) is not str or len(qs) > MAX_URL:
        raise UIError("invalid bounded URL")
    try:
        args = parse_qs(qs, keep_blank_values=True, strict_parsing=True,
                        max_num_fields=6, encoding="utf-8", errors="strict") if qs else {}
    except (ValueError, UnicodeError) as exc:
        raise UIError("invalid query parameters") from exc
    if not set(args).issubset(PARAMS) or any(len(a) != 1 for a in args.values()):
        raise UIError("unexpected or duplicated query parameters")
    q = args.get("q", [""])[0]
    source = args.get("source", [""])[0] or None
    domain = args.get("domain", [""])[0] or None
    kind = args.get("kind", [""])[0] or None
    limit = args.get("limit", ["10"])[0]
    page = args.get("page", ["1"])[0]
    if (source is not None and source not in APPROVED_SOURCES
            or not limit.isascii() or not limit.isdecimal() or limit not in ("5", "10", "20")
            or not page.isascii() or not page.isdecimal() or len(page) > 3
            or not 1 <= int(page) <= 200):
        raise UIError("out-of-scope search selection")
    try:
        _filters(query=q, source_id=source, domain=domain,
                 kind=kind, limit=int(limit), group_revisions=True)
    except LibrarySearchError as exc:
        raise UIError("invalid public metadata search term") from exc
    return {"query": q, "source_id": source, "domain": domain,
            "kind": kind, "limit": int(limit), "page": int(page)}


def _t(value: object, n: int = 160) -> str:
    return escape(value[:n] if type(value) is str else "", quote=True)


def _url(filters: dict, **overrides) -> str:
    f = dict(filters, **overrides)
    return "/?" + urlencode({
        "q": f["query"], "domain": f["domain"] or "", "kind": f["kind"] or "",
        "source": f["source_id"] or "", "limit": str(f["limit"]),
        "page": str(f["page"]),
    })


def _option(values, selected, blank):
    opts = ['<option value="">' + escape(blank) + "</option>"]
    for name in values:
        checked = " selected" if selected == name else ""
        opts.append('<option value="' + _t(name) + '"' + checked + ">"
                    + escape(name) + "</option>")
    return "".join(opts)


def _public_link(url: object) -> str:
    if type(url) is str and PUBLIC_LINK.fullmatch(url):
        return ('<a target="_blank" rel="noopener noreferrer" href="'
                + _t(url, 200) + '">공개 근거 열기</a>')
    return "<span>공개 근거 링크 확인 불가</span>"


CSS = """<style>
:root{font-family:system-ui,"Malgun Gothic",sans-serif;color:#192536;color-scheme:light}
body{margin:0;background:#f4f7fb} main{max-width:1160px;margin:auto;padding:32px 20px 70px}
h1{margin:3px 0 7px;font-size:27px}.subtitle{font-size:13px;color:#596b82}
.panel,.item,.empty{background:#fff;border:1px solid #dfe7f1;border-radius:13px;padding:17px}
.panel{margin-top:20px;padding:23px}form{display:grid;grid-template-columns:2fr 1fr 1fr;gap:13px}
label{display:flex;flex-direction:column;gap:6px;font-weight:600;font-size:13px}
input,select{padding:11px;border:1px solid #afc0d6;border-radius:8px;font:inherit;min-width:0}
button{padding:11px 22px;border:0;border-radius:8px;background:#2555a3;color:#fff;font:inherit;cursor:pointer}
.note{margin:18px 0;padding:13px;border-left:3px solid #5280c2;background:#eaf1fa;font-size:14px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
.chip{font-size:12px;padding:6px 10px;border:1px solid #c9d7e9;border-radius:22px;text-decoration:none;background:#fff}
.chip.active{background:#e2ecfa} .stats{font-weight:650;margin:18px 0}
.items{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:13px}
.item{overflow-wrap:anywhere}.item h3{font-size:17px;margin:9px 0}
.item p,.detail p{font-size:13px;color:#475970;overflow-wrap:anywhere}
.item .meta{font-weight:650;color:#27569b;font-size:12px}
a{color:#2053a2;font-weight:600}.pages{display:flex;gap:14px;align-items:center;margin:20px 0}
code{word-break:break-all;font-size:12px} .tag{font-size:12px;color:#805511}
.detail{max-width:830px;margin-top:20px}
.detail dt{font-size:12px;color:#4e6483;margin-top:14px}
.detail dd{margin:4px 0;font-size:14px;overflow-wrap:anywhere}
footer{font-size:12px;color:#657790;margin-top:28px}
@media(max-width:720px){form{grid-template-columns:1fr}main{padding:20px 13px}}
</style>"""


def _head(title: str):
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>UCIE | ' + _t(title) + "</title>" + CSS
            + '</head><body><main><header><div class="subtitle">'
            'UCIE · LOCAL ONLY · SOURCE-LINKED PUBLIC EVIDENCE</div>'
            '<h1>' + _t(title) + '</h1><div class="subtitle">'
            'V0.2 · 미검증 공개 근거 후보 · 자동 승인/배포 없음</div></header>')


def _foot():
    return ('<footer>검색 대상은 UCIE의 승인된 공개 출처 메타데이터뿐입니다. '
            '검증·라이선스·버전 적용성은 별도 확인 필요 · 읽기 전용 · '
            + SCHEMA + '</footer></main></body></html>')


def _facets(title, field, counts: object, filters: dict, allowed):
    if type(counts) is not dict:
        return ""
    chips = []
    for name in sorted(counts):
        count = counts[name]
        if (name not in allowed or type(count) is not int
                or count < 0 or count > 1000):
            continue
        link = _url(filters, **{field: name, "page": 1})
        mark = " active" if filters[field] == name else ""
        chips.append('<a class="chip' + mark + '" href="' + _t(link, 350) + '">'
                     + _t(name, 100) + " · " + str(count) + '</a>')
    return ('<section aria-label="' + _t(title) + '"><div class="subtitle">'
            + _t(title) + '</div><div class="toolbar">'
            + "".join(chips) + "</div></section>")


def render_results(filters: dict, result: dict | None = None,
                   *, error: str | None = None) -> str:
    if (result is not None and (
            type(result) is not dict or type(result.get("items")) is not list
            or type(result.get("status")) is not str)):
        raise UIError("invalid query result")
    f = filters
    page = [_head("공개 기술 근거 검색"), '<section class="panel"><form method="get" action="/">',
            '<label>검색어 (영문 메타데이터)<input name="q" maxlength="80" value="'
            + _t(f["query"], 80) + '" placeholder="예: API_CONTRACT, Python, Git"></label>',
            '<label>기술 분야<select name="domain">'
            + _option(sorted(ALLOWED_DOMAINS), f["domain"], "전체 분야") + '</select></label>',
            '<label>근거 종류<select name="kind">'
            + _option(sorted(ALLOWED_KINDS), f["kind"], "전체 후보") + '</select></label>',
            '<label>승인된 공개 출처<select name="source">'
            + _option(APPROVED_SOURCES, f["source_id"], "전체 출처") + '</select></label>',
            '<label>표시 건수<select name="limit">'
            + _option(("5", "10", "20"), str(f["limit"]), "10건") + '</select></label>',
            '<input type="hidden" name="page" value="1">',
            '<div><button type="submit">근거 검색</button></div></form></section>',
            '<div class="note">미검증 후보입니다. 관련도는 메타데이터 문자열 기준이며, '
            '원본 코드 실행이나 검증 통과를 의미하지 않습니다.</div>']
    if error == "INPUT_NO_GO":
        page += ['<p class="stats">입력 조건 오류 · 허용된 검색 조건만 사용하세요.</p>']
    elif error is not None:
        page += ['<p class="stats">원장 조회/검증 차단 · ' + _t(error) + '</p>']
    elif result is None:
        page += ['<p class="stats">검색 조건을 선택해 원장 조회를 시작하세요.</p>']
    elif result["status"] == INCOMPLETE:
        page += ['<p class="stats">원장 연결 미완료 · 결과 표시 차단</p>']
    elif result["status"] != READY:
        page += ['<p class="stats">검증 상태 미확인 · 결과 표시 차단</p>']
    else:
        count = result.get("total_matches")
        count = count if type(count) is int and 0 <= count <= 1000 else 0
        current = result.get("page", 1)
        total_pages = result.get("total_pages", 0)
        page += ['<div class="stats">검색된 후보 ' + str(count)
                 + '건 · ' + str(current) + '/' + str(total_pages or 1)
                 + '페이지 · 현재 ' + str(len(result["items"])) + '건</div>']
        page += [_facets("기술 분야별 후보", "domain", result.get("domain_facets"),
                         f, ALLOWED_DOMAINS),
                 _facets("출처별 후보", "source_id", result.get("source_facets"),
                         f, APPROVED_SOURCES)]
        parts = []
        for row in result["items"][:20]:
            if type(row) is not dict:
                continue
            title, desc = describe_purpose(row.get("purpose_code", ""))
            cid = row.get("library_item_id", "")
            ident = (('<a href="/item/' + cid + '">상세보기</a>')
                     if type(cid) is str and HEX64.fullmatch(cid)
                     else "상세보기 불가")
            parts.append('<article class="item"><div class="meta">'
                         + _t(row.get("source_id")) + ' · '
                         + _t(row.get("domain")) + '</div><h3>'
                         + _t(title) + '</h3><p>' + _t(desc, 200)
                         + '</p><p>분류: <code>' + _t(row.get("purpose_code"), 80)
                         + '</code> · 개정 근거 ' + str(min(
                             1000, row.get("evidence_revision_count", 1)
                             if type(row.get("evidence_revision_count")) is int else 1))
                         + '건</p><p class="tag">미검증 · 승인/내보내기 불가</p>'
                         + '<p>' + ident + ' · '
                         + _public_link(row.get("public_url")) + '</p></article>')
        if not parts:
            parts = ['<div class="empty">해당 조건의 후보가 없습니다.</div>']
        page += ['<section class="items">' + "".join(parts) + '</section>']
        if type(current) is int and type(total_pages) is int:
            links = []
            if current > 1:
                links.append('<a href="' + _t(_url(f, page=current-1), 350)
                             + '">이전 페이지</a>')
            links.append('<span>' + str(current) + ' / '
                         + str(total_pages or 1) + '</span>')
            if current < total_pages:
                links.append('<a href="' + _t(_url(f, page=current+1), 350)
                             + '">다음 페이지</a>')
            page.append('<nav class="pages" aria-label="검색 페이지 이동">'
                        + ' '.join(links) + '</nav>')
    page.append(_foot())
    return "\n".join(page)


def render_detail(row: dict) -> str:
    title, description = describe_purpose(row.get("purpose_code", ""))
    fields = [
        ("분류 코드", row.get("purpose_code")),
        ("기술 분야", row.get("domain")),
        ("근거 종류", row.get("kind")),
        ("승인된 출처", row.get("source_id")),
        ("공개 개정", row.get("revision_hint")),
        ("후보 식별자", row.get("library_item_id")),
        ("근거 SHA-256", row.get("evidence_sha256")),
        ("버전 적용성", "미확인 · 검증된 지원 버전 없음"),
        ("독립 회귀/보안 시험", "후보별 검증 미완료"),
        ("소스 라이선스", "검토 필요 · " + str(row.get("license_status", "UNKNOWN"))[:100]),
        ("서명·승인", "이 검색 결과는 서명·소유자 승인을 증명하지 않음"),
    ]
    field_html = "".join('<dt>' + _t(label) + '</dt><dd>' + _t(value, 180)
                         + '</dd>' for label, value in fields)
    return (_head("근거 후보 상세")
            + '<article class="panel detail"><p><a href="/">검색으로 돌아가기</a></p>'
            + '<h2>' + _t(title) + '</h2><p>' + _t(description, 200)
            + '</p><p class="tag">미검증 후보 · 배포/실행/내보내기 불가</p>'
            + '<dl>' + field_html + '</dl><p>'
            + _public_link(row.get("public_url"))
            + '</p><p>상세 내역은 승인된 공개 원문 링크에서 직접 검토해야 합니다. '
            '이 화면은 원문 내용을 저장하거나 검증된 동작을 보증하지 않습니다.</p>'
            + '</article>' + _foot())


def make_handler(root: Path, *, explorer=None):
    if explorer is None:
        explorer = explore_existing_public_library

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, fmt, *args):
            return  # Never persist private search terms

        def _reply(self, status, content, mime="text/html; charset=utf-8"):
            body = content.encode("utf-8") if type(content) is str else content
            self.send_response(status)
            for key, value in (
                ("Content-Type", mime), ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; "
                 "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"),
                ("X-Content-Type-Options", "nosniff"),
                ("X-Frame-Options", "DENY"),
                ("Referrer-Policy", "no-referrer"),
            ):
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self._reply(405, "GET_ONLY", "text/plain; charset=utf-8")

        def do_GET(self):
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self._reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if len(self.path) > MAX_URL + 80:
                return self._reply(400, "BOUNDED_URL_ONLY", "text/plain; charset=utf-8")
            parts = urlsplit(self.path)
            if parts.path == "/health" and not parts.query:
                return self._reply(200, json.dumps({
                    "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_READY",
                    "db_writes": 0, "scheduler_changes": 0, "auto_promoted": False,
                }), "application/json; charset=utf-8")
            if parts.path == "/" and not parts.query:
                return self._reply(200, render_results(read_filters("")))
            if parts.path == "/":
                try:
                    filters = read_filters(parts.query)
                except UIError:
                    return self._reply(400, render_results(read_filters(""), error="INPUT_NO_GO"))
                try:
                    result = explorer(root, **filters)
                    return self._reply(200, render_results(filters, result))
                except (LibrarySearchError, ExploreError, DiscoveryError,
                        ValueError, TypeError, KeyError):
                    return self._reply(503, render_results(
                        filters, error="SOURCE_VALIDATION_FAILED_NO_GO"))
                except (sqlite3.DatabaseError, OSError):
                    return self._reply(503, render_results(
                        filters, error="SOURCE_STORAGE_UNAVAILABLE_NO_GO"))
            if parts.path.startswith("/item/") and not parts.query:
                cid = parts.path[len("/item/"):]
                if HEX64.fullmatch(cid) is None:
                    return self._reply(404, "ITEM_NOT_FOUND", "text/plain; charset=utf-8")
                try:
                    result = explorer(root, item_id=cid)
                    if result["status"] != READY or result.get("detail") is None:
                        return self._reply(404, "ITEM_NOT_FOUND", "text/plain; charset=utf-8")
                    return self._reply(200, render_detail(result["detail"]))
                except (LibrarySearchError, ExploreError, DiscoveryError,
                        ValueError, TypeError, KeyError, sqlite3.DatabaseError, OSError):
                    return self._reply(503, "SOURCE_VALIDATION_FAILED_NO_GO",
                                       "text/plain; charset=utf-8")
            return self._reply(404, "ROUTE_NOT_FOUND", "text/plain; charset=utf-8")
    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE V0.2 loopback read-only catalog")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if (root.name.casefold() != "ucie" or root.is_symlink() or not root.is_dir()
            or not 0 <= args.port <= 65535
            or (os.name == "nt" and root.resolve() != Path("D:/UCIE").resolve())):
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED"}))
        return 2
    try:
        with HTTPServer(("127.0.0.1", args.port), make_handler(root)) as server:
            print(json.dumps({
                "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_LISTENING",
                "url": "http://127.0.0.1:" + str(server.server_port) + "/",
                "database_writes": 0, "scheduler_changes": 0,
                "production_approved": False,
            }, ensure_ascii=True), flush=True)
            server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except OSError:
        print(json.dumps({"schema": SCHEMA, "status": "LOCAL_BIND_FAILED_NO_GO"}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
