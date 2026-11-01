"""UCIE V1.1 read-only offline independent-upstream review checklist browser."""
from __future__ import annotations

import argparse
from http.server import HTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from . import library_browser_v10 as v10
from .library_browser_v02 import _head, _foot, _t
from .library_upstream_review_v11 import (
    ReviewBundleError, SCHEMA as BUNDLE_SCHEMA, review_current_candidate,
)
from .library_observation_receipts_v10 import ObservationError

SCHEMA = "UCIE_LOCAL_SOURCE_REVIEW_BROWSER_V11"
HEX = re.compile(r"[0-9a-f]{64}\Z")
CSS = """<style>.v11-item{border:1px solid #dbe5f1;border-radius:11px;
padding:15px;background:#fff;margin:12px 0}.v11-note{background:#ebf2fb;
border-left:3px solid #4779ae;padding:13px}
.v11-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px}
</style>"""


def _brand(content: str) -> str:
    for old in ("V0.2 ·", "V0.3 ·", "V0.4 ·", "V0.5 ·",
                "V0.7 ·", "V0.9 ·", "V1.0 ·"):
        content = content.replace(old, "V1.1 ·")
    for old in ("UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02",
                "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V03",
                "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V04",
                "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V05",
                "UCIE_LOCAL_PUBLIC_LIBRARY_AUDIT_BROWSER_V07",
                "UCIE_LOCAL_PUBLIC_SOURCE_CHECK_BROWSER_V09", v10.SCHEMA):
        content = content.replace(old, SCHEMA)
    if CSS not in content:
        content = content.replace("</head>", CSS + "</head>")
    return content


def render_review(report: dict) -> str:
    if (type(report) is not dict or report.get("schema") != BUNDLE_SCHEMA
            or report.get("status") != "UPSTREAM_FIX_AND_RELEASE_REVIEW_REQUIRED_NO_GO"
            or report.get("approved_rule_count") != 0
            or report.get("exportable_rule_count") != 0
            or report.get("auto_promotion") is not False
            or report.get("independent_upstream_regression_passes") != 0
            or type(report.get("requirements")) is not list
            or len(report["requirements"]) != 7):
        raise ReviewBundleError("unsafe review report")
    identity = report.get("item_id")
    if type(identity) is not str or HEX.fullmatch(identity) is None:
        raise ReviewBundleError("invalid review identity")
    out = [
        _head("UCIE 독립 회귀시험·공식 릴리스 검토 준비"),
        '<p><a href="/audit/item/' + identity + '">후보 감사로 돌아가기</a> · '
        '<a href="/observations/item/' + identity + '">원본 관측 영수증</a></p>',
        '<p class="v11-note">이 화면은 UCIE 자체 안전검사 PASS와 '
        '외부 소스 변경의 독립 회귀시험을 엄격히 구분합니다. '
        '릴리스 태그에 원본 커밋이 포함됐더라도 실제 오류 수정, '
        '호환 버전, 라이선스 및 담당자 승인은 검증되지 않았습니다.</p>',
        '<div class="v11-item"><h2>출처 결속 검토</h2><p>후보 SHA: '
        '<code>' + identity + '</code></p><p>출처: '
        + _t(report["source_id"]) + '</p><p>관측 영수증: '
        + str(report["observation_count"]) + '건</p><p>'
        'UCIE 자체 안전 회귀시험: ' + str(report["ucie_owned_guard_tests_passed"])
        + '/6 PASS</p><p>실제 공개 수정 독립 회귀시험: 0 PASS</p></div>',
        '<h2>독립 검증 전 차단 관문</h2><div class="v11-grid">',
    ]
    for gate in report["requirements"]:
        if (type(gate) is not dict
                or gate.get("status") not in (
                    "NOT_PERFORMED", "NOT_PROVEN_IN_OFFLINE_PACKET",
                    "NOT_VERIFIED", "NOT_APPROVED")
                or gate.get("automatic_approval") is not False):
            raise ReviewBundleError("unapproved gate state")
        out.append('<section class="v11-item"><h3>' + _t(gate.get("gate"))
                   + '</h3><p><strong>' + _t(gate["status"])
                   + '</strong></p><p>' + _t(gate.get("human_next_action"), 330)
                   + '</p></section>')
    out.extend([
        '</div><section class="v11-item"><h3>오류 예방 규칙 검토 초안</h3>',
        '<p>' + _t(report["fixed_ucie_review_question"], 260) + '</p>',
        '<p>' + _t(report["safe_review_guidance"], 260) + '</p>',
        '<p>실행 가능 규칙 생성 없음 · 버전 적용성 미검증 · 승인/배포 차단</p>',
        '<p>보고 SHA-256: <code>' + report["bundle_sha256"] + '</code>'
        ' (서명 아님)</p></section>', _foot(),
    ])
    return _brand("".join(out))


def make_handler(root: Path, *, bundle_reader=None,
                 observation_reader=None, public_prober=None,
                 auditor=None, explorer=None, comparer=None,
                 reviewer=None, claims_loader=None):
    base = v10.make_handler(
        root, observation_reader=observation_reader,
        public_prober=public_prober, auditor=auditor,
        explorer=explorer, comparer=comparer,
        reviewer=reviewer, claims_loader=claims_loader)
    review = review_current_candidate if bundle_reader is None else bundle_reader

    class Handler(base):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            if status == 200 and mime == "text/html; charset=utf-8":
                content = _brand(content)
                part = urlsplit(self.path)
                if part.path.startswith("/audit/item/"):
                    ident = part.path.removeprefix("/audit/item/")
                    if HEX.fullmatch(ident) is not None:
                        content = content.replace(
                            "</main>", '<section class="v11-item"><a href="/review-bundle/'
                            + ident + '">독립 회귀시험·릴리스 검토 준비표</a>'
                            '</section></main>')
            return super().reply(status, content, mime)

        def do_GET(self):
            part = urlsplit(self.path)
            if part.path == "/health" and not part.query and not part.fragment:
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
                return self.reply(200, json.dumps({
                    "schema": SCHEMA, "status": "LOCAL_READ_ONLY_UI_READY",
                    "automatic_public_checks": 0,
                    "automatic_rule_approvals": 0,
                    "operating_db_writes": 0,
                }), "application/json; charset=utf-8")
            if not part.path.startswith("/review-bundle/"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if len(self.path) > 100 or part.query or part.fragment:
                return self.reply(400, "EXACT_REVIEW_ROUTE_ONLY", "text/plain; charset=utf-8")
            ident = part.path.removeprefix("/review-bundle/")
            if HEX.fullmatch(ident) is None:
                return self.reply(404, "SOURCE_REVIEW_ITEM_NOT_FOUND",
                                  "text/plain; charset=utf-8")
            try:
                return self.reply(200, render_review(review(root, item_id=ident)))
            except (ReviewBundleError, ObservationError, ValueError,
                    TypeError, KeyError):
                return self.reply(503, "SOURCE_REVIEW_NO_GO", "text/plain; charset=utf-8")
            except (OSError, sqlite3.DatabaseError):
                return self.reply(503, "REVIEW_STORAGE_NO_GO", "text/plain; charset=utf-8")

    return Handler


def main() -> int:
    p = argparse.ArgumentParser(description="UCIE V1.1 local source review browser")
    p.add_argument("--port", type=int, default=0)
    args = p.parse_args()
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
                "operating_db_writes": 0, "rule_approvals": 0,
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
