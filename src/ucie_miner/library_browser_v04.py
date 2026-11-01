"""UCIE V0.4 owner-local read-only source evidence review preparation.

The verified V0.3 search, comparison, selection restoration and V0.2 detail
remain unchanged. This separate browser adds source-linked review worksheets.
No persisted session, notes, approval, test execution or network fetch.
"""
from __future__ import annotations

import argparse
import json
import os
from html import escape
from http.server import HTTPServer
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from . import library_browser_v03 as v03
from .library_browser_v02 import _head, _foot, _t, _public_link, HEX64
from .library_review_v04 import (
    READY, ReviewDossierError, dossier_existing_public_candidate,
)
from .library_search import LibrarySearchError
from .library_explore import ExploreError
from .public_discovery import DiscoveryError

SCHEMA = "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V04"
DETAIL_LINK = re.compile(r'<a href="/item/([0-9a-f]{64})">상세보기</a>')
REVIEW_CSS = """<style>
.review-gates{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px;margin-top:14px}
.gate{border:1px solid #dfe7f1;border-radius:12px;background:#fff;padding:15px}
.gate h3{margin:4px 0;font-size:16px}.gate p{font-size:13px;color:#456078}
.dossier{max-width:940px}.dossier dl{display:grid;grid-template-columns:190px 1fr;gap:8px 12px}
.dossier dt{font-weight:650;font-size:13px}.dossier dd{margin:0;font-size:13px;overflow-wrap:anywhere}
.review-hint{margin:13px 0;background:#edf3fa;border-left:3px solid #4d78b0;padding:12px}
@media(max-width:720px){.dossier dl{grid-template-columns:1fr}}
</style>"""


def _branding(html: str) -> str:
    return (v03._branding(html)
            .replace("V0.3 ·", "V0.4 ·")
            .replace(v03.SCHEMA, SCHEMA)
            .replace("</head>", REVIEW_CSS + "</head>"))


def _review_href(identity: str, context: dict | None,
                 selected: tuple[str, ...] = ()) -> str:
    if HEX64.fullmatch(identity) is None:
        raise ReviewDossierError("invalid review identity")
    return "/review/" + identity + (
        "?" + v03._return_href(context, selected)[2:]
        if context is not None else ""
    )


def add_review_links(html: str, filters: dict,
                     selected: tuple[str, ...] = ()) -> str:
    """Insert only source-linked SHA hyperlinks into already verified UI cards."""
    def substitute(match):
        identity = match.group(1)
        href = _review_href(identity, filters, selected)
        return (match.group(0)
                + ' · <a href="' + _t(href, v03.MAX_RETURN_URL + 80)
                + '">검증 준비표</a>')
    return DETAIL_LINK.sub(substitute, _branding(html))


