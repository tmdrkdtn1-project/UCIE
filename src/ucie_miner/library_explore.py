"""UCIE V0.2: bounded read-only exploration of ALL source-linked W04 candidates.

No source code execution, external fetch, persistent index, approval, export,
cross-project access, or new scheduler. Original Stage10/12/15 source-ledger
verification remains mandatory before any candidate is displayed.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import re

from .automated_candidate_qa import _checked_handoff
from .library_entry import build_library_entry
from .library_search import _filters, LibrarySearchError
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_W04_PUBLIC_LIBRARY_EXPLORE_V02"
READY = "READ_ONLY_UNVERIFIED_LIBRARY_EXPLORE_NO_GO"
INCOMPLETE = "SOURCE_LINKAGE_INCOMPLETE_NO_GO"
MAX_PAGE = 100
SHA = re.compile(r"[0-9a-f]{64}\Z")

# These are UCIE-authored explanations of classification codes, NOT claims
# about a particular upstream PR or a verified vulnerability/fix.
PURPOSE_LABELS = {
    "UNCLASSIFIED": ("분류되지 않은 공개 변경", "변경 성격을 추가 검토해야 합니다."),
    "API_CONTRACT": ("API 계약 변경 후보", "호출 인수, 반환값과 호환성을 검토하는 분류입니다."),
    "CONCURRENCY": ("동시성 검토 후보", "실행 순서와 자원 공유 조건을 검토하는 분류입니다."),
    "REGRESSION": ("회귀 위험 검토 후보", "기존 기능의 재시험 필요성을 검토하는 분류입니다."),
    "SECURITY": ("보안 영향 검토 후보", "보안 관련 변경 여부를 독립적으로 확인해야 합니다."),
    "ERROR_HANDLING": ("오류 처리 검토 후보", "예외와 실패 처리 동작을 검토하는 분류입니다."),
    "TEST_CHANGE": ("시험 변경 후보", "시험 추가 또는 변경의 목적을 검토하는 분류입니다."),
}
UNKNOWN_LABEL = ("공개 기술 변경 후보", "원본 변경 내용과 적용 범위를 별도로 검토해야 합니다.")


class ExploreError(ValueError):
    pass


def describe_purpose(purpose: str) -> tuple[str, str]:
    return PURPOSE_LABELS.get(purpose, UNKNOWN_LABEL)


def _candidate_rows(handoff: object) -> tuple[bool, list[dict]]:
    complete, tasks = _checked_handoff(handoff)
    if not complete:
        return False, []
    records = []
    for task in tasks:
        if (type(task) is not dict
                or any(type(task.get(k)) is not str for k in (
                    "source", "reference", "pattern_code", "evidence_sha256",
                    "skill_id", "candidate_id_sha256"))):
            raise ExploreError("incomplete public review metadata")
        kind = ("PREVENTION_RULE" if task.get("stage6_candidate") is not None
                else "PUBLIC_TECHNICAL_EVIDENCE")
        entry = build_library_entry({
            "kind": kind,
            "source_id": "repo:" + task["source"],
            "evidence_reference": task["reference"],
            "evidence_sha256": task["evidence_sha256"],
            "purpose_code": task["pattern_code"],
            "version_scope": "UNDETERMINED", "dependencies": [],
        })
        if entry["skill_profile"] != task["skill_id"]:
            raise ExploreError("review source skill identity mismatch")
        records.append({
            "library_item_id": entry["library_item_id"],
            "source_id": entry["source_id"],
            "domain": entry["domain"],
            "kind": kind,
            "purpose_code": entry["purpose_code"],
            "public_url": entry["public_url"],
            "revision_hint": entry["revision_hint"],
            "evidence_sha256": entry["evidence_sha256"],
            "review_candidate_sha256": task["candidate_id_sha256"],
            "version_scope_claim": entry["version_scope_claim"],
            "license_status": entry["source_license_status"],
            "human_approved": False,
            "export_allowed": False,
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        })
    records.sort(key=lambda r: (r["source_id"], r["public_url"], r["kind"],
                                r["purpose_code"], r["library_item_id"]))
    groups = {}
    for row in records:
        key = (row["source_id"], row["public_url"], row["revision_hint"],
               row["kind"], row["purpose_code"])
        if key not in groups:
            base = dict(row)
            base["evidence_revision_sha256s"] = []
            base["review_candidate_sha256s"] = []
            groups[key] = base
        groups[key]["evidence_revision_sha256s"].append(row["evidence_sha256"])
        groups[key]["review_candidate_sha256s"].append(row["review_candidate_sha256"])
    grouped = list(groups.values())
    for row in grouped:
        row["evidence_revision_sha256s"].sort()
        row["review_candidate_sha256s"].sort()
        row["evidence_revision_count"] = len(row["review_candidate_sha256s"])
    return True, grouped


def _score(row: dict, terms: tuple[str, ...]) -> int:
    if not terms:
        return 0
    purpose = row["purpose_code"].casefold()
    domain = row["domain"].casefold()
    source = row["source_id"].casefold()
    kind = row["kind"].casefold()
    url = row["public_url"].casefold()
    fields = (purpose, domain, source, kind, url)
    if not all(any(term in field for field in fields) for term in terms):
        return -1
    score = 0
    for term in terms:
        if term == purpose:
            score += 100
        elif purpose.startswith(term):
            score += 75
        elif term in purpose:
            score += 55
        elif term == domain:
            score += 45
        elif term in domain:
            score += 34
        elif term in source:
            score += 24
        elif term in kind:
            score += 18
        elif term in url:
            score += 8
    return score


def _balanced(rows: list[dict]) -> list[dict]:
    """No query: round-robin public sources rather than showing one source first."""
    buckets = defaultdict(list)
    for row in sorted(rows, key=lambda r: (
            r["source_id"], r["purpose_code"], r["public_url"],
            r["library_item_id"])):
        buckets[row["source_id"]].append(row)
    sources = sorted(buckets)
    result = []
    index = 0
    while len(result) < len(rows):
        for source in sources:
            if index < len(buckets[source]):
                result.append(buckets[source][index])
        index += 1
    return result


def explore_linked_public_candidates(
        handoff: object, *, query: str = "", kind: str | None = None,
        domain: str | None = None, source_id: str | None = None,
        limit: int = 10, page: int = 1, item_id: str | None = None) -> dict:
    """Page and inspect complete, immutable-source-linked candidate metadata."""
    q, kind, domain, source, limit, _ = _filters(
        query=query, kind=kind, domain=domain, source_id=source_id,
        limit=limit, group_revisions=True)
    if type(page) is not int or not 1 <= page <= MAX_PAGE:
        raise ExploreError("page outside bounded range")
    if item_id is not None and (
            type(item_id) is not str or SHA.fullmatch(item_id) is None):
        raise ExploreError("invalid candidate detail identity")
    complete, all_rows = _candidate_rows(handoff)
    base = {
        "schema": SCHEMA, "query": q, "page": page, "limit": limit,
        "source_filter": source, "domain_filter": domain, "kind_filter": kind,
        "items": [], "total_matches": 0, "returned_count": 0,
        "total_pages": 0, "source_facets": {}, "domain_facets": {}, "kind_facets": {},
        "detail": None, "source_linked_count": len(all_rows),
        "network_requests": 0, "operating_database_writes": 0,
        "approved_or_exportable_items": 0, "auto_promoted": False,
        "v1_library_accepted": False, "search_index_persisted": False,
        "ranking_method": "BOUNDED_METADATA_LEXICAL_V1_NOT_SEMANTIC",
    }
    if not complete:
        return dict(base, status=INCOMPLETE)
    if item_id is not None:
        found = [r for r in all_rows if r["library_item_id"] == item_id]
        if len(found) != 1:
            return dict(base, status="DETAIL_NOT_FOUND_NO_GO")
        return dict(base, status=READY, detail=found[0])
    terms = tuple(q.split())  # _filters rejects unbounded/unsafe terms
    scored = [(_score(row, terms), row) for row in all_rows]
    hits = [row for rank, row in scored if rank >= 0]
    # Each facet ignores only its own selection, while honoring the
    # other two filters and the query. Counts are GROUPED candidates.
    sources = Counter(row["source_id"] for row in hits
                      if (domain is None or row["domain"] == domain)
                      and (kind is None or row["kind"] == kind))
    domains = Counter(row["domain"] for row in hits
                      if (source is None or row["source_id"] == source)
                      and (kind is None or row["kind"] == kind))
    kinds = Counter(row["kind"] for row in hits
                    if (source is None or row["source_id"] == source)
                    and (domain is None or row["domain"] == domain))
    filtered = [row for row in hits
                if (source is None or row["source_id"] == source)
                and (domain is None or row["domain"] == domain)
                and (kind is None or row["kind"] == kind)]
    if terms:
        filtered.sort(key=lambda row: (
            -_score(row, terms), row["source_id"], row["purpose_code"],
            row["public_url"], row["library_item_id"]))
    else:
        filtered = _balanced(filtered)
    total = len(filtered)
    offset = (page - 1) * limit
    return dict(
        base, status=READY, total_matches=total,
        returned_count=len(filtered[offset:offset + limit]),
        total_pages=(total + limit - 1) // limit,
        items=filtered[offset:offset + limit],
        source_facets=dict(sorted(sources.items())),
        domain_facets=dict(sorted(domains.items())),
        kind_facets=dict(sorted(kinds.items())),
    )


def explore_existing_public_library(root: Path, **kwargs) -> dict:
    root = Path(root)
    if root.name.casefold() != "ucie" or root.is_symlink() or not root.is_dir():
        raise ExploreError("dedicated UCIE checkout required")
    # Reuse existing Stage10/12/15 source fingerprint/revision checks exactly.
    return explore_linked_public_candidates(
        prepare_verification_handoff(root), **kwargs)
