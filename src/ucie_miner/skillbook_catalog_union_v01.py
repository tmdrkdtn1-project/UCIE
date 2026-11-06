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
from .public_discovery import DiscoveryError, SOURCE_SKILL
from .skill_profiles import PROFILE
from . import skillbook_editorial_production_v01 as editorial
from . import skillbook_official_doc_observation_v01 as official_docs
from .skillbook_product_v01 import (
    SKILLBOOK_ID, SOURCE_DOCUMENT_SHA256, SkillBookProductError,
    search_skillbooks, build_skillbook as build_python_book,
)
from .skillbook_git_porcelain_product_v01 import build_skillbook as build_git_book
from .skillbook_scandir_qa_v01 import CASES as W08_CASES
from .skillbook_w09_release_gate_v01 import (
    BLOCKERS as W09_BLOCKERS, SCHEMA as W09_SCHEMA,
    PREVIEW_STATE as W09_PREVIEW_STATE, preview_release_gate,
)
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


REVIEW_SCHEMA = "UCIE_W04_SKILLBOOK_EDITORIAL_COMPARISON_V01"
REVIEW_STATUS = "EDITORIAL_REVIEW_ONLY_NOT_A_RELEASE"
REVIEW_LIMIT = 4


def _editorial_drafts(editorial_records=None) -> list[dict]:
    """Only UCIE-first-party curated pilot or explicitly supplied bounded drafts.

    No GET/body parameters are accepted as draft source; data is passed only
    via a caller-supplied in-memory interface, recompiled through W01/W02.
    """
    if editorial_records is None:
        drafts = [editorial.compose_curated_two_book_pilot()]
    else:
        if (type(editorial_records) is not tuple
                or not 1 <= len(editorial_records) <= REVIEW_LIMIT):
            raise FederationError("bounded in-memory review set required")
        try:
            drafts = [editorial.compile_review_draft(r) for r in editorial_records]
        except editorial.EditorialDraftError as exc:
            raise FederationError("unverified editorial record") from exc
    identifiers = [d["draft_sha256"] for d in drafts]
    if len(set(identifiers)) != len(drafts):
        raise FederationError("duplicate editorial candidate")
    if any(d["status"] != "EDITORIAL_CANDIDATE_REVIEW_PENDING_NO_GO"
           or d["export_allowed"] is not False
           or d["human_approved"] is not False
           or d["source_digest_independently_verified"] is not False
           for d in drafts):
        raise FederationError("editorial approval state drift")
    return sorted(drafts, key=lambda d: d["draft_sha256"])


def _review_domains(draft: dict) -> list[str]:
    domains = set()
    for source in draft["sources"]:
        rid = source["source_id"].split(":", 1)[1]
        profile = SOURCE_SKILL.get(rid)
        if profile not in PROFILE:
            raise FederationError("unrecognized editorial source skill")
        domains.add(PROFILE[profile]["domain"])
    return sorted(domains)


def _review_observation_status(draft: dict, observations=None) -> list[dict]:
    """Read bounded, already-observed and UNSIGNED source-byte metadata.

    This display NEVER fetches official sources or authenticates receipt JSON.
    An observed byte SHA match does not attest revision, facts, rights or QA.
    """
    if observations is None:
        observations = ()
    if type(observations) is not tuple or len(observations) > REVIEW_LIMIT:
        raise FederationError("only bounded in-memory unsigned observation receipts")
    seen = set()
    linked = {}
    candidate_ids = {item["source_id"] for item in draft["sources"]}
    for receipt in observations:
        if type(receipt) is not dict:
            raise FederationError("unrecognized official byte receipt")
        sid = receipt.get("source_id")
        if type(sid) is not str or sid in seen:
            raise FederationError("invalid or duplicate observation source")
        seen.add(sid)
        if sid not in candidate_ids:
            continue  # Multiple candidates may use distinct registered sources.
        try:
            result = official_docs.compare_editorial_source_to_observation(
                draft, receipt)
        except official_docs.OfficialDocumentObservationError as exc:
            raise FederationError("untrusted source byte receipt") from exc
        linked[sid] = result
    statuses = []
    for sid in sorted(candidate_ids):
        result = linked.get(sid)
        if result is None:
            status = ("NOT_AN_OFFICIAL_DOCUMENT_ROUTE"
                      if sid.startswith("repo:") else "NO_MANUAL_RAW_BYTE_OBSERVATION")
            statuses.append({
                "source_id": sid, "status": status,
                "byte_sha_equal": None, "observed_raw_sha256": None,
                "observed_at_utc": None, "source_revision_verified": False,
                "receipt_authenticity_cryptographically_verified": False,
                "review_completed": False, "export_allowed": False,
            })
        else:
            statuses.append({
                "source_id": sid, "status": result["status"],
                "byte_sha_equal": result["byte_sha_equal"],
                "observed_raw_sha256": result["observed_raw_sha256"],
                "observed_at_utc": result["observed_at_utc"],
                "source_revision_verified": False,
                "receipt_authenticity_cryptographically_verified": False,
                "review_completed": False, "export_allowed": False,
            })
    return statuses


