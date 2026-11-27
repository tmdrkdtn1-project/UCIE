"""UCIE V2 isolated B2 evidence-truth browser preview (GET-only, loopback).

This does not register routes on frozen owner V04. It never executes a trial
from HTTP, imports customer files or reads/changes any operating service.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

from .b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from .b2_receipt_truth_view_v01 import render_b2_receipt_truth_view
from .v2_b1_b4_explorer_v01 import STYLES
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_V2_ISOLATED_B2_RECEIPT_PREVIEW_V01"
ROUTE = "/v2/truth"
HOST = "127.0.0.1"


def _shell(content: str) -> str:
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src \'none\'; style-src \'unsafe-inline\'; '
        'base-uri \'none\'; form-action \'none\'">'
        '<title>기술 확인 안내 · UCIE</title><style>' + STYLES + '</style>'
        '</head><body><header><strong>UCIE · 기술 확인 안내</strong></header>'
        '<main id="main">' + content + '</main>'
        '<footer>실제 사용 환경의 호환성·권리·독립 QA 미확인 · 독립 미리보기</footer>'
        '</body></html>'
    )


def route_truth_request(method: str, target: str) -> tuple[int, str]:
    """Exact GET route and exact two first-party case selectors only."""
    if method != "GET":
        return 405, ""
    if type(target) is not str or len(target) > 220:
        return 400, ""
    url = urlsplit(target)
    if (url.path != ROUTE or url.fragment or
            (url.netloc or url.scheme)):
        return 404, ""
    caps = build_pinned_b1_capsules()
    known = {c["case_id"]: c for c in caps}
    if not url.query:
        links = "".join(
            '<li><a href="' + ROUTE + '?' +
            escape(urlencode({"case": c["case_id"]}), quote=True) + '">' +
            ("Python" if c["source_id"] == "doc:python/cpython" else "Git") +
            ' · 공식 문서 범위 살펴보기</a></li>'
            for c in caps
        )
        return 200, _shell(
            '<section class="panel"><h1>어떤 기술 설명을 살펴볼까요?</h1>'
            '<p>준비된 두 사례만 살펴봅니다. 이 화면은 고객 코드를 받지 않습니다.</p>'
            '<ol>' + links + '</ol></section>')
    try:
        parsed = parse_qs(url.query, strict_parsing=True,
                          keep_blank_values=True, max_num_fields=1)
    except (UnicodeError, ValueError):
        return 400, ""
    if set(parsed) != {"case"} or len(parsed["case"]) != 1:
        return 400, ""
    chosen = parsed["case"][0]
    if chosen not in known:
        return 400, ""
    # No implicit trial here: screen explicitly states absence of receipt.
    html = render_b2_receipt_truth_view(
        chosen, source_tag=known[chosen]["source_tag"], receipt=None)
    return 200, _shell(
        '<a class="back" href="' + ROUTE + '">다른 사례 보기</a>'
        '<section class="panel">' + html + '</section>')


class TruthPreviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond("GET")

    def do_POST(self):
        self._respond("POST")

    def _respond(self, method: str):
        # Refuse DNS-rebinding / proxy Host aliases and duplicate Host fields.
        # A valid loopback socket address alone is not a trustworthy Host claim.
        hosts = self.headers.get_all("Host", [])
        expected_host = HOST + ":" + str(self.server.server_port)
        if hosts != [expected_host]:
            status, page = 403, ""
        else:
            try:
                status, page = route_truth_request(method, self.path)
            except (ValueError, KeyError, TypeError):
                status, page = 500, ""
        data = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def log_message(self, *_args):
        return  # Do not log selector data or private browser access.


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE isolated B2 truth preview")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args(argv)
    if args.port and not 1024 <= args.port <= 65535:
        raise ValueError("PORT_OUT_OF_RANGE")
    require_local_work("VIRTUAL_LIBRARY")
    with ThreadingHTTPServer((HOST, args.port), TruthPreviewHandler) as server:
        url = "http://" + HOST + ":" + str(server.server_port) + ROUTE
        print("UCIE_V2_B2_TRUTH_PREVIEW_READY " + url, flush=True)
        if args.open_browser:
            import webbrowser
            webbrowser.open(url, new=2)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
