"""UCIE W04/W06: first-party read-only Virtual Library + official evidence.

Keeps W03/W04/W05 candidate search and W06 Stage14 metadata on separate
named evidence planes. Neither a document URL nor a hash is a source
revision/license/behavior certification. Never GET, execute, sign or deploy.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from .library_federated_readonly_v01 import (
    SCHEMA as BASE_SCHEMA, search_federated_library,
)
from .library_shelves import (
    SCHEMA as W06_SCHEMA, OFFICIAL_KINDS,
    search_official_metadata_shelf,
)
from .source_registry import get_source

SCHEMA = "UCIE_W04_W06_FEDERATED_EVIDENCE_PLANES_READONLY_V02"
OFFICIAL_LEVEL = "STAGE14_METADATA_HASH_ONLY_NOT_CONTENT_OR_VERSION_CERTIFICATION"
ID = re.compile(r"[a-f0-9]{64}\Z")
MAX_LIMIT = 20
MAX_OFFSET = 20000
W06_PRESENT = "STAGE14_OFFICIAL_METADATA_READ_ONLY_UNVERIFIED_NO_GO"
W06_ABSENT = "STAGE14_OFFICIAL_LEDGER_ABSENT_NO_GO"


class FederatedOfficialError(ValueError):
    """Unapproved source, unsafe search or W06 ledger contract drift."""


def _official_identity(item: dict) -> str:
    # This is an inventory key for metadata, NOT a verified document hash
    # or an owner-signed portable LibraryEntry.
    fields = (item["kind"], item["source_id"], item["public_url"],
              item["source_reference"], item["content_sha256"],
              item["observed_or_published_utc"])
    if any(type(f) is not str or not f or len(f) > 220 for f in fields):
        raise FederatedOfficialError("unsafe Stage14 inventory identity")
    return sha256(("\x1f".join(fields)).encode("utf-8")).hexdigest()


def _view(item: dict) -> dict:
    if (type(item) is not dict
            or item.get("kind") not in (
                "OFFICIAL_DOCUMENT_EVIDENCE",
                "OFFICIAL_RELEASE_EVIDENCE",
                "OFFICIAL_ADVISORY_EVIDENCE")
            or type(item.get("source_id")) is not str
            or type(item.get("content_sha256")) is not str
            or ID.fullmatch(item["content_sha256"]) is None
            or type(item.get("public_url")) is not str
            or type(item.get("reference_scope")) is not str
            or item.get("lifecycle") != "PUBLIC_METADATA_UNVERIFIED"
            or item.get("source_license_reviewed") is not False
            or item.get("verified_applicability") is not False
            or item.get("human_approved") is not False
            or item.get("export_allowed") is not False):
        raise FederatedOfficialError("Stage14 metadata cannot be approved")
    src = get_source(item["source_id"])
    if (src.get("status") != "ACTIVE_APPROVED"
            or src.get("source_id") != item["source_id"]
            or src.get("fetch_authorized_by_this_registry") is not False):
        raise FederatedOfficialError("W01 source registry changed")
    # No title, untrusted description, patch or raw external document body.
    return {
        "metadata_inventory_id": _official_identity(item),
        "kind": item["kind"],
        "source_id": item["source_id"],
        "public_url": item["public_url"],
        "source_reference": item["source_reference"],
        "metadata_fingerprint_sha256": item["content_sha256"],
        "observed_or_published_utc": item["observed_or_published_utc"],
        "reference_scope": item["reference_scope"],
        "evidence_level": OFFICIAL_LEVEL,
        "lifecycle": "PUBLIC_METADATA_UNVERIFIED",
        "content_bytes_independently_verified": False,
        "source_revision_validated": False,
        "license_verified": False,
        "version_verified": False,
        "effect_measured": False,
        "human_approved": False,
        "export_allowed": False,
    }


def search_with_official_evidence(
        root: Path, *, query: str = "", source_id: str = "",
        official_kind: str | None = None,
        limit: int = 10, offset: int = 0,
        official_offset: int = 0,
        include_w04: bool = True) -> dict:
    """One caller-controlled read-only request, two typed evidence windows.

    Both windows have independent offsets/counts; totals MUST NOT be added
    as if all hits were distinct validated technologies.
    """
    if (type(limit) is not int or not 1 <= limit <= MAX_LIMIT
            or type(offset) is not int or not 0 <= offset <= 10000
            or type(official_offset) is not int
            or not 0 <= official_offset <= MAX_OFFSET
            or type(include_w04) is not bool
            or official_kind is not None and (
                type(official_kind) is not str
                or official_kind not in OFFICIAL_KINDS)):
        raise FederatedOfficialError("unsafe bounded W04/W06 search")
    # The base itself validates the exact UCIE root and source registry.
    catalog = search_federated_library(
        root, query=query, source_id=source_id, limit=limit,
        offset=offset, include_legacy=include_w04)
    if (catalog.get("schema") != BASE_SCHEMA
            or catalog.get("network_requests") != 0
            or catalog.get("operating_database_writes") != 0
            or catalog.get("approved_or_exportable_items") != 0
            or catalog.get("auto_promoted") is not False
            or catalog.get("v1_library_accepted") is not False
            or catalog.get("customer_release_authorized") is not False):
        raise FederatedOfficialError("W04 candidate catalog trust drift")
    official = search_official_metadata_shelf(
        root, source_id=source_id or None, kind=official_kind,
        limit=limit, offset=official_offset)
    if (official.get("schema") != W06_SCHEMA
            or official.get("status") not in (W06_PRESENT, W06_ABSENT)
            or official.get("shelf") != "OFFICIAL_PUBLIC_METADATA"
            or official.get("network_requests") != 0
            or official.get("database_writes") != 0
            or official.get("auto_promoted") is not False
            or official.get("full_library_implemented") is not False
            or type(official.get("items")) is not list
            or official.get("returned_count") != len(official["items"])
            or official.get("returned_count") > limit
            or type(official.get("total_matches")) is not int
            or official["total_matches"] < official["returned_count"]):
        raise FederatedOfficialError("Stage14 source contract changed")
    if official["status"] == W06_ABSENT and (
            official["items"] or official["total_matches"] != 0):
        raise FederatedOfficialError("absent W06 ledger cannot contain evidence")
    rows = [_view(row) for row in official["items"]]
    unique = [r["metadata_inventory_id"] for r in rows]
    if len(unique) != len(set(unique)):
        raise FederatedOfficialError("duplicate Stage14 inventory identity")
    return {
        "schema": SCHEMA,
        "status": ("FEDERATED_TWO_EVIDENCE_PLANES_UNVERIFIED_NO_GO"
                   if (catalog["total_matches_known"]
                       and official["status"] == W06_PRESENT)
                   else "FEDERATED_PARTIAL_EVIDENCE_PLANES_NO_GO"),
        "query": query.casefold().strip(),
        "source_filter": source_id or None,
        "official_kind_filter": official_kind,
        "candidate_window": catalog,
        "official_window": {
            "schema": W06_SCHEMA, "status": official["status"],
            "offset": official_offset, "limit": limit,
            "returned_count": len(rows),
            "total_matches_known": official["status"] == W06_PRESENT,
            "total_matches": (official["total_matches"]
                              if official["status"] == W06_PRESENT else None),
            "items": rows,
            "inventory_keys_are_not_document_content_hashes": True,
            "source_metadata_is_not_a_verified_vulnerability_fix": True,
        },
        "cross_plane_result_totals_combined": False,
        "cross_plane_duplicate_or_revision_equivalence_certified": False,
        "network_requests": 0, "operating_database_writes": 0,
        "project_code_executed": False, "source_allowlist_changed": False,
        "model_weights_changed": False,
        "approved_or_exportable_items": 0,
        "auto_promoted": False, "v1_library_accepted": False,
        "customer_release_authorized": False,
    }


def compare_catalog_to_official(
        result: dict, *, candidate_id: str, official_id: str) -> dict:
    """Compare evidence-type provenance only, never declare a working fix."""
    if (type(result) is not dict or result.get("schema") != SCHEMA
            or result.get("network_requests") != 0
            or result.get("operating_database_writes") != 0
            or result.get("auto_promoted") is not False
            or type(candidate_id) is not str or ID.fullmatch(candidate_id) is None
            or type(official_id) is not str or ID.fullmatch(official_id) is None):
        raise FederatedOfficialError("invalid two-plane comparison")
    candidates = [
        row for row in result["candidate_window"]["items"]
        if row.get("library_item_id") == candidate_id
    ]
    official = [
        row for row in result["official_window"]["items"]
        if row.get("metadata_inventory_id") == official_id
    ]
    if (len(candidates) != 1 or len(official) != 1
            or candidates[0].get("human_approved") is not False
            or candidates[0].get("export_allowed") is not False
            or candidates[0].get("capability_effect_verified") is not False
            or official[0].get("human_approved") is not False
            or official[0].get("export_allowed") is not False
            or official[0].get("content_bytes_independently_verified") is not False):
        raise FederatedOfficialError("unverified comparison item missing")
    return {
        "schema": SCHEMA,
        "status": "CROSS_PLANE_EVIDENCE_PROVENANCE_ONLY_NO_GO",
        "candidate": {
            "library_item_id": candidate_id,
            "kind": candidates[0]["kind"],
            "source_id": candidates[0]["source_id"],
            "evidence_level": candidates[0]["evidence_level"],
        },
        "official": {
            "metadata_inventory_id": official_id,
            "kind": official[0]["kind"],
            "source_id": official[0]["source_id"],
            "evidence_level": OFFICIAL_LEVEL,
        },
        "same_underlying_fix_or_causal_link_verified": False,
        "performance_benefit_measured": False,
        "source_license_verified": False,
        "network_requests": 0, "auto_promoted": False,
        "export_allowed": False,
    }


def _plain_text(result: dict) -> str:
    """A bounded, human-readable CLI search screen with truthfully split counts."""
    first = result["candidate_window"]
    second = result["official_window"]
    lines = [
        "UCIE Virtual Library / REVIEW ONLY / NO RELEASE",
        f"Query: {result['query'] or '(all)'}",
        ("W03/W04/W05 candidates: " +
         (str(first["total_matches"]) if first["total_matches_known"]
          else "INCOMPLETE") +
         f" | page {first['returned_count']} | {first['status']}"),
    ]
    for item in first["items"]:
        lines.append(
            "  CANDIDATE " + item["library_item_id"][:12] +
            " | " + item["kind"] + " | " + item["source_id"] +
            " | UNVERIFIED / NOT EXPORTABLE")
    lines.append(
        ("W06 official metadata: " +
         (str(second["total_matches"]) if second["total_matches_known"]
          else "LEDGER ABSENT") +
         f" | page {second['returned_count']} | {second['status']}"))
    for item in second["items"]:
        lines.append(
            "  OFFICIAL " + item["metadata_inventory_id"][:12] +
            " | " + item["kind"] + " | " + item["source_id"] +
            " | HASH METADATA ONLY / NOT VERIFIED")
    lines.append("GET=0 | DB-WRITES=0 | AUTO-PROMOTION=OFF")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="UCIE W04/W06 read-only evidence search")
    p.add_argument("--query", default="")
    p.add_argument("--source-id", default="")
    p.add_argument("--official-kind", choices=sorted(OFFICIAL_KINDS))
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--official-offset", type=int, default=0)
    p.add_argument("--no-w04", action="store_true")
    p.add_argument("--format", choices=("text", "json"), default="text")
    args = p.parse_args()
    try:
        out = search_with_official_evidence(
            Path(__file__).resolve().parents[2],
            query=args.query, source_id=args.source_id,
            official_kind=args.official_kind, limit=args.limit,
            offset=args.offset, official_offset=args.official_offset,
            include_w04=not args.no_w04)
    except (ValueError, OSError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "network_requests": 0, "operating_database_writes": 0,
            "customer_release_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(out, ensure_ascii=True, sort_keys=True)
          if args.format == "json" else _plain_text(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
