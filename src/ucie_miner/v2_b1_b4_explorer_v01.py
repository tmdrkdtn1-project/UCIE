"""Isolated UCIE V2 B0-B1-B2-B4 explorer (owner-local, preview only).

This module is NOT registered in the frozen V04 app. It serves two pinned
first-party SkillBook examples, their derived B1 capsules, and the review-only
B4 draft through local-only GET routes. No network fetch or write endpoints.
"""
from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .b1_b4_skillbook_capsule_link_v01 import (
    build_pinned_b1_capsules, build_b4_capsule_journey,
)
from .b4_skillbook_draft_v01 import build_b4_skillbook
from .b4_transfer_boundary_v01 import evaluate_transfer_case
from .b4_revision_impact_v01 import propose_affected_retests
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_V2_ISOLATED_B1_B4_EXPLORER_V01"
ROUTE = "/v2/library"
SCENARIOS = ("supported", "missing_permission", "unapproved_target")
HOST = "127.0.0.1"
LABELS = {
    "doc:python/cpython": ("Python · 제한된 폴더 탐색", "허용된 디렉터리만 검사하는 경계"),
    "doc:git/git": ("Git · 상태 요약", "파일명 대신 개수만 전달하는 경계"),
}
STYLES = """
:root{color-scheme:dark;font-family:system-ui,'Malgun Gothic',sans-serif;
background:#101620;color:#edf3fa}*{box-sizing:border-box}body{margin:0}
a{color:#99dcf4}header{border-bottom:1px solid #293548;padding:19px max(18px,calc((100vw - 1050px)/2))}
header strong{font-size:18px}header span{color:#9eaec0;margin-left:14px;font-size:13px}
main{max-width:1050px;margin:34px auto 80px;padding:0 18px}.eyebrow{color:#8ed6d2;
font-size:12px;letter-spacing:.12em;font-weight:750}h1{font-size:clamp(26px,4vw,40px);
line-height:1.25;margin:9px 0 14px}p{line-height:1.65;color:#b5c4d5}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}
.card,.panel{background:#192331;border:1px solid #334356;border-radius:17px;padding:23px}
.card h2{font-size:19px;margin:12px 0 8px}.card p{margin:8px 0 17px}
.button{display:inline-block;background:#73d6d0;color:#10212b!important;padding:11px 17px;
border-radius:10px;font-weight:750;text-decoration:none}.button:focus-visible,a:focus-visible{
outline:3px solid #d5ff62;outline-offset:4px}.tag{display:inline-block;font-size:12px;
padding:5px 9px;border-radius:30px;background:#293a4e;color:#d1e1ee}
ol{padding-left:23px}li{padding:7px 0;line-height:1.6}.mono{font-family:ui-monospace,monospace;
overflow-wrap:anywhere;font-size:12px;color:#d9e9f7}.muted{color:#99aabf}
.back{display:inline-block;margin-bottom:15px}details{border-top:1px solid #334356;
padding:15px 0}summary{cursor:pointer;font-weight:700}section{margin-bottom:24px}
.choices{display:flex;flex-wrap:wrap;gap:9px;margin:12px 0 17px}.choice{display:inline-block;padding:9px 13px;border:1px solid #5c7289;border-radius:9px;text-decoration:none}.choice[aria-current="true"]{background:#73d6d0;color:#10212b;border-color:#73d6d0;font-weight:750}.verdict{border-left:4px solid #73d6d0;padding:14px;background:#12232d}.verdict.reject{border-left-color:#ffb788;background:#302127}.metrics-scroll{overflow-x:auto;width:100%}.metrics{width:100%;border-collapse:collapse;table-layout:fixed;font-variant-numeric:tabular-nums}
.metrics th,.metrics td{padding:12px 14px;border-bottom:1px solid #334356;text-align:right;vertical-align:middle;font-size:13px}
.metrics th:first-child{width:48%;text-align:left;overflow-wrap:anywhere}
.metrics th:nth-child(2),.metrics th:nth-child(3){width:26%}
.metrics thead th{color:#c1d5ea;font-weight:700}
.metrics tbody th{font-weight:500;color:#dbe9f6}
@media(max-width:620px){.metrics{min-width:590px}}
footer{border-top:1px solid #293548;padding:22px;text-align:center;color:#96a7bd;font-size:12px}
"""


