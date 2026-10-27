"""UCIE W05/W06 read-only Library shelves; no collector, DB, or network mutation.

W05: convert exactly validated, bounded positive public PR metadata into
searchable, source-anchored *hypotheses* (not working engines or skills).
W06: browse the existing Stage14 official metadata ledger only after checking
its original identity and schema. Neither shelf creates a knowledge database.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime
from pathlib import Path
import re
import sqlite3

from .positive_capability_discovery import classify_public_capability_metadata
from .public_discovery import DiscoveryError, SOURCES
from .public_official_evidence import (
    _path, _schema, _utc, RECORD_CAP, GHSA,
)
from .public_evidence_routes import DOC_ENDPOINTS
from .source_registry import get_source, SourceRegistryError

SCHEMA = "UCIE_W05_W06_READ_ONLY_LIBRARY_SHELVES_V1"
POSITIVE_KINDS = ("DEVELOPMENT_ENGINE", "REUSABLE_SKILL", "LEARNING_LOGIC")
OFFICIAL_KINDS = ("document", "release", "advisory")
MAX_LIMIT = 20
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
RELEASE_ID = re.compile(r"[1-9][0-9]{0,17}\Z")


class LibraryShelfError(ValueError):
    pass


def _limit(value: object) -> int:
    if type(value) is not int or not 1 <= value <= MAX_LIMIT:
        raise LibraryShelfError("invalid bounded Library shelf page size")
    return value


def search_positive_capability_shelf(rows: object, *,
                                     source_id: str,
                                     now: datetime | None = None,
                                     kind: str | None = None,
                                     limit: int = 10) -> dict:
    """Source-validated W05 title-cue hypotheses, not validated capabilities."""
    _limit(limit)
    if kind is not None and (type(kind) is not str or kind not in POSITIVE_KINDS):
        raise LibraryShelfError("unrecognized positive capability kind")
    verified = classify_public_capability_metadata(
        rows, source_id=source_id, now=now)
    if verified["status"] != "POSITIVE_CAPABILITY_HINTS_UNVERIFIED_NO_GO":
        raise LibraryShelfError("unexpected W05 candidate status")
    matches = [x for x in verified["candidates"]
               if kind is None or x["kind"] == kind]
    return {
        "schema": SCHEMA,
        "shelf": "POSITIVE_CAPABILITY_HYPOTHESES",
        "status": "PUBLIC_CAPABILITY_TITLE_CUES_UNVERIFIED_NO_GO",
        "source_id": source_id,
        "kind_filter": kind,
        "records_examined": verified["source_rows_examined"],
        "source_candidate_count": verified["candidate_count"],
        "total_matches": len(matches),
        "returned_count": min(limit, len(matches)),
        "omitted_count": max(0, len(matches) - limit),
        "items": [
            {
                "library_item_id": x["library_item_id"],
                "kind": x["kind"],
                "source_id": x["source_id"],
                "public_url": x["public_url"],
                "merge_commit_sha": x["merge_commit_sha"],
                "evidence_sha256": x["evidence_sha256"],
                "purpose_code": x["purpose_code"],
                "domain": x["domain"],
                "upstream_age_days": x["upstream_age_days"],
                "freshness_bucket": x["freshness_bucket"],
                "classification_basis": x["evidence_strength"],
                "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
                "actual_capability_verified": False,
                "benefit_measured": False,
                "human_approved": False,
                "export_allowed": False,
            }
            for x in matches[:limit]
        ],
        "search_index_persisted": False,
        "network_requests": 0,
        "database_writes": 0,
        "auto_promoted": False,
        "full_library_implemented": False,
    }


def search_official_metadata_shelf(root: Path, *,
                                   source_id: str | None = None,
                                   kind: str | None = None,
                                   limit: int = 10) -> dict:
    """Browse read-only Stage14 *hashes*, not original document/code content."""
    _limit(limit)
    if kind is not None and (type(kind) is not str or kind not in OFFICIAL_KINDS):
        raise LibraryShelfError("invalid official evidence kind")
    repo = None
    if source_id is not None:
        try:
            src = get_source(source_id)
        except (SourceRegistryError, TypeError) as exc:
            raise LibraryShelfError("official source not approved") from exc
        if src["source_kind"] not in ("INDEPENDENT_PUBLIC_REPOSITORY",
                                      "OFFICIAL_PUBLIC_DOCUMENT"):
            raise LibraryShelfError("unknown official evidence source type")
        repo = source_id.split(":", 1)[1]
        if repo not in SOURCES:
            raise LibraryShelfError("official source outside approved scope")
        if source_id.startswith("doc:") and kind not in (None, "document"):
            raise LibraryShelfError("document source cannot filter release/advisory")
    path = _path(Path(root))
    if not path.exists():
        return {
            "schema": SCHEMA, "shelf": "OFFICIAL_PUBLIC_METADATA",
            "status": "STAGE14_OFFICIAL_LEDGER_ABSENT_NO_GO",
            "items": [], "total_matches": 0, "returned_count": 0,
            "network_requests": 0, "database_writes": 0,
            "full_library_implemented": False, "auto_promoted": False,
        }
    try:
        with closing(sqlite3.connect(
                path.as_uri() + "?mode=ro", uri=True, timeout=3)) as conn:
            conn.execute("PRAGMA query_only=ON")
            _schema(conn, new=False)  # original Stage14 source/identity checks
            terms, params = [], []
            if repo is not None:
                terms.append("source=?")
                params.append(repo)
            if kind is not None:
                terms.append("evidence_kind=?")
                params.append(kind)
            if source_id is not None and source_id.startswith("doc:"):
                terms.append("evidence_kind='document'")
            where = (" WHERE " + " AND ".join(terms)) if terms else ""
            total = conn.execute(
                "SELECT COUNT(*) FROM official_revision" + where, params
            ).fetchone()[0]
            if type(total) is not int or not 0 <= total <= RECORD_CAP:
                raise LibraryShelfError("invalid bounded Stage14 row count")
            selected = conn.execute(
                "SELECT evidence_kind,source,upstream_reference,"
                "content_sha256,observed_or_published_utc,review_state "
                "FROM official_revision" + where +
                " ORDER BY source,evidence_kind,upstream_reference,"
                "content_sha256 LIMIT ?",
                [*params, limit],
            ).fetchall()
    except sqlite3.DatabaseError as exc:
        raise LibraryShelfError("read-only Stage14 official ledger unavailable") from exc
    items = []
    for evidence_kind, source, ref, digest, observed, status in selected:
        if (evidence_kind not in OFFICIAL_KINDS or source not in SOURCES
                or status != "PUBLIC_METADATA_UNVERIFIED"
                or type(digest) is not str or SHA64.fullmatch(digest) is None
                or type(ref) is not str or not 1 <= len(ref) <= 80):
            raise LibraryShelfError("invalid public official evidence row")
        _utc(observed)
        if evidence_kind == "document":
            if ref != "pinned-doc-url":
                raise LibraryShelfError("document reference mismatch")
            url = DOC_ENDPOINTS[source][0]
            reference_scope = "PINNED_OFFICIAL_DOCUMENT_CURRENT_URL"
        elif evidence_kind == "release":
            if RELEASE_ID.fullmatch(ref) is None:
                raise LibraryShelfError("release metadata ID malformed")
            # Original Stage14 stores only release ID/hash; tag and exact URL
            # cannot be attested or reconstructed from this fingerprint alone.
            url = "https://github.com/" + source + "/releases"
            reference_scope = "PUBLIC_REPOSITORY_RELEASE_INDEX_NOT_EXACT_RELEASE"
        else:
            if GHSA.fullmatch(ref) is None:
                raise LibraryShelfError("invalid published advisory ID")
            url = "https://github.com/advisories/" + ref
            reference_scope = "PUBLIC_ADVISORY_IDENTIFIER_UNVERIFIED"
        items.append({
            "kind": "OFFICIAL_" + evidence_kind.upper() + "_EVIDENCE",
            "source_id": ("doc:" if evidence_kind == "document" else "repo:") + source,
            "public_url": url,
            "reference_scope": reference_scope,
            "source_reference": ref,
            "content_sha256": digest,
            "observed_or_published_utc": observed,
            "lifecycle": "PUBLIC_METADATA_UNVERIFIED",
            "source_license_reviewed": False,
            "verified_applicability": False,
            "human_approved": False,
            "export_allowed": False,
        })
    return {
        "schema": SCHEMA,
        "shelf": "OFFICIAL_PUBLIC_METADATA",
        "status": "STAGE14_OFFICIAL_METADATA_READ_ONLY_UNVERIFIED_NO_GO",
        "source_filter": source_id, "kind_filter": kind,
        "total_matches": total, "returned_count": len(items),
        "omitted_count": total - len(items),
        "items": items,
        "search_index_persisted": False,
        "network_requests": 0, "database_writes": 0,
        "auto_promoted": False, "full_library_implemented": False,
    }