def _review_summary(draft: dict, observations=None) -> dict:
    return {
        "draft_sha256": draft["draft_sha256"], "topic": draft["topic"],
        "source_ids": sorted(s["source_id"] for s in draft["sources"]),
        "source_observation_statuses": _review_observation_status(
            draft, observations),
        "domains": _review_domains(draft),
        "chapter_count": len(draft["chapters"]),
        "status": draft["status"], "kind": "REUSABLE_SKILL",
        "machine_contract_implemented": False,
        "source_content_verified": False, "independent_qa_verified": False,
        "human_approved": False, "export_allowed": False,
    }


def inspect_review_candidate(candidate_id: str | None = None, *,
                             editorial_records=None,
                             editorial_observations=None) -> dict:
    """Actual browse-to-compare-to-review dossier, no DB/network/QA run."""
    if (candidate_id is not None
            and (type(candidate_id) is not str
                 or HEX64.fullmatch(candidate_id) is None)):
        raise FederationError("bad editorial detail selector")
    drafts = _editorial_drafts(editorial_records)
    if candidate_id is None and len(drafts) == 1:
        chosen = drafts[0]
    else:
        selected = [d for d in drafts if d["draft_sha256"] == candidate_id]
        if len(selected) != 1:
            raise FederationError("unknown editorial revision")
        chosen = selected[0]
    try:
        handoff = editorial.build_review_handoff(chosen["authoring_input"])
    except editorial.EditorialDraftError as exc:
        raise FederationError("invalid editorial handoff") from exc
    if (handoff["receipt"]["draft_sha256"] != chosen["draft_sha256"]
            or handoff["receipt"]["human_review_completed"] is not False
            or handoff["receipt"]["export_allowed"] is not False):
        raise FederationError("review dossier identity/approval drift")
    comparison = []
    for book in (build_python_book(), build_git_book()):
        entry = book["library_entry"]
        gates = book["proof_gates"]
        if (book["status"] != "FIRST_PARTY_DRAFT_NOT_APPROVED"
                or book["export_allowed"] is not False
                or gates["human_approved"] is not False):
            raise FederationError("existing SkillBook approval drift")
        comparison.append({
            "item_id": book["skillbook_id"], "title": book["title"],
            "asset_type": "EXISTING_UCIE_AUTHORED_BOOK_DRAFT",
            "source_ids": [entry["source_id"]],
            "chapter_count": len(book["ucie_authored_chapters"]),
            "machine_contract": "FIRST_PARTY_RECIPE_EXISTS_NOT_RELEASED",
            "independent_qa_verified": False,
            "source_content_verified_in_this_request": False,
            "human_approved": False, "export_allowed": False,
        })
    comparison.append({
        "item_id": chosen["draft_sha256"], "title": chosen["topic"],
        "asset_type": "EDITORIAL_CANDIDATE_NOT_REVIEWED",
        "source_ids": sorted(s["source_id"] for s in chosen["sources"]),
        "chapter_count": len(chosen["chapters"]),
        "machine_contract": "DESIGN_ONLY_NO_EXECUTABLE",
        "independent_qa_verified": False,
        "source_content_verified_in_this_request": False,
        "human_approved": False, "export_allowed": False,
    })
    return {
        "schema": REVIEW_SCHEMA, "status": REVIEW_STATUS,
        "candidate": chosen,
        "summary": _review_summary(chosen, editorial_observations),
        "source_observation_statuses": _review_observation_status(
            chosen, editorial_observations),
        "observation_receipts_cryptographically_authenticated": False,
        "browser_performs_official_network_fetch": False,
        "comparison": comparison, "review_receipt": handoff["receipt"],
        "human_markdown_sha256": handoff["receipt"]["human_markdown_sha256"],
        "machine_json_sha256": handoff["receipt"]["machine_json_sha256"],
        "source_document_bytes_fetched": 0,
        "source_content_independently_verified": False,
        "manual_editorial_review_completed": False,
        "machine_contract_executed": False,
        "approved_items": 0, "export_allowed": False,
        "network_requests": 0, "operating_database_writes": 0,
        "other_project_access": False,
    }


