"""W04: first real read-only Virtual Library candidate search, existing UCIE ledgers.

Uses the already validated Stage10/15 -> Stage12 handoff (which checks SQLite
source linkage and rejects forged review rows). No new persistent index, no
approval, no external project access, no network, no schema migration.
W04 is a PARTIAL search slice; W07 signed Rulepacks/other shelves come later.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from .library_entry import build_library_entry
from .skill_profiles import PROFILE
from .public_discovery import DiscoveryError
from .verification_handoff import prepare_verification_handoff
from .automated_candidate_qa import _checked_handoff

SCHEMA = "UCIE_W04_READ_ONLY_LIBRARY_CANDIDATE_SEARCH_V1"
MAX_QUERY = 80
MAX_LIMIT = 20
QUERY = re.compile(r"[A-Za-z0-9_.:/ -]{0,80}\Z")
SOURCE = re.compile(r"(?:repo:)?[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\Z")
ALLOWED_KINDS = frozenset(("PREVENTION_RULE", "REUSABLE_SKILL"))
ALLOWED_DOMAINS = frozenset(p["domain"] for p in PROFILE.values())


class LibrarySearchError(ValueError):
    pass


def _filters(*, query: str, kind: str | None, domain: str | None,
             source_id: str | None, limit: int,
             group_revisions: bool) -> tuple[str, str | None, str | None, str | None, int, bool]:
    if type(query) is not str or len(query) > MAX_QUERY or QUERY.fullmatch(query) is None:
        raise LibrarySearchError("invalid bounded searchable term")
    if kind is not None and (type(kind) is not str or kind not in ALLOWED_KINDS):
        raise LibrarySearchError("unknown candidate search kind")
    if source_id is not None and (
            type(source_id) is not str or len(source_id) > 128
            or SOURCE.fullmatch(source_id) is None):
        raise LibrarySearchError("invalid source search filter")
    if domain is not None and (type(domain) is not str
            or domain.casefold() not in {x.casefold() for x in ALLOWED_DOMAINS}):
        raise LibrarySearchError("unknown domain search filter")
    if type(group_revisions) is not bool:
        raise LibrarySearchError("invalid grouping switch")
    if type(limit) is not int or not 1 <= limit <= MAX_LIMIT:
        raise LibrarySearchError("result limit outside bounds")
    if source_id is not None and not source_id.startswith("repo:"):
        source_id = "repo:" + source_id
    normalized_domain = (next((x for x in ALLOWED_DOMAINS
                               if domain is not None and x.casefold() == domain.casefold()),
                              None))
    return query.casefold().strip(), kind, normalized_domain, source_id, limit, group_revisions


def search_linked_public_candidates(handoff: dict, *, query: str = "",
                                    kind: str | None = None,
                                    domain: str | None = None,
                                    source_id: str | None = None,
                                    limit: int = 20,
                                    group_revisions: bool = False) -> dict:
    """Search validated candidates; optionally group duplicate PR evidence."""
    q, kind, domain, source_id, limit, group_revisions = _filters(
        query=query, kind=kind, domain=domain,
        source_id=source_id, limit=limit, group_revisions=group_revisions)
    complete, tasks = _checked_handoff(handoff)
    if not complete:
        return {
            "schema": SCHEMA,
            "status": "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
            "query": q, "total_matches": 0, "returned_count": 0,
            "items": [], "search_index_persisted": False,
            "network_requests": 0, "operating_database_writes": 0,
            "approved_or_exportable_items": 0, "auto_promoted": False,
            "v1_library_accepted": False,
        }
    matched = []
    for task in tasks:
        if (type(task) is not dict or type(task.get("source")) is not str
                or type(task.get("reference")) is not str
                or type(task.get("pattern_code")) is not str
                or type(task.get("evidence_sha256")) is not str
                or type(task.get("skill_id")) is not str):
            raise LibrarySearchError("incomplete source-linked review task")
        shelf = ("PREVENTION_RULE" if task.get("stage6_candidate") is not None
                 else "REUSABLE_SKILL")
        record = build_library_entry({
            "kind": shelf,
            "source_id": "repo:" + task["source"],
            "evidence_reference": task["reference"],
            "evidence_sha256": task["evidence_sha256"],
            "purpose_code": task["pattern_code"],
            "version_scope": "UNDETERMINED",
            "dependencies": [],
        })
        if task["skill_id"] != record["skill_profile"]:
            raise LibrarySearchError("review skill disagrees with pinned public source")
        if kind is not None and shelf != kind:
            continue
        if source_id is not None and record["source_id"] != source_id:
            continue
        if domain is not None and record["domain"] != domain:
            continue
        searchable = " ".join((
            shelf, record["source_id"], record["domain"],
            record["skill_profile"], record["purpose_code"],
            task["reference"],
        )).casefold()
        if q and q not in searchable:
            continue
        matched.append({
            "library_item_id": record["library_item_id"],
            "review_candidate_sha256": task["candidate_id_sha256"],
            "kind": record["kind"],
            "source_id": record["source_id"],
            "public_url": record["public_url"],
            "domain": record["domain"],
            "purpose_code": record["purpose_code"],
            "skill_profile": record["skill_profile"],
            "revision_hint": record["revision_hint"],
            "evidence_sha256": record["evidence_sha256"],
            "version_scope_claim": record["version_scope_claim"],
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
            "signature_status": "NOT_ATTESTED_BY_THIS_SEARCH",
            "license_status": record["source_license_status"],
            "human_approved": False,
            "export_allowed": False,
        })
    matched.sort(key=lambda x: (x["source_id"], x["kind"],
                                x["purpose_code"], x["library_item_id"]))
    raw_matches = len(matched)
    if group_revisions:
        groups = {}
        for item in matched:
            key = (item["source_id"], item["public_url"], item["revision_hint"],
                   item["kind"], item["purpose_code"])
            if key not in groups:
                row = dict(item)
                row["evidence_revision_sha256s"] = []
                row["review_candidate_sha256s"] = []
                groups[key] = row
            group = groups[key]
            group["evidence_revision_sha256s"].append(item["evidence_sha256"])
            group["review_candidate_sha256s"].append(item["review_candidate_sha256"])
        matched = []
        for item in groups.values():
            item["evidence_revision_sha256s"].sort()
            item["review_candidate_sha256s"].sort()
            item["evidence_revision_count"] = len(item["review_candidate_sha256s"])
            matched.append(item)
        matched.sort(key=lambda x: (x["source_id"], x["kind"],
                                    x["purpose_code"], x["library_item_id"]))
    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO",
        "query": q,
        "source_filter": source_id,
        "kind_filter": kind,
        "domain_filter": domain,
        "group_revisions": group_revisions,
        "raw_evidence_revision_matches": raw_matches,
        "source_linked_count": len(tasks),
        "total_matches": len(matched),
        "returned_count": min(limit, len(matched)),
        "omitted_count": max(0, len(matched) - limit),
        "items": matched[:limit],
        "shelves_available": ["PREVENTION_RULE", "REUSABLE_SKILL"],
        "available_domains": sorted(ALLOWED_DOMAINS),
        "full_library_implemented": False,
        "search_index_persisted": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "approved_or_exportable_items": 0,
        "auto_promoted": False,
        "v1_library_accepted": False,
    }


def search_existing_public_library(root: Path, *, query: str = "",
                                   kind: str | None = None,
                                   domain: str | None = None,
                                   source_id: str | None = None,
                                   limit: int = 20,
                                   group_revisions: bool = False) -> dict:
    """Use existing Stage10/12/15 UCIE SQLite readers in query-only mode."""
    _filters(query=query, kind=kind, domain=domain,
             source_id=source_id, limit=limit, group_revisions=group_revisions)
    root = Path(root)
    if root.name.casefold() != "ucie" or root.is_symlink() or not root.is_dir():
        raise LibrarySearchError("dedicated UCIE checkout required")
    handoff = prepare_verification_handoff(root)
    return search_linked_public_candidates(
        handoff, query=query, kind=kind, domain=domain,
        source_id=source_id, limit=limit, group_revisions=group_revisions)


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE read-only candidate Library search")
    parser.add_argument("--query", default="")
    parser.add_argument("--kind", choices=sorted(ALLOWED_KINDS))
    parser.add_argument("--domain", choices=sorted(ALLOWED_DOMAINS))
    parser.add_argument("--group-revisions", action="store_true")
    parser.add_argument("--source-id")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        result = search_existing_public_library(
            root, query=args.query, kind=args.kind, domain=args.domain,
            source_id=args.source_id, limit=args.limit,
            group_revisions=args.group_revisions)
    except (ValueError, DiscoveryError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "FAIL_CLOSED",
                          "error_type": type(exc).__name__,
                          "network_requests": 0,
                          "operating_database_writes": 0,
                          "v1_library_accepted": False}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
