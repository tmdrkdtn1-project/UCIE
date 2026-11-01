"""UCIE V1.0 browser: read-only replay of explicit public observations.

V0.9's search, audit, candidate selection and explicit network probe remain
available. Merely opening this V1.0 observation dashboard never makes public
HTTP calls or writes local proof records. Recording always requires the
separate owner-executed script, not a GET or POST button.
"""
from __future__ import annotations

import argparse
from http.server import HTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit

from . import library_browser_v09 as v09
from .library_browser_v02 import _head, _foot, _t
from .library_observation_receipts_v10 import (
    AUDIT_SCHEMA, ObservationError, replay_observations,
)
from .library_public_proof_v09 import BatchError
from .library_audit_v07 import AuditError

SCHEMA = "UCIE_LOCAL_PUBLIC_OBSERVATION_BROWSER_V10"
HEX = re.compile(r"[0-9a-f]{64}\Z")
STYLE = """<style>
.obs-title{margin:12px 0}.obs-alert{padding:14px;background:#edf3fa;
border-left:3px solid #4a78b7;margin:16px 0}
.obs-box{padding:15px;background:white;border:1px solid #dbe4ef;
border-radius:11px;margin:14px 0;overflow-wrap:anywhere}
.obs-box h3{margin:0 0 10px}.obs-flex{display:flex;gap:15px;flex-wrap:wrap}
.obs-stat{padding:13px;min-width:165px;border:1px solid #e2e8f2;
border-radius:9px;background:#fff}
</style>"""


def _brand(html: str) -> str:
    for old in ("V0.2 ·", "V0.3 ·", "V0.4 ·", "V0.5 ·", "V0.7 ·", "V0.9 ·"):
        html = html.replace(old, "V1.0 ·")
    for old in (
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02",
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V03",
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V04",
            "UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V05",
            "UCIE_LOCAL_PUBLIC_LIBRARY_AUDIT_BROWSER_V07",
            v09.SCHEMA):
        html = html.replace(old, SCHEMA)
    if STYLE not in html:
        html = html.replace("</head>", STYLE + "</head>")
    return html


def render_observation_dashboard(view: dict, *, item_id: str | None = None) -> str:
    if (type(view) is not dict or view.get("schema") != AUDIT_SCHEMA
            or view.get("source_linkage_valid") is not True
            or view.get("production_approved") is not False
            or view.get("automatic_promotions") != 0
            or view.get("actual_independent_fix_regressions") != 0
            or type(view.get("source_linked_candidates")) is not int
            or type(view.get("integrity_checked_observation_count")) is not int
            or type(view.get("observations")) is not list
            or len(view["observations"]) != view["integrity_checked_observation_count"]
            or len(view["observations"]) > 100):
        raise ObservationError("invalid source-bound observations view")
    if item_id is not None and (type(item_id) is not str
                                or HEX.fullmatch(item_id) is None):
        raise ObservationError("invalid selected observation item")
    subset = [x for x in view["observations"]
              if item_id is None or x["item_id"] == item_id]
    markup = [
        _head("UCIE 공개 원본 관측·재검사 현황"),
        '<p><a href="/audit">전체 감사로 돌아가기</a> · '
        '<a href="/audit/candidates">공개 후보 전체 목록</a></p>',
        '<p class="obs-alert">이 화면은 명시적으로 기록한 공개 병합 SHA·'
        '공식 문서 응답 해시의 영수증 무결성 및 현재 원장 결속만 검사합니다. '
        '수정 효과·릴리스 포함·라이선스 승인·독립 회귀시험·담당자 승인 '
        '모두 여전히 NOT_VERIFIED입니다. 자체 SHA는 디지털 서명이 아닙니다.'
        '</p><h2 class="obs-title">현재 공개 원본 관측 결과</h2>',
        '<div class="obs-flex">',
    ]
    for title, key in (
        ("원장에 결속된 후보", "source_linked_candidates"),
        ("무결성 재검사 영수증", "integrity_checked_observation_count"),
        ("관측이 있는 후보", "items_with_observations"),
        ("외부 오류 수정 독립 검증", "actual_independent_fix_regressions"),
        ("승인·서명된 규칙", "signed_rules"),
    ):
        n = view[key]
        if type(n) is not int or not 0 <= n <= 1000:
            raise ObservationError("invalid bounded observation count")
        markup.append('<div class="obs-stat"><strong>' + str(n)
                      + '</strong><p>' + _t(title) + '</p></div>')
    markup.append('</div>')
    if item_id is not None and not subset:
        markup.append('<section class="obs-box"><h3>이 후보의 관측 영수증 0건</h3>'
                      '<p>공개 원본 대조를 실행했더라도 별도 영수증 기록 '
                      '명령을 실행하기 전에는 저장된 자료가 없습니다.</p></section>')
    if not view["observations"]:
        markup.append('<section class="obs-box"><h3>저장된 관측 영수증 없음</h3>'
                      '<p>별도 PowerShell 등록 명령으로 명시적으로 '
                      '기록해야 하며, 브라우저는 자동 저장하지 않습니다.</p>'
                      '</section>')
    for entry in subset:
        if (type(entry) is not dict or type(entry.get("item_id")) is not str
                or HEX.fullmatch(entry["item_id"]) is None
                or type(entry.get("receipt_id")) is not str
                or HEX.fullmatch(entry["receipt_id"]) is None
                or type(entry.get("revision_hint")) is not str
                or not re.fullmatch("[0-9a-f]{40}", entry["revision_hint"])
                or entry.get("independently_verified_fix") is not False
                or entry.get("owner_approved") is not False
                or entry.get("identity_matched") not in (True, False)):
            raise ObservationError("unsafe observation row rendering")
        markup.extend([
            '<section class="obs-box"><h3>공개 원본 기록 · ',
            _t(entry["source_id"]), '</h3><p>후보 ID: <code>',
            entry["item_id"], '</code></p><p>원장 개정 SHA: <code>',
            entry["revision_hint"], '</code></p><p>공개 원본 관측 상태: ',
            _t(entry["metadata_status"]),
            '</p><p>현재 기록 내 SHA 일치: ',
            ("일치(수정 검증 아님)" if entry["identity_matched"]
             else "불일치 또는 미확인"),
            '</p><p>관측 영수증 ID: <code>',
            entry["receipt_id"],
            '</code></p><p>기록 시간 UTC: ',
            _t(entry["recorded_utc"]),
            '</p><p>공식 문서 응답 해시 확인 건수: ',
            str(entry["document_sha_checks"]),
            '</p><p>실제 오류 수정 독립 검증: NOT_VERIFIED</p>'
            '<p><a href="/audit/item/' + entry["item_id"],
            '">후보별 감사·검토로 돌아가기</a></p></section>',
        ])
    markup.append(_foot())
    return _brand("".join(markup))