def render_review_candidate(report: dict) -> str:
    if (type(report) is not dict or report.get("schema") != REVIEW_SCHEMA
            or report.get("status") != REVIEW_STATUS
            or report.get("export_allowed") is not False
            or report.get("manual_editorial_review_completed") is not False
            or report.get("machine_contract_executed") is not False
            or type(report.get("candidate")) is not dict
            or report["candidate"].get("human_approved") is not False):
        raise FederationError("unsafe editorial detail display")
    e = lambda x: escape(str(x), quote=True)
    draft = report["candidate"]
    lines = [
        '<p><a href="/catalog">통합 도서관으로 돌아가기</a></p>',
        '<section class="panel"><h2>SkillBook 검토 후보 · 미승인</h2>',
        '<p>이 문서는 편집자 제출 원리 초안입니다. 공식 원문 SHA·기술 사실·권리·독립 QA를 '
        '이 화면에서 검증하거나 승인하지 않습니다.</p>',
        '<p>주제: <strong>' + e(draft["topic"]) + '</strong></p>',
        '<p>초안 SHA-256: <code>' + e(draft["draft_sha256"]) + '</code></p>',
        '<h3>기존 실행형 기술서적과 후보 비교</h3>',
        '<table><thead><tr><th>기술 자산</th><th>출처</th><th>챕터</th>'
        '<th>기계 계약 상태</th><th>검토/반출</th></tr></thead><tbody>',
    ]
    for item in report["comparison"]:
        lines.append(
            "<tr><td>" + e(item["title"]) + "</td><td>"
            + e(", ".join(item["source_ids"])) + "</td><td>"
            + str(item["chapter_count"]) + "</td><td>"
            + e(item["machine_contract"]) +
            "</td><td>미승인 · 반출 불가</td></tr>"
        )
    lines.extend(["</tbody></table>", "<h3>편집 후보의 출처</h3><ul>"])
    for src in draft["sources"]:
        lines.append(
            '<li>' + e(src["source_id"]) + ' · '
            + e(src["version_scope_claim"]) + ' · '
            + e(src["public_url"]) + '<p>제출 근거 SHA: '
            + e(src["evidence_sha256"]) + ' · 원문 재확인 미실시</p></li>'
        )
    lines.extend(["</ul>", "<h3>공식 문서 바이트 관측 상태 (미서명)</h3>",
                  "<p>조회 전 수동으로 받은 영수증만 비교합니다. "
                  "바이트 일치도 문서 버전·기술 정확성·권리 승인이 아닙니다.</p>",
                  "<ul>"])
    observation_labels = {
        "NO_MANUAL_RAW_BYTE_OBSERVATION": "공식 원문 바이트 관측 미실시",
        "NOT_AN_OFFICIAL_DOCUMENT_ROUTE": "공식 HTML 문서 관측 대상 아님",
        "OBSERVED_BODY_SHA_MATCH_REVISION_UNVERIFIED":
            "제출 SHA와 관측 SHA 일치 · 버전/권리·외부 검증 미완",
        "OBSERVED_BODY_SHA_MISMATCH_BLOCKED":
            "제출 SHA와 관측 SHA 불일치 · 차단",
    }
    for proof in report["source_observation_statuses"]:
        state = proof["status"]
        if state not in observation_labels:
            raise FederationError("unknown source byte status")
        lines.append(
            "<li>" + e(proof["source_id"]) + " · "
            + e(observation_labels[state])
            + (" · 관측 SHA: " + e(proof["observed_raw_sha256"])
               if proof["observed_raw_sha256"] is not None else "")
            + " · 영수증 미서명 · 재배포 불가</li>"
        )
    lines.extend(["</ul>", "<h3>사람이 검토할 5개 기술 챕터</h3>"])
    for chapter in draft["chapters"]:
        lines.append(
            '<section><h4>' + e(chapter["heading"]) + '</h4>'
            + '<p style="white-space:pre-wrap">' + e(chapter["text"])
            + '</p><small>편집자 주장 · 미검증 · 근거: '
            + e(", ".join(chapter["source_ids"])) + '</small></section>'
        )
    lines.extend([
        "<h3>실행 불가 기계 설계 계약</h3><p>"
        + e(draft["machine_contract"]["interface_name"]) +
        " · DESIGN_ONLY_NO_EXECUTABLE</p>",
        "<h3>필수 사람 검토 게이트</h3><ol>",
    ])
    lines.extend("<li>" + e(g["gate"]) + " · PENDING</li>"
                 for g in draft["manual_review_checklist"])
    lines.extend([
        "</ol>", "<p>문서 SHA: <code>" + e(report["human_markdown_sha256"])
        + "</code></p>",
        "<p>JSON SHA: <code>" + e(report["machine_json_sha256"])
        + "</code></p>",
        '<p><a href="/catalog/review.json?id=' + e(draft["draft_sha256"])
        + '">기계 검토 JSON</a></p>',
        "<p>실행 · 다운로드 · 서명 · 승인: 불가</p></section>",
    ])
    page = previous._template("UCIE 편집 SkillBook 검토·비교", "".join(lines))
    return page.replace("UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02", REVIEW_SCHEMA)


