"""Source-honest Local V1 official-reference shelf for an EMPTY clean checkout.

An installed first-party UCIE wheel already contains approved official-document
pointers, source-pinned draft SkillBooks and safe first-party demos. They can be
shown even when operating SQLite ledgers are NOT packaged in a clean recipient.

This is *not* a copy/restore of the owner's operating public_miner DB, not
evidence of published document bytes, not verified upstream fixes, and never
an exportable customer public-PR catalog. A populated, symlinked or suspicious
runtime directory MUST use original protected readers/fail closed, not this
separate reference-only path.
"""
from __future__ import annotations

from pathlib import Path

from .library_search import (
    SCHEMA as W04_SCHEMA, MAX_PAGE_OFFSET, _filters,
)
from .public_collection_inventory_v01 import (
    SCHEMA as INVENTORY_SCHEMA,
)

SCHEMA = "UCIE_CLEAN_FIRST_PARTY_OFFLINE_REFERENCE_MODE_V01"
STATUS = "OFFICIAL_DOCUMENT_REFERENCES_ONLY_NO_CAPTURED_PR_LEDGER_NO_GO"
NOTE = (
    "공식 문서 링크와 UCIE 작성 검토용 SkillBook만 제공됩니다. "
    "수집된 공개 PR 원장은 이 독립 설치본에 포함되지 않았습니다. "
    "문서 원문 바이트·적용 버전·재배포 권리·실제 수정 효과는 "
    "확인되지 않았으며, 자동 승격이나 고객 출시 승인도 없습니다."
)


class PortableReferenceError(ValueError):
    """Only a definitely empty UCIE source tree may use the safe reference mode."""


def reference_only(root: Path) -> bool:
    """True ONLY for an empty UCIE runtime; not invalid/tampered live ledgers.

    No file contents are read; no directory is created. An existing ANY
    runtime artifact, including an unexpected file, disables this fallback.
    """
    if (not isinstance(root, Path) or root.name.casefold() != "ucie"
            or root.is_symlink() or not root.is_dir()
            or (root / ".git").is_symlink() or not (root / ".git").is_dir()):
        raise PortableReferenceError("UCIE-only checked out source root required")
    runtime = root / "runtime"
    if runtime.is_symlink():
        raise PortableReferenceError("runtime symlink is not a clean UCIE ledger")
    if not runtime.exists():
        return True
    if not runtime.is_dir():
        raise PortableReferenceError("non-directory runtime must not be bypassed")
    return not any(runtime.iterdir())


def no_captured_public_candidates(*, query: str, limit: int,
                                  offset: int, source_id: str | None) -> dict:
    """A W04 INCOMPLETE response, never fabricated accepted candidates."""
    if type(offset) is not int or offset != 0 or offset > MAX_PAGE_OFFSET:
        raise PortableReferenceError("no candidate pages in reference-only mode")
    q, kind, domain, src, bounded_limit, grouped = _filters(
        query=query, kind=None, domain=None, source_id=source_id,
        limit=limit, group_revisions=False,
    )
    if kind is not None or domain is not None or grouped:
        raise PortableReferenceError("unexpected portable shelf query options")
    if src is not None:
        from .product_plan import APPROVED_REPOSITORIES
        if src.removeprefix("repo:") not in APPROVED_REPOSITORIES:
            raise PortableReferenceError("portable reference query outside approved sources")
    return {
        "schema": W04_SCHEMA,
        "status": "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
        "portable_reference_mode": STATUS,
        "query": q,
        "source_filter": src,
        "total_matches": 0,
        "returned_count": 0,
        "source_linked_count": 0,
        "items": [],
        "search_index_persisted": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "approved_or_exportable_items": 0,
        "auto_promoted": False,
        "v1_library_accepted": False,
    }


def no_captured_inventory() -> dict:
    """Unavailable is unknown (None), NEVER a fabricated 0-candidate report."""
    return {
        "schema": INVENTORY_SCHEMA,
        "status": STATUS,
        "captured_utc": "NOT_CAPTURED",
        "legacy_miner": {"candidates": None, "status": "NOT_INSTALLED_NO_GO"},
        "stage10_public_candidate_staging": {
            "candidate_revisions": None, "status": "NOT_INSTALLED_NO_GO",
        },
        "stage12_unverified_review": {
            "review_proposals": None, "status": "NOT_INSTALLED_NO_GO",
        },
        "issues": ["PUBLIC_PR_SOURCE_LEDGER_NOT_INSTALLED"],
        "network_requests": 0,
        "operating_database_writes": 0,
        "owner_approval": False,
        "customer_distribution_authorized": False,
    }