class V2ExplorerError(ValueError):
    pass


def _e(x: object) -> str:
    return escape(str(x), quote=True)


def _shell(content: str, title: str) -> str:
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
        '<title>' + _e(title) + ' · UCIE V2</title><style>' + STYLES + '</style></head>'
        '<body><header><strong>UCIE / Virtual Library</strong>'
        '<span>V2 독립 개발 미리보기 · 검토 전</span></header>'
        '<main id="main">' + content + '</main>'
        '<footer>독립 QA·원본 인증·고객 배포 승인 전 | UCIE 전용 로컬 미리보기</footer>'
        '</body></html>'
    )


def _scenario_panel(capsule: dict, scenario: str) -> str:
    """Run only fixed first-party cases, never accept arbitrary code/paths."""
    if scenario not in SCENARIOS:
        raise V2ExplorerError("INVALID_REVIEW_SCENARIO")
    tech = ("BOUNDED_SCANDIR" if capsule["source_id"] == "doc:python/cpython"
            else "BOUNDED_GIT_PORCELAIN")
    data = {
        "case_id": "UCIE_B4_REVIEW_" + scenario.upper(),
        "technology": tech,
        "caller_authorized": scenario != "missing_permission",
        "bounded_input": True,
        "fail_closed": True,
        "disclosure_documented": True,
        "evidence_pinned": True,
    }
    if scenario == "unapproved_target":
        data["technology"] = "UNAPPROVED_THIRD_TECHNOLOGY"
    verdict = evaluate_transfer_case(data)
    if verdict["release_approved"] is not False:
        raise V2ExplorerError("UNAPPROVED_VERDICT")
    selected = capsule["case_id"]
    choices = (
        ("supported", "조건 모두 충족"),
        ("missing_permission", "권한 없음"),
        ("unapproved_target", "미검증 기술"),
    )
    links = "".join(
        '<a class="choice" href="' + ROUTE + '?case=' + _e(selected) +
        '&amp;review=' + _e(key) + '" aria-current="' +
        ("true" if key == scenario else "false") + '">' + _e(label) + '</a>'
        for key, label in choices
    )
    accepted = verdict["decision"] == "CANDIDATE_WITHIN_TESTED_BOUNDARY"
    if accepted:
        message = "정적 조건을 통과한 검토 후보입니다. 실제 안전성·사용 권한·배포 승인은 입증되지 않았습니다."
    else:
        message = ("권한이 부족해 전이 후보를 거부했습니다."
                   if scenario == "missing_permission" else
                   "현재 근거에 없는 기술이므로 전이를 거부했습니다.")
    return (
        '<section class="panel" id="review" aria-label="원리 적용 조건 체험">'
        '<span class="eyebrow">B4 · 안전한 정적 판정 체험</span>'
        '<h2>조건을 바꾸면 판정이 어떻게 달라질까요?</h2>'
        '<p>내 파일이나 코드를 입력하지 않고 UCIE 자체 작성된 세 가지 사례를 비교합니다.</p>'
        '<nav class="choices" aria-label="비교할 고정 조건">' + links + '</nav>'
        '<div class="verdict' + ("" if accepted else " reject") +
        '" role="status"><strong>' +
        ("검토 후보 · 미승인" if accepted else "전이 거부") +
        '</strong><p>' + _e(message) + '</p>'
        '<p class="mono">판정 코드: ' + _e(verdict["reason"]) +
        '</p></div><p class="muted">자동 코드 실행 없음 · 고객 데이터 사용 없음</p></section>'
    )


