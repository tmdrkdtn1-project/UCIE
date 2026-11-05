"""UCIE local-only SkillBook V0.1 explorer layered over the V1.1 Library.

All /skillbooks routes are first-party, fixed, memory-only and offline.
Legacy V1.1 evidence search/audit and explicit public check remain unchanged.
No background collection, exports, approval or new server/service registration.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import HTTPServer
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import library_browser_v11 as previous
from . import skillbook_git_porcelain_product_v01 as git002
from .library_browser_v02 import _head, _foot
from .skillbook_product_v01 import (
    SKILLBOOK_ID, SkillBookProductError, get_skillbook, search_skillbooks,
)

SCHEMA = "UCIE_LOCAL_SKILLBOOK_BROWSER_V01"
NAVIGATION = '<nav class="audit-nav"><a href="/skillbooks">실물 SkillBook 탐색 (미승인 초안)</a></nav>'
STYLE = """<style>
.skillbook-notice{background:#f3f5f8;border-left:3px solid #496a9f;padding:16px;margin:16px 0}
.skillbook-chapter{border:1px solid #dce5f1;background:white;border-radius:12px;padding:16px;margin:16px 0}
.skillbook-chapter h2{font-size:20px;margin:0 0 10px}.skillbook-meta{overflow-wrap:anywhere}
</style>"""


def _safe_text(value: object) -> str:
    return escape(str(value), quote=True)


def _template(title: str, body: str) -> str:
    page = _head(title)
    page = page.replace("</head>", STYLE + "</head>", 1)
    page = page.replace("V0.2 ·", "SkillBook V0.1 ·", 1)
    return page + NAVIGATION + body + _foot()


def render_catalog(result: dict, *, query: str, language: str, kind: str) -> str:
    if (type(result) is not dict
            or result.get("schema") != "UCIE_SKILLBOOK_V01_READONLY_CATALOG"
            or result.get("status") != "READ_ONLY_FIRST_PARTY_DRAFT_CATALOG"
            or type(result.get("items")) is not list
            or result.get("total") != len(result["items"])
            or len(result["items"]) > 2
            or result.get("approved_reusable_packages") != 0
            or result.get("operating_database_writes") != 0):
        raise SkillBookProductError("untrusted SkillBook catalog result")
    body = [
        '<p><a href="/">기존 공개 근거 검색</a> · <a href="/audit">공개 원장 감사</a></p>',
        '<p class="skillbook-notice">UCIE가 작성한 재사용 레시피 초안입니다. '
        '공식 API 동작과 UCIE 권고/시험은 별개이며, 이 자산은 '
        '독립 검증·라이선스 승인·서명·외부 배포가 완료되지 않았습니다.</p>',
        '<section class="panel"><form method="get" action="/skillbooks">',
        '<label>기술·작업 검색<input name="q" maxlength="80" value="'
        + _safe_text(query) + '" placeholder="Python, scandir, 디렉터리"></label>',
        '<label>언어<select name="language"><option value="">전체</option>'
        '<option value="Python"' + (' selected' if language == "Python" else "")
        + '>Python</option></select></label>',
        '<label>종류<select name="kind"><option value="">전체</option>'
        '<option value="REUSABLE_SKILL"' + (
            ' selected' if kind == "REUSABLE_SKILL" else "")
        + '>REUSABLE_SKILL</option></select></label>',
        '<button type="submit">SkillBook 검색</button></form></section>',
        '<p>검색 결과: ' + str(result["total"]) + '건</p>',
    ]
    for row in result["items"]:
        if (type(row) is not dict
                or row.get("skillbook_id") not in (
                    SKILLBOOK_ID, git002.SKILLBOOK_ID)
                or row.get("export_allowed") is not False
                or row.get("human_approved") is not False
                or row.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"):
            raise SkillBookProductError("forged approved SkillBook row")
        body.append('<article class="skillbook-chapter"><h2>'
                    + _safe_text(row["title"]) + '</h2><p>'
                    + _safe_text(row["domain"]) + ' · '
                    + _safe_text(row["kind"]) + ' · '
                    + _safe_text(row["language"]) + '</p><p>'
                    + _safe_text(row["status"]) + '</p><p><a href="/skillbooks/'
                    + _safe_text(row["skillbook_id"])
                    + '">기술 챕터·시험·출처 확인</a></p></article>')
    if not result["items"]:
        body.append('<p>선택한 조건에 맞는 SkillBook이 없습니다.</p>')
    return _template("SkillBook 재사용 기술 자산", "".join(body))



def render_git_chapter(book: dict) -> str:
    """Second topic, same source/evidence/contract/approval page structure."""
    if (type(book) is not dict
            or book.get("schema") != git002.SCHEMA
            or book.get("skillbook_id") != git002.SKILLBOOK_ID
            or book.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"
            or book.get("export_allowed") is not False
            or type(book.get("ucie_authored_chapters")) is not tuple
            or len(book["ucie_authored_chapters"]) != 4
            or type(book.get("source_evidence")) is not dict
            or book["source_evidence"].get("source_document_sha256")
                != git002.SOURCE_DOC_SHA256
            or book["source_evidence"].get("publisher") != "git/git"
            or type(book.get("library_entry")) is not dict
            or book["library_entry"].get("source_id") != "doc:git/git"
            or type(book.get("proof_gates")) is not dict
            or any(book["proof_gates"].get(key) is not False for key in (
                "independent_test_verified", "security_review_approved",
                "license_redistribution_approved", "human_approved",
                "published", "signed"))
            or type(book.get("consumer_pilot")) is not dict
            or book["consumer_pilot"].get("module")
                != "ucie_miner.skillbook_git_porcelain_product_v01"
            or book["consumer_pilot"].get("manual_opt_in")
                != "--run-synthetic-demo"
            or book["consumer_pilot"].get("executes_from_browser") is not False
            or type(book.get("revision_history")) is not list
            or len(book["revision_history"]) != 1
            or book["revision_history"][0].get("published") is not False):
        raise SkillBookProductError("unsafe second SkillBook view")
    e = _safe_text
    evidence = book["source_evidence"]
    contract = book["machine_skill_contract"]
    command = (
        "$env:PYTHONPATH = 'D:\\UCIE\\src'\n"
        "& 'D:\\UCIE\\.venv\\Scripts\\python.exe' -B -m "
        "ucie_miner.skillbook_git_porcelain_product_v01 "
        "--run-synthetic-demo"
    )
    body = [
        '<p><a href="/skillbooks">SkillBook 검색으로 돌아가기</a> · '
        '<a href="/catalog">통합 도서관</a></p>',
        '<p class="skillbook-notice">Git 기술 자산 초안 · 독립 QA 미검증 · '
        '라이선스/보안 검토 미승인 · 외부 패키지 반출 불가</p>',
        '<section class="skillbook-chapter"><h2>공식 근거와 적용 범위</h2>',
        '<p>UCIE ID: <code>' + e(book["skillbook_id"]) + '</code></p>',
        '<p>공식 Git 문서: <a rel="noopener noreferrer" target="_blank" href="'
        + e(evidence["official_document_url"]) + '">Git status</a></p>',
        '<p>고정 출처: git/git / ' + e(evidence["source_tag"])
        + ' / ' + e(evidence["source_file"]) + '</p>',
        '<p>Git 문서 SHA-256: <code>'
        + e(evidence["source_document_sha256"]) + '</code></p></section>',
    ]
    for chapter in book["ucie_authored_chapters"]:
        if (type(chapter) is not dict
                or set(chapter) != {"heading", "text", "claim_type"}):
            raise SkillBookProductError("invalid Git technical chapter")
        body.append(
            '<section class="skillbook-chapter"><h2>'
            + e(chapter["heading"]) + '</h2><p>'
            + e(chapter["text"]) + '</p><small>'
            + e(chapter["claim_type"]) + '</small></section>')
    body += [
        '<section class="skillbook-chapter"><h2>기계 판독 계약</h2>',
        '<p><code>' + e(contract["callable"]) + '</code></p>',
        '<p>Git 명령을 직접 실행하지 않습니다. 원시 bytes 최대 8KiB, '
        '최대 64개 항목; 경로 문자열·코드·파일 내용 반환 없음.</p>',
        '<p><a href="/skillbooks/' + git002.SKILLBOOK_ID
        + '.json">기계 계약(JSON) 읽기 전용 보기</a></p></section>',
        '<section class="skillbook-chapter"><h2>직접 실행하는 소비자 예제</h2>',
        '<p>UCIE가 만든 메모리 내 NUL 구분 시험 bytes만 분석합니다. '
        '실제 Git 저장소나 다른 프로젝트를 검색하지 않습니다.</p>',
        '<pre><code>' + e(command) + '</code></pre>',
        '<p>기대 결과: 수정 1, rename 1, 충돌 1, 미추적 1; '
        '총 4개 항목. 최대 3개 제한 입력은 실패.</p></section>',
        '<section class="skillbook-chapter"><h2>개정 이력 및 출시 경계</h2>',
        '<p>' + e(book["revision_history"][0]["version"])
        + ' · FIRST_PARTY_DRAFT_NOT_APPROVED</p>',
        '<p>독립 QA·사용권 검토·보안 검토·서명·외부 배포 미완료.</p>',
        '</section>',
    ]
    return _template(book["title"], "".join(body))


def render_chapter(book: dict) -> str:
    if type(book) is dict and book.get("skillbook_id") == git002.SKILLBOOK_ID:
        return render_git_chapter(book)
    if (type(book) is not dict or book.get("skillbook_id") != SKILLBOOK_ID
            or book.get("schema") != "UCIE_SKILLBOOK_SCANDIR_PRODUCT_V01"
            or book.get("export_allowed") is not False
            or book.get("status") != "FIRST_PARTY_DRAFT_NOT_APPROVED"
            or type(book.get("ucie_authored_chapters")) is not tuple
            or len(book["ucie_authored_chapters"]) != 4
            or book["proof_gates"].get("published") is not False):
        raise SkillBookProductError("unsafe SkillBook view")
    src = book["source_evidence"]
    metadata = book["library_entry"]
    body = [
        '<p><a href="/skillbooks">SkillBook 검색으로 돌아가기</a> · '
        '<a href="/">기존 공개 근거 검색</a></p>',
        '<p class="skillbook-notice">재사용 코드 초안: 미승인·미서명·외부 배포 불가. '
        '실제로 시험한 환경의 통과 증거와 공식문서의 API 사실을 구분합니다.</p>',
        '<section class="skillbook-chapter skillbook-meta"><h2>출처 및 범위</h2>',
        '<dl><dt>UCIE ID</dt><dd>' + _safe_text(book["skillbook_id"]) + '</dd>',
        '<dt>LibraryEntry</dt><dd><code>'
        + _safe_text(metadata["library_item_id"]) + '</code></dd>',
        '<dt>승인된 공개 출처</dt><dd><a href="'
        + _safe_text(src["official_document_url"])
        + '" rel="noopener noreferrer" target="_blank">Python 공식 os 문서</a></dd>',
        '<dt>고정 버전/커밋</dt><dd><code>'
        + _safe_text(src["source_tag"]) + ' / '
        + _safe_text(src["source_commit_sha1"]) + '</code></dd>',
        '<dt>공식 소스 전체 SHA-256</dt><dd><code>'
        + _safe_text(src["source_document_sha256"]) + '</code></dd>',
        '<dt>사용권 검토</dt><dd>NOT_REVIEWED_FOR_DISTRIBUTION</dd>',
        '<dt>외부 지원 버전 독립 검증</dt><dd>NOT_VERIFIED</dd></dl></section>',
    ]
    for row in book["ucie_authored_chapters"]:
        body += ['<section class="skillbook-chapter"><h2>'
                 + _safe_text(row["heading"]) + '</h2><p>'
                 + _safe_text(row["text"]) + '</p><p><small>'
                 + _safe_text(row["claim_type"]) + '</small></p></section>']
    pilot = book.get("consumer_pilot")
    history = book.get("revision_history")
    if (type(pilot) is not dict
            or pilot.get("mode") != "UCIE_AUTHORED_DISPOSABLE_EXAMPLE_ONLY"
            or pilot.get("module") != "ucie_miner.skillbook_consumer_pilot_v01"
            or pilot.get("manual_opt_in") != "--run-synthetic-demo"
            or pilot.get("executes_from_browser") is not False
            or pilot.get("package_export_allowed") is not False
            or type(history) is not list or len(history) != 1
            or history[0].get("state") != "FIRST_PARTY_DRAFT_NOT_APPROVED"
            or history[0].get("published") is not False):
        raise SkillBookProductError("untrusted manual consumer or revision history")
    command = (
        "$env:PYTHONPATH = 'D:\\UCIE\\src'\n"
        "& 'D:\\UCIE\\.venv\\Scripts\\python.exe' -B -m "
        "ucie_miner.skillbook_consumer_pilot_v01 --run-synthetic-demo"
    )
    body += [
        '<section class="skillbook-chapter"><h2>기계 판독 레시피</h2>',
        '<p><code>' + _safe_text(book["machine_skill_contract"]["callable"])
        + '</code></p><p>허용된 절대 경로, 총 항목 1–128개, '
        '파일 이름만 반환합니다. 도서관 조회 중 이 코드는 실행되지 않습니다.</p>',
        '<p><a href="/skillbooks/' + SKILLBOOK_ID
        + '.json">기계 계약(JSON) 읽기 전용 보기</a></p></section>',
        '<section class="skillbook-chapter"><h2>직접 실행하는 소비자 예제</h2>',
        '<p>실제 UCIE 작성 레시피를 임시 모의 디렉터리에만 실행합니다. '
        '외부 파일이나 다른 프로젝트는 탐색하지 않고 기존 도서관 서버에서도 '
        '이 코드를 실행하지 않습니다. PowerShell에서 명시적으로 실행하세요.</p>',
        '<pre><code>' + _safe_text(command) + '</code></pre>',
        '<p>예상 관측: 총 항목 3개(일반 파일 2개, 하위 폴더 1개) 중 '
        '정렬된 일반 파일명 2개; 예산 2개 제한은 실패, 예산 3개는 통과. '
        '실제 서비스 성능이나 보안 경계 검증을 뜻하지 않습니다.</p>',
        '<p>초안 v0.1.0-draft · 독립 QA 미확인 · 권리 미승인 · '
        '외부 패키지 반출 불가</p></section>',
        '<section class="skillbook-chapter"><h2>개정 이력</h2>',
        '<p>' + _safe_text(history[0]["version"]) + ' · '
        + _safe_text(history[0]["state"]) + ' · '
        + _safe_text(history[0]["scope"]) + '</p></section>',
        '<section class="skillbook-chapter"><h2>시험 및 출시 게이트</h2>',
        '<p>별도 CI/실호스트 시험 영수증을 확인하십시오. '
        '외부 프로젝트 검증·권리·보안·배포 승인은 현재 전부 미완료입니다.</p>',
        '</section>',
    ]
    return _template(book["title"], "".join(body))


def _filters(query: str) -> tuple[str, str, str]:
    if len(query) > 256:
        raise SkillBookProductError("oversized SkillBook search")
    parsed = parse_qs(query, keep_blank_values=True, strict_parsing=False)
    if (set(parsed) - {"q", "language", "kind"}
            or any(len(v) != 1 for v in parsed.values())):
        raise SkillBookProductError("unknown SkillBook search parameter")
    return (parsed.get("q", [""])[0],
            parsed.get("language", [""])[0],
            parsed.get("kind", [""])[0])


def make_handler(root: Path, **legacy_injections):
    base = previous.make_handler(root, **legacy_injections)

    class Handler(base):
        def reply(self, status, content, mime="text/html; charset=utf-8"):
            if (status == 200 and mime == "text/html; charset=utf-8"
                    and NAVIGATION not in content and "</header>" in content):
                content = content.replace("</header>", "</header>" + NAVIGATION, 1)
            return super().reply(status, content, mime)

        def do_GET(self):
            parts = urlsplit(self.path)
            is_books = parts.path in ("/skillbooks", "/skillbooks.json")
            is_detail = parts.path.startswith("/skillbooks/")
            if not (is_books or is_detail):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if parts.fragment or len(self.path) > 290:
                return self.reply(400, "INVALID_SKILLBOOK_ROUTE", "text/plain; charset=utf-8")
            try:
                if is_books:
                    query, language, kind = _filters(parts.query)
                    result = search_skillbooks(
                        query=query, language=language, kind=kind)
                    if parts.path.endswith(".json"):
                        return self.reply(200, json.dumps(
                            result, ensure_ascii=False, sort_keys=True),
                            "application/json; charset=utf-8")
                    return self.reply(200, render_catalog(
                        result, query=query, language=language, kind=kind))
                if parts.query:
                    return self.reply(400, "DETAIL_MUST_HAVE_NO_QUERY",
                                      "text/plain; charset=utf-8")
                item = parts.path.removeprefix("/skillbooks/")
                known = (SKILLBOOK_ID, git002.SKILLBOOK_ID)
                doc_id = item[:-5] if item.endswith(".json") else item
                if doc_id not in known or item not in (
                        doc_id, doc_id + ".json"):
                    return self.reply(404, "SKILLBOOK_NOT_FOUND",
                                      "text/plain; charset=utf-8")
                book = get_skillbook(doc_id)
                if item.endswith(".json"):
                    return self.reply(200, json.dumps(
                        book, ensure_ascii=False, sort_keys=True),
                        "application/json; charset=utf-8")
                return self.reply(200, render_chapter(book))
            except SkillBookProductError:
                return self.reply(400, "SKILLBOOK_BOUNDARY_NO_GO",
                                  "text/plain; charset=utf-8")
    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE owner-local draft SkillBook browser")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if (not 0 <= args.port <= 65535 or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or (os.name == "nt" and root.resolve() != Path("D:/UCIE").resolve())):
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED"}))
        return 3
    try:
        with HTTPServer(("127.0.0.1", args.port), make_handler(root)) as server:
            print(json.dumps({
                "schema": SCHEMA,
                "status": "LOCAL_DRAFT_SKILLBOOK_BROWSER_LISTENING",
                "url": "http://127.0.0.1:" + str(server.server_port) + "/skillbooks",
                "read_only": True,
                "approved_packages": 0,
                "external_code_executed": False,
                "network_without_explicit_public_probe": False,
                "scheduler_registered": False,
            }, sort_keys=True), flush=True)
            server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        return 0
    except OSError:
        print(json.dumps({"schema": SCHEMA, "status": "LOCAL_BIND_FAILED_NO_GO"}))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