def search_federated(root: Path, *, filters: dict, public_reader=None,
                     editorial_records=None,
                     editorial_observations=None) -> dict:
    """Default SkillBook queries never read SQLite; public shelf is opt-in."""
    f = _safe_filters(filters)
    q, shelf, kind, domain, limit = (
        f["query"], f["shelf"], f["kind"], f["domain"], f["limit"])
    books = []
    if (shelf in ("skillbooks", "all") and kind in ("", "REUSABLE_SKILL")
            and domain in ("", "Python", "Git")):
        found = search_skillbooks(query=q, kind="REUSABLE_SKILL", language="Python")
        if (found.get("status") != "READ_ONLY_FIRST_PARTY_DRAFT_CATALOG"
                or found.get("approved_reusable_packages") != 0
                or found.get("network_requests") != 0
                or found.get("operating_database_writes") != 0):
            raise FederationError("untrusted SkillBook")
        books = [
            row for row in found["items"]
            if not domain or row["domain"].casefold() == domain.casefold()
        ]
        if (len(books) > 2 or any(
                row.get("human_approved") is not False
                or row.get("export_allowed") is not False for row in books)):
            raise FederationError("untrusted SkillBook approval")
    pending = []
    if shelf in ("skillbooks", "all") and kind in ("", "REUSABLE_SKILL"):
        for draft in _editorial_drafts(editorial_records):
            item = _review_summary(draft, editorial_observations)
            searchable = " ".join([
                item["topic"], *item["source_ids"],
                *[c["text"] for c in draft["chapters"]],
            ]).casefold()
            if ((not q or q.casefold() in searchable)
                    and (not domain or domain in item["domains"])):
                pending.append(item)
        pending = pending[:limit]
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
        "skillbooks": books, "editorial_review_candidates": pending,
        "editorial_candidates_unapproved": True,
        "public_evidence_candidates": candidates,
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
    parts += ['</section><section class="panel"><h2>편집 검토 대기 기술서적</h2>']
    for review in result["editorial_review_candidates"]:
        parts.append(
            '<p><a href="/catalog/review?id=' + e(review["draft_sha256"])
            + '">' + e(review["topic"]) + '</a> · '
            + e(", ".join(review["source_ids"])) +
            ' · 기술 본문/원문 독립 검증 미완 · 기계 실행 미구현 · 반출 불가</p>'
        )
        note = review.get("source_observation_statuses", [])
        if any(item.get("byte_sha_equal") is False for item in note):
            parts.append("<p>원문 바이트 SHA 불일치 후보 · 차단</p>")
        elif any(item.get("byte_sha_equal") is True for item in note):
            parts.append("<p>관측 SHA 일치 (미서명/버전 확인·검토 미완)</p>")
        else:
            parts.append("<p>수동 공식 문서 바이트 관측 미실시</p>")
    if not result["editorial_review_candidates"]:
        parts.append('<p>검색 조건에 맞는 편집 후보가 없습니다.</p>')
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
              '<a href="/skillbooks/release-gates">W09 출시 준비도</a> · '
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
        '<a href="/skillbooks">SkillBook 검색</a> · '
        '<a href="/skillbooks/release-gates">W09 출시 준비도</a></p>',
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


