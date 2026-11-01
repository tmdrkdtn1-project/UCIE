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
from urllib.parse import urlsplit

from . import library_browser_v07 as v07
from .library_browser_v02 import _head, _foot, _t
from .library_public_proof_v09 import (
    SCHEMA as PROBE_SCHEMA, BatchError, perform_public_probe_batch,
)
from .library_public_probe_v08 import ProbeError
from .library_review_records_v05 import ClaimError
from .library_audit_v07 import AuditError
from .library_explore import ExploreError
from .public_discovery import DiscoveryError

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
    text = (html.replace("V0.7 ·", "V0.9 ·")
            .replace("V0.8 ·", "V0.9 ·")
            .replace(v07.SCHEMA, SCHEMA))
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


def make_handler(root: Path, *, auditor=None, public_prober=None,
                 explorer=None, comparer=None, reviewer=None,
                 claims_loader=None):
    base = v07.make_handler(
        root, auditor=auditor, explorer=explorer,
        comparer=comparer, reviewer=reviewer, claims_loader=claims_loader)
    if public_prober is None:
        public_prober = perform_public_probe_batch

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
