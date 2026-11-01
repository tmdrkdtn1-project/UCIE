"""Local UCIE-only read-only browser for the existing W04 public evidence shelf.

One loopback HTTP process. GET requests invoke the existing source-linked
read-only library search. No file browser, source execution, task registration,
persistent index, external assets, cross-project routes or export endpoint.
This UI intentionally does not claim the Virtual Library V1 is complete.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from .library_search import (
    ALLOWED_DOMAINS, ALLOWED_KINDS, LibrarySearchError, _filters,
    search_existing_public_library,
)
from .public_discovery import DiscoveryError, SOURCES

SCHEMA = "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V1"
APPROVED_SOURCES = tuple(sorted("repo:" + name for name in SOURCES))
MAX_PATH_CHARS = 512
ALLOWED_PARAMS = frozenset(("q", "kind", "domain", "source", "limit"))
DEFAULT_LIMIT = 10
# Only exact links generated from source-pinned UCIE library entries.
PUBLIC_LINK = re.compile(
    r"https://github[.]com/(?:python/cpython|PowerShell/PowerShell|git/git|"
    r"modelcontextprotocol/python-sdk|actions/runner-images)/pull/[1-9][0-9]{0,8}\Z"
    r"|https://github[.]com/git/git/commit/[0-9a-f]{40}\Z"
)


class BrowserError(ValueError):
    pass


def parse_request_filters(query_string: str) -> dict:
    """One bounded, unambiguous GET query; reuse W04's original validation."""
    if type(query_string) is not str or len(query_string) > MAX_PATH_CHARS:
        raise BrowserError("invalid request size")
    if not query_string:
        raw = {}
    else:
        try:
            raw = parse_qs(
                query_string, keep_blank_values=True,
                strict_parsing=True, max_num_fields=5, encoding="utf-8",
                errors="strict",
            )
        except (ValueError, UnicodeError) as exc:
            raise BrowserError("invalid request parameters") from exc
    if not set(raw).issubset(ALLOWED_PARAMS) or any(len(v) != 1 for v in raw.values()):
        raise BrowserError("unknown or duplicated parameters")
    q = raw.get("q", [""])[0]
    kind = raw.get("kind", [""])[0] or None
    domain = raw.get("domain", [""])[0] or None
    source = raw.get("source", [""])[0] or None
    limit_str = raw.get("limit", [str(DEFAULT_LIMIT)])[0]
    if not limit_str.isascii() or not limit_str.isdecimal() or len(limit_str) > 2:
        raise BrowserError("invalid limit")
    limit = int(limit_str)
    if source is not None and source not in APPROVED_SOURCES:
        raise BrowserError("source is not in the approved public repository list")
    try:
        _filters(
            query=q, kind=kind, domain=domain,
            source_id=source, limit=limit, group_revisions=True,
        )
    except LibrarySearchError as exc:
        raise BrowserError("invalid bounded public metadata filters") from exc
    return {"query": q, "kind": kind, "domain": domain, "source_id": source, "limit": limit,
            "group_revisions": True}


def _text(value: object, max_chars: int = 150) -> str:
    return escape(value[:max_chars] if type(value) is str else "", quote=True)


def _options(values: tuple[str, ...], current: str | None, blank: str) -> str:
    output = ['<option value="">' + escape(blank) + "</option>"]
    for value in values:
        chosen = " selected" if value == current else ""
        output.append(
            '<option value="' + escape(value, quote=True) + '"' + chosen + ">"
            + escape(value) + "</option>"
        )
    return "\n".join(output)