W09_KOREAN_BLOCKER_LABELS = {
    "EXACT_HEAD_COMPLETE_CI_4_OF_4_NOT_ATTESTED_BY_LOCAL_RECEIPT":
        "정확한 커밋 기준 CI 4개 환경 성공 확인",
    "INDEPENDENT_THIRD_PARTY_QA_NOT_ATTESTED":
        "독립 제3자 재현·기능 검증",
    "PLATFORM_SECURITY_REVIEW_NOT_ATTESTED":
        "보안·플랫폼 위험 검토",
    "LICENSE_DISTRIBUTION_RIGHTS_NOT_APPROVED":
        "라이선스 및 재배포 권리 검토",
    "OWNER_RELEASE_AUTHORIZATION_NOT_PROVIDED":
        "소유자 출시 승인",
    "SIGNED_PACKAGE_AND_EXTERNAL_PUBLICATION_NOT_AUTHORIZED":
        "패키지 서명 및 외부 공개 승인",
}


def render_skillbook_w09_release_gate(plan: dict) -> str:
    """Read-only readiness explainer, NOT a receipt-runner or signing UI."""
    if (type(plan) is not dict or plan.get("schema") != W09_SCHEMA
            or plan.get("status") != W09_PREVIEW_STATE
            or plan.get("skillbook_id") != SKILLBOOK_ID
            or plan.get("receipt_validation_performed") is not False
            or plan.get("package_created") is not False
            or plan.get("export_allowed") is not False
            or plan.get("owner_release_authorized") is not False
            or plan.get("independent_qa_verified") is not False
            or plan.get("security_review_approved") is not False
            or plan.get("license_redistribution_approved") is not False
            or plan.get("package_signed") is not False
            or plan.get("blocked_release_requirements") != list(W09_BLOCKERS)
            or set(W09_KOREAN_BLOCKER_LABELS) != set(W09_BLOCKERS)):
        raise FederationError("untrusted W09 release preview")
    esc = lambda value: escape(str(value), quote=True)
    items = [
        '<p><a href="/catalog">통합 도서관으로 돌아가기</a> · '
        '<a href="/skillbooks/qa-plan">W08 합성 검증 계획</a></p>',
        '<section class="panel"><h2>W09 출시 준비도 · 승인 전</h2>',
        '<p>이 화면은 실제 영수증이나 CI를 읽지 않고, 미충족 승인을 '
        '보여주는 정적 목록입니다. PASS 또는 배포 가능 선언이 아닙니다.</p>',
        '<p>대상: ' + esc(plan["skillbook_id"]) + '</p>',
        '<h3>해결되어야 할 관문 6개</h3><ol>',
    ]
    for item in W09_BLOCKERS:
        items.append('<li>' + esc(W09_KOREAN_BLOCKER_LABELS[item])
                     + ' · 미검증 / 승인 필요</li>')
    items.extend([
        '</ol><p>검증 영수증 상태: 이 브라우저에서는 미조회</p>',
        '<p>패키지 생성: 차단 · 서명: 없음 · 내보내기/배포: 불가</p>',
        '<p>UCIE 소유자 PowerShell에서 수동 사전검토:</p>',
        '<pre><code>&amp; &#39;'
        'D:\\UCIE\\scripts\\ucie_skillbook_w09_preflight_v01.ps1'
        '&#39; -RunSynthetic</code></pre>',
        '<p>위 명령은 별도로 실행하는 경우에만 작은 합성 파일을 만들고 '
        '삭제하며, QA 영수증의 일치 여부를 확인합니다. '
        '독립 QA 및 배포 승인은 제공하지 않습니다.</p>',
        '</section>',
    ])
    html = previous._template("SkillBook 001 · W09 출시 준비도", "".join(items))
    return html.replace("UCIE_LOCAL_PUBLIC_LIBRARY_BROWSER_V02", W09_SCHEMA)


