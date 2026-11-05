"""UCIE-only read-only search of distinct SkillBook and existing W04 shelves.

A SkillBook official-document SHA and a W04 public PR candidate are NOT
equivalent evidence. No DB migration, approval, export or background reader.
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
from urllib.parse import parse_qs, urlencode, urlsplit

from . import library_browser_skillbook_v01 as previous
from .library_search import (
    ALLOWED_DOMAINS, LibrarySearchError, SCHEMA as W04_SCHEMA,
    search_existing_public_library,
)
from .public_discovery import DiscoveryError
from .skillbook_product_v01 import (
    SKILLBOOK_ID, SOURCE_DOCUMENT_SHA256, SkillBookProductError,
    search_skillbooks,
)
from .skillbook_scandir_qa_v01 import CASES as W08_CASES
from .source_registry import SourceRegistryError, get_source

SCHEMA = "UCIE_SKILLBOOK_W04_FEDERATED_READONLY_V01"
SHELVES = ("skillbooks", "all", "public")
KINDS = ("", "REUSABLE_SKILL", "PREVENTION_RULE", "PUBLIC_TECHNICAL_EVIDENCE")
QUERY = re.compile(r"[\w .-]{0,80}\Z", re.UNICODE)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class FederationError(ValueError):
    pass


def parse_filters(raw: str) -> dict:
    if type(raw) is not str or len(raw) > 280:
        raise FederationError("invalid URL size")
    try:
        args = parse_qs(raw, keep_blank_values=True, strict_parsing=True,
                        max_num_fields=5, encoding="utf-8", errors="strict") if raw else {}
    except (ValueError, UnicodeError) as exc:
        raise FederationError("invalid query encoding") from exc
    if (set(args) - {"q", "shelf", "kind", "domain", "limit"}
            or any(len(v) != 1 for v in args.values())):
        raise FederationError("unknown or duplicate filter")
    result = {
        "query": args.get("q", [""])[0],
        "shelf": args.get("shelf", ["skillbooks"])[0],
        "kind": args.get("kind", [""])[0],
        "domain": args.get("domain", [""])[0],
        "limit": args.get("limit", ["10"])[0],
    }
    if (QUERY.fullmatch(result["query"]) is None
            or result["shelf"] not in SHELVES or result["kind"] not in KINDS
            or result["domain"] not in ("", *ALLOWED_DOMAINS)
            or result["limit"] not in ("5", "10", "20")):
        raise FederationError("filter not allowed")
    result["limit"] = int(result["limit"])
    return result


def _safe_filters(filters: dict) -> dict:
    if (type(filters) is not dict
            or set(filters) != {"query", "shelf", "kind", "domain", "limit"}
            or type(filters["limit"]) is not int):
        raise FederationError("invalid internal filters")
    parsed = parse_filters(urlencode({
        "q": filters["query"], "shelf": filters["shelf"],
        "kind": filters["kind"], "domain": filters["domain"],
        "limit": filters["limit"],
    }))
    if parsed != filters:
        raise FederationError("filter drift")
    return parsed


def _read_public(report: dict, limit: int) -> tuple[str, int | None, list]:
    if (type(report) is not dict or report.get("schema") != W04_SCHEMA
            or report.get("network_requests") != 0
            or report.get("operating_database_writes") != 0
            or report.get("approved_or_exportable_items") != 0
            or report.get("auto_promoted") is not False):
        raise FederationError("untrusted W04 response")
    status = report.get("status")
    if status == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        if report.get("items") != []:
            raise FederationError("incomplete W04 leaked results")
        return status, None, []
    if status != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO":
        raise FederationError("unexpected W04 status")
    rows, count = report.get("items"), report.get("total_matches")
    if (type(rows) is not list or type(count) is not int
            or count < 0 or len(rows) > min(count, limit)):
        raise FederationError("invalid W04 result bound")
    for item in rows:
        if (type(item) is not dict
                or type(item.get("library_item_id")) is not str
                or HEX64.fullmatch(item["library_item_id"]) is None
                or item.get("kind") not in KINDS[2:]
                or item.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"
                or item.get("human_approved") is not False
                or item.get("export_allowed") is not False):
            raise FederationError("untrusted W04 item")
        try:
            source = get_source(item.get("source_id"))
        except (SourceRegistryError, TypeError) as exc:
            raise FederationError("unknown W04 public source") from exc
        if source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
            raise FederationError("W04 source boundary mismatch")
    return status, count, list(rows)


def search_federated(root: Path, *, filters: dict, public_reader=None) -> dict:
    """Default SkillBook queries never read SQLite; public shelf is opt-in."""
    f = _safe_filters(filters)
    q, shelf, kind, domain, limit = (
        f["query"], f["shelf"], f["kind"], f["domain"], f["limit"])
    books = []
    if (shelf in ("skillbooks", "all") and kind in ("", "REUSABLE_SKILL")
            and domain in ("", "Python")):
        found = search_skillbooks(query=q, kind="REUSABLE_SKILL", language="Python")
        if (found.get("status") != "READ_ONLY_FIRST_PARTY_DRAFT_CATALOG"
                or found.get("approved_reusable_packages") != 0
                or found.get("network_requests") != 0
                or found.get("operating_database_writes") != 0):
            raise FederationError("untrusted SkillBook")
        books = list(found["items"])
        if (len(books) > 1 or any(
                row.get("human_approved") is not False
                or row.get("export_allowed") is not False for row in books)):
            raise FederationError("untrusted SkillBook approval")
    state, total, candidates = "NOT_REQUESTED", None, []
    if shelf in ("all", "public") and kind != "REUSABLE_SKILL":
        if not q.isascii():
            # W04 rejects non-ASCII queries. Never turn Korean into an
            # empty W04 query, thereby claiming false result counts.
            state = "W04_NONASCII_QUERY_NOT_SUPPORTED_NO_SEARCH"
        else:
            reader = search_existing_public_library if public_reader is None else public_reader
            result = reader(root, query=q, kind=kind or None,
                            domain=domain or None, limit=limit)
            state, total, candidates = _read_public(result, limit)
    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_TWO_SHELF_DRAFT_NOT_APPROVED",
        **f,
        "skillbooks": books, "public_evidence_candidates": candidates,
        "public_candidate_total": total, "public_shelf_status": state,
        "distinct_evidence_units_not_joined": True,
        "legacy_sqlite_index_migrated": False,
        "human_approved": False, "export_allowed": False,
        "approved_packages": 0, "operating_database_writes": 0,
        "network_requests": 0, "rule_promotions": 0,
    }


def render_federated(result: dict) -> str:
    if (type(result) is not dict or result.get("schema") != SCHEMA
            or result.get("status") != "READ_ONLY_TWO_SHELF_DRAFT_NOT_APPROVED"
            or result.get("export_allowed") is not False
            or result.get("distinct_evidence_units_not_joined") is not True):
        raise FederationError("unsafe HTML render")
    e = lambda value: escape(str(value), quote=True)
    choices = [
        ("shelf", [("skillbooks", "SkillBook"), ("all", "전체"),
                   ("public", "W04 후보")]),
        ("kind", [("", "모든 종류"), ("REUSABLE_SKILL", "재사용 기술"),
                  ("PREVENTION_RULE", "예방 후보"),
                  ("PUBLIC_TECHNICAL_EVIDENCE", "공개 후보")]),
        ("domain", [("", "모든 분야")]
         + [(x, x) for x in sorted(ALLOWED_DOMAINS)]),
        ("limit", [("5", "5"), ("10", "10"), ("20", "20")]),
    ]
    parts = [
        "<p>SkillBook 공식문서 근거와 W04 공개 PR 후보는 별도 자산입니다. "
        "같은 소유자라 하더라도 검증 결과가 같다는 의미는 아닙니다.</p>",
        '<p>검색 결과는 공개 출처와 기술 분류 메타데이터 기준입니다. '
        '표시 순서는 성능·검증 수준 또는 검색 관련도 순위가 아닙니다.</p>',
        '<section class="panel"><form method="get" action="/catalog">',
        '<label>검색어<input name="q" maxlength="80" value="'
        + e(result["query"]) + '"></label>',
    ]
    korean_labels = {
        "shelf": "자료 구분", "kind": "자료 유형",
        "domain": "기술 분야", "limit": "표시 건수",
    }
    for key, opts in choices:
        parts.append('<label>' + e(korean_labels[key])
                     + '<select name="' + key + '">')
        for value, label in opts:
            parts.append('<option value="' + e(value) + '"'
                         + (' selected' if value == str(result[key]) else "")
                         + '>' + e(label) + '</option>')
        parts.append('</select></label>')
    parts += ['<button type="submit">검색</button></form></section>',
              '<section class="panel"><h2>SkillBook 초안</h2>']
    for book in result["skillbooks"]:
        parts.append('<p><a href="/skillbooks/' + e(book["skillbook_id"])
                     + '">' + e(book["title"]) + '</a> · '
                     + 'UCIE 제작 초안 · 미승인 · 내보내기 불가</p>')
    if not result["skillbooks"]:
        parts.append("<p>조건에 맞는 SkillBook 없음</p>")
    public_status_labels = {
        "NOT_REQUESTED": "검색하지 않음 (SkillBook 전용 검색)",
        "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO":
            "미검증 공개 근거 검색 완료 · 승인/배포 불가",
        "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
            "공개 근거 출처 연결 미완료 · 결과 표시 차단",
        "W04_NONASCII_QUERY_NOT_SUPPORTED_NO_SEARCH":
            "W04는 현재 영문 검색어만 지원 · W04 조회 생략",
    }
    public_state = result["public_shelf_status"]
    if public_state not in public_status_labels:
        raise FederationError("unrecognized W04 display status")
    parts += [
        '</section><section class="panel"><h2>W04 공개 근거 후보</h2>',
        '<p>조회 상태: ' + e(public_status_labels[public_state]) + '</p>',
        '<details><summary>기술 상태 코드</summary><code>'
        + e(public_state) + '</code></details>',
    ]
    if result["public_candidate_total"] is not None:
        parts.append(
            '<p>전체 일치 후보: ' + str(result["public_candidate_total"])
            + '건 · 현재 ' + str(len(result["public_evidence_candidates"]))
            + '건 표시 (기존 W04 정렬순, 관련도 순위 아님)</p>'
        )
    if result["public_evidence_candidates"]:
        parts.append('<ol aria-label="W04 공개 근거 검색 결과">')
        for item in result["public_evidence_candidates"]:
            digest = item["library_item_id"]
            revision = item.get("revision_hint")
            revision_label = (revision[:100] if type(revision) is str and revision
                              else "개정 정보 미확인")
            parts.append(
                '<li><strong>분류: ' + e(item.get("purpose_code", ""))
                + '</strong> · ' + e(item["kind"])
                + '<p>출처: ' + e(item["source_id"])
                + ' · 개정: ' + e(revision_label)
                + ' · 후보 ID: <code>' + e(digest[:12]) + '</code>'
                + ' · 미승인 · 내보내기 불가</p>'
                + '<p><a href="/item/' + digest
                + '">이 후보의 근거·상세 확인</a></p></li>'
            )
        parts.append('</ol>')
    parts += ['</section><p><a href="/">기존 W04 검색</a> · '
              '<a href="/skillbooks">SkillBook 검색</a> · '
              '<a href="/skillbooks/qa-plan">SkillBook 검증 계획</a> · '
              '<a href="/catalog.json">JSON 계약</a></p>']
    template = previous._template("UCIE SkillBook + W04 읽기 전용 검색", "")
    template = template.replace("UCIE_LOCAL_SOURCE_REVIEW_BROWSER_V11", SCHEMA)
    template = template.replace("UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02", SCHEMA)
    return template.replace("<footer>", "".join(parts) + "<footer>", 1)


QA_PLAN_SCHEMA = "UCIE_W08_SKILLBOOK_QA_PLAN_BROWSER_V01"
QA_PLAN_STATUS = "MANUAL_SYNTHETIC_QA_NOT_RUN_IN_BROWSER"


def preview_skillbook_qa_plan() -> dict:
    """Static manifest only: NEVER runs synthetic fixtures via HTTP GET."""
    return {
        "schema": QA_PLAN_SCHEMA,
        "status": QA_PLAN_STATUS,
        "skillbook_id": SKILLBOOK_ID,
        "source_document_sha256": SOURCE_DOCUMENT_SHA256,
        "case_ids": [name for name, _ in W08_CASES],
        "case_count": len(W08_CASES),
        "runner_module": "ucie_miner.skillbook_scandir_qa_v01",
        "owner_ps1": r"D:\UCIE\scripts\ucie_skillbook_scandir_qa_v01.ps1",
        "qa_receipt_loaded": False,
        "browser_executes_tests": False,
        "independent_qa_verified": False,
        "security_review_approved": False,
        "human_approved": False,
        "export_allowed": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }


def render_skillbook_qa_plan(plan: dict) -> str:
    """Explain what's testable without fabricating a PASS or executing it."""
    if (type(plan) is not dict or plan.get("schema") != QA_PLAN_SCHEMA
            or plan.get("status") != QA_PLAN_STATUS
            or plan.get("skillbook_id") != SKILLBOOK_ID
            or plan.get("browser_executes_tests") is not False
            or plan.get("qa_receipt_loaded") is not False
            or plan.get("independent_qa_verified") is not False
            or plan.get("human_approved") is not False
            or plan.get("export_allowed") is not False
            or plan.get("case_count") != 9
            or plan.get("case_ids") != [name for name, _ in W08_CASES]):
        raise FederationError("untrusted QA display manifest")
    e = lambda value: escape(str(value), quote=True)
    content = [
        '<p><a href="/catalog">통합 도서관으로 돌아가기</a> · '
        '<a href="/skillbooks">SkillBook 검색</a></p>',
        '<section class="panel"><h2>실행하지 않은 QA 계획</h2>',
        '<p>이 페이지는 검증 항목의 목록만 보여줍니다. '
        '브라우저 조회만으로 시험을 실행하거나 PASS, 외부 독립 인증, '
        '보안·라이선스·배포 승인을 부여하지 않습니다.</p>',
        '<p>검증할 SkillBook: ' + e(plan["skillbook_id"]) + '</p>',
        '<p>시험 항목 ' + str(plan["case_count"]) + '개</p><ol>',
    ]
    for case_id in plan["case_ids"]:
        content.append("<li>" + e(case_id) + "</li>")
    content += [
        '</ol><p>UCIE 소유자 Windows PowerShell에서 독립적으로 실행:</p>',
        '<pre><code>&amp; &#39;' + e(plan["owner_ps1"]) + '&#39;</code></pre>',
        '<p>실제 실행한 후 출력되는 JSON 영수증은 소스 SHA와 각 시험 '
        '결과를 포함합니다. 이 UI는 외부/운영 파일을 스캔하지 않습니다.</p>',
        '<p>검증 상태: 합성 테스트 실행은 이 화면에서 미실행 · '
        '독립 QA 미검증 · 승인/내보내기 불가</p></section>',
    ]
    page = previous._template("SkillBook 001 · W08 검증 계획", "".join(content))
    page = page.replace("UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02", QA_PLAN_SCHEMA)
    return page