def render_page(filters: dict, result: dict | None = None,
                *, error: bool = False) -> str:
    """Escape all untrusted fields and never mark unverified as usable."""
    if result is not None and (
        type(result) is not dict or type(result.get("items")) is not list
        or type(result.get("status")) is not str
    ):
        raise BrowserError("invalid search result shape")
    message = (
        "입력 조건이 유효하지 않습니다. 승인된 공개 출처와 제한된 검색어만 사용하세요."
        if error else
        "검색 전용 · 결과는 미검증 공개 기술 근거 후보입니다. "
        "규칙 적용·서명·패키지 내보내기·자동 승격은 제공하지 않습니다."
    )
    rows = []
    if result is not None and result.get("status") == "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO":
        items = result["items"][:20]
        for item in items:
            if type(item) is not dict:
                continue
            url = item.get("public_url")
            link = (('<a target="_blank" rel="noopener noreferrer" href="'
                     + escape(url, quote=True) + '">공개 근거 열기</a>')
                    if type(url) is str and PUBLIC_LINK.fullmatch(url)
                    else "<span>공개 링크 검증 불가</span>")
            rows.append(
                '<article class="item"><div class="meta">'
                + _text(item.get("source_id")) + " · " + _text(item.get("domain"))
                + '</div><h3>' + _text(item.get("purpose_code"))
                + '</h3><p>분류: ' + _text(item.get("kind"))
                + ' · 개정: ' + _text(item.get("revision_hint"), 45)
                + '</p><p>근거 SHA-256: <code>'
                + _text(item.get("evidence_sha256"), 64)
                + '</code></p><p>상태: <strong>미검증 후보 · 승인되지 않음</strong>'
                + '</p>' + link + "</article>"
            )
    if error:
        count = "검색 조건 오류 · 결과 없음"
    elif result is None:
        count = "승인된 공개 근거 원장을 조회합니다."
    elif result.get("status") == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        count = "원장 연결 검증 미완료 · 결과 표시 차단"
    elif result.get("status") != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO":
        count = "안전 검증 미완료 · 결과 표시 차단"
    else:
        total = result.get("total_matches")
        shown = len(rows)
        count = (str(total) if type(total) is int and 0 <= total <= 1_000_000 else "0")
        count = "검색된 후보 " + count + "건 · 화면 표시 " + str(shown) + "건"
    if not rows:
        rows = ['<div class="empty">표시할 근거 후보가 없습니다. '
                "필터를 조정하거나 원장 검증 상태를 확인하세요.</div>"]
    # Fixed, static CSS; no scripts or third-party assets are requested.
    return """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UCIE | 공개 기술 근거 검색</title>
<style>
:root{color-scheme:light;font-family:system-ui,"Malgun Gothic",sans-serif}
body{margin:0;background:#f5f7fb;color:#182337}
main{max-width:1050px;margin:auto;padding:34px 20px 70px}
header{margin:0 0 25px} h1{font-size:28px;margin:4px 0 8px}
.subtitle{color:#51627a;font-size:14px}
.panel{background:white;border:1px solid #e0e7f0;border-radius:16px;padding:24px}
form{display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px}
label{font-size:13px;font-weight:650;display:flex;flex-direction:column;gap:7px}
input,select{font:inherit;padding:11px;border:1px solid #b8c7da;border-radius:8px;min-width:0}
button{background:#2153a4;border:0;color:white;border-radius:8px;font:inherit;
font-weight:650;padding:11px 20px;cursor:pointer}
button:hover{background:#153a78}
.notice{margin:18px 0;padding:12px 16px;background:#eef3fa;
border-left:3px solid #5179b0;border-radius:8px;font-size:14px}
.stats{margin:22px 0 14px;font-weight:650}
.items{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:12px}
.item,.empty{background:white;border:1px solid #e0e7f0;border-radius:12px;padding:18px;overflow-wrap:anywhere}
.item h3{margin:10px 0;font-size:17px}.item p{font-size:13px;color:#42516a}
.item .meta{font-size:12px;color:#2153a4;font-weight:650}
a{color:#1c4c99;font-weight:650}
footer{margin-top:28px;color:#6b778c;font-size:12px}
@media(max-width:700px){form{grid-template-columns:1fr}main{padding:22px 14px}}
</style></head><body><main>
<header><div class="subtitle">UCIE · LOCAL READ-ONLY · APPROVED PUBLIC SOURCES</div>
<h1>공개 기술 근거 검색</h1>
<div class="subtitle">기존 W04 검증 원장 연결 · 외부 프로젝트 접근 없음</div></header>
<section class="panel"><form method="get" action="/">
<label>검색어 (영문 메타데이터)<input name="q" maxlength="80"
placeholder="예: Python, CONCURRENCY, PR"
value="%s"></label>
<label>기술 분야<select name="domain">%s</select></label>
<label>근거 종류<select name="kind">%s</select></label>
<label>승인된 공개 출처<select name="source">%s</select></label>
<label>표시 건수<select name="limit">%s</select></label>
<div><button type="submit">근거 검색</button></div></form></section>
<div class="notice">%s</div>
<div class="stats">%s</div><section class="items">%s</section>
<footer>읽기 전용 · 라이선스·버전·독립 시험 미확정 · 승인/배포 불가 ·
%s</footer>
</main></body></html>""" % (
        _text(filters["query"], 80),
        _options(tuple(sorted(ALLOWED_DOMAINS)), filters["domain"], "전체 분야"),
        _options(tuple(sorted(ALLOWED_KINDS)), filters["kind"], "전체 후보"),
        _options(APPROVED_SOURCES, filters["source_id"], "전체 승인 출처"),
        _options(("5", "10", "20"), str(filters["limit"]), "10건"),
        escape(message), escape(count), "\n".join(rows), SCHEMA,
    )


