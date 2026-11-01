"""UCIE V0.5 local read-only public evidence receipt browser.

V0.4 query/compare/return flows are inherited unchanged. The new receipts
panel displays only explicitly submitted, source-bound *unverified* citations.
This HTTP server never accepts POST or writes any receipts or databases.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import HTTPServer
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

from . import library_browser_v04 as v04
from . import library_browser_v03 as v03
from .library_browser_v02 import HEX64, _t
from .library_review_v04 import (
    READY, ReviewDossierError, dossier_existing_public_candidate,
)
from .library_review_records_v05 import (
    CLAIM_ONLY, GATES, VIEW_SCHEMA, ClaimError,
    _public_evidence_url, review_claims,
)
from .library_search import LibrarySearchError
from .library_explore import ExploreError
from .public_discovery import DiscoveryError

SCHEMA = "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V05"

RECEIPT_CSS = """<style>
.review-submissions{border:1px solid #ccd8ea;background:#fff;
border-radius:13px;margin:22px 0;padding:19px}
.review-submissions h2{margin:0 0 9px}
.review-entry{padding:10px 0;border-top:1px solid #e6ebf3;overflow-wrap:anywhere}
.review-entry p{font-size:13px;color:#425777;margin:6px 0}
.review-entry .notice{font-weight:700;color:#8a4d0e}
</style>"""


def render_claims_panel(claims: dict, dossier: dict) -> str:
    """No untrusted freeform title, test command or review approval rendering."""
    if (type(claims) is not dict
            or claims.get("schema") != VIEW_SCHEMA
            or claims.get("status") != "SOURCE_LINKED_CLAIMS_UNVERIFIED_ONLY"
            or claims.get("independently_verified") is not False
            or claims.get("owner_approved") is not False
            or claims.get("auto_promoted") is not False
            or type(claims.get("claims")) is not list
            or type(claims.get("total_claims")) is not int
            or claims["total_claims"] != len(claims["claims"])
            or claims["total_claims"] > 500
            or claims.get("item_id") != dossier["item"]["library_item_id"]):
        raise ClaimError("source-bound receipt view invalid")
    lines = [
        '<section class="review-submissions"><h2>접수된 공개 검토 근거</h2>',
        '<p class="review-hint">접수는 출처·내용·수정 효과를 독립적으로 확인한 '
        '것이 아닙니다. 모든 항목은 미검증 주장으로 유지되며, 기존 6개 검증 '
        '관문과 승인은 변경되지 않습니다.</p>',
        '<p>후보에 결속된 접수 건수: <strong>'
        + str(claims["total_claims"]) + '</strong></p>',
    ]
    for gate in sorted(GATES):
        count = claims["gate_counts"].get(gate)
        if type(count) is not int or not 0 <= count <= 500:
            raise ClaimError("invalid source-bound gate summary")
        lines.append('<p class="subtitle">' + _t(gate) + ': '
                     + str(count) + '건 · 검증 여부: NOT_VERIFIED</p>')
    for entry in claims["claims"]:
        if (type(entry) is not dict or entry.get("status") != CLAIM_ONLY
                or entry.get("independent_verification") is not False
                or entry.get("source_id") != dossier["item"]["source_id"]
                or entry.get("source_sha256") != dossier["item"]["evidence_sha256"]
                or entry.get("item_id") != dossier["item"]["library_item_id"]
                or entry.get("gate") not in GATES):
            raise ClaimError("untrusted candidate evidence row")
        citation = _public_evidence_url(
            entry["public_evidence_url"], source_id=entry["source_id"])
        lines.extend([
            '<article class="review-entry"><p><strong>'
            + _t(entry["gate"]) + '</strong> · <span class="notice">'
            + CLAIM_ONLY + '</span></p>',
            '<p>제출된 버전 표기 (검증 전): '
            + _t(entry["version_hint"]) + '</p>',
            '<p>제출된 문서 SHA-256 (독립 계산·확인 전): <code>'
            + _t(entry["claimed_document_sha256"]) + '</code></p>',
            '<p><a target="_blank" rel="noopener noreferrer" href="'
            + _t(citation, 240) + '">제출된 공개 근거 URL 열기</a></p>',
            '<p>접수 시간(UTC): ' + _t(entry["recorded_utc"]) + '</p>',
            '</article>',
        ])
    lines.append('</section>')
    return "".join(lines)


def make_handler(root: Path, *, explorer=None, comparer=None,
                 reviewer=None, claims_loader=None):
    base = v04.make_handler(root, explorer=explorer,
                            comparer=comparer, reviewer=reviewer)
    if reviewer is None:
        reviewer = dossier_existing_public_candidate
    if claims_loader is None:
        claims_loader = review_claims

    class Handler(base):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            if status == 200 and mime == "text/html; charset=utf-8":
                # V0.4's inherited reply performs its own branding *after*
                # this override. Normalize the V0.2/0.3 base first, then
                # stamp V0.5. Keep V0.4 reply for trusted review-link insertion.
                content = v04._branding(content)
                content = (content.replace("V0.4 ·", "V0.5 ·")
                          .replace(v04.SCHEMA, SCHEMA))
                if RECEIPT_CSS not in content:
                    content = content.replace("</head>", RECEIPT_CSS + "</head>")
            return super().reply(status, content, mime)

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path == "/health" and not parts.query and not parts.fragment:
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY",
                                      "text/plain; charset=utf-8")
                return self.reply(200, json.dumps({
                    "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_READY",
                    "db_writes": 0, "review_receipt_writes": 0,
                    "scheduler_changes": 0, "auto_promoted": False,
                    "production_approved": False,
                }), "application/json; charset=utf-8")
            if not parts.path.startswith("/review/"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if len(self.path) > v03.MAX_RETURN_URL + 100 or parts.fragment:
                return self.reply(400, "BOUNDED_URL_ONLY", "text/plain; charset=utf-8")
            item_id = parts.path.removeprefix("/review/")
            if HEX64.fullmatch(item_id) is None:
                return self.reply(404, "ITEM_NOT_FOUND", "text/plain; charset=utf-8")
            try:
                context, selected = (v03.parse_search_request(parts.query)
                                     if parts.query else (None, ()))
            except v03.UIError:
                return self.reply(400, "INVALID_REVIEW_QUERY",
                                  "text/plain; charset=utf-8")
            try:
                dossier = reviewer(root, item_id=item_id)
                if dossier.get("status") != READY:
                    return self.reply(404, "SOURCE_LINKAGE_OR_ITEM_NO_GO",
                                      "text/plain; charset=utf-8")
                claims = claims_loader(root, dossier)
                back = v03._return_href(context, selected)
                html = v04.render_review(dossier, back=back)
                panel = render_claims_panel(claims, dossier)
                if "</main>" not in html:
                    raise ClaimError("review document missing layout boundary")
                return self.reply(200, html.replace("</main>", panel + "</main>"))
            except (ClaimError, ReviewDossierError, LibrarySearchError,
                    ExploreError, DiscoveryError, ValueError, TypeError, KeyError):
                return self.reply(503, "SOURCE_VALIDATION_FAILED_NO_GO",
                                  "text/plain; charset=utf-8")
            except (sqlite3.DatabaseError, OSError):
                return self.reply(503, "SOURCE_STORAGE_UNAVAILABLE_NO_GO",
                                  "text/plain; charset=utf-8")

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE V0.5 read-only public review status")
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
                "automatic_approval": False,
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