def make_handler(root: Path, *, public_reader=None, **legacy_injections):
    base = previous.make_handler(root, **legacy_injections)

    class Handler(base):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            # Only the federated launcher supplies /catalog; leave standalone
            # V1.1 and standalone SkillBook launchers untouched.
            route = urlsplit(self.path).path
            if (status == 200 and mime == "text/html; charset=utf-8"
                    and type(content) is str
                    and (route == "/" or route.startswith("/skillbooks"))
                    and "</header>" in content
                    and 'href="/catalog"' not in content):
                jump = (
                    '<nav class="panel" aria-label="UCIE 통합 도서관으로 이동">'
                    '<strong><a href="/catalog">'
                    '통합 도서관 열기 (SkillBook + W04)</a></strong>'
                    '<p>SkillBook과 공개 기술 근거 후보를 한 화면에서 검색합니다.</p>'
                    '</nav>'
                )
                content = content.replace("</header>", "</header>" + jump, 1)
            if (status == 200 and mime == "text/html; charset=utf-8"
                    and type(content) is str
                    and (route == "/skillbooks"
                         or route == "/skillbooks/" + SKILLBOOK_ID)
                    and "</header>" in content
                    and 'href="/skillbooks/qa-plan"' not in content):
                content = content.replace(
                    "</header>",
                    '</header><nav aria-label="SkillBook 검증 메뉴">'
                    '<a href="/skillbooks/qa-plan">'
                    '검증 계획 보기 (9개 합성 시험)</a></nav>', 1)
            return super().reply(status, content, mime)

        def do_GET(self):
            path = urlsplit(self.path)
            if path.path in ("/skillbooks/qa-plan", "/skillbooks/qa-plan.json"):
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
                if path.query or path.fragment or len(self.path) > 100:
                    return self.reply(400, "EXACT_QA_PLAN_ROUTE_ONLY",
                                      "text/plain; charset=utf-8")
                plan = preview_skillbook_qa_plan()
                if path.path.endswith(".json"):
                    return self.reply(
                        200, json.dumps(plan, ensure_ascii=True, sort_keys=True),
                        "application/json; charset=utf-8")
                return self.reply(200, render_skillbook_qa_plan(plan))
            if path.path not in ("/catalog", "/catalog.json"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if len(self.path) > 340 or path.fragment:
                return self.reply(400, "INVALID_CATALOG_ROUTE", "text/plain; charset=utf-8")
            try:
                data = search_federated(root, filters=parse_filters(path.query),
                                        public_reader=public_reader)
                if path.path == "/catalog.json":
                    return self.reply(200, json.dumps(data, ensure_ascii=False, sort_keys=True),
                                      "application/json; charset=utf-8")
                return self.reply(200, render_federated(data))
            except (FederationError, SkillBookProductError):
                return self.reply(400, "CATALOG_INPUT_OR_CONTRACT_NO_GO",
                                  "text/plain; charset=utf-8")
            except (LibrarySearchError, DiscoveryError, OSError,
                    sqlite3.DatabaseError, ValueError, TypeError, KeyError):
                return self.reply(503, "W04_SOURCE_LINKAGE_UNAVAILABLE_NO_GO",
                                  "text/plain; charset=utf-8")
    return Handler


def main() -> int:
    p = argparse.ArgumentParser(description="UCIE local read-only federated catalog")
    p.add_argument("--port", type=int, default=0)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    if (not 0 <= args.port <= 65535 or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or (os.name == "nt" and root.resolve() != Path("D:/UCIE").resolve())):
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED"}))
        return 3
    try:
        with HTTPServer(("127.0.0.1", args.port), make_handler(root)) as server:
            print(json.dumps({
                "schema": SCHEMA, "status": "LOCAL_DRAFT_CATALOG_LISTENING",
                "url": "http://127.0.0.1:" + str(server.server_port) + "/catalog",
                "default_public_db_opened": False, "scheduler_registered": False,
                "approved_packages": 0, "export_allowed": False,
            }), flush=True)
            server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except OSError:
        print(json.dumps({"schema": SCHEMA, "status": "LOCAL_BIND_FAILED_NO_GO"}))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