def make_handler(root: Path, *, observation_reader=None,
                 public_prober=None, auditor=None, explorer=None,
                 comparer=None, reviewer=None, claims_loader=None):
    base = v09.make_handler(
        root, public_prober=public_prober, auditor=auditor,
        explorer=explorer, comparer=comparer,
        reviewer=reviewer, claims_loader=claims_loader)
    read = replay_observations if observation_reader is None else observation_reader

    class Handler(base):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            if status == 200 and mime == "text/html; charset=utf-8":
                content = _brand(content)
                parts = urlsplit(self.path)
                if parts.path.startswith("/audit/item/"):
                    ident = parts.path.removeprefix("/audit/item/")
                    if HEX.fullmatch(ident) is not None:
                        content = content.replace("</main>", (
                            '<section class="obs-box"><p><a href="/observations/item/'
                            + ident + '">이 후보의 공개 원본 관측 영수증 확인</a>'
                            '</p></section></main>'))
                if parts.path in ("/audit", "/audit/candidates"):
                    content = content.replace("</main>",
                        '<section class="obs-box"><p><a href="/observations">'
                        '전체 공개 원본 관측 영수증·무결성 확인</a></p>'
                        '</section></main>')
            return super().reply(status, content, mime)

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path == "/health" and not parts.query and not parts.fragment:
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
                return self.reply(200, json.dumps({
                    "schema": SCHEMA,
                    "status": "LOCAL_READ_ONLY_UI_READY",
                    "automatic_observation_writes": 0,
                    "external_public_calls_on_observation_pages": 0,
                    "operating_db_writes": 0,
                    "scheduler_changes": 0,
                    "auto_promoted": False,
                }), "application/json; charset=utf-8")
            if parts.path != "/observations" and not parts.path.startswith(
                    "/observations/item/"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if parts.query or parts.fragment or len(self.path) > 100:
                return self.reply(400, "INVALID_OBSERVATION_REQUEST",
                                  "text/plain; charset=utf-8")
            selected = None
            if parts.path.startswith("/observations/item/"):
                selected = parts.path.removeprefix("/observations/item/")
                if HEX.fullmatch(selected) is None:
                    return self.reply(404, "OBSERVATION_ITEM_NOT_FOUND",
                                      "text/plain; charset=utf-8")
            try:
                view = read(root)
                if selected is not None and (
                        selected not in {row["item_id"] for row in view["observations"]}):
                    # All source-bound candidate identities are checked in
                    # replay; absent receipt is an empty candidate state.
                    pass
                return self.reply(200, render_observation_dashboard(
                    view, item_id=selected))
            except (ObservationError, BatchError, AuditError, ValueError,
                    TypeError, KeyError):
                return self.reply(503, "OBSERVATION_REPLAY_NO_GO",
                                  "text/plain; charset=utf-8")
            except (OSError, sqlite3.DatabaseError):
                return self.reply(503, "OBSERVATION_STORAGE_NO_GO",
                                  "text/plain; charset=utf-8")

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE V1.0 read-only observation audit browser")
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
                "operating_db_writes": 0, "scheduler_changes": 0,
                "observation_writes": 0, "auto_approval": False,
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