def render_review(dossier: dict, *, back: str = "/") -> str:
    """Only checked public metadata; no unsafe source prose interpreted."""
    if (type(dossier) is not dict or dossier.get("status") != READY
            or dossier.get("source_linkage_checked") is not True
            or dossier.get("independently_verified") is not False
            or dossier.get("owner_approved") is not False
            or dossier.get("auto_promoted") is not False
            or dossier.get("production_approved") is not False
            or dossier.get("export_allowed") is not False
            or type(dossier.get("item")) is not dict
            or type(dossier.get("requirements")) is not list
            or len(dossier["requirements"]) != 6):
        raise ReviewDossierError("source-linked dossier not eligible for review rendering")
    item = dossier["item"]
    if (item.get("status") != "UNVERIFIED_CANDIDATE_ONLY"
            or type(item.get("library_item_id")) is not str
            or HEX64.fullmatch(item["library_item_id"]) is None
            or not (back == "/" or back.startswith("/?"))):
        raise ReviewDossierError("invalid dossier identity or navigation")
    meta = (
        ("후보 ID", "library_item_id"),
        ("승인된 공개 출처", "source_id"),
        ("기술 분야", "domain"),
        ("분류", "purpose_code"),
        ("근거 종류", "kind"),
        ("공개 개정", "revision_hint"),
        ("근거 SHA-256", "evidence_sha256"),
        ("같은 후보에 연결된 근거 개정 수", "evidence_revision_count"),
        ("적용 버전", "version_scope"),
        ("라이선스 확인", "license_status"),
        ("다음 검토 작업", "next_review_action"),
    )
    header = (
        _branding(_head("후보별 공개 근거 검증 준비표"))
        + '<p><a href="' + _t(back, v03.MAX_RETURN_URL)
        + '">선택했던 검색 결과로 돌아가기</a></p>'
        + '<p class="review-hint">원장 출처·개정·SHA 연결은 확인됐지만, '
          '수정 효과·버전 범위·라이선스·독립 시험·담당자 승인은 모두 미검증입니다. '
          '이 페이지는 검증 작업 목록이지 완료 영수증이 아닙니다.</p>'
        + '<section class="panel dossier"><h2>'
        + _t(item.get("purpose_label"))
        + '</h2><p>' + _t(item.get("purpose_description"), 230)
        + '</p><dl>'
        + "".join("<dt>" + _t(label) + "</dt><dd>"
                  + _t(str(item.get(key)) if type(item.get(key)) is int
                       else item.get(key), 220) + "</dd>" for label, key in meta)
        + '</dl><p>' + _public_link(item.get("public_url")) + '</p></section>'
    )
    blocks = []
    for gate in dossier["requirements"]:
        if (type(gate) is not dict or gate.get("status") not in (
                "SOURCE_LINKAGE_ONLY_NOT_FIX_VERIFIED", "NOT_VERIFIED")):
            raise ReviewDossierError("unapproved gate state")
        blocks.append(
            '<article class="gate"><div class="subtitle">'
            + _t(gate.get("gate")) + '</div><h3>' + _t(gate.get("label"))
            + '</h3><p><strong>' + _t(gate.get("status"))
            + '</strong></p><p>' + _t(gate.get("next_action"), 280)
            + '</p></article>'
        )
    reasons = dossier.get("blocking_reasons")
    if type(reasons) is not list or any(type(x) is not str for x in reasons):
        raise ReviewDossierError("invalid dossier blockers")
    blockers = ('<section class="panel"><h3>현재 검토 차단 사유</h3><ul>'
                + "".join("<li>" + _t(reason, 230) + "</li>" for reason in reasons[:12])
                + '</ul></section>')
    return (header + '<h2>검증 요구사항 · 승인 전 확인 6개 관문</h2>'
            '<section class="review-gates">' + "".join(blocks) + "</section>"
            + blockers + _branding(_foot()))


def make_handler(root: Path, *, explorer=None, comparer=None, reviewer=None):
    base = v03.make_handler(root, explorer=explorer, comparer=comparer)
    if reviewer is None:
        reviewer = dossier_existing_public_candidate

    class Handler(base):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            parts = urlsplit(self.path)
            if (status == 200 and mime == "text/html; charset=utf-8"
                    and parts.path == "/" and parts.query):
                try:
                    filters, selected = v03.parse_search_request(parts.query)
                    content = add_review_links(content, filters, selected)
                except (v03.UIError, ReviewDossierError, ValueError):
                    return super().reply(503, "SOURCE_VALIDATION_FAILED_NO_GO",
                                         "text/plain; charset=utf-8")
            elif status == 200 and mime == "text/html; charset=utf-8":
                content = _branding(content)
            return super().reply(status, content, mime)

        def do_GET(self):
            parts = urlsplit(self.path)
            if not parts.path.startswith("/review/"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if len(self.path) > v03.MAX_RETURN_URL + 100 or parts.fragment:
                return self.reply(400, "BOUNDED_URL_ONLY", "text/plain; charset=utf-8")
            identity = parts.path.removeprefix("/review/")
            if HEX64.fullmatch(identity) is None:
                return self.reply(404, "ITEM_NOT_FOUND", "text/plain; charset=utf-8")
            try:
                context = None
                selected = ()
                if parts.query:
                    context, selected = v03.parse_search_request(parts.query)
            except v03.UIError:
                return self.reply(400, "INVALID_REVIEW_QUERY",
                                  "text/plain; charset=utf-8")
            try:
                receipt = reviewer(root, item_id=identity)
                if receipt.get("status") != READY:
                    return self.reply(404, "SOURCE_LINKAGE_OR_ITEM_NO_GO",
                                      "text/plain; charset=utf-8")
                back = v03._return_href(context, selected)
                return self.reply(200, render_review(receipt, back=back))
            except (ReviewDossierError, LibrarySearchError, ExploreError,
                    DiscoveryError, ValueError, TypeError, KeyError):
                return self.reply(503, "SOURCE_VALIDATION_FAILED_NO_GO",
                                  "text/plain; charset=utf-8")
            except (sqlite3.DatabaseError, OSError):
                return self.reply(503, "SOURCE_STORAGE_UNAVAILABLE_NO_GO",
                                  "text/plain; charset=utf-8")

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE V0.4 source-linked review checklist browser")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if (root.is_symlink() or root.name.casefold() != "ucie" or not root.is_dir()
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
