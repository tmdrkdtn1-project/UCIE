"""UCIE V0.3 loopback search and side-by-side review-only candidate comparison.

The existing V0.2 browser and scheduled collector remain untouched. Comparison
requests always require 2-3 source-linked SHA identities checked against the
current immutable-source-provenance handoff, never arbitrary selected text.
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
from urllib.parse import parse_qs, urlsplit

from .library_browser_v02 import (
    MAX_URL, UIError, _head, _foot, _t, _public_link,
    read_filters, render_results,
)
from .library_explore import (
    ExploreError, READY as EXPLORE_READY, explore_existing_public_library,
)
from .library_compare import (
    SCHEMA as COMPARE_SCHEMA, READY as COMPARE_READY, INCOMPLETE,
    CompareError, validate_ids, compare_existing_public_candidates,
)
from .public_discovery import DiscoveryError
from .library_search import LibrarySearchError

SCHEMA = "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V03"
CARD_START = '<article class="item">'
ITEMS_START = '<section class="items">'
ITEMS_END = '</section>'
MAX_COMPARE_QUERY = 210
COMPARE_CSS = """
<style>
.items .compare-grid{display:grid;grid-column:1/-1;
grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:13px}
.compare-grid .compare-actions{grid-column:1/-1;padding:12px;background:#e8eff9;
border-radius:9px;display:flex;gap:12px;align-items:center}
.compare-grid label{display:flex;flex-direction:row;align-items:center;gap:7px;
font-size:12px;color:#19416f}
.compare-grid input[type=checkbox]{width:17px;height:17px}
.compare-table{overflow-x:auto;background:#fff;border:1px solid #dfe7f1;
border-radius:14px;margin-top:20px}
.compare-table table{border-collapse:collapse;min-width:720px;width:100%}
.compare-table th,.compare-table td{border-bottom:1px solid #e4eaf2;
padding:13px;vertical-align:top;text-align:left;word-break:break-word}
.compare-table th{background:#eef3fa;color:#183758}
.compare-table td{max-width:320px;font-size:13px}
.compare-table .field{min-width:145px;font-weight:650;color:#425671}
@media(max-width:720px){.items .compare-grid{grid-template-columns:1fr}}
</style>"""


def _branding(html: str) -> str:
    return (html.replace("V0.2 ·", "V0.3 ·")
            .replace("UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02", SCHEMA)
            .replace("</head>", COMPARE_CSS + "</head>"))


def render_search(filters: dict, result: dict | None = None,
                  *, error: str | None = None) -> str:
    """Reuse verified V0.2 UI; add a bounded GET-only compare selection form."""
    base = _branding(render_results(filters, result, error=error))
    if result is None or result.get("status") != EXPLORE_READY or not result.get("items"):
        return base
    before, found, tail = base.partition(ITEMS_START)
    if not found:
        raise UIError("missing read-only result grid")
    cards, end, after = tail.partition(ITEMS_END)
    if not end:
        raise UIError("unterminated read-only result grid")
    ids = []
    for row in result["items"]:
        if type(row) is not dict:
            raise UIError("invalid compare candidate")
        identity = row.get("library_item_id")
        if (type(identity) is not str or re.fullmatch(r"[0-9a-f]{64}", identity) is None):
            raise UIError("unbound compare candidate identity")
        ids.append(identity)
    # Every card originates exclusively from the validated W04 result, and
    # each rendered checkbox belongs to its exact source-linked row.
    if cards.count(CARD_START) != len(ids):
        raise UIError("result-card identities do not match source ledger")
    i = iter(ids)
    def label(_):
        identity = next(i)
        return (CARD_START + '<label><input type="checkbox" name="item" value="'
                + identity + '">비교 선택</label>')
    cards = re.sub(re.escape(CARD_START), label, cards)
    form = ('<form class="compare-grid" action="/compare" method="get">'
            + cards + '<div class="compare-actions">'
            '<button type="submit">선택한 후보 비교</button>'
            '<span>현재 페이지에서 2~3개를 선택 · 미검증 후보</span>'
            '</div></form>')
    return before + ITEMS_START + form + ITEMS_END + after


def parse_compare(qs: str) -> tuple[str, ...]:
    if type(qs) is not str or not qs or len(qs) > MAX_COMPARE_QUERY:
        raise CompareError("invalid compare request length")
    try:
        params = parse_qs(qs, keep_blank_values=True, strict_parsing=True,
                          max_num_fields=3, encoding="utf-8", errors="strict")
    except (ValueError, UnicodeError) as exc:
        raise CompareError("invalid compare request") from exc
    if set(params) != {"item"}:
        raise CompareError("only exact public item identities may be compared")
    return validate_ids(tuple(params["item"]))


def render_comparison(result: dict) -> str:
    if (type(result) is not dict or result.get("status") != COMPARE_READY
            or type(result.get("items")) is not list
            or len(result["items"]) not in (2, 3)):
        raise CompareError("incomplete source-verified comparison")
    rows = result["items"]
    for item in rows:
        if (type(item) is not dict or item.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
                or item.get("human_approved") is not False
                or item.get("export_allowed") is not False):
            raise CompareError("comparison attempted to approve candidate")
    labels = (
        ("분류·검토 목적", "purpose_label"),
        ("분류 코드", "purpose_code"),
        ("기술 분야", "domain"),
        ("출처", "source_id"),
        ("후보 종류", "kind"),
        ("공개 개정", "revision_hint"),
        ("근거 SHA-256", "evidence_sha256"),
        ("개정 근거 건수", "evidence_revision_count"),
        ("적용 버전", "version_scope_claim"),
        ("라이선스 상태", "license_status"),
        ("검토 질문 (UCIE 공통 가이드)", "review_question"),
        ("다음 확인 작업", "next_review_action"),
        ("안전 검토 가이드", "safe_review_guidance"),
        ("승인·내보내기", "status"),
    )
    head = (_branding(_head("공개 근거 후보 비교"))
            + '<p><a href="/">검색으로 돌아가기</a></p>'
            '<div class="note">후보 2~3개의 공개 메타데이터 비교입니다. '
            '우열·수정 완료·취약점 증명·검증 통과·실제 적용 가능성을 뜻하지 않습니다.</div>')
    table = ['<div class="compare-table"><table><thead><tr><th scope="col">항목</th>']
    for i, item in enumerate(rows, 1):
        table.append('<th scope="col">후보 ' + str(i) + '<p>'
                     + _t(item.get("purpose_label")) + '</p></th>')
    table.append("</tr></thead><tbody>")
    for label, field in labels:
        table.append('<tr><th scope="row" class="field">' + _t(label) + "</th>")
        for item in rows:
            value = item.get(field)
            table.append("<td>" + (_t(str(value), 280) if type(value) in (int,)
                                   else _t(value, 280)) + "</td>")
        table.append("</tr>")
    table.append('<tr><th scope="row" class="field">공개 기술 근거</th>')
    for item in rows:
        table.append("<td>" + _public_link(item.get("public_url")) + "</td>")
    table.append("</tr></tbody></table></div>")
    return head + "".join(table) + _branding(_foot())


def make_handler(root: Path, *, explorer=None, comparer=None):
    if explorer is None:
        explorer = explore_existing_public_library
    if comparer is None:
        comparer = compare_existing_public_candidates

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, fmt, *args):
            # Do not persist search terms, selected hashes, or any project data.
            return

        def reply(self, status: int, content: str, mime="text/html; charset=utf-8"):
            body = content.encode("utf-8")
            self.send_response(status)
            for key, value in (
                ("Content-Type", mime),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
                ("Content-Security-Policy",
                 "default-src 'none'; style-src 'unsafe-inline'; "
                 "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"),
                ("X-Content-Type-Options", "nosniff"),
                ("X-Frame-Options", "DENY"),
                ("Referrer-Policy", "no-referrer"),
            ):
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.reply(405, "GET_ONLY", "text/plain; charset=utf-8")

        def do_GET(self):
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if len(self.path) > MAX_URL + 80:
                return self.reply(400, "BOUNDED_URL_ONLY", "text/plain; charset=utf-8")
            parts = urlsplit(self.path)
            if parts.fragment:
                return self.reply(404, "ROUTE_NOT_FOUND", "text/plain; charset=utf-8")
            if parts.path == "/health" and not parts.query:
                return self.reply(200, json.dumps({
                    "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_READY",
                    "db_writes": 0, "scheduler_changes": 0,
                    "auto_promoted": False, "production_approved": False,
                }), "application/json; charset=utf-8")
            if parts.path == "/" and not parts.query:
                return self.reply(200, render_search(read_filters("")))
            if parts.path == "/":
                try:
                    filters = read_filters(parts.query)
                except UIError:
                    return self.reply(400, render_search(
                        read_filters(""), error="INPUT_NO_GO"))
                try:
                    result = explorer(root, **filters)
                    return self.reply(200, render_search(filters, result))
                except (LibrarySearchError, ExploreError, DiscoveryError,
                        ValueError, TypeError, KeyError):
                    return self.reply(503, render_search(filters,
                        error="SOURCE_VALIDATION_FAILED_NO_GO"))
                except (sqlite3.DatabaseError, OSError):
                    return self.reply(503, render_search(filters,
                        error="SOURCE_STORAGE_UNAVAILABLE_NO_GO"))
            if parts.path == "/compare":
                try:
                    ids = parse_compare(parts.query)
                except CompareError:
                    return self.reply(400, "TWO_OR_THREE_DISTINCT_CANDIDATES_REQUIRED",
                                      "text/plain; charset=utf-8")
                try:
                    result = comparer(root, item_ids=ids)
                    if result.get("status") != COMPARE_READY:
                        return self.reply(404, "UNLINKED_CANDIDATES_NO_GO",
                                          "text/plain; charset=utf-8")
                    return self.reply(200, render_comparison(result))
                except (CompareError, LibrarySearchError, ExploreError,
                        DiscoveryError, ValueError, TypeError, KeyError):
                    return self.reply(503, "SOURCE_VALIDATION_FAILED_NO_GO",
                                      "text/plain; charset=utf-8")
                except (sqlite3.DatabaseError, OSError):
                    return self.reply(503, "SOURCE_STORAGE_UNAVAILABLE_NO_GO",
                                      "text/plain; charset=utf-8")
            if parts.path.startswith("/item/") and not parts.query:
                # Detail is a V0.2 feature; reused unchanged in the new server.
                from .library_browser_v02 import render_detail, HEX64
                identity = parts.path[len("/item/"):]
                if HEX64.fullmatch(identity) is None:
                    return self.reply(404, "ITEM_NOT_FOUND", "text/plain; charset=utf-8")
                try:
                    result = explorer(root, item_id=identity)
                    if result.get("status") != EXPLORE_READY or result.get("detail") is None:
                        return self.reply(404, "ITEM_NOT_FOUND", "text/plain; charset=utf-8")
                    return self.reply(200, _branding(render_detail(result["detail"])))
                except (LibrarySearchError, ExploreError, DiscoveryError,
                        ValueError, TypeError, KeyError, sqlite3.DatabaseError, OSError):
                    return self.reply(503, "SOURCE_VALIDATION_FAILED_NO_GO",
                                      "text/plain; charset=utf-8")
            return self.reply(404, "ROUTE_NOT_FOUND", "text/plain; charset=utf-8")

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE V0.3 read-only evidence comparator")
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
