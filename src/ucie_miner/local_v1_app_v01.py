"""UCIE Local V1 owner-operated product, not a deployment or a demo-only CLI.

Single localhost browser entrypoint wiring existing first-party evidence,
reusable engine, SkillBooks and change review. No POST, network fetch,
customer/other-project paths, automatic promotion or background tasks.
Local V1 owner acceptance is separately documented, not inferred from a running app.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import ThreadingHTTPServer
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
APP_STATUS = "LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE"
# Browser/Edge speculative or unfinished connections must not block /local.
# This does not change the exact loopback bind or permit online access.
LOCAL_SERVER_CLASS = ThreadingHTTPServer
QUERY = re.compile(r"[A-Za-z0-9_.:/ -]{0,80}\Z")
BOOK_QUERY = re.compile(r"[\w .-]{0,80}\Z", re.UNICODE)
# Entry-link tracking is dropped, never reflected or interpreted as approval.
HOME_TRACKING_FIELDS = frozenset((
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
))
HOME_TRACKING_VALUE = re.compile(r"[A-Za-z0-9._:/+-]{1,80}\Z")
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


def _is_benign_home_tracking(raw: str) -> bool:
    """Only bounded UTM fields can be discarded at the local entry URL."""
    if type(raw) is not str or not raw or len(raw) > 240:
        return False
    try:
        fields = parse_qs(
            raw, keep_blank_values=True, strict_parsing=True,
            max_num_fields=5, encoding="utf-8", errors="strict",
        )
    except (ValueError, UnicodeError):
        return False
    return bool(fields) and set(fields).issubset(HOME_TRACKING_FIELDS) and all(
        len(values) == 1 and HOME_TRACKING_VALUE.fullmatch(values[0]) is not None
        for values in fields.values()
    )


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
    """Premium-dark UCIE UI; internal release gates remain enforced elsewhere."""
    from .local_v1_design_v04 import render_shell

    return render_shell(name, main, ROUTES)


def _home() -> str:
    require_local_work("LOCAL_APP")
    names = (
        ("문제 예방", "공개 기술 사례를 살펴보고 해결 방향을 확인하세요."),
        ("개발 도구", "유용한 개발 도구와 실행 예제를 만나보세요."),
        ("라이브러리", "기술 가이드와 참고 자료를 한곳에서 찾아보세요."),
        ("개선 제안", "최근 공개 기술 변경에서 새로운 아이디어를 찾아보세요."),
    )
    entries = []
    for i, ((href, _, _), (label, detail)) in enumerate(zip(ROUTES, names), 1):
        entries.append(
            '<a class="pillar-card" href="' + href + '">'
            '<span class="pillar-number" aria-hidden="true">' +
            str(i).zfill(2) + '</span>'
            '<span class="pillar-content"><h3>' + _e(label) + '</h3>'
            '<p>' + _e(detail) + '</p></span>'
            '<span class="pillar-arrow" aria-hidden="true">→</span></a>'
        )
    body = (
        '<section class="intro-workbench" aria-labelledby="hero-title">'
        '<div class="intro-text">'
        '<span class="eyebrow">THE UCIE EXPERIENCE</span>'
        '<h2 class="intro-title" id="hero-title">'
        '더 좋은 코드를 위한<br><em>더 나은 선택.</em></h2>'
        '<p>문제를 예방하고, 새로운 방법을 발견하고,'
        ' 필요한 기술을 더 쉽게 찾아보세요.</p>'
        '<div class="intro-note"><span>EXPLORE</span>'
        '<span>관심 있는 기술을 입력해 바로 시작하세요.</span></div>'
        '</div>'
        '<div class="quick-query">'
        '<span class="eyebrow">SEARCH</span>'
        '<h3>무엇을 찾고 계신가요?</h3>'
        '<p>기술 이름이나 오류 키워드로 관련 사례를 확인해 보세요.</p>'
        '<form action="/local/error" method="get">'
        '<label>기술 검색'
        '<input name="q" maxlength="80" placeholder="Python, API, Git"'
        ' autocomplete="off"></label>'
        '<button type="submit">검색하기 <span aria-hidden="true">→</span></button>'
        '</form>'
        '<span class="quick-examples">PYTHON · GIT · API</span>'
        '</div></section>'
        '<section class="section-heading">'
        '<span class="eyebrow">EXPLORE UCIE</span>'
        '<h2>주요 기능</h2>'
        '<p>원하는 작업을 선택하세요.</p></section>'
        '<section class="pillar-grid" aria-label="UCIE 주요 기능">' +
        ''.join(entries) + '</section>'
        '<section class="workbench-note">'
        '<h2>자료를 살펴보실 때</h2>'
        '<p>공개 기술 자료의 출처와 검토 상태는 상세 화면에서 확인하실 수 있습니다.'
        ' 모든 제안이 실제 환경에서 검증된 해결책을 의미하지는 않습니다.</p>'
        '<a href="/local/policy">자료 이용 안내 <span aria-hidden="true">→</span></a>'
        '</section>'
    )
    return _page("시작", body)


def _evidence_rows(report: dict, *, guidance: bool = False,
                   query: str = "", page: int = 1,
                   route: str = "/local/error") -> str:
    """Display a clear customer summary; preserve inspectable evidence."""
    from .rule_candidates import GUIDANCE

    if report.get("status") == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        return (
            '<section class="workbench-note"><h2>자료를 불러오지 못했습니다</h2>'
            '<p>출처 연결이 불완전하여 검색 결과를 표시하지 않습니다.'
            ' 잠시 후 다시 확인해 주세요.</p></section>'
        )
    rows = report.get("items", [])
    if not rows:
        return (
            '<section class="workbench-note"><h2>검색 결과가 없습니다</h2>'
            '<p>다른 기술명이나 오류 키워드로 다시 검색해 보세요.</p>'
            '</section>'
        )
    output = []
    for row in rows:
        url = row["public_url"]
        candidate_id = row.get("library_item_id")
        if (type(candidate_id) is not str
                or re.fullmatch(r"[0-9a-f]{64}", candidate_id) is None
                or route not in ("/local/error", "/local/evolution", "/local/library")):
            raise LocalProductError("unsafe public candidate review selector")
        origin = route.removeprefix("/local/")
        target = (
            "/local/review?q=" + quote(query, safe="") +
            "&amp;page=" + str(page) + "&amp;id=" + candidate_id +
            "&amp;from=" + origin
        )
        source = str(row.get("source_id", "")).removeprefix("repo:")
        pattern = _e(row.get("purpose_code", "기술 사례"))
        item = (
            '<article class="evidence-item">'
            '<header class="evidence-title"><div>'
            '<span class="card-kicker">' + _e(source) + '</span>'
            '<h3>' + pattern + '</h3>'
            '<p class="customer-note">공개된 기술 변경을 바탕으로 정리한 참고 사례입니다.</p>'
            '</div><span class="record-stamp">검토 전</span></header>'
            '<div class="evidence-actions">'
            '<a href="' + target + '">개선 방향 살펴보기'
            '<span aria-hidden="true"> →</span></a>'
            '<a href="' + _e(url) + '" target="_blank"'
            ' rel="noopener noreferrer">원문 보기 ↗</a>'
            '</div>'
            '<details class="technical-details"><summary>'
            '출처·버전·기술 정보 보기</summary>'
            '<dl class="evidence-properties">'
            '<div><dt>출처 / 기술</dt><dd>' + _e(row.get("source_id", "")) +
            ' · ' + _e(row.get("domain", "")) + '</dd></div>'
            '<div><dt>적용 버전 주장</dt><dd>' +
            _e(row.get("version_scope_claim", "미확인")) + '</dd></div>'
            '<div><dt>원본 공개 근거</dt><dd>'
            '<a rel="noopener noreferrer" target="_blank" href="' +
            _e(url) + '">' + _e(url) + '</a></dd></div>'
            '<div><dt>검증 상태</dt><dd>'
            '<strong>UNVERIFIED_CANDIDATE_ONLY</strong>'
            ' · 실제 적용 전 별도 확인이 필요한 자료</dd></div>'
            '<div><dt>근거 SHA-256</dt><dd><code>' +
            _e(row.get("evidence_sha256", "")) + '</code></dd></div>'
            '<div><dt>분류 코드</dt><dd><code>' + pattern +
            '</code></dd></div></dl></details>'
        )
        if guidance:
            guidance_row = GUIDANCE.get(row.get("purpose_code"))
            item += (
                '<details class="technical-details"><summary>'
                '검토 가이드 보기</summary>'
                '<div class="evidence-guidance">'
            )
            if guidance_row:
                item += (
                    '<p><strong>안전 검토 방향 · 승인된 패치 아님</strong> ' +
                    _e(guidance_row[0]) + '</p>'
                    '<p><strong>권장 회귀 확인 · 실행 결과 아님</strong> ' +
                    _e(guidance_row[1]) + '</p>'
                )
            else:
                item += '<p>이 자료의 개별 검토 안내는 아직 준비되지 않았습니다.</p>'
            item += '</div></details>'
        item += '</article>'
        output.append(item)
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
        '<section class="result-summary">'
        '<p><strong>검색 결과 ' + _e(total) + '건</strong>'
        ' · ' + _e(start) + '–' + _e(finish) + '건 표시</p>'
        '<p class="customer-note">공개 기술 자료이며, 각 항목의 출처와'
        ' 검토 상태는 상세 정보에서 확인하실 수 있습니다.</p></section>'
    )
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
        '<section class="pager-box"><nav class="pagination" aria-label="공개 근거 검색 페이지">'
        + ' · '.join(links) + '</nav></section>' if links else '')
    return (summary + _evidence_rows(
        report, guidance=guidance, query=query, page=page, route=route)
        + navigation)


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
        '<section class="search-panel"><h2>문제 예방 자료 검색</h2>'
        '<p>찾고 계신 기술이나 오류 키워드를 입력하세요.</p>'
        '<form action="/local/error" method="get">'
        '<label>검색어 <input name="q" maxlength="80" value="' +
        _e(term) + '" placeholder="예: scandir, API"></label>'
        '<button type="submit">검색</button></form>'
        '<small>자료별 출처와 검토 상태를 확인하실 수 있습니다.</small>'
        '</section>'
    )
    # Guided bridge from a concrete public MCP error to its UCIE-authored
    # source-pinned review-only SkillBook. This is NOT an automatic fix,
    # generic MCP certification, rule promotion or a change to V04 styling.
    if page == 1 and term.casefold().strip() in (
            "mcp", "prompts/get", "prompt", "-32602"):
        from .mcp_prompts_guide_v01 import (
            build_readonly_guide, SCHEMA as GUIDE_SCHEMA,
            STATUS as GUIDE_STATUS, SKILLBOOK_ID as GUIDE_ID,
        )
        guide = build_readonly_guide()
        if (guide.get("schema") != GUIDE_SCHEMA
                or guide.get("skillbook_id") != GUIDE_ID
                or guide.get("status") != GUIDE_STATUS
                or guide.get("export_allowed") is not False
                or guide.get("auto_promoted") is not False
                or type(guide.get("review_gates")) is not dict
                or any(x is not False for x in guide["review_gates"].values())
                or guide.get("network_requests") != 0
                or guide.get("operating_database_writes") != 0):
            raise LocalProductError("MCP prevention guide is not safe to display")
        body += (
            '<section class="workbench-note">'
            '<span class="eyebrow">SOURCE-LINKED REVIEW</span>'
            '<h2>MCP prompts/get 입력 오류와 서버 실행 오류 구분</h2>'
            '<p>공식 Python SDK의 고정된 수정 전후 소스로 확인한 사례입니다. '
            '요청·응답의 오류 코드(-32602), 필수 인수, 수정 조건과 '
            '실제 시험 범위를 자세히 확인할 수 있습니다.</p>'
            '<p>검토 중인 기술 자료이며 자동 수정·승인·배포 기능은 아닙니다.</p>'
            '<p><a href="/local/guide/mcp-prompts">'
            '오류 구분 기술 가이드 보기 →</a></p></section>'
        )
    if term:
        body += _paged_evidence(root, term, page=page,
                                route="/local/error", guidance=True)
    else:
        body += '<section class="workbench-note"><p>관심 있는 기술명을 검색해 보세요.</p></section>'
    return _page("오류 예방", body)

def _review(root: Path, raw: str) -> str:
    """Complete one actual public-source -> manual regression work task."""
    require_local_work("ERROR_PREVENTION")
    from .local_v1_public_review_v01 import (
        SCHEMA as REVIEW_SCHEMA, create_review_worksheet,
    )

    args = _params(raw, ("q", "page", "id", "from"))
    term = args.get("q", "")
    page = _page_number(args)
    candidate_id = args.get("id", "")
    origin = args.get("from", "error")
    if (QUERY.fullmatch(term) is None
            or type(candidate_id) is not str
            or re.fullmatch(r"[0-9a-f]{64}", candidate_id) is None
            or origin not in ("error", "evolution", "library")):
        raise LocalProductError("invalid source-bound review selection")
    search = _search(root, term, limit=PAGE_SIZE,
                     offset=(page - 1) * PAGE_SIZE)
    if search["status"] != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO":
        raise LocalProductError("source provenance unavailable for review")
    matches = [
        row for row in search["items"]
        if row.get("library_item_id") == candidate_id
    ]
    if len(matches) != 1:
        raise LocalProductError("candidate no longer exists on this verified page")
    brief = create_review_worksheet(matches[0])
    if (brief.get("schema") != REVIEW_SCHEMA
            or brief.get("status") !=
            "SOURCE_BOUND_MANUAL_REVIEW_DRAFT_NOT_APPROVED"
            or brief.get("library_item_id") != candidate_id
            or brief.get("automatic_rule_promotion") is not False
            or brief.get("operating_database_writes") != 0
            or brief.get("network_requests") != 0
            or brief.get("regression_executed") is not False
            or brief.get("export_allowed") is not False):
        raise LocalProductError("review source/approval boundary drift")
    for field in ("public_url", "source_id", "pattern_code", "version_scope_claim"):
        if type(brief.get(field)) is not str:
            raise LocalProductError("incomplete review provenance")
    gates = brief.get("required_gates")
    if (type(gates) is not dict
            or any(status != "NOT_VERIFIED" for status in gates.values())):
        raise LocalProductError("unapproved review gate")
    return_path = "/local/" + origin + "?q=" + quote(term, safe="")
    if page > 1:
        return_path += "&page=" + str(page)
    markup = [
        '<section class="search-panel">'
        '<span class="eyebrow">TECH REVIEW</span>'
        '<h2>개선 방향 살펴보기</h2>'
        '<p><a href="' + _e(return_path) +
        '">← 검색 결과로 돌아가기</a></p>'
        '<p>공개된 기술 사례를 바탕으로 참고할 만한 개선 방향과'
        ' 검토할 사항을 정리했습니다.</p>'
        '<span class="record-stamp">검토 전 자료</span>'
        '<details class="technical-details"><summary>'
        '출처와 검토 정보</summary>'
        '<dl class="inventory-grid">'
        '<div><dt>검토 대상</dt><dd><code>' +
        _e(brief["pattern_code"]) + '</code></dd></div>'
        '<div><dt>출처</dt><dd>' + _e(brief["source_id"]) + '</dd></div>'
        '<div><dt>적용 버전 주장</dt><dd>' +
        _e(brief["version_scope_claim"]) + '</dd></div>'
        '<div><dt>검증 상태</dt><dd>'
        'UNVERIFIED_CANDIDATE_ONLY</dd></div>'
        '<div><dt>원본 공개 근거</dt><dd>'
        '<a target="_blank" rel="noopener noreferrer" href="' +
        _e(brief["public_url"]) + '">' + _e(brief["public_url"]) +
        '</a></dd></div>'
        '<div><dt>증거 SHA-256</dt><dd><code>' +
        _e(brief["evidence_sha256"]) + '</code></dd></div></dl>'
        '</details></section>',
        '<section><span class="eyebrow">SUGGESTED NEXT STEP</span>'
        '<h2>참고할 개선 방향</h2><p>' +
        _e(brief["safe_fix_guidance"] or
           "이 사례의 구체적인 해결 방법은 추가 검토가 필요합니다.") +
        '</p><h3>확인해 볼 항목</h3><p>' +
        _e(brief["regression_plan"] or
           "적용 전 확인할 항목을 먼저 정의해 보세요.") +
        '</p><p class="customer-note">'
        '참고용 제안입니다. 실제 적용 환경에서 별도로 검증해 주세요.'
        '</p></section>',
    ]
    if brief["fixture_design"] is not None:
        markup.append(
            '<section><h2>패턴별 한정형 재현 설계</h2>'
            '<p>입력/조건: ' + _e(brief["fixture_design"]) + '</p>'
            '<p>기대 불변조건: ' + _e(brief["expected_invariant"]) + '</p>'
            '<p>시험 환경 가정: ' + _e(brief["target_environment"]) + '</p>'
            '<p>이 설계는 독립 실행한 회귀시험의 결과가 아닙니다.</p>'
            '</section>')
    else:
        markup.append(
            '<section><h2>개별 재현 설계</h2><p>'
            '이 후보의 전용 재현 입력·기대값이 아직 정의되지 않았습니다.'
            ' 공개 변경 내용을 검토하고 독립 회귀시험을 수동 설계해야 합니다.'
            '</p></section>')
    markup.append(
        '<section><h2>다음에 할 일</h2><ol class="review-steps">' +
        "".join('<li>' + _e(action) + '</li>'
                for action in brief["manual_actions"]) +
        '</ol></section>')
    markup.append(
        '<section><details class="technical-details">'
        '<summary>세부 검증 상태</summary><ul class="review-gates">' +
        "".join('<li>' + _e(name) + ': <strong>' + _e(state) +
                '</strong></li>' for name, state in gates.items()) +
        '</ul><p>실제 회귀시험: NOT_EXECUTED · 승인: NO · 배포: NO</p>'
        '</details></section>')
    return _page("후보 검토 작업", "".join(markup))


def _engine(raw: str, *, root: Path | None = None) -> str:
    require_local_work("DEV_ENGINE_SKILL")
    from .capability_trials import RECIPES, evaluate_ucie_owned_recipe

    args = _params(raw, ("purpose",))
    purpose = args.get("purpose", "")
    if purpose and purpose not in (*RECIPES, "REAL_PUBLIC_CATALOG",
                                   "MCP_PROMPTS_CONTRACT"):
        raise LocalProductError("unregistered development engine")
    friendly = {
        "ENGINE_INCREMENTAL_BUILD": ("증분 빌드 실험", "변경된 부분만 다시 계산하는 방법"),
        "SKILL_TEST_AUTOMATION": ("테스트 탐색 도구", "필요한 테스트를 더 빠르게 찾아보는 방법"),
        "LEARNING_FEEDBACK_LOOP": ("피드백 분석 예제", "변경된 결과를 효율적으로 모으는 방법"),
    }
    choices = "".join(
        '<li><a href="/local/engine?purpose=' + _e(name) + '">'
        '<span>' + _e(friendly[name][0]) + '</span>'
        '<span class="recipe-copy">' + _e(friendly[name][1]) +
        ' · 예제 체험</span></a></li>'
        for name in sorted(RECIPES))
    choices += (
        '<li><a href="/local/engine?purpose=MCP_PROMPTS_CONTRACT">'
        '<span>MCP 입력 오류 계약 체험</span>'
        '<span class="recipe-copy">UCIE 자체 생성 JSON-RPC 사례로 '
        '오류 분류 계약을 검사해 보세요. 실제 SDK 실행 아님.</span></a></li>'
        '<li><a href="/local/engine?purpose=REAL_PUBLIC_CATALOG">'
        '<span>기술 자료 검색 비교</span>'
        '<span class="recipe-copy">기존 공개 기술 자료의 검색 방법을 비교해 보세요.'
        '</span></a></li>')
    body = (
        '<section class="search-panel"><h2>개발 도구 선택</h2>'
        '<p>관심 있는 기능을 선택해 사용 방법과 예제 결과를 살펴보세요.</p>'
        '<ul class="recipe-list">' + choices + '</ul>'
        '<p class="customer-note">예제의 결과는 실제 작업 환경에서'
        ' 동일한 성능을 보장하지 않습니다.</p></section>')
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
                '<dl class="inventory-grid">'
                '<div><dt>공개 항목</dt><dd>' +
                _e(out.get("real_public_catalog_items")) + '건</dd></div>'
                '<div><dt>요청</dt><dd>' + _e(out.get("query_count")) + '회</dd></div>'
                '<div><dt>검색 결과 불일치</dt><dd>' +
                _e(out.get("mismatched_query_results")) + '건</dd></div>'
                '<div><dt>기본 탐색 연산</dt><dd>' +
                _e(out.get("baseline_scan_operations")) + '</dd></div>'
                '<div><dt>색인 구축 포함 연산</dt><dd>' +
                _e(out.get("candidate_index_build_and_lookup_operations")) +
                '</dd></div><div><dt>소스 집합 SHA-256</dt>'
                '<dd><code>' + _e(out.get("public_catalog_sha256")) +
                '</code></dd></div></dl>'
                '<p>상태: <code>' + _e(out.get("status")) + '</code></p>'
                '<p><strong>한계:</strong> 승인된 로컬 공개 근거 메타데이터의'
                ' 정확 키 테스트이며, 전체 문자열 검색·원본 코드 실행·'
                ' 고객 성능 검증·운영 색인 반영이 아닙니다.</p></section>')
        else:
            raise LocalProductError("real public catalog result requires review")
    elif purpose == "MCP_PROMPTS_CONTRACT":
        from .mcp_prompt_regression_v01 import (
            SCHEMA as MCP_WIRE_SCHEMA, SOURCE_PR as MCP_SOURCE_PR,
            UPSTREAM_MERGE_SHA as MCP_MERGE_SHA,
            synthetic_demonstration,
        )
        trial = synthetic_demonstration()
        if (type(trial) is not dict
                or trial.get("schema") != MCP_WIRE_SCHEMA
                or trial.get("status") !=
                "SYNTHETIC_WIRE_CONTRACT_ONLY_NO_SDK_EXECUTION"
                or trial.get("source_pr") != MCP_SOURCE_PR
                or trial.get("source_merge_sha") != MCP_MERGE_SHA
                or trial.get("cases") != 8
                or trial.get("contract_matches") != 6
                or trial.get("non_input_controls") != 2
                or trial.get("synthetic_pre_fix_violations_detected") != 4
                or trial.get("independent_sdk_regression") != "NOT_EXECUTED"
                or trial.get("first_fixed_release") != "NOT_VERIFIED"
                or trial.get("per_revision_rights_approved") is not False
                or trial.get("auto_promoted") is not False
                or trial.get("customer_release_authorized") is not False
                or trial.get("network_requests") != 0
                or trial.get("persistent_writes") != 0):
            raise LocalProductError("unsafe synthetic MCP contract trial")
        body += (
            '<section class="shelf-entry"><span class="eyebrow">'
            'UCIE FIRST-PARTY TEST</span>'
            '<h2>입력 오류 분류 계약 · 자체 예제 결과</h2>'
            '<dl class="inventory-grid">'
            '<div><dt>UCIE 자체 사례</dt><dd>' +
            _e(trial["cases"]) + '건</dd></div>'
            '<div><dt>계약 일치</dt><dd>' +
            _e(trial["contract_matches"]) + '건</dd></div>'
            '<div><dt>서버 실행 오류 대조</dt><dd>' +
            _e(trial["non_input_controls"]) + '건</dd></div>'
            '<div><dt>수정 전 합성 오류 탐지</dt><dd>' +
            _e(trial["synthetic_pre_fix_violations_detected"]) +
            '건</dd></div></dl>'
            '<p>검사 기준: 입력 오류 -32602. 현재 실행은 UCIE가 만든 '
            '고정 JSON-RPC 사례의 검사이며 실제 MCP SDK·네트워크·'
            '고객 코드 실행 결과가 아닙니다.</p>'
            '<p>공식 최초 수정 포함 배포판·독립 보안 검토·배포 권리는 '
            '미확인입니다. 자동 승인 및 고객 배포는 금지됩니다.</p>'
            '<p><a href="/local/guide/mcp-prompts">'
            '출처·수정 전후 근거와 SkillBook 003 검토 가이드 보기 →'
            '</a></p></section>'
        )
    elif purpose:
        out = evaluate_ucie_owned_recipe(
            purpose, rows=128, queries=16, repeats=2)
        if (out.get("purpose_code") != purpose
                or out.get("exact_result_equivalence_observed") is not True
                or out.get("production_adopted") is True):
            raise LocalProductError("UCIE engine result not safe for local use")
        body += (
            '<section><h2>실행 결과</h2>'
            '<p>엔진 ID: <code>' + _e(out.get("recipe_id")) + '</code></p>'
            '<dl class="inventory-grid">'
            '<div><dt>기준 연산</dt><dd>' +
            _e(out.get("baseline_operations")) + '</dd></div>'
            '<div><dt>후보 연산 · 준비 포함</dt><dd>' +
            _e(out.get("candidate_operations_including_setup")) + '</dd></div>'
            '<div><dt>결과 동등성</dt><dd>' +
            _e(out["exact_result_equivalence_observed"]) + '</dd></div>'
            '<div><dt>검토 상태</dt><dd><code>' +
            _e(out.get("status")) + '</code></dd></div></dl>'
            '<p><strong>한계:</strong> 합성 workload 비교입니다.'
            ' 실제 프로젝트 또는 운영환경 개선 효과는 아직 검증하지 않았습니다.</p>'
            '</section>')
    return _page("개발 엔진·스킬", body)



def _skillbook_runner(raw: str) -> str:
    """User-initiated execution of ONLY the two existing first-party demos.

    This is a real recipe call over UCIE-owned disposable/static inputs.
    It is neither a customer-data analyser nor an approved or signed skill.
    """
    require_local_work("VIRTUAL_LIBRARY")
    from .skillbook_consumer_pilot_v01 import (
        SCHEMA as PY_SCHEMA, OBSERVED as PY_OBSERVED,
        demonstrate_synthetic_consumer,
    )
    from .skillbook_git_porcelain_product_v01 import (
        DEMO_SCHEMA as GIT_SCHEMA, DEMO_OBSERVED as GIT_OBSERVED,
        demonstrate_in_memory_consumer,
    )

    args = _params(raw, ("book", "run"))
    book = args.get("book", "")
    execution = args.get("run", "")
    if book not in ("python", "git") or execution not in ("", "1"):
        raise LocalProductError("only registered existing UCIE SkillBook consumers")
    title = (
        "Python os.scandir 제한형 파일 열거"
        if book == "python" else "Git porcelain v1 -z 상태 요약"
    )
    back = "/local/library?q=" + book
    html = (
        '<section class="search-panel"><h2>' + _e(title) + '</h2>'
        '<p><a href="' + back + '">← 라이브러리로 돌아가기</a></p>'
        '<p>준비된 예제 데이터로 기능을 체험할 수 있습니다.'
        ' 개인 파일과 저장소는 분석하지 않습니다.</p>'
        '<div class="page-controls">'
        '<a class="button-primary" href="/local/skillbook-run?book=' + book +
        '&amp;run=1">예제 실행 <span aria-hidden="true">→</span></a>'
        '</div><p class="customer-note">'
        '이 예제는 실제 작업 환경에서의 결과를 보장하지 않습니다.'
        '</p></section>'
    )
    if execution != "1":
        return _page("SkillBook 실행", html)
    if book == "python":
        out = demonstrate_synthetic_consumer()
        if (type(out) is not dict or out.get("schema") != PY_SCHEMA
                or out.get("status") != PY_OBSERVED
                or out.get("real_ucie_authored_recipe_executed") is not True
                or out.get("only_temporary_synthetic_fixture_used") is not True
                or out.get("temporary_fixture_cleaned") is not True
                or out.get("real_owner_directory_scanned") is not False
                or out.get("file_contents_read") is not False
                or out.get("operating_database_writes") != 0
                or out.get("network_requests") != 0
                or out.get("independent_qa_verified") is not False
                or out.get("owner_release_approved") is not False
                or out.get("export_allowed") is not False
                or out.get("bounded_regular_file_name_count") != 2
                or out.get("directory_entry_budget") != 3
                or out.get("budget_overflow_blocked") is not True
                or out.get("invalid_budget_blocked") is not True
                or out.get("relative_path_blocked") is not True):
            raise LocalProductError("Python SkillBook demo scope or result drift")
        html += (
            '<section><h2>Python 예제 결과</h2>'
            '<dl class="inventory-grid">'
            '<div><dt>찾은 파일</dt><dd>' +
            _e(out["bounded_regular_file_name_count"]) + '개</dd></div>'
            '<div><dt>탐색한 항목</dt><dd>' +
            _e(out["directory_entry_budget"]) + '개</dd></div>'
            '<div><dt>안전 확인</dt><dd>잘못된 입력 및 경로 제한 확인</dd></div>'
            '<div><dt>예제 정리</dt><dd>완료</dd></div></dl>'
            '<details class="technical-details"><summary>기술적 실행 정보</summary>'
            '<p>정규 파일: ' + _e(out["bounded_regular_file_name_count"]) + '개'
            ' · 상대 경로 차단: 예 · 소유자 실제 파일 스캔: 없음</p>'
            '<p>상태 코드: <code>' + _e(out["status"]) + '</code></p>'
            '</details></section>'
        )
    else:
        out = demonstrate_in_memory_consumer()
        counts = out.get("safe_summary_counts")
        if (type(out) is not dict or out.get("schema") != GIT_SCHEMA
                or out.get("status") != GIT_OBSERVED
                or out.get("real_ucie_recipe_executed") is not True
                or out.get("only_static_ucie_authored_bytes_used") is not True
                or out.get("real_repository_inspected") is not False
                or out.get("git_subprocess_invoked") is not False
                or out.get("filename_or_private_data_returned") is not False
                or out.get("operating_database_writes") != 0
                or out.get("network_requests") != 0
                or out.get("independent_qa_verified") is not False
                or out.get("owner_release_approved") is not False
                or out.get("export_allowed") is not False
                or out.get("demo_entries") != 4
                or out.get("budget_3_rejected") is not True
                or type(counts) is not dict
                or counts != {
                    "tracked_changed": 1, "renamed": 1, "copied": 0,
                    "conflicted": 1, "untracked": 1, "ignored": 0}):
            raise LocalProductError("Git SkillBook demo scope or result drift")
        html += (
            '<section><h2>Git 예제 결과</h2>'
            '<dl class="inventory-grid">'
            '<div><dt>변경된 항목</dt><dd>' +
            _e(counts["tracked_changed"]) + '개</dd></div>'
            '<div><dt>이름이 변경된 항목</dt><dd>' +
            _e(counts["renamed"]) + '개</dd></div>'
            '<div><dt>충돌 표시</dt><dd>' +
            _e(counts["conflicted"]) + '개</dd></div>'
            '<div><dt>추적하지 않는 항목</dt><dd>' +
            _e(counts["untracked"]) + '개</dd></div></dl>'
            '<details class="technical-details"><summary>기술적 실행 정보</summary>'
            '<p>합성 Git 레코드: ' + _e(out["demo_entries"]) + '건'
            ' · 추적 변경: ' + _e(counts["tracked_changed"]) +
            ' · 충돌: ' + _e(counts["conflicted"]) +
            ' · 저장소 스캔: 없음</p>'
            '<p>상태 코드: <code>' + _e(out["status"]) +
            '</code></p></details></section>'
        )
    html += (
        '<section class="workbench-note"><h2>참고해 주세요</h2>'
        '<p>이 결과는 준비된 예제만 사용한 결과입니다.'
        ' 실제 코드나 파일은 분석하지 않았으며,'
        ' 업무 환경에 적용하기 전에 별도의 확인이 필요합니다.</p>'
        '</section>'
    )
    return _page("SkillBook 실행 결과", html)


def _mcp_review_guide(raw: str, *, json_mode: bool = False) -> str:
    """Local V04-shell reading only; NO book activation or browser execution."""
    require_local_work("VIRTUAL_LIBRARY")
    if raw:
        raise LocalProductError("MCP guide detail cannot have query arguments")
    from .mcp_prompts_guide_v01 import (
        build_readonly_guide, SCHEMA as MCP_SCHEMA, STATUS as MCP_STATUS,
        SKILLBOOK_ID as MCP_ID,
    )
    guide = build_readonly_guide()
    gates = guide.get("review_gates")
    source = guide.get("source_evidence")
    if (guide.get("schema") != MCP_SCHEMA
            or guide.get("skillbook_id") != MCP_ID
            or guide.get("status") != MCP_STATUS
            or guide.get("export_allowed") is not False
            or guide.get("auto_promoted") is not False
            or guide.get("network_requests") != 0
            or guide.get("operating_database_writes") != 0
            or type(gates) is not dict
            or any(value is not False for value in gates.values())
            or type(source) is not dict
            or source.get("official_repository") != "modelcontextprotocol/python-sdk"
            or source.get("patch_merge_commit") !=
            "754254c08fe1c3eda18b69da3d336106fe8d72d6"
            or type(guide.get("chapters")) is not list
            or len(guide["chapters"]) != 5):
        raise LocalProductError("unapproved SkillBook 003 state drift")
    if json_mode:
        return json.dumps(guide, ensure_ascii=False, sort_keys=True)
    body = (
        '<section class="search-panel"><span class="eyebrow">'
        'SKILLBOOK 003 · REVIEW ONLY</span>'
        '<h2>' + _e(guide["title"]) + '</h2>'
        '<p>실제 공개 SDK 전후 검증에 근거한 UCIE 작성 기술 가이드입니다. '
        '미승인 초안이며 재배포·자동 실행·출시가 허용되지 않습니다.</p>'
        '<div class="page-controls"><a href="/local/library?q=MCP">'
        '도서관으로 돌아가기</a></div></section>'
        '<section class="shelf-entry"><h3>공식 근거·검증 범위</h3>'
        '<p><a href="' + _e(source["pr_url"]) +
        '" rel="noopener noreferrer" target="_blank">'
        '공식 MCP SDK 수정 PR #3696</a></p>'
        '<p>수정 전 ' + _e(source["pre_fix_tag"]) +
        ' · 수정 병합 ' + _e(source["patch_merge_commit"]) + '</p>'
        '<p>실제 설치 SDK 메모리 내 테스트: ' +
        _e(source["observed_cases"]) + '건(두 시점·두 프로토콜). '
        '공식 최초 수정 포함 배포판: 미확인.</p></section>'
    )
    for chapter in guide["chapters"]:
        if (type(chapter) is not dict
                or set(chapter) != {"heading", "text", "claim_scope"}
                or any(type(value) is not str or not value
                       for value in chapter.values())):
            raise LocalProductError("unexpected MCP guide chapter")
        body += (
            '<section class="shelf-entry"><h3>' + _e(chapter["heading"]) +
            '</h3><p>' + _e(chapter["text"]) +
            '</p><details class="technical-details"><summary>근거 범위'
            '</summary><code>' + _e(chapter["claim_scope"]) +
            '</code></details></section>'
        )
    body += (
        '<section class="shelf-entry"><h3>재사용 인터페이스</h3>'
        '<p><code>' + _e(guide["machine_skill_contract"]["callable"]) +
        '</code> · 제한된 호출 자료만 검사; 브라우저에서는 실행하지 않습니다.</p>'
        '<p><a href="/local/guide/mcp-prompts.json">계약 및 근거 JSON 보기</a></p>'
        '<p><a href="/local/engine?purpose=MCP_PROMPTS_CONTRACT">'
        'UCIE 자체 오류 분류 계약 예제 실행하기 →</a></p>'
        '<p>의존성 보안·사용권·소유자 승인·고객 배포는 모두 NO-GO입니다.</p>'
        '</section>'
    )
    # Preserve the frozen V04 whitelist and visual shell without a new page type.
    return _page("통합 가상도서관", body)


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
        '<section class="search-panel"><h2>라이브러리 검색</h2>'
        '<p>기술 가이드, 참고 자료, 공개 기술 사례를 한곳에서 찾아보세요.</p>'
        '<form action="/local/library" method="get">'
        '<label>자료 검색 <input name="q" maxlength="80" value="' +
        _e(term) + '" placeholder="예: Git, Python, scandir"></label>'
        '<button type="submit">검색</button></form></section>'
        '<section class="shelf-title"><span class="eyebrow">GUIDES</span>'
        '<h2>기술 가이드</h2>'
        '<p>' + _e(len(books)) + '개 자료</p></section>'
    )
    for book in books:
        identity = book.get("skillbook_id")
        if (type(identity) is not str or len(identity) > 100
                or not identity.isascii()
                or book.get("human_approved") is not False
                or book.get("export_allowed") is not False):
            raise LocalProductError("forged or unsafe SkillBook")
        from .skillbook_product_v01 import SKILLBOOK_ID as PY_BOOK_ID
        from .skillbook_git_porcelain_product_v01 import SKILLBOOK_ID as GIT_BOOK_ID
        if identity == PY_BOOK_ID:
            demo_link = (
                '<a href="/local/skillbook-run?book=python">'
                'Python 예제 체험 →</a>'
            )
        elif identity == GIT_BOOK_ID:
            demo_link = (
                '<a href="/local/skillbook-run?book=git">'
                'Git 예제 체험 →</a>'
            )
        else:
            raise LocalProductError("unexpected unregistered SkillBook")
        body += (
            '<article class="shelf-entry">'
            '<span class="card-kicker">GUIDE · 검토 중</span>'
            '<h3><a href="/skillbooks/' + quote(identity, safe="") +
            '">' + _e(book.get("title", "기술 가이드")) + '</a></h3>'
            '<p>기술 내용을 살펴보고 예제를 확인해 보세요.</p>'
            '<div class="page-controls">' + demo_link + '</div>'
            '<details class="technical-details"><summary>'
            '자료 정보</summary><p>출처 ' + _e(book.get("source_id")) +
            ' · 적용 범위 ' + _e(book.get("version_scope_claim")) +
            '</p><p>검토 중인 초안 · 외부 배포 가능한 완성본이 아닙니다.</p>'
            '</details></article>'
        )
    if not books:
        body += (
            '<section class="workbench-note"><h2>일치하는 가이드가 없습니다</h2>'
            '<p>검색어를 바꿔 다시 확인해 보세요.</p></section>'
        )
    from .mcp_prompts_guide_v01 import matches as matches_mcp_guide
    mcp_guide_visible = matches_mcp_guide(term)
    body += (
        '<section class="shelf-title"><span class="eyebrow">READING</span>'
        '<h2>검토 중인 자료</h2><p>' + _e(len(drafts) + int(mcp_guide_visible)) +
        '개 자료 · 준비 중인 초안</p></section>'
    )
    if mcp_guide_visible:
        body += (
            '<article class="shelf-entry">'
            '<span class="card-kicker">SKILLBOOK 003 · 미승인 초안</span>'
            '<h3><a href="/local/guide/mcp-prompts">'
            'MCP prompts/get 입력 오류와 실행 오류 구분</a></h3>'
            '<p>실제 SDK 16개 호출 전후 비교 근거 · 안전한 오류 구분 · '
            '제한된 기계 판독 계약 · 재배포 불가</p></article>'
        )
    for draft in drafts:
        ident = draft.get("draft_sha256")
        if type(ident) is not str or re.fullmatch(r"[0-9a-f]{64}", ident) is None:
            raise LocalProductError("invalid reviewed editorial draft reference")
        body += (
            '<article class="shelf-entry">'
            '<span class="card-kicker">ARTICLE · 검토 중</span>'
            '<h3><a href="/catalog/review?id=' + ident + '">' +
            _e(draft.get("topic", "기술 자료")) + '</a></h3>'
            '<p>내용을 검토하고 있는 자료입니다.</p>'
            '<details class="technical-details"><summary>'
            '자료 출처</summary><p>' +
            _e(", ".join(draft.get("source_ids", []))) +
            '</p><p>원문·권리·정확성 추가 확인 필요</p></details></article>'
        )
    if not drafts and not mcp_guide_visible:
        body += (
            '<section class="workbench-note"><h2>일치하는 자료가 없습니다</h2>'
            '<p>다른 키워드로 검색해 보세요.</p></section>'
        )
    body += (
        '<section class="shelf-title" data-shelf="public">'
        '<span class="eyebrow">SOURCES</span>'
        '<h2>공개 기술 사례</h2>'
        '<p>공개 저장소의 변경 사례를 찾아보고 원문을 확인하세요.'
        ' 검토 전 자료는 따로 표시됩니다.</p></section>'
    )
    if term.isascii():
        body += _paged_evidence(
            root, term, page=page, route="/local/library")
    else:
        if page != 1:
            raise LocalProductError("non-ASCII public evidence paging not supported")
        body += (
            '<section class="workbench-note"><h2>검색어 안내</h2>'
            '<p>공개 기술 사례는 현재 영문 검색어로 찾아보실 수 있습니다.'
            ' Python 또는 Git 등의 키워드를 사용해 주세요.'
            '</p></section>'
        )
    return _page("통합 가상도서관", body)


def _evolution(root: Path, raw: str) -> str:
    """Read-only actual collection inventory, not an approval metric."""
    require_local_work("EVIDENCE_EVOLUTION")
    from .public_collection_inventory_v01 import SCHEMA as INVENTORY_SCHEMA, collection_inventory

    args = _params(raw, ("q", "page"))
    term = args.get("q", "")
    if QUERY.fullmatch(term) is None:
        raise LocalProductError("invalid public change search")
    page = _page_number(args)
    inventory = collection_inventory(root)
    if (inventory.get("schema") != INVENTORY_SCHEMA
            or inventory.get("operating_database_writes") != 0):
        raise LocalProductError("unexpected UCIE collection inventory")
    issues = inventory.get("issues", [])
    body = (
        '<section class="search-panel">'
        '<h2>개선 아이디어 찾아보기</h2>'
        '<p>공개 기술 변경 사례에서 새로운 방법을 살펴보세요.</p>'
        '<form action="/local/evolution" method="get">'
        '<label>검색어 <input name="q" maxlength="80" value="' +
        _e(term) + '" placeholder="예: python, API"></label>'
        '<button type="submit">검색</button></form></section>'
        '<section class="workbench-note">'
        '<details class="technical-details"><summary>자료 수집 현황 보기'
        '</summary>'
        '<dl class="inventory-grid">'
        '<div><dt>수집 현황</dt><dd><code>' +
        _e(inventory.get("status")) + '</code></dd></div>'
        '<div><dt>기록 시각</dt><dd><code>' +
        _e(inventory.get("captured_utc", "보고되지 않음")) + '</code></dd></div>'
        '<div><dt>공개 변경 기록</dt><dd>기존 공개 PR 후보: ' +
        _e(inventory.get("legacy_miner", {}).get("candidates", "확인 불가")) +
        '</dd></div>'
        '<div><dt>근거 개정</dt><dd>Stage10 개정: ' +
        _e(inventory.get("stage10_public_candidate_staging", {}).get(
            "candidate_revisions", "확인 불가")) + '</dd></div>'
        '<div><dt>확인할 항목</dt><dd>' +
        _e(", ".join(issues) if issues else "현재 별도 기록 없음") +
        '</dd></div></dl>'
        '<p class="customer-note">원본 자료·개정 내역은 서로 다른'
        ' 기준으로 집계되며, 검증된 해결책의 수를 의미하지 않습니다.'
        ' 자동 승격은 수행하지 않습니다.</p></details>'
        '</section>'
    )
    body += _paged_evidence(root, term, page=page,
                            route="/local/evolution")
    return _page("근거 기반 개선", body)


def _policy() -> str:
    require_local_work("LOCAL_APP")
    return _page(
        "개발 규칙",
        '<section class="search-panel">'
        '<h2>UCIE는 어떤 서비스인가요?</h2>'
        '<p>UCIE는 공개된 기술 자료를 찾고, 개발 도구를 체험하며,'
        ' 개선 방향을 살펴보는 기술 탐색 공간입니다.</p>'
        '<div class="page-controls">'
        '<a href="/local/error">문제 예방 살펴보기 →</a>'
        '<a href="/local/library">라이브러리 열기 →</a>'
        '</div></section>'
        '<section><h2>자료는 어떻게 활용하나요?</h2>'
        '<p>기술 자료에는 원본 출처와 검토 상태가 함께 제공됩니다.'
        ' 관심 있는 내용을 살펴보고, 실제 코드에 적용하기 전에'
        ' 사용 중인 버전과 환경에 맞는 시험을 진행해 주세요.</p>'
        '<p>검토 전 자료에는 별도 표시가 있습니다.'
        ' 표시된 안내나 예제는 자동으로 코드를 수정하지 않습니다.</p>'
        '</section>'
        '<section><h2>예제 결과는 무엇을 의미하나요?</h2>'
        '<p>예제는 제한된 시험 조건에서 실행됩니다.'
        ' 프로젝트 전체의 성능이나 보안을 보증하지 않으므로'
        ' 실제 환경에서 추가 확인이 필요합니다.</p>'
        '</section>'
    )


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
                friendly = (
                    ("/local/error", "문제 예방"),
                    ("/local/engine", "개발 도구"),
                    ("/local/library", "라이브러리"),
                    ("/local/evolution", "개선 제안"),
                )
                links = "".join(
                    '<a href="' + href + '">' + _e(label) + '</a>'
                    for href, label in friendly)
                local_nav = (
                    '<nav aria-label="UCIE 메뉴" data-ucie-local-nav="true">'
                    '<strong>UCIE</strong>'
                    '<a href="/local">홈</a>' + links + '</nav>'
                )
                content = content.replace("</header>", "</header>" + local_nav, 1)
            if (status == 200 and mime == "text/html; charset=utf-8"
                    and type(content) is str
                    and (route in ("/catalog", "/catalog/review")
                         or route.startswith("/skillbooks")
                         or route.startswith("/item/"))
                    and content.startswith("<!doctype html>")
                    and content.count("<head>") == 1
                    and content.count("</head>") == 1
                    and content.count("<body>") == 1
                    and content.count("</body>") == 1
                    and content.count("</html>") == 1):
                # Re-skin only the first-party nested page envelope.
                # Keep base renderer paths, evidence, headers and policies.
                from .local_v1_design_v04 import skin_nested_local_page
                content = skin_nested_local_page(content)
            return super().reply(status, content, mime)

        def do_POST(self):
            return self.reply(405, "LOCAL_PRODUCT_READ_ONLY",
                              "text/plain; charset=utf-8")

        def do_GET(self):
            parts = urlsplit(self.path)
            if parts.path not in (
                    "/", "/local", "/local/", "/local/health", "/local/error",
                    "/local/engine", "/local/books", "/local/library",
                    "/local/evolution", "/local/review", "/local/policy",
                    "/local/skillbook-run", "/local/guide/mcp-prompts",
                    "/local/guide/mcp-prompts.json"):
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
                        "owner_acceptance_verified": True,
                        "online_release_authorized": False,
                        "operating_database_writes": 0,
                    }, sort_keys=True), "application/json; charset=utf-8")
                if parts.path in ("/", "/local", "/local/"):
                    if parts.query and not (
                        parts.path in ("/local", "/local/")
                        and _is_benign_home_tracking(parts.query)
                    ):
                        raise LocalProductError("local home cannot take query")
                    if parts.path == "/local/" or parts.query:
                        # Normalize only the local landing path: no query
                        # values reflected, no customer/approval bypass.
                        self.send_response(302)
                        self.send_header("Location", "/local")
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("Content-Length", "0")
                        self.send_header("X-Content-Type-Options", "nosniff")
                        self.end_headers()
                        return
                    html = _home()
                elif parts.path == "/local/error":
                    html = _error(root, parts.query)
                elif parts.path == "/local/review":
                    html = _review(root, parts.query)
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
                elif parts.path == "/local/skillbook-run":
                    html = _skillbook_runner(parts.query)
                elif parts.path in ("/local/guide/mcp-prompts",
                                    "/local/guide/mcp-prompts.json"):
                    is_json = parts.path.endswith(".json")
                    value = _mcp_review_guide(parts.query, json_mode=is_json)
                    return self.reply(200, value,
                                      "application/json; charset=utf-8" if is_json
                                      else "text/html; charset=utf-8")
                elif parts.path == "/local/evolution":
                    html = _evolution(root, parts.query)
                else:
                    if parts.query:
                        raise LocalProductError("local roadmap does not take query")
                    html = _policy()
                return self.reply(200, html)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                # Edge/Chromium may abandon a speculative or stale socket.
                # Do not attempt a second response to an already closed peer.
                self.close_connection = True
                return
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
        with LOCAL_SERVER_CLASS(("127.0.0.1", args.port), make_handler(root)) as server:
            url = "http://127.0.0.1:" + str(server.server_port) + "/local"
            print(json.dumps({
                "schema": APP_SCHEMA,
                "status": APP_STATUS,
                "local_app_url": url,
                "bound_port": server.server_port,
                "port_selected_automatically": args.port == 0,
                "owner_acceptance_verified": True,
                "online_release_authorized": False,
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