def make_handler(root: Path, *, public_reader=None,
                 editorial_records=None,
                 editorial_observations=None, **legacy_injections):
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
                    '검증 계획 보기 (9개 합성 시험)</a> · '
                    '<a href="/skillbooks/release-gates">'
                    '출시 준비도 (미승인) 확인</a></nav>', 1)
            return super().reply(status, content, mime)

        def do_GET(self):
            path = urlsplit(self.path)
            if path.path in ("/skillbooks/release-gates",
                             "/skillbooks/release-gates.json"):
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
                if path.query or path.fragment or len(self.path) > 110:
                    return self.reply(400, "EXACT_W09_PLAN_ROUTE_ONLY",
                                      "text/plain; charset=utf-8")
                preview = preview_release_gate()
                if path.path.endswith(".json"):
                    return self.reply(
                        200, json.dumps(preview, ensure_ascii=True, sort_keys=True),
                        "application/json; charset=utf-8")
                return self.reply(200, render_skillbook_w09_release_gate(preview))
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
            if path.path in ("/catalog/review", "/catalog/review.json"):
                if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                    return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
                if path.fragment or len(self.path) > 185:
                    return self.reply(400, "INVALID_REVIEW_ROUTE", "text/plain; charset=utf-8")
                try:
                    args = parse_qs(path.query, strict_parsing=True,
                                    keep_blank_values=True, max_num_fields=1) if path.query else {}
                    if set(args) not in (set(), {"id"}) or any(
                            len(v) != 1 for v in args.values()):
                        raise FederationError("unexpected review selector")
                    ident = args.get("id", [None])[0]
                    data = inspect_review_candidate(
                        ident, editorial_records=editorial_records,
                        editorial_observations=editorial_observations)
                    if path.path.endswith(".json"):
                        return self.reply(
                            200, json.dumps(data, sort_keys=True, ensure_ascii=True),
                            "application/json; charset=utf-8")
                    return self.reply(200, render_review_candidate(data))
                except (FederationError, editorial.EditorialDraftError, ValueError):
                    return self.reply(400, "REVIEW_CANDIDATE_INPUT_NO_GO",
                                      "text/plain; charset=utf-8")
            if path.path not in ("/catalog", "/catalog.json"):
                return super().do_GET()
            if self.headers.get("Host") != "127.0.0.1:" + str(self.server.server_port):
                return self.reply(403, "LOOPBACK_ONLY", "text/plain; charset=utf-8")
            if len(self.path) > 340 or path.fragment:
                return self.reply(400, "INVALID_CATALOG_ROUTE", "text/plain; charset=utf-8")
            try:
                data = search_federated(root, filters=parse_filters(path.query),
                                        public_reader=public_reader,
                                        editorial_records=editorial_records,
                                        editorial_observations=editorial_observations)
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
