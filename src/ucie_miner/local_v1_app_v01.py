"""UCIE Local V1 owner-operated product, not a deployment or a demo-only CLI.

Single localhost browser entrypoint wiring existing first-party evidence,
reusable engine, SkillBooks and change review. No POST, network fetch,
customer/other-project paths, automatic promotion or background tasks.
Local V1 has NOT been owner-accepted merely because this app runs.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import HTTPServer
import json
import os
from pathlib import Path
import re
from urllib.parse import parse_qs, quote, urlsplit
import webbrowser

from .local_v1_priority_v01 import (
    LocalPriorityError, require_local_work, roadmap,
)

APP_SCHEMA = "UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01"
APP_STATUS = "LOCAL_V1_USER_WORKFLOW_IMPLEMENTED_OWNER_ACCEPTANCE_PENDING"
QUERY = re.compile(r"[A-Za-z0-9_.:/ -]{0,80}\Z")
BOOK_QUERY = re.compile(r"[\w .-]{0,80}\Z", re.UNICODE)
ROUTES = (
    ("/local/error", "코딩 오류 예방", "승인된 공개 근거 후보, 안전한 수정 방향, 회귀 검토"),
    ("/local/engine", "개발 엔진 · 스킬", "직접 선택해 UCIE 작성 알고리즘 실행"),
    ("/local/books", "가상도서관 · SkillBook", "본문, 원본 출처, 기계 계약과 검토 상태"),
    ("/local/evolution", "근거 기반 개선", "UCIE 로컬 공개 변경 이력, 검토 대기와 다음 작업"),
)
ALLOWED_SOURCE_PREFIXES = (
    "https://github.com/python/cpython/",
    "https://github.com/PowerShell/PowerShell/",
    "https://github.com/git/git/",
    "https://github.com/modelcontextprotocol/python-sdk/",
    "https://github.com/actions/runner-images/",
)


class LocalProductError(ValueError):
    pass


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _params(raw: str, allowed: tuple[str, ...]) -> dict[str, str]:
    if type(raw) is not str or len(raw) > 260:
        raise LocalProductError("invalid bounded query")
    try:
        parsed = parse_qs(raw, keep_blank_values=True, strict_parsing=True,
                          max_num_fields=max(1, len(allowed)),
                          encoding="utf-8", errors="strict") if raw else {}
    except (UnicodeError, ValueError) as exc:
        raise LocalProductError("invalid query") from exc
    if any(k not in allowed or len(v) != 1 for k, v in parsed.items()):
        raise LocalProductError("unexpected or duplicate query field")
    return {key: values[0] for key, values in parsed.items()}


def _search(root: Path, query: str, *, limit: int = 5) -> dict:
    from .library_search import SCHEMA, search_existing_public_library

    if type(query) is not str or QUERY.fullmatch(query) is None:
        raise LocalProductError("invalid public evidence search")
    result = search_existing_public_library(
        root, query=query, limit=limit, group_revisions=False)
    if (type(result) is not dict or result.get("schema") != SCHEMA
            or result.get("status") not in (
                "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
                "SOURCE_LINKAGE_INCOMPLETE_NO_GO")
            or result.get("network_requests") != 0
            or result.get("operating_database_writes") != 0
            or result.get("approved_or_exportable_items") != 0
            or result.get("auto_promoted") is not False):
        raise LocalProductError("public evidence not safely readable")
    items = result.get("items")
    if type(items) is not list or len(items) > limit:
        raise LocalProductError("public evidence bound violated")
    if result["status"] == "SOURCE_LINKAGE_INCOMPLETE_NO_GO" and items:
        raise LocalProductError("incomplete source was presented as evidence")
    for row in items:
        if (type(row) is not dict
                or row.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"
                or row.get("human_approved") is not False
                or row.get("export_allowed") is not False
                or type(row.get("public_url")) is not str
                or not row["public_url"].startswith(ALLOWED_SOURCE_PREFIXES)):
            raise LocalProductError("unapproved public evidence promoted")
    return result


def _page(name: str, main: str) -> str:
    nav = "".join(
        '<a href="' + href + '">' + _e(title) + "</a>"
        for href, title, _ in ROUTES)
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>UCIE Local V1 - ' + _e(name) + '</title>'
        '<style>body{font-family:system-ui,Malgun Gothic,sans-serif;'
        'max-width:1000px;margin:0 auto;padding:22px;background:#f8fafc;color:#17263b}'
        'header{border-bottom:2px solid #0e7490;padding-bottom:13px}'
        'nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:15px}'
        'nav a,button{background:#075985;color:#fff;border-radius:6px;'
        'padding:9px 12px;text-decoration:none;border:0;cursor:pointer}'
        'main{line-height:1.65}section,article{background:white;margin:14px 0;'
        'border:1px solid #cbd5e1;padding:14px;border-radius:8px}'
        'input,select{padding:8px;max-width:95%;margin:5px}'
        'small,.muted{color:#475569}code,pre{white-space:pre-wrap;overflow-wrap:anywhere}'
        'a{overflow-wrap:anywhere}h1{font-size:1.6rem}'
        '</style></head><body><header>'
        '<h1>UCIE Local V1 · ' + _e(name) + '</h1>'
        '<p>로컬 실사용 제품 우선 · 공개 근거만 사용 · 자동 규칙 승격 없음'
        ' · 소유자 실제 인수 <strong>미완료</strong></p>'
        '<nav><a href="/local">홈</a>' + nav +
        '<a href="/catalog">기존 통합 도서관</a></nav></header>'
        '<main>' + main + '</main></body></html>'
    )


def _home() -> str:
    require_local_work("LOCAL_APP")
    blocks = []
    for route, title, summary in ROUTES:
        blocks.append(
            '<article><h2><a href="' + route + '">' + _e(title)
            + '</a></h2><p>' + _e(summary) + '</p></article>')
    body = (
        '<section><h2>로컬 V1 실제 사용자 작업</h2>'
        '<p>아래 네 기능을 직접 실행하세요. 과거의 합성 테스트 통과를'
        ' 로컬 제품 인수로 표시하지 않습니다.</p></section>'
        + "".join(blocks) +
        '<section><h2>개발 우선순위 잠금</h2><p>'
        '1. 로컬 제품 완성 → 2. 온라인·고객 전용 출시'
        ' → 3. 주변 확장. 출시 승인·서명·자동 승격은 모두 보류.</p>'
        '<a href="/local/policy">현재 하드코딩된 규칙과 인수 조건 보기</a></section>'
    )
    return _page("시작", body)


def _evidence_rows(report: dict, *, guidance: bool = False) -> str:
    from .rule_candidates import GUIDANCE

    if report.get("status") == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        return '<section>출처 연결이 불완전하여 검색 결과를 표시하지 않습니다. ' \
               '운영 원장을 수정하지 않고 수동으로 소스 계보를 확인하세요.</section>'
    rows = report.get("items", [])
    if not rows:
        return '<section>선택한 조건과 일치하는 기존 공개 근거가 없습니다. ' \
               '검증된 수정 또는 학습 결과를 만들어 내지 않습니다.</section>'
    output = []
    for row in rows:
        url = row["public_url"]
        guidance_row = GUIDANCE.get(row.get("purpose_code"))
        details = (
            '<p>근거: <a rel="noopener noreferrer" target="_blank" href="'
            + _e(url) + '">' + _e(url) + '</a></p>'
            '<p>출처 ' + _e(row.get("source_id", "")) +
            ' · 기술 ' + _e(row.get("domain", "")) +
            ' · 버전 ' + _e(row.get("version_scope_claim", "미확인")) +
            ' · 패턴 ' + _e(row.get("purpose_code", "미확인")) + '</p>'
            '<p>상태: <strong>UNVERIFIED_CANDIDATE_ONLY</strong>'
            ' · SHA-256 ' + _e(row.get("evidence_sha256", "")) + '</p>'
        )
        if guidance and guidance_row:
            details += (
                '<p>UCIE 작성 안전 검토 방향 (승인된 패치 아님): ' +
                _e(guidance_row[0]) + '</p>'
                '<p>권장 회귀 확인 계획 (실행 결과 아님): ' +
                _e(guidance_row[1]) + '</p>')
        elif guidance:
            details += '<p>이 패턴에 확인된 수정 안내가 없습니다. 출처 수동 검토가 필요합니다.</p>'
        output.append('<article><h3>' + _e(row.get("purpose_code", "공개 근거"))
                      + '</h3>' + details + '</article>')
    return "".join(output)


def _error(root: Path, raw: str) -> str:
    require_local_work("ERROR_PREVENTION")
    args = _params(raw, ("q",))
    term = args.get("q", "")
    if QUERY.fullmatch(term) is None:
        raise LocalProductError("invalid error search keyword")
    body = (
        '<section><h2>코딩 오류 또는 API 패턴 검색</h2>'
        '<form action="/local/error" method="get">'
        '<label>공개 근거 검색어 <input name="q" maxlength="80" value="' +
        _e(term) + '" placeholder="scandir 또는 API_CONTRACT"></label>'
        '<button>검색</button></form>'
        '<small>실제 기존 UCIE 공개 기술 후보에서 검색합니다.'
        ' 미검증 수정법을 자동 적용하지 않습니다.</small></section>')
    if term:
        body += _evidence_rows(_search(root, term), guidance=True)
    else:
        body += '<section>검색어를 입력하면 관련 공개 변경과 안전 검토·회귀 방향을 보여줍니다.</section>'
    return _page("오류 예방", body)


def _engine(raw: str) -> str:
    require_local_work("DEV_ENGINE_SKILL")
    from .capability_trials import RECIPES, evaluate_ucie_owned_recipe

    args = _params(raw, ("purpose",))
    purpose = args.get("purpose", "")
    if purpose and purpose not in RECIPES:
        raise LocalProductError("unregistered development engine")
    choices = "".join(
        '<li><a href="/local/engine?purpose=' + _e(name) + '">' +
        _e(name) + '</a> - ' + _e(info[0]) + '</li>'
        for name, info in sorted(RECIPES.items()))
    body = (
        '<section><h2>UCIE 자체 개발 엔진 선택</h2>'
        '<p>실제 첫 번째 파티 알고리즘을 선택해 호출합니다. 입력 워크로드는'
        ' UCIE 생성 합성 데이터이며 실사용 코드 분석으로 오해하면 안 됩니다.</p>'
        '<ul>' + choices + '</ul></section>')
    if purpose:
        out = evaluate_ucie_owned_recipe(
            purpose, rows=128, queries=16, repeats=2)
        if (out.get("purpose_code") != purpose
                or out.get("exact_result_equivalence_observed") is not True
                or out.get("production_adopted") is True):
            raise LocalProductError("UCIE engine result not safe for local use")
        body += (
            '<section><h2>실행 결과</h2>'
            '<p>엔진 ID: ' + _e(out.get("recipe_id")) + '</p>'
            '<p>기준 연산: ' + _e(out.get("baseline_operations")) +
            ' · 후보 연산: ' + _e(out.get("candidate_operations_including_setup")) +
            ' · 결과 동등성: ' +
            _e(out["exact_result_equivalence_observed"]) + '</p>'
            '<p>상태: ' + _e(out.get("status")) + '</p>'
            '<p><strong>한계:</strong> 합성 workload 비교입니다.'
            ' 실제 프로젝트 또는 운영환경 개선 효과는 아직 검증하지 않았습니다.</p>'
            '</section>')
    return _page("개발 엔진·스킬", body)


def _books(raw: str) -> str:
    require_local_work("VIRTUAL_LIBRARY")
    from .skillbook_product_v01 import search_skillbooks

    args = _params(raw, ("q",))
    term = args.get("q", "")
    if BOOK_QUERY.fullmatch(term) is None:
        raise LocalProductError("invalid SkillBook search term")
    result = search_skillbooks(query=term)
    if (result.get("status") != "READ_ONLY_FIRST_PARTY_DRAFT_CATALOG"
            or result.get("approved_reusable_packages") != 0
            or result.get("operating_database_writes") != 0
            or result.get("network_requests") != 0):
        raise LocalProductError("untrusted SkillBook result")
    body = (
        '<section><h2>실제 UCIE 작성 SkillBook 열람</h2>'
        '<form action="/local/books" method="get">'
        '<input name="q" maxlength="80" value="' + _e(term) +
        '" placeholder="scandir 또는 Git"><button>도서 검색</button></form>'
        '<p>본문과 기계 실행 계약은 아래 링크에서 열람합니다.'
        ' 미승인 초안은 승인된 제품으로 내보내지 않습니다.</p></section>')
    for book in result.get("items", []):
        if book.get("human_approved") is not False or book.get("export_allowed") is not False:
            raise LocalProductError("unapproved SkillBook status tampered")
        ident = book.get("skillbook_id")
        if type(ident) is not str or len(ident) > 100 or not ident.isascii():
            raise LocalProductError("unsafe book identifier")
        body += (
            '<article><h3><a href="/skillbooks/' + quote(ident, safe="") +
            '">' + _e(book.get("title")) + '</a></h3>'
            '<p>출처 ' + _e(book.get("source_id")) +
            ' · 버전 ' + _e(book.get("version_scope_claim")) +
            ' · ' + _e(book.get("status")) + '</p>'
            '<p>미승인·수동 검토 필요·상용 내보내기 불가</p></article>')
    if not result.get("items"):
        body += '<section>검색 조건과 일치하는 SkillBook이 없습니다.</section>'
    return _page("가상도서관", body)


def _evolution(root: Path, raw: str) -> str:
    require_local_work("EVIDENCE_EVOLUTION")
    from .public_collection_inventory_v01 import collection_inventory

    args = _params(raw, ("q",))
    term = args.get("q", "")
    if QUERY.fullmatch(term) is None:
        raise LocalProductError("invalid public change search")
    body = (
        '<section><h2>현재 UCIE 공개 수집·검토 현황</h2>'
        '<p>실제 기존 UCIE 공개 기록만 읽습니다. 추가 수집·자동 승격은 하지 않습니다.</p>')
    inventory = collection_inventory(root)
    if (inventory.get("schema") != "UCIE_PUBLIC_COLLECTION_INVENTORY_V01"
            or inventory.get("operating_database_writes") != 0):
        raise LocalProductError("unexpected UCIE collection inventory")
    body += (
        '<p>수집 현황: ' + _e(inventory.get("status")) + '</p>'
        '<p>관측 시각: ' + _e(inventory.get("observed_utc", "보고되지 않음")) +
        '</p>'
        '<p>검증 문제: ' + _e(", ".join(inventory.get("issues", []))) +
        '</p></section>'
        '<section><h2>개선·검토할 공개 변경 검색</h2>'
        '<form action="/local/evolution" method="get">'
        '<input name="q" maxlength="80" value="' + _e(term) +
        '" placeholder="python/cpython 또는 pattern">'
        '<button>변경 조회</button></form>'
        '<p>원본 공개 URL → 검증 미완료 상태 → 원본·중복·버전·회귀시험'
        ' 수동 검토가 다음 단계입니다.</p></section>'
    )
    report = _search(root, term)
    body += _evidence_rows(report)
    return _page("근거 기반 개선", body)


def _policy() -> str:
    require_local_work("LOCAL_APP")
    state = roadmap()
    items = "".join("<li>" + _e(gate) + "</li>"
                    for gate in state["local_acceptance_gates"])
    return _page(
        "개발 규칙", '<section><h2>강제 개발 순서</h2>'
        '<p>' + _e(" → ".join(state["ordered_phases"])) + '</p>'
        '<p>LOCAL V1 GO: <strong>아직 미승인</strong></p>'
        '<p>온라인·고객 출시: 금지 / 주변 확장: 보류</p>'
        '<ol>' + items + '</ol>'
        '<p>실제 소유자 PC 사용 인수 전에는 완료 상태를 자동 설정할 수 없습니다.</p>'
        '</section>')


def make_handler(root: Path):
    """Expose a single existing catalog server plus four local product routes."""
    if (not isinstance(root, Path) or root.is_symlink()
            or root.name.casefold() != "ucie" or not root.is_dir()
            or not (root / ".git").is_dir()):
        raise LocalProductError("UCIE-only checkout root required")
    require_local_work("LOCAL_APP")
    from .skillbook_catalog_union_v01 import make_handler as base_handler

    parent = base_handler(root)

    class LocalHandler(parent):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            route = urlsplit(self.path).path
            if route == "/" or route.startswith("/local"):
                data = content.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; style-src 'unsafe-inline'; "
                    "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
                )
                self.end_headers()
                self.wfile.write(data)
                return
            return super().reply(status, content, mime)

        def do_POST(self):
            return self.reply(405, "LOCAL_PRODUCT_READ_ONLY",
                              "text/plain; charset=utf-8")

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path not in (
                    "/", "/local", "/local/error", "/local/engine",
                    "/local/books", "/local/evolution", "/local/policy"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY",
                                  "text/plain; charset=utf-8")
            if len(self.path) > 300 or parts.fragment:
                return self.reply(400, "INVALID_LOCAL_PRODUCT_ROUTE",
                                  "text/plain; charset=utf-8")
            try:
                if parts.path in ("/", "/local"):
                    if parts.query:
                        raise LocalProductError("local home cannot take query")
                    html = _home()
                elif parts.path == "/local/error":
                    html = _error(root, parts.query)
                elif parts.path == "/local/engine":
                    html = _engine(parts.query)
                elif parts.path == "/local/books":
                    html = _books(parts.query)
                elif parts.path == "/local/evolution":
                    html = _evolution(root, parts.query)
                else:
                    if parts.query:
                        raise LocalProductError("local roadmap does not take query")
                    html = _policy()
                return self.reply(200, html)
            except (LocalProductError, LocalPriorityError, ValueError,
                    KeyError, TypeError, OSError):
                return self.reply(400, "UCIE_LOCAL_V1_FAIL_CLOSED_NO_RELEASE",
                                  "text/plain; charset=utf-8")

    return LocalHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE Local V1 four-pillar localhost work surface")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if (not 1024 <= args.port <= 65535 or root.is_symlink()
            or root.name.casefold() != "ucie"
            or not (root / ".git").is_dir()
            or (os.name == "nt"
                and root.resolve() != Path("D:/UCIE").resolve())):
        print(json.dumps({
            "schema": APP_SCHEMA,
            "status": "UCIE_LOCAL_V1_EXACT_OWNER_ROOT_REQUIRED",
            "local_release_accepted": False,
        }, sort_keys=True))
        return 2
    try:
        require_local_work("LOCAL_APP")
        with HTTPServer(("127.0.0.1", args.port), make_handler(root)) as server:
            url = "http://127.0.0.1:" + str(server.server_port) + "/local"
            print(json.dumps({
                "schema": APP_SCHEMA,
                "status": APP_STATUS,
                "local_app_url": url,
                "owner_acceptance_verified": False,
                "customer_distribution_authorized": False,
                "external_network_requests": 0,
                "scheduler_modified": False,
                "automatic_rule_promotion": False,
            }, ensure_ascii=True, sort_keys=True), flush=True)
            if args.open_browser:
                webbrowser.open(url)
            server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except (OSError, LocalProductError, LocalPriorityError):
        print(json.dumps({
            "schema": APP_SCHEMA,
            "status": "UCIE_LOCAL_V1_START_FAIL_CLOSED",
            "owner_acceptance_verified": False,
        }, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