def _revision_panel(capsule: dict) -> str:
    """Compare the same pinned source against a no-change control, no external fetch."""
    source = next(r for r in build_b4_skillbook()["source_provenance"]
                  if r["source_id"] == capsule["source_id"])
    result = propose_affected_retests([{
        "source_id": source["source_id"],
        "expected_sha256": source["sha256"],
        "observed_sha256": source["sha256"],
        "observed_tag": source["tag"],
        "independently_verified": False,
    }])
    if (result["retests_proposed"] != 0 or result["affected_sources"]
            or result["test_execution"] != "NOT_RUN"):
        raise V2ExplorerError("UNEXPECTED_REVISION_IMPACT")
    return (
        '<section class="panel" aria-label="근거 개정 영향">'
        '<h2>공개 근거가 바뀌면 무엇을 다시 확인하나요?</h2>'
        '<p>현재 고정된 버전과 SHA-256을 그대로 비교한 결과, '
        '이 사례의 재검토 제안은 <strong>0건</strong>입니다.</p>'
        '<p>이 결과는 새 공개 릴리스를 조회한 것이 아니라 '
        '변경이 없는 자체 대조 시험입니다. 실제 변경 근거는 별도 확인이 필요합니다.</p>'
        '</section>'
    )


def render_v2_explorer(case_id: str | None = None, *, review: str = "supported") -> str:
    require_local_work("VIRTUAL_LIBRARY")
    if review not in SCENARIOS:
        raise V2ExplorerError("INVALID_REVIEW_SCENARIO")
    capsules = build_pinned_b1_capsules()
    if case_id is not None and (type(case_id) is not str
                                 or case_id not in {x["case_id"] for x in capsules}):
        raise V2ExplorerError("INVALID_CASE_SELECTOR")
    if case_id is None:
        cards = []
        for capsule in capsules:
            name, detail = LABELS[capsule["source_id"]]
            cards.append(
                '<article class="card"><span class="tag">고정 공개 근거 · 검토 전</span>'
                '<h2>' + _e(name) + '</h2><p>' + _e(detail) + '</p>'
                '<p class="mono">' + _e(capsule["source_tag"]) + ' / ' +
                _e(capsule["source_id"]) + '</p>'
                '<a class="button" href="' + ROUTE + '?case=' +
                _e(capsule["case_id"]) + '">근거와 SkillBook 살펴보기</a></article>'
            )
        body = (
            '<span class="eyebrow">B0 → B1 → B2 → B4</span>'
            '<h1>기술 근거에서 재사용 가능한 원리까지</h1>'
            '<p>UCIE가 작성한 두 개의 고정 기술 사례를 선택하면 근거 Capsule, '
            '적용 한계, SkillBook 초안을 한 화면에서 확인할 수 있습니다.</p>'
            '<section class="grid" aria-label="선택 가능한 기술 사례">' +
            ''.join(cards) + '</section>'
            '<section class="panel"><h2>B5 · 로컬 기술 측정</h2>'
            '<p>이 화면이 제공하는 두 사례와 세 가지 조건 판정 경로를 '
            '사용자 데이터 없이 직접 측정할 수 있습니다.</p>'
            '<a class="choice" href="/v2/assessment">기능 측정 결과 보기</a>'
            '</section>'
            '<section class="panel"><h2>이 화면의 제한</h2>'
            '<p>개인 저장소 분석·자동 코드 수정·범용 AI 생성·배포 기능은 없습니다. '
            '기술 원리는 UCIE 검토용 추론이며 공개 문서의 독립 인증을 뜻하지 않습니다.</p>'
            '</section>'
        )
        return _shell(body, "기술 사례 선택")
    selected = next(x for x in capsules if x["case_id"] == case_id)
    journey = build_b4_capsule_journey(case_id)
    book = build_b4_skillbook()
    if (journey["capsule_id"] != selected["capsule_id"]
            or journey["b4_skillbook_sha256"] != book["content_sha256"]
            or journey["source_id"] != selected["source_id"]
            or journey["stage_b4"] != "LINKED_REVIEW_ONLY_UNVERIFIED"):
        raise V2ExplorerError("CASE_CAPSULE_BOOK_IDENTITY_DRIFT")
    name, detail = LABELS[selected["source_id"]]
    steps = [
        ("01", "기존 SkillBook 사례", selected["case_id"]),
        ("02", "고정 근거 Capsule", selected["capsule_id"]),
        ("03", "원리 및 SkillBook 초안", journey["b4_skillbook_id"]),
    ]
    listing = ''.join(
        '<li><strong>' + _e(number) + ' · ' + _e(title) + '</strong>'
        '<div class="mono">' + _e(value) + '</div></li>'
        for number, title, value in steps
    )
    chapters = ''.join(
        '<details><summary>' + _e(section["heading"]) + '</summary>'
        '<p>' + _e(section["text"]) + '</p>'
        '<p class="muted">UCIE 자체 작성 · ' + _e(section["claim_kind"]) + '</p>'
        '</details>'
        for section in book["human_chapters"]
    )
    body = (
        '<a class="back" href="' + ROUTE + '">← 다른 사례 선택</a>'
        '<span class="eyebrow">B0 + B1 + B2 → B4 / 읽기 전용</span>'
        '<h1>' + _e(name) + '</h1><p>' + _e(detail) + '</p>'
        '<section class="panel" aria-label="근거 연결 세 단계">'
        '<span class="tag">동일 출처·태그·해시 연결 확인</span><h2>3단계 근거 연결</h2>'
        '<ol>' + listing + '</ol></section>'
        '<section class="panel"><h2>공개 출처와 적용 범위</h2>'
        '<p>문서 버전: <strong>' + _e(selected["source_tag"]) + '</strong></p>'
        '<p class="mono">Source SHA-256: ' + _e(selected["source_document_sha256"]) + '</p>'
        '<p>출력 정보: ' + _e(selected["data_disclosed"]) + '</p>'
        '<p>처리 제한: ' + _e(selected["budget"]) + '</p>'
        '<p><a href="' + _e(selected["official_url"]) +
        '" rel="noopener noreferrer" target="_blank">공식 공개 문서 열기</a></p></section>'
        '<section class="panel"><h2>B4 · 재사용 원리 SkillBook</h2>'
        '<p>다른 기술로 일반화하기 전에는 권한, 입력 크기, 실패 시 중단 조건, '
        '출력 정보 노출 범위를 각각 확인해야 합니다.</p>' +
        chapters + '</section>'
        '<section class="panel"><h2>승인과 검증 상태</h2>'
        '<p><strong>REVIEW_ONLY_UNVERIFIED</strong> · 출처는 고정됐지만 '
        '독립 인증·실사용 문제 해결·권리 승인·외부 배포는 완료되지 않았습니다.</p>'
        '<p class="mono">Capsule SHA-256: ' + _e(selected["content_sha256"]) +
        '</p><p class="mono">SkillBook SHA-256: ' +
        _e(book["content_sha256"]) + '</p></section>' +
        _scenario_panel(selected, review) + _revision_panel(selected)
    )
    return _shell(body, name)


