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

# Scoped preview-only accessibility adjustments; no frozen V04 CSS changes.
PREVIEW_STYLES = """
.skip-link{position:absolute;left:12px;top:-100px;padding:12px;
background:#73d6d0;color:#10212b;z-index:20}
.skip-link:focus{top:12px}
summary:focus-visible,.back:focus-visible{outline:3px solid #d5ff62;outline-offset:4px}
main{max-width:760px}main p,main li,main dd{overflow-wrap:anywhere}
main a{display:inline-block;max-width:100%;overflow-wrap:anywhere}
main ol{padding-inline-start:1.75rem;margin:1rem 0}
main ol li{padding:.25rem 0;line-height:1.55}
main ol li>a{display:block;width:100%;max-width:100%;
min-width:0;overflow-wrap:break-word;word-break:keep-all;
padding:.5rem 0;min-height:44px}
main ol li::marker{color:#dbe9f6;font-variant-numeric:tabular-nums}
main section{min-width:0}main details{max-width:100%}
.preview-steps{color:#c6d5e5;padding:0 0 0 1.5rem;margin:16px 0 20px}
.preview-steps li{padding:5px 0}
.case-choices{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;
margin:18px 0 0;padding:0;list-style:none;counter-reset:ucie-case}
.case-choices li{counter-increment:ucie-case;padding:0;min-width:0;position:relative}
.case-choices li>a{position:relative;box-sizing:border-box;display:block;
min-height:60px;padding:16px 15px 16px 48px;border:1px solid #53687e;
border-radius:12px;text-decoration:none;color:#b1e5ff;
font-weight:650;line-height:1.55;word-break:keep-all;overflow-wrap:anywhere}
.case-choices li>a::before{content:counter(ucie-case);
position:absolute;top:15px;left:15px;color:#dbe9f6;font-weight:750}
.case-choices li>a:hover{background:#23384b;border-color:#73d6d0}
.case-choices li>a:focus-visible{outline:3px solid #d5ff62;outline-offset:3px}
.preview-boundary{font-size:13px;margin:22px 0 0}
@media(max-width:390px){main{margin:18px auto 36px;padding:0 12px}
.panel{padding:16px}header{padding:16px 12px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important}}
"""


def _shell(content: str) -> str:
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src \'none\'; style-src \'unsafe-inline\'; '
        'base-uri \'none\'; form-action \'none\'">'
        '<title>기술 확인 안내 · UCIE</title><style>' + STYLES + PREVIEW_STYLES + '</style>'
        '</head><body><a class="skip-link" href="#main">본문으로 건너뛰기</a>'
        '<header><strong>UCIE · 기술 확인 안내</strong></header>'
        '<main id="main">' + content + '</main>'
        '<footer>실제 사용 환경의 호환성·권리·독립 QA 미확인 · 독립 미리보기</footer>'
        '</body></html>'
    )


def route_truth_request(method: str, target: str, *,
                        receipts: dict | None = None) -> tuple[int, str]:
    """Exact GET selectors; show only already precomputed opt-in receipts."""
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
            '<section class="panel" aria-labelledby="preview-title">'
            '<h1 id="preview-title">어떤 기술 설명을 살펴볼까요?</h1>'
            '<p>준비된 두 사례만 살펴봅니다. 이 화면은 고객 코드를 받지 않습니다.</p>'
            '<h2>이 화면에서 할 수 있는 일</h2>'
            '<ol class="preview-steps"><li>아래 기술 사례를 하나 고릅니다.</li>'
            '<li>근거와 UCIE 자체 예제의 확인 범위를 읽습니다.</li>'
            '<li>지금 확인할 일과 아직 모르는 내용을 구분합니다.</li></ol>'
            '<h2>살펴볼 수 있는 기술</h2>'
            '<ol class="case-choices" aria-label="기술 사례 선택">' + links + '</ol>'
            '<p class="preview-boundary">고객 환경을 자동으로 점검하거나 '
            '코드를 수정하지 않습니다. 사용권·독립 품질 검증은 미확인입니다.</p>'
            '</section>')
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
    receipt = None if receipts is None else receipts.get(chosen)
    html = render_b2_receipt_truth_view(
        chosen, source_tag=known[chosen]["source_tag"], receipt=receipt)
    return 200, _shell(
        '<a class="back" href="' + ROUTE + '">다른 사례 보기</a>'
        '<h1>기술 안내와 확인된 범위</h1>'
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
                status, page = route_truth_request(
                    method, self.path,
                    receipts=getattr(self.server, "ucie_receipts", None))
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
    parser.add_argument("--run-synthetic-demo", action="store_true",
                        help="Explicitly run two UCIE-authored synthetic fixtures before starting; no customer code")
    args = parser.parse_args(argv)
    if args.port and not 1024 <= args.port <= 65535:
        raise ValueError("PORT_OUT_OF_RANGE")
    require_local_work("VIRTUAL_LIBRARY")
    receipts = None
    if args.run_synthetic_demo:
        # Execute only at explicit startup, once per approved fixed case.
        # Never run a trial from HTTP GET, POST or a preview render.
        from .b1_first_party_receipt_link_v01 import run_scoped_receipt
        caps = build_pinned_b1_capsules()
        if len(caps) != 2 or len({c["case_id"] for c in caps}) != 2:
            raise ValueError("UNEXPECTED_FIXED_CASES")
        receipts = {
            c["case_id"]: run_scoped_receipt(c["case_id"], c["source_tag"])
            for c in caps
        }
    with ThreadingHTTPServer((HOST, args.port), TruthPreviewHandler) as server:
        server.ucie_receipts = receipts
        url = "http://" + HOST + ":" + str(server.server_port) + ROUTE
        print("UCIE_V2_B2_TRUTH_PREVIEW_READY " + url, flush=True)
        if args.open_browser:
            import webbrowser
            webbrowser.open(url, new=2)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