def make_handler(root: Path, *, searcher=None):
    """Injectable searcher used only for synthetic HTTP regression tests."""
    if searcher is None:
        searcher = search_existing_public_library

    class UCIEBrowserHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, format, *args):
            # Do not persist raw query terms or accidental private input.
            return

        def _reply(self, status: int, data: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; style-src 'unsafe-inline'; "
                             "form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            self._reply(405, b"READ_ONLY_GET_ONLY", "text/plain; charset=utf-8")

        def do_GET(self):
            # Host verification guards against DNS rebinding to a loopback UI.
            expected_host = "127.0.0.1:" + str(self.server.server_port)
            host = self.headers.get("Host", "")
            if host != expected_host:
                self._reply(403, b"LOCAL_HOST_ONLY", "text/plain; charset=utf-8")
                return
            if len(self.path) > MAX_PATH_CHARS + 3:
                self._reply(400, b"BOUNDED_REQUEST_ONLY", "text/plain; charset=utf-8")
                return
            parsed = urlsplit(self.path)
            if parsed.path == "/health" and not parsed.query:
                payload = json.dumps({
                    "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_READY",
                    "network_requests_to_public_sources": 0,
                    "operating_database_writes": 0,
                    "production_approved": False,
                }, sort_keys=True).encode("utf-8")
                self._reply(200, payload, "application/json; charset=utf-8")
                return
            if parsed.path != "/" or parsed.fragment:
                self._reply(404, b"UCIE_ROUTE_NOT_FOUND", "text/plain; charset=utf-8")
                return
            try:
                filters = parse_request_filters(parsed.query)
                result = searcher(root, **filters)
                html = render_page(filters, result)
            except (BrowserError, LibrarySearchError, DiscoveryError, ValueError):
                defaults = parse_request_filters("")
                html = render_page(defaults, error=True)
                self._reply(400, html.encode("utf-8"), "text/html; charset=utf-8")
                return
            self._reply(200, html.encode("utf-8"), "text/html; charset=utf-8")

    return UCIEBrowserHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE loopback-only read-only public Library search")
    parser.add_argument("--port", type=int, default=0,
                        help="loopback port, default 0 selects an available local port")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    # The user-owned Windows installation is the only production root.
    if (root.is_symlink() or root.name.casefold() != "ucie" or not root.is_dir()
            or not 0 <= args.port <= 65535
            or (__import__("os").name == "nt" and root.resolve() != Path("D:/UCIE").resolve())):
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED"}))
        return 2
    try:
        with HTTPServer(("127.0.0.1", args.port), make_handler(root)) as server:
            url = "http://127.0.0.1:" + str(server.server_port) + "/"
            print(json.dumps({
                "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_LISTENING",
                "url": url, "database_writes": 0,
                "scheduler_changes": 0, "production_approved": False,
            }, ensure_ascii=True), flush=True)
            server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except OSError:
        print(json.dumps({"schema": SCHEMA, "status": "LOCAL_BIND_FAILED_NO_GO"}), flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