def render_b5_evaluation() -> str:
    """User-invoked read-only measured owner probe; no usage analytics."""
    from .b5_local_task_probe_v01 import run_b5_local_probe
    report = run_b5_local_probe(3)
    rows = "".join(
        '<tr><th scope="row">' + _e(item["task"]) + '</th><td>' +
        _e(item["route_render_wall_median_ms"]) + ' ms</td><td>' +
        (_e(item["route_render_cpu_median_ms"]) + ' ms'
         if item["cpu_measurement_status"] == "MEASURED"
         else '측정 해상도 미달') + '</td></tr>'
        for item in report["rows"]
    )
    content = (
        '<a class="back" href="' + ROUTE + '">← 기술 사례로 돌아가기</a>'
        '<span class="eyebrow">B5 · UCIE 자체 기술 측정</span>'
        '<h1>로컬 기능 작동 측정</h1>'
        '<p>고정된 UCIE 화면 경로 7개를 각각 3회 실행해, '
        '응답에 예상 설명이 있는지 확인했습니다. '
        '수치는 브라우저 조작 시간이 아닌 Python 서버 내부 렌더링 시간입니다. '
        'CPU 시간은 Windows 타이머 해상도보다 짧으면 0으로 표기하지 않고 '
        '측정 해상도 미달로 표시합니다.</p>'
        '<section class="panel"><h2>고정 경로별 측정값</h2>'
        '<div class="metrics-scroll"><table class="metrics"><thead><tr><th scope="col">검증 경로</th>'
        '<th scope="col">중앙값 / 벽시계</th>'
        '<th scope="col">중앙값 / CPU</th></tr></thead><tbody>' +
        rows + '</tbody></table></div>'
        '<p>총 ' + _e(report["task_observations"]) +
        '회 렌더링 · 검증된 결과만 표기했습니다.</p></section>'
        '<section class="panel"><h2>아직 측정하지 않은 항목</h2>'
        '<p>공식 문서 대비 시간, 일반 도구 대비 효율, 실제 사용자 완료율, '
        '초보자의 10초 내 첫 행동 이해도, 구매 의향, RAM 최대 사용량은 '
        '<strong>NOT_MEASURED</strong>입니다.</p>'
        '<p>사용자 행동을 기록하거나 다른 프로젝트를 읽지 않습니다. '
        '이 보고서에는 독립 QA나 제품 승인 효력이 없습니다.</p></section>'
    )
    return _shell(content, "로컬 B5 기술 측정")


