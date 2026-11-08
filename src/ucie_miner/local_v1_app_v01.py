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
PAGE_SIZE = 10
MAX_PAGE = 500  # 10 at a time; covers the owner public catalog without bulk dumps.
ROUTES = (
    ("/local/error", "코딩 오류 예방", "승인된 공개 출처의 미검증 후보, 안전한 수정 방향과 회귀 계획"),
    ("/local/engine", "개발 엔진 · 스킬", "직접 선택해 UCIE 작성 알고리즘 실행"),
    ("/local/library", "통합 가상도서관", "SkillBook·공개 기술 근거·편집 검토를 한 화면에서 탐색"),
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


def _search(root: Path, query: str, *, limit: int = PAGE_SIZE,
            offset: int = 0) -> dict:
    from .library_search import SCHEMA, search_existing_public_library

    if type(query) is not str or QUERY.fullmatch(query) is None:
        raise LocalProductError("invalid public evidence search")
    result = search_existing_public_library(
        root, query=query, limit=limit, group_revisions=False,
        offset=offset)
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
    total = result.get("total_matches")
    if (type(items) is not list or len(items) > limit
            or type(total) is not int or total < len(items)
            or type(result.get("returned_count")) is not int
            or result["returned_count"] != len(items)
            or (offset and result.get("page_offset") != offset)):
        raise LocalProductError("public evidence count/pagination contract violated")
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
        '<nav><a href="/local">홈</a>' + nav + '</nav></header>'
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


def _page_number(args: dict[str, str]) -> int:
    raw = args.get("page", "1")
    if (type(raw) is not str or re.fullmatch(r"[1-9][0-9]{0,2}", raw) is None
            or not 1 <= int(raw) <= MAX_PAGE):
        raise LocalProductError("invalid bounded public evidence page")
    return int(raw)


def _paged_evidence(root: Path, query: str, *, page: int,
                    route: str, guidance: bool = False) -> str:
    """Keep every approved public candidate accessible in bounded pages."""
    offset = (page - 1) * PAGE_SIZE
    report = _search(root, query, limit=PAGE_SIZE, offset=offset)
    total = report["total_matches"]
    shown = len(report["items"])
    if total and offset >= total:
        raise LocalProductError("requested page outside available public evidence")
    if report["status"] == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        return _evidence_rows(report, guidance=guidance)
    start = offset + 1 if shown else 0
    finish = offset + shown
    summary = (
        '<section><p><strong>전체 일치 공개 근거 후보·개정 행: ' + _e(total)
        + '건</strong> · 현재 ' + _e(start) + '–' + _e(finish)
        + '건 표시 · 페이지당 최대 ' + _e(PAGE_SIZE) + '건</p>'
        '<p class="muted">이 값은 미검증 공개 근거 행의 검색 결과입니다.'
        ' 승인된 규칙이나 SkillBook 개수가 아니며, 색인 실험의 항목 수와'
        ' 동일한 지표로 비교할 수 없습니다.</p></section>')
    links = []
    if page > 1:
        links.append('<a href="' + route + '?q=' +
                     quote(query, safe="") + '&page=' + str(page - 1) +
                     '">이전 ' + str(PAGE_SIZE) + '건</a>')
    if finish < total:
        links.append('<a href="' + route + '?q=' +
                     quote(query, safe="") + '&page=' + str(page + 1) +
                     '">다음 ' + str(PAGE_SIZE) + '건</a>')
    navigation = (
        '<section><nav aria-label="공개 근거 검색 페이지">'
        + ' · '.join(links) + '</nav></section>' if links else '')
    return summary + _evidence_rows(report, guidance=guidance) + navigation


def _error(root: Path, raw: str) -> str:
    require_local_work("ERROR_PREVENTION")
    args = _params(raw, ("q", "page"))
    term = args.get("q", "")
    if QUERY.fullmatch(term) is None:
        raise LocalProductError("invalid error search keyword")
    page = _page_number(args)
    if not term and page != 1:
        raise LocalProductError("query required for non-initial error page")
    body = (
        '<section><h2>코딩 오류 또는 API 패턴 검색</h2>'
        '<form action="/local/error" method="get">'
        '<label>공개 근거 검색어 <input name="q" maxlength="80" value="' +
        _e(term) + '" placeholder="scandir 또는 API_CONTRACT"></label>'
        '<button>검색</button></form>'
        '<small>전체 일치 건수를 표시하고 10건씩 이동할 수 있습니다.'
        ' 모든 후보는 미검증이며 실제 코드를 자동 수정하지 않습니다.</small></section>')
    if term:
        body += _paged_evidence(root, term, page=page,
                                route="/local/error", guidance=True)
    else:
        body += '<section>검색어를 입력하면 공개 변경과 UCIE 안전 검토·회귀 방향을 보여줍니다.</section>'
    return _page("오류 예방", body)

def _engine(raw: str, *, root: Path | None = None) -> str:
    require_local_work("DEV_ENGINE_SKILL")
    from .capability_trials import RECIPES, evaluate_ucie_owned_recipe

    args = _params(raw, ("purpose",))
    purpose = args.get("purpose", "")
    if purpose and purpose not in (*RECIPES, "REAL_PUBLIC_CATALOG"):
        raise LocalProductError("unregistered development engine")
    choices = "".join(
        '<li><a href="/local/engine?purpose=' + _e(name) + '">' +
        _e(name) + '</a> - ' + _e(info[0]) + ' (UCIE 합성 워크로드)</li>'
        for name, info in sorted(RECIPES.items()))
    choices += (
        '<li><a href="/local/engine?purpose=REAL_PUBLIC_CATALOG">'
        'REAL_PUBLIC_CATALOG</a> - 실제 기존 UCIE 공개 기술 근거의'
        ' 정확 키 검색 인덱스와 기본 탐색을 비교 (원본 코드 실행 없음)</li>')
    body = (
        '<section><h2>UCIE 자체 개발 엔진 선택</h2>'
        '<p>실제 UCIE 알고리즘을 선택해 호출합니다. 아래 공개 근거 엔진은'
        ' 기존 UCIE 공개 후보의 메타데이터에서 실제 계산을 수행하며,'
        ' 나머지 세 엔진은 명시된 합성 워크로드 실험입니다.</p>'
        '<ul>' + choices + '</ul></section>')
    if purpose == "REAL_PUBLIC_CATALOG":
        from .experience_application import (
            SCHEMA as PUBLIC_ENGINE_SCHEMA,
            benchmark_existing_ucie_public_catalog,
        )
        if root is None:
            raise LocalProductError("UCIE catalog owner root required")
        out = benchmark_existing_ucie_public_catalog(
            root, queries=24, repeats=2)
        if (out.get("schema") != PUBLIC_ENGINE_SCHEMA
                or out.get("network_requests") != 0
                or out.get("operating_database_writes") != 0
                or out.get("production_index_applied") is not False
                or out.get("v1_accepted") is not False):
            raise LocalProductError("real public catalog engine scope drift")
        if out.get("status") == "NO_COMPLETE_SOURCE_LINKED_PUBLIC_CATALOG_NO_GO":
            body += ('<section>현재 소스 계보가 연결된 공개 카탈로그가 없습니다.'
                     ' 미확인 데이터를 만든 것으로 표시하지 않습니다.</section>')
        elif out.get("status") == "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED":
            if (out.get("automatic_learning_or_promotion") is not False
                    or out.get("upstream_code_executed") is not False
                    or out.get("approved_or_exportable_items") != 0
                    or out.get("mismatched_query_results") != 0):
                raise LocalProductError("unsafe real public catalog engine result")
            body += (
                '<section><h2>실제 UCIE 공개 근거 색인 비교</h2>'
                '<p>공개 항목 ' + _e(out.get("real_public_catalog_items")) +
                '건 · 요청 ' + _e(out.get("query_count")) +
                '회 · 검색 결과 불일치 ' +
                _e(out.get("mismatched_query_results")) + '건</p>'
                '<p>기본 탐색 연산: ' + _e(out.get("baseline_scan_operations")) +
                ' · 색인 구축 포함 연산: ' +
                _e(out.get("candidate_index_build_and_lookup_operations")) +
                ' · 소스 집합 SHA-256: ' +
                _e(out.get("public_catalog_sha256")) + '</p>'
                '<p>상태: ' + _e(out.get("status")) + '</p>'
                '<p><strong>한계:</strong> 승인된 로컬 공개 근거 메타데이터의'
                ' 정확 키 테스트이며, 전체 문자열 검색·원본 코드 실행·'
                ' 고객 성능 검증·운영 색인 반영이 아닙니다.</p></section>')
        else:
            raise LocalProductError("real public catalog result requires review")
    elif purpose:
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


def _library(root: Path, raw: str) -> str:
    """One user-facing UCIE library: SkillBooks, editorial drafts and all W04 pages.

    Reuse the existing federated catalog for human/machine books and draft
    review, and existing W04 source validation for paged public evidence.
    Never merge the distinct approval/rights statuses into one count.
    """
    require_local_work("VIRTUAL_LIBRARY")
    from .skillbook_catalog_union_v01 import (
        SCHEMA as FEDERATED_SCHEMA, search_federated,
    )

    args = _params(raw, ("q", "page"))
    term = args.get("q", "")
    if BOOK_QUERY.fullmatch(term) is None:
        raise LocalProductError("invalid unified library query")
    page = _page_number(args)
    catalog = search_federated(root, filters={
        "query": term, "shelf": "skillbooks", "kind": "",
        "domain": "", "limit": 20,
    })
    if (catalog.get("schema") != FEDERATED_SCHEMA
            or catalog.get("status") != "READ_ONLY_TWO_SHELF_DRAFT_NOT_APPROVED"
            or catalog.get("public_shelf_status") != "NOT_REQUESTED"
            or catalog.get("public_evidence_candidates") != []
            or catalog.get("human_approved") is not False
            or catalog.get("export_allowed") is not False
            or catalog.get("approved_packages") != 0
            or catalog.get("network_requests") != 0
            or catalog.get("operating_database_writes") != 0):
        raise LocalProductError("untrusted unified catalog contract")
    books = catalog.get("skillbooks")
    drafts = catalog.get("editorial_review_candidates")
    if (type(books) is not list or len(books) > 2
            or type(drafts) is not list or len(drafts) > 20):
        raise LocalProductError("unbounded unified catalog shelves")

    body = (
        '<section><h2>UCIE 통합 가상도서관</h2>'
        '<p>SkillBook · 편집 검토 기술서적 · 실제 수집된 공개 기술 근거를'
        ' 한 화면에서 검색합니다. 세 자료는 검증 단위가 달라'
        ' 개수를 합산하거나 승인된 책/규칙으로 간주하지 않습니다.</p>'
        '<form action="/local/library" method="get">'
        '<label>검색어 <input name="q" maxlength="80" value="' +
        _e(term) + '" placeholder="Git, Python, scandir"></label>'
        '<button>통합 검색</button></form>'
        '<p>모든 자료는 미검증 또는 미승인 상태입니다.'
        ' 자동 적용·출시·외부 배포는 하지 않습니다.</p></section>'
        '<section><h2>SkillBook 본문 · 기계 계약 (미승인 초안)</h2>'
        '<p>일치 초안: ' + _e(len(books)) +
        '권 · SkillBook 초안은 전체 공개 근거와 별도로 집계합니다.</p></section>'
    )
    for book in books:
        identity = book.get("skillbook_id")
        if (type(identity) is not str or len(identity) > 100
                or not identity.isascii()
                or book.get("human_approved") is not False
                or book.get("export_allowed") is not False):
            raise LocalProductError("forged or unsafe SkillBook")
        body += (
            '<article><h3><a href="/skillbooks/' + quote(identity, safe="") +
            '">' + _e(book.get("title", "SkillBook")) + '</a></h3>'
            '<p>출처 ' + _e(book.get("source_id")) +
            ' · 적용 범위 ' + _e(book.get("version_scope_claim")) + '</p>'
            '<p>본문 및 기계 판독 계약 열람 가능 · 미승인 · 내보내기 불가</p>'
            '</article>')
    if not books:
        body += '<section>일치하는 SkillBook 초안이 없습니다.</section>'
    body += (
        '<section><h2>편집·원문 검토 대기 기술서적</h2>'
        '<p>일치 편집 후보: ' + _e(len(drafts)) +
        '건 · 검토 미완료 · 실행 계약과 승인된 책이 아닙니다.</p></section>'
    )
    for draft in drafts:
        ident = draft.get("draft_sha256")
        if type(ident) is not str or re.fullmatch(r"[0-9a-f]{64}", ident) is None:
            raise LocalProductError("invalid reviewed editorial draft reference")
        body += (
            '<article><a href="/catalog/review?id=' + ident + '">' +
            _e(draft.get("topic", "검토 대기")) + '</a>'
            '<p>출처 ' + _e(", ".join(draft.get("source_ids", []))) +
            ' · 원문·라이선스·QA 미승인</p></article>')
    body += (
        '<section><h2>기존 UCIE 공개 근거·코딩 예방 후보</h2>'
        '<p>원본 공개 변경 링크와 미승인 상태를 표시하며'
        ' 전체 검색 결과를 페이지별로 탐색할 수 있습니다.</p></section>')
    if term.isascii():
        body += _paged_evidence(
            root, term, page=page, route="/local/library")
    else:
        if page != 1:
            raise LocalProductError("non-ASCII public evidence paging not supported")
        body += (
            '<section>공개 근거 W04 검색은 현재 영문 검색어만 지원합니다.'
            ' SkillBook·편집 자료 검색 결과는 위에 표시했습니다.'
            ' 공개 근거를 보려면 Python, Git 등의 영문 검색어를 사용하세요.'
            '</section>')
    return _page("통합 가상도서관", body)


def _evolution(root: Path, raw: str) -> str:
    require_local_work("EVIDENCE_EVOLUTION")
    from .public_collection_inventory_v01 import SCHEMA as INVENTORY_SCHEMA, collection_inventory

    args = _params(raw, ("q", "page"))
    term = args.get("q", "")
    if QUERY.fullmatch(term) is None:
        raise LocalProductError("invalid public change search")
    page = _page_number(args)
    body = (
        '<section><h2>현재 UCIE 공개 수집·검토 현황</h2>'
        '<p>실제 기존 UCIE 공개 기록만 읽습니다. 추가 수집·자동 승격은 하지 않습니다.</p>')
    inventory = collection_inventory(root)
    if (inventory.get("schema") != INVENTORY_SCHEMA
            or inventory.get("operating_database_writes") != 0):
        raise LocalProductError("unexpected UCIE collection inventory")
    body += (
        '<p>수집 현황: ' + _e(inventory.get("status")) + '</p>'
        '<p>관측 시각: ' + _e(inventory.get("captured_utc", "보고되지 않음")) +
        '</p>'
        '<p>기존 공개 PR 후보: ' + _e(inventory.get("legacy_miner", {}).get("candidates", "확인 불가")) +
        ' · Stage10 개정: ' + _e(inventory.get("stage10_public_candidate_staging", {}).get("candidate_revisions", "확인 불가")) + '</p>'
        '<p>검증 문제: ' + _e(", ".join(inventory.get("issues", []))) +
        '</p><p>기본 마이너·Stage10 개정·W04 검색 결과는 서로 다른 원장이므로'
        ' 합산된 제품 규칙 수가 아닙니다.</p></section>'
        '<section><h2>개선·검토할 공개 변경 검색</h2>'
        '<form action="/local/evolution" method="get">'
        '<input name="q" maxlength="80" value="' + _e(term) +
        '" placeholder="python/cpython 또는 pattern">'
        '<button>변경 조회</button></form>'
        '<p>원본 공개 URL → 검증 미완료 상태 → 원본·중복·버전·회귀시험'
        ' 수동 검토가 다음 단계입니다.</p></section>'
    )
    body += _paged_evidence(root, term, page=page,
                            route="/local/evolution")
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
            if (status == 200 and mime == "text/html; charset=utf-8"
                    and isinstance(content, str)
                    and "</header>" in content
                    and 'data-ucie-local-nav="true"' not in content):
                links = "".join(
                    '<a href="' + href + '">' + _e(title) + '</a> · '
                    for href, title, _ in ROUTES)
                local_nav = (
                    '<nav aria-label="UCIE Local V1" data-ucie-local-nav="true" '
                    'style="margin:12px 0;padding:12px;background:#e9f2f7;'
                    'border-radius:8px">'
                    '<strong>UCIE Local V1</strong> · '
                    '<a href="/local">UCIE 홈</a> · ' + links +
                    '</nav>'
                )
                content = content.replace("</header>", "</header>" + local_nav, 1)
            return super().reply(status, content, mime)

        def do_POST(self):
            return self.reply(405, "LOCAL_PRODUCT_READ_ONLY",
                              "text/plain; charset=utf-8")

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path not in (
                    "/", "/local", "/local/health", "/local/error",
                    "/local/engine", "/local/books", "/local/library",
                    "/local/evolution", "/local/policy"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY",
                                  "text/plain; charset=utf-8")
            if len(self.path) > 300 or parts.fragment:
                return self.reply(400, "INVALID_LOCAL_PRODUCT_ROUTE",
                                  "text/plain; charset=utf-8")
            try:
                if parts.path == "/local/health":
                    if parts.query:
                        raise LocalProductError("local health cannot take query")
                    require_local_work("LOCAL_APP")
                    return self.reply(200, json.dumps({
                        "schema": APP_SCHEMA,
                        "status": APP_STATUS,
                        "bound_host": "127.0.0.1",
                        "bound_port": self.server.server_port,
                        "owner_acceptance_verified": False,
                        "online_release_authorized": False,
                        "operating_database_writes": 0,
                    }, sort_keys=True), "application/json; charset=utf-8")
                if parts.path in ("/", "/local"):
                    if parts.query:
                        raise LocalProductError("local home cannot take query")
                    html = _home()
                elif parts.path == "/local/error":
                    html = _error(root, parts.query)
                elif parts.path == "/local/engine":
                    html = _engine(parts.query, root=root)
                elif parts.path == "/local/books":
                    # Existing Local V1 bookmarks converge on ONE library.
                    old_args = _params(parts.query, ("q", "page"))
                    term = old_args.get("q", "")
                    if BOOK_QUERY.fullmatch(term) is None:
                        raise LocalProductError("invalid legacy library query")
                    old_page = _page_number(old_args)
                    destination = "/local/library"
                    if term or old_page > 1:
                        destination += "?q=" + quote(term, safe="")
                        if old_page > 1:
                            destination += "&page=" + str(old_page)
                    self.send_response(302)
                    self.send_header("Location", destination)
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                elif parts.path == "/local/library":
                    html = _library(root, parts.query)
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
    parser.add_argument("--port", type=int, default=0,
                        help="0 = automatically choose a free local port")
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if (args.port != 0 and not 1024 <= args.port <= 65535
            or root.is_symlink()
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
                "bound_port": server.server_port,
                "port_selected_automatically": args.port == 0,
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
    except OSError as exc:
        print(json.dumps({
            "schema": APP_SCHEMA,
            "status": "UCIE_LOCAL_V1_LISTEN_FAILED_USE_AUTO_PORT",
            "requested_port": args.port,
            "reason": type(exc).__name__,
            "remedy": "Use --port 0 or the one-command owner launcher",
            "owner_acceptance_verified": False,
        }, sort_keys=True))
        return 2
    except (LocalProductError, LocalPriorityError):
        print(json.dumps({
            "schema": APP_SCHEMA,
            "status": "UCIE_LOCAL_V1_START_FAIL_CLOSED",
            "owner_acceptance_verified": False,
        }, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
