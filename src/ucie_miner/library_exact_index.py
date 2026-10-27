"""W04 exact-match batch search using the P8-tested in-memory composite index.

Opt-in only. Default W04 substring search is unchanged. The existing Stage10-
12/15 source-linked verification handoff, W02 LibraryEntry provenance and the
approved five-public-repo allowlist are reused. An index is constructed only
for this call, never persisted or installed in the hourly collector.
"""
from __future__ import annotations

from pathlib import Path

from .automated_candidate_qa import _checked_handoff
from .library_entry import build_library_entry, TOKEN
from .library_search import ALLOWED_DOMAINS, ALLOWED_KINDS
from .source_registry import get_source, SourceRegistryError
from .verification_handoff import prepare_verification_handoff

SCHEMA = "UCIE_W04_EXACT_PUBLIC_LIBRARY_BATCH_INDEX_V1"
MAX_CATALOG_ROWS = 1000
MAX_BATCH = 32
MAX_RESULTS_PER_QUERY = 20


class ExactLibraryError(ValueError):
    pass


def _validate_query(value: object) -> tuple[str, str, str, str]:
    if type(value) is not tuple or len(value) != 4:
        raise ExactLibraryError("exact query must be a four-field tuple")
    source_id, domain, kind, purpose = value
    if (type(source_id) is not str or not source_id.startswith("repo:")
            or len(source_id) > 128):
        raise ExactLibraryError("exact approved repository source ID required")
    try:
        src = get_source(source_id)
    except SourceRegistryError as exc:
        raise ExactLibraryError("unapproved source in exact query") from exc
    if src["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
        raise ExactLibraryError("only approved public repository metadata may be queried")
    if (type(domain) is not str or domain not in ALLOWED_DOMAINS
            or type(kind) is not str or kind not in ALLOWED_KINDS
            or type(purpose) is not str or TOKEN.fullmatch(purpose) is None):
        raise ExactLibraryError("unknown domain, candidate kind or purpose")
    return source_id, domain, kind, purpose


def exact_search_linked_public_candidates(handoff: dict, *,
                                          queries: tuple[tuple[str, str, str, str], ...],
                                          limit: int = 10) -> dict:
    """One read-only index for multiple exact queries, including zero matches."""
    if (type(queries) is not tuple or not 1 <= len(queries) <= MAX_BATCH
            or type(limit) is not int or not 1 <= limit <= MAX_RESULTS_PER_QUERY):
        raise ExactLibraryError("unbounded exact Library batch")
    keys = tuple(_validate_query(query) for query in queries)
    complete, tasks = _checked_handoff(handoff)
    if not complete:
        return {
            "schema": SCHEMA,
            "status": "INCOMPLETE_SOURCE_LINKED_CATALOG_NO_GO",
            "query_count": len(keys), "catalog_items": 0,
            "items": [], "network_requests": 0,
            "operating_database_writes": 0,
            "approved_or_exportable_items": 0,
            "index_persisted": False, "auto_promoted": False,
            "v1_accepted": False,
        }
    if len(tasks) > MAX_CATALOG_ROWS:
        raise ExactLibraryError("unbounded source-linked catalog")
    index: dict[tuple[str, str, str, str], list[dict]] = {}
    for task in tasks:
        if (type(task) is not dict or type(task.get("source")) is not str
                or type(task.get("reference")) is not str
                or type(task.get("pattern_code")) is not str
                or type(task.get("evidence_sha256")) is not str):
            raise ExactLibraryError("incomplete public review metadata")
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
        if task.get("skill_id") != entry["skill_profile"]:
            raise ExactLibraryError("provenance/skill classifier disagree")
        key = (entry["source_id"], entry["domain"],
               entry["kind"], entry["purpose_code"])
        index.setdefault(key, []).append({
            "library_item_id": entry["library_item_id"],
            "public_url": entry["public_url"],
            "evidence_sha256": entry["evidence_sha256"],
            "revision_hint": entry["revision_hint"],
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
            "human_approved": False,
            "export_allowed": False,
        })
    for items in index.values():
        items.sort(key=lambda row: row["library_item_id"])
    returned = []
    for key in keys:
        found = index.get(key, ())
        returned.append({
            "query": {
                "source_id": key[0], "domain": key[1],
                "kind": key[2], "purpose_code": key[3],
            },
            "total_matches": len(found),
            "returned_count": min(len(found), limit),
            "omitted_count": max(0, len(found) - limit),
            "items": list(found[:limit]),
        })
    return {
        "schema": SCHEMA,
        "status": "READ_ONLY_EXACT_PUBLIC_LIBRARY_INDEX_UNVERIFIED_NO_GO",
        "query_mode": "EXACT_SOURCE_DOMAIN_KIND_PURPOSE_ONLY",
        "query_count": len(keys),
        "catalog_items": len(tasks),
        "unique_index_keys": len(index),
        "index_build_plus_lookup_operations": len(tasks) + len(keys),
        "linear_scan_comparisons_for_same_queries": len(tasks) * len(keys),
        "items": returned,
        "substring_search_modified": False,
        "index_persisted": False,
        "production_index_replaced": False,
        "full_library_implemented": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "approved_or_exportable_items": 0,
        "auto_promoted": False,
        "v1_accepted": False,
    }


def search_exact_existing_public_library(root: Path, *,
                                         queries: tuple[tuple[str, str, str, str], ...],
                                         limit: int = 10) -> dict:
    """Read only the existing dedicated UCIE Stage10-12/15 evidence linkage."""
    if (not isinstance(root, Path) or root.is_symlink()
            or root.name.casefold() != "ucie" or not root.is_dir()):
        raise ExactLibraryError("dedicated UCIE root required")
    # Validate all exact caller-supplied keys before touching a real ledger.
    if type(queries) is not tuple or not 1 <= len(queries) <= MAX_BATCH:
        raise ExactLibraryError("invalid bounded query list")
    for query in queries:
        _validate_query(query)
    handoff = prepare_verification_handoff(root)
    return exact_search_linked_public_candidates(
        handoff, queries=queries, limit=limit)