def route_v2_request(method: str, target: str) -> tuple[int, str]:
    """Pure routing, exactly one GET route and one known selector."""
    if method != "GET" or type(target) is not str or len(target) > 220:
        return 405, ""
    parsed = urlsplit(target)
    if parsed.path == "/v2/assessment" and not parsed.fragment:
        if parsed.query:
            return 400, ""
        return 200, render_b5_evaluation()
    if parsed.path != ROUTE or parsed.fragment:
        return 404, ""
    if not parsed.query:
        return 200, render_v2_explorer()
    try:
        query = parse_qs(parsed.query, strict_parsing=True,
                         keep_blank_values=True, max_num_fields=2)
    except (UnicodeError, ValueError):
        return 400, ""
    if (not set(query).issubset({"case", "review"}) or "case" not in query
            or any(len(value) != 1 for value in query.values())
            or query.get("review", ["supported"])[0] not in SCENARIOS):
        return 400, ""
    try:
        return 200, render_v2_explorer(
            query["case"][0], review=query.get("review", ["supported"])[0])
    except V2ExplorerError:
        return 400, ""


class V2ExplorerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self._respond("GET")

    def do_POST(self):
        self._respond("POST")

    def _respond(self, method):
        try:
            code, document = route_v2_request(method, self.path)
        except (ValueError, KeyError, TypeError):
            code, document = 500, ""
        payload = document.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def log_message(self, *_args):
        return  # Never log case selectors or client traffic.


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE isolated V2 evidence explorer")
    parser.add_argument("--port", type=int, default=0,
                        help="0 = choose a free loopback port (default)")
    parser.add_argument("--open-browser", action="store_true",
                        help="Open the exact bound address in the default browser")
    args = parser.parse_args(argv)
    if args.port != 0 and not 1024 <= args.port <= 65535:
        raise V2ExplorerError("PORT_OUT_OF_RANGE")
    require_local_work("VIRTUAL_LIBRARY")
    # Never terminate, reuse or take over any pre-existing service/port.
    with ThreadingHTTPServer((HOST, args.port), V2ExplorerHandler) as server:
        url = "http://" + HOST + ":" + str(server.server_port) + ROUTE
        print("UCIE_V2_B1_B4_PREVIEW_READY " + url, flush=True)
        if args.open_browser:
            import webbrowser
            webbrowser.open(url, new=2)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
