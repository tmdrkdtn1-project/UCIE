"""W04 exact-match batch search with a P8 evidence-informed cost policy.

Opt-in only. Default W04 substring search is unchanged. The original
Stage10-12/15 linked handoff and W02 source provenance are reused. A bounded
linear exact scan is selected for one/few queries when building an index
cannot reduce the simple modeled operation count. Otherwise an ephemeral
composite hash index is built once for the batch.

Operation estimates are NOT timing guarantees; input normalization, sorting,
memory and source validation are additional costs common to both options.
No persistent index, runtime collector changes, or new source permissions.
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
    # Normalize all untrusted input through original W02 provenance first.
    # Keeping this pass common to both algorithms avoids trusting a fast path.
    records: list[tuple[tuple[str, str, str, str], dict]] = []
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
        records.append((key, {
            "library_item_id": entry["library_item_id"],
            "public_url": entry["public_url"],
            "evidence_sha256": entry["evidence_sha256"],
            "revision_hint": entry["revision_hint"],
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
            "human_approved": False,
            "export_allowed": False,
        }))

    linear_cost = len(records) * len(keys)
    index_cost = len(records) + len(keys)
    use_index = index_cost < linear_cost  # tie goes to simpler linear search
    choice = "BUILD_ONCE_COMPOSITE_INDEX" if use_index else "LINEAR_EXACT_SCAN"
    index: dict[tuple[str, str, str, str], list[dict]] | None = None
    if use_index:
        index = {}
        for key, item in records:
            index.setdefault(key, []).append(item)
        for items in index.values():
            items.sort(key=lambda row: row["library_item_id"])

    returned = []
    for key in keys:
        if index is not None:
            found = index.get(key, ())
        else:
            found = sorted(
                (item for row_key, item in records if row_key == key),
                key=lambda row: row["library_item_id"])
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
        "unique_index_keys": len(index) if index is not None else None,
        "index_built": index is not None,
        "selected_strategy": choice,
        "strategy_reason": ("LOWER_ESTIMATED_COMPARISONS_INCLUDING_INDEX_BUILD"
                            if use_index else "INDEX_BUILD_NOT_ESTIMATED_BENEFICIAL"),
        "index_build_plus_lookup_operations": index_cost,
        "linear_scan_comparisons_for_same_queries": linear_cost,
        "executed_strategy_estimated_operations": index_cost if use_index else linear_cost,
        "alternative_strategy_estimated_operations": linear_cost if use_index else index_cost,
        "cost_metric": "SIMPLE_KEY_COMPARE_OR_BUILD_PLUS_LOOKUP_ESTIMATE_NOT_ELAPSED_TIME",
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
