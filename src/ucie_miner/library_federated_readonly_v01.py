"""UCIE W03/W04/W05: bounded, read-only multi-shelf Virtual Library search.

Reuses the existing W01 Registry, W02 LibraryEntry, W03 adapter route
preview, W04 source-linked Stage10/12/15 SQLite search, official doc and
first-party test-recipe shelves, and optional offline W05 title-cue review.

No HTTP, model, external code execution, operating database migration,
activation, customer export, source expansion or automatic promotion.
Missing/stale W04 linkage remains explicitly PARTIAL, never an empty
verified library. Positive snapshots are untrusted caller-supplied
metadata and NEVER become verified improvements or licenses.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re

from .library_approved_document_shelf_v01 import (
    search_approved_document_references,
)
from .library_python_recipe_shelf_v01 import search_python_reference_recipe
from .library_search import (
    SCHEMA as W04_SCHEMA, search_existing_public_library,
)
from .positive_capability_discovery import (
    classify_public_capability_metadata,
)
from .product_plan import APPROVED_REPOSITORIES
from .public_source_adapter import SCHEMA as W03_SCHEMA, adapter_plan
from .source_registry import get_source, SourceRegistryError

SCHEMA = "UCIE_W03_W04_W05_FEDERATED_LIBRARY_READONLY_V01"
MAX_PAGE = 20
MAX_OFFSET = 10000
QUERY = re.compile(r"[\w .:/-]{0,80}\Z", re.UNICODE)
# Legacy Stage10-12 W04 cannot represent Unicode queries; report partial
# coverage instead of querying every PR and claiming a Korean match.
W04_QUERY = re.compile(r"[A-Za-z0-9_.:/ -]{0,80}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
CATALOG_STATUS = "FEDERATED_UNVERIFIED_CANDIDATE_SEARCH_NO_GO"
PARTIAL_STATUS = "FEDERATED_PARTIAL_SOURCE_LINKAGE_OR_QUERY_NO_GO"
OFFLINE_W05 = "CALLER_SUPPLIED_OFFLINE_PUBLIC_METADATA_UNVERIFIED"


class FederatedLibraryError(ValueError):
    """Unsafe query, source, provenance or first-party shelf drift."""


def _source(source_id: str) -> str:
    if type(source_id) is not str or len(source_id) > 128:
        raise FederatedLibraryError("invalid bounded source selector")
    if source_id == "":
        return ""
    try:
        source = get_source(source_id)
    except (SourceRegistryError, TypeError) as exc:
        raise FederatedLibraryError("unapproved registry source") from exc
    if (source.get("source_id") != source_id
            or source.get("status") != "ACTIVE_APPROVED"
            or source.get("source_kind") != "INDEPENDENT_PUBLIC_REPOSITORY"
            or source.get("fetch_authorized_by_this_registry") is not False):
        raise FederatedLibraryError("select one approved public repository only")
    return source_id.removeprefix("repo:")


def _normalize(item: dict, shelf: str, *, basis: str) -> dict:
    if (type(item) is not dict
            or type(item.get("library_item_id")) is not str
            or SHA64.fullmatch(item["library_item_id"]) is None
            or type(item.get("kind")) is not str
            or type(item.get("source_id")) is not str
            or type(item.get("public_url")) is not str
            or item.get("human_approved") is not False
            or item.get("export_allowed") is not False
            or item.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"):
        raise FederatedLibraryError("unverified shelf cannot grant approval")
    source = get_source(item["source_id"])
    if (source.get("status") != "ACTIVE_APPROVED"
            or source["source_id"] != item["source_id"]):
        raise FederatedLibraryError("source registry mismatch")
    return {
        "library_item_id": item["library_item_id"],
        "kind": item["kind"], "source_id": item["source_id"],
        "public_url": item["public_url"],
        "purpose_code": item.get("purpose_code"),
        "domain": item.get("domain"),
        "origin_shelf": shelf,
        "evidence_level": basis,
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "license_verified": False,
        "version_verified": False,
        "capability_effect_verified": False,
        "human_approved": False,
        "export_allowed": False,
    }


def _approved_plans(repo: str) -> list[dict]:
    rows = []
    for name in APPROVED_REPOSITORIES:
        if repo and name != repo:
            continue
        plan = adapter_plan("repo:" + name)
        if (plan.get("schema") != W03_SCHEMA
                or plan.get("source_id") != "repo:" + name
                or plan.get("fetch_budget_for_this_page") != 1
                or plan.get("transport_invoked") is not False
                or plan.get("registry_grants_network_permission") is not False
                or plan.get("persistent_writes") != 0):
            raise FederatedLibraryError("W03 existing route plan drift")
        rows.append({
            "source_id": plan["source_id"],
            "existing_route_planned_only": True,
            "network_authorized_by_catalog": False,
        })
    if len(rows) != (1 if repo else 5):
        raise FederatedLibraryError("W03 source count changed")
    return rows


def _metadata_head(*, query: str, repo: str,
                   positive_snapshot: dict | None,
                   now: datetime | None) -> tuple[list[dict], dict]:
    items: list[dict] = []
    official = search_approved_document_references(query, source=repo)
    if (official.get("network_requests") != 0
            or official.get("operating_database_writes") != 0
            or official.get("human_approved") is not False
            or official.get("export_allowed") is not False
            or official.get("auto_promoted") is not False
            or official.get("returned_count") != len(official.get("items", []))):
        raise FederatedLibraryError("official document reference shelf drift")
    for item in official["items"]:
        if item.get("reference_digest_scope") != (
                "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES"):
            raise FederatedLibraryError("reference is not document bytes")
        items.append(_normalize(
            item, "APPROVED_OFFICIAL_DOCUMENT_POINTER",
            basis="OFFICIAL_URL_REFERENCE_ONLY_DOCUMENT_REVISION_UNVERIFIED"))
    recipe_count = 0
    if not repo or repo == "python/cpython":
        recipe = search_python_reference_recipe(query)
        if (recipe.get("network_requests") != 0
                or recipe.get("operating_database_writes") != 0
                or recipe.get("human_approved") is not False
                or recipe.get("export_allowed") is not False
                or recipe.get("auto_promoted") is not False
                or recipe.get("returned_count") != len(recipe.get("items", []))):
            raise FederatedLibraryError("first-party recipe shelf drift")
        for item in recipe["items"]:
            if item.get("reference_digest_scope") != (
                    "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES"):
                raise FederatedLibraryError("recipe reference not document bytes")
            items.append(_normalize(
                item, "FIRST_PARTY_TEST_RECIPE_REFERENCE",
                basis="OFFICIAL_DOCUMENT_POINTER_AND_UCIE_SYNTHETIC_RECIPE_ONLY"))
            recipe_count += 1

    positive_count = 0
    if positive_snapshot is not None:
        if (type(positive_snapshot) is not dict
                or set(positive_snapshot) != {"source_id", "rows"}
                or type(positive_snapshot["source_id"]) is not str
                or type(positive_snapshot["rows"]) is not list
                or len(positive_snapshot["rows"]) > 20):
            raise FederatedLibraryError("only bounded offline W05 metadata allowed")
        source_id = positive_snapshot["source_id"]
        # Both W01 and W03 must accept the exact same route before a
        # caller-supplied metadata snapshot can even be classified.
        source_repo = _source(source_id)
        adapter_plan(source_id)
        if repo and source_repo != repo:
            raise FederatedLibraryError("offline positive source disagrees with filter")
        classified = classify_public_capability_metadata(
            positive_snapshot["rows"], source_id=source_id, now=now)
        if (classified.get("status") != "POSITIVE_CAPABILITY_HINTS_UNVERIFIED_NO_GO"
                or classified.get("network_requests") != 0
                or classified.get("database_writes") != 0
                or classified.get("auto_promoted") is not False
                or classified.get("model_weights_changed") is not False
                or classified.get("candidate_count") != len(
                    classified.get("candidates", []))):
            raise FederatedLibraryError("W05 positive classifier contract drift")
        term = query.casefold().strip()
        for item in classified["candidates"]:
            if (item.get("evidence_strength") != "MERGED_PR_TITLE_CUE_ONLY"
                    or item.get("actual_capability_verified") is not False
                    or item.get("benefit_measured") is not False
                    or item.get("license_independently_reviewed") is not False
                    or item.get("export_allowed") is not False):
                raise FederatedLibraryError("W05 positive cue incorrectly approved")
            # Match only safe categorical identifiers, never raw PR title.
            searchable = " ".join((item["kind"], item["source_id"],
                                   item["purpose_code"], item["domain"]))
            if term and term not in searchable.casefold():
                continue
            view = {
                "library_item_id": item["library_item_id"],
                "kind": item["kind"], "source_id": item["source_id"],
                "public_url": item["public_url"],
                "purpose_code": item["purpose_code"],
                "domain": item["domain"],
                "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
                "human_approved": False, "export_allowed": False,
            }
            items.append(_normalize(
                view, "W05_OFFLINE_POSITIVE_TITLE_CUE",
                basis="CALLER_SUPPLIED_MERGED_PR_TITLE_HEURISTIC_UNVERIFIED"))
            positive_count += 1

    # Ordering is deterministic between disjoint shelves. W04 result
    # arrives afterward as its own verified source-linked sorted page.
    items.sort(key=lambda x: (
        {"APPROVED_OFFICIAL_DOCUMENT_POINTER": 0,
         "FIRST_PARTY_TEST_RECIPE_REFERENCE": 1,
         "W05_OFFLINE_POSITIVE_TITLE_CUE": 2}[x["origin_shelf"]],
        x["source_id"], x["kind"], x["library_item_id"]))
    identities = [x["library_item_id"] for x in items]
    if len(identities) != len(set(identities)):
        raise FederatedLibraryError("duplicate item identity across head shelves")
    return items, {
        "official_document_pointer_count": official["total_matches"],
        "first_party_recipe_reference_count": recipe_count,
        "offline_positive_title_cue_count": positive_count,
    }


def search_federated_library(
        root: Path, *, query: str = "", source_id: str = "",
        limit: int = 10, offset: int = 0,
        positive_snapshot: dict | None = None,
        now: datetime | None = None,
        include_legacy: bool = True) -> dict:
    """Search approved first-party shelves, one read-only W04 ledger window.

    This function never invokes any transport callback; W05 caller metadata
    is explicitly OFFLINE/UNVERIFIED. Do not pass arbitrary project roots.
    """
    if (type(query) is not str or QUERY.fullmatch(query) is None
            or type(limit) is not int or not 1 <= limit <= MAX_PAGE
            or type(offset) is not int or not 0 <= offset <= MAX_OFFSET
            or type(include_legacy) is not bool
            or not isinstance(root, Path) or root.is_symlink()
            or root.name.casefold() != "ucie" or not root.is_dir()):
        raise FederatedLibraryError("bounded dedicated UCIE read-only query required")
    repo = _source(source_id)
    plans = _approved_plans(repo)
    head, counts = _metadata_head(
        query=query, repo=repo,
        positive_snapshot=positive_snapshot, now=now)
    public_count = None
    public_items = []
    linked_state = "W04_NOT_REQUESTED"
    public_coverage = True
    if include_legacy:
        if W04_QUERY.fullmatch(query) is None:
            linked_state = "W04_QUERY_UNSUPPORTED_UNICODE_NO_LEDGER_SEARCH"
            public_coverage = False
        else:
            public_offset = max(0, offset-len(head))
            # The existing W04 function validates live source linkage
            # before returning any candidate; no direct SQLite access here.
            r = search_existing_public_library(
                root, query=query, source_id=("repo:"+repo if repo else None),
                limit=limit, offset=public_offset,
                group_revisions=True)
            linked_state = r.get("status")
            if (r.get("schema") != W04_SCHEMA
                    or r.get("network_requests") != 0
                    or r.get("operating_database_writes") != 0
                    or r.get("approved_or_exportable_items") != 0
                    or r.get("auto_promoted") is not False
                    or r.get("returned_count") != len(r.get("items", []))):
                raise FederatedLibraryError("W04 linked-evidence reader drift")
            if linked_state == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
                public_coverage = False
                if r["items"] or r["returned_count"] != 0:
                    raise FederatedLibraryError("unlinked W04 data must not display")
            elif linked_state == "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO":
                public_count = r["total_matches"]
                for item in r["items"]:
                    public_items.append(_normalize(
                        item, "SOURCE_LINKED_PUBLIC_PR_REVIEW",
                        basis="EXISTING_STAGE10_12_15_LINKED_UNVERIFIED_EVIDENCE"))
            else:
                raise FederatedLibraryError("unknown W04 evidence gate status")
    prefix_count = len(head)
    result_items = head[offset:offset+limit]
    needed = limit-len(result_items)
    if needed > 0 and public_coverage and include_legacy and public_count is not None:
        result_items.extend(public_items[:needed])
    all_ids = [x["library_item_id"] for x in result_items]
    if len(all_ids) != len(set(all_ids)):
        raise FederatedLibraryError("duplicate first-party library item on page")
    total = (prefix_count + public_count if public_count is not None
             else prefix_count)
    return {
        "schema": SCHEMA,
        "status": CATALOG_STATUS if public_coverage else PARTIAL_STATUS,
        "query": query.casefold().strip(), "source_filter": source_id or None,
        "limit": limit, "offset": offset,
        "returned_count": len(result_items),
        "total_matches_known": public_coverage,
        "total_matches": total if public_coverage else None,
        "known_shelf_matches": prefix_count,
        "legacy_w04_matches": public_count,
        "legacy_w04_status": linked_state,
        "legacy_w04_queried": include_legacy and W04_QUERY.fullmatch(query) is not None,
        "catalog_scope": ("REQUESTED_REFERENCE_SHELVES_ONLY"
                          if not include_legacy else "REFERENCE_SHELVES_PLUS_W04_LEDGER"),
        "all_product_types_indexed": False,
        "shelf_counts": counts,
        "items": result_items,
        "w03_existing_approved_adapter_plans": plans,
        "w03_network_requests": 0, "w05_public_snapshot_provenance":
            OFFLINE_W05 if positive_snapshot is not None
            else "NOT_LOADED_NO_POSITIVE_CANDIDATE_COMPLETENESS_CLAIM",
        "network_requests": 0, "operating_database_writes": 0,
        "source_allowlist_changed": False, "model_weights_changed": False,
        "positive_classification_performed_on_real_network": False,
        "full_library_implemented": False,
        "approved_or_exportable_items": 0,
        "auto_promoted": False, "v1_library_accepted": False,
        "customer_release_authorized": False,
    }


def compare_visible_items(catalog: dict, left_id: str, right_id: str) -> dict:
    """Compare provenance and missing validation only; never rank by benefit."""
    if (type(catalog) is not dict
            or catalog.get("schema") != SCHEMA
            or catalog.get("network_requests") != 0
            or catalog.get("operating_database_writes") != 0
            or catalog.get("auto_promoted") is not False
            or type(catalog.get("items")) is not list
            or type(left_id) is not str or SHA64.fullmatch(left_id) is None
            or type(right_id) is not str or SHA64.fullmatch(right_id) is None
            or left_id == right_id):
        raise FederatedLibraryError("exact distinct visible unverified items required")
    found = []
    for identity in (left_id, right_id):
        selected = [item for item in catalog["items"]
                    if item.get("library_item_id") == identity]
        if (len(selected) != 1
                or selected[0].get("human_approved") is not False
                or selected[0].get("export_allowed") is not False
                or selected[0].get("capability_effect_verified") is not False):
            raise FederatedLibraryError("item not visible or falsely approved")
        found.append({
            "library_item_id": identity,
            "kind": selected[0]["kind"],
            "source_id": selected[0]["source_id"],
            "origin_shelf": selected[0]["origin_shelf"],
            "evidence_level": selected[0]["evidence_level"],
            "license_verified": False,
            "version_verified": False,
            "capability_effect_verified": False,
            "export_allowed": False,
        })
    return {
        "schema": SCHEMA,
        "status": "EVIDENCE_PROVENANCE_COMPARISON_ONLY_NOT_QUALITY_RANKING",
        "items": found, "comparison_is_performance_evaluation": False,
        "source_types_are_not_interchangeable": True,
        "network_requests": 0, "operating_database_writes": 0,
        "auto_promoted": False, "export_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="UCIE first-party read-only federated library")
    parser.add_argument("--query", default="")
    parser.add_argument("--source-id", default="")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--no-legacy", action="store_true",
                        help="Official pointers + first-party recipe only")
    parser.add_argument("--compare-left",
                        help="64-hex ID from the current visible result page")
    parser.add_argument("--compare-right",
                        help="different 64-hex ID from the same result page")
    args = parser.parse_args()
    try:
        result = search_federated_library(
            Path(__file__).resolve().parents[2], query=args.query,
            source_id=args.source_id, limit=args.limit, offset=args.offset,
            include_legacy=not args.no_legacy)
        if args.compare_left is not None or args.compare_right is not None:
            if args.compare_left is None or args.compare_right is None:
                raise FederatedLibraryError("two visible comparison identities required")
            result["comparison"] = compare_visible_items(
                result, args.compare_left, args.compare_right)
    except (ValueError, OSError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "FAIL_CLOSED",
            "error_type": type(exc).__name__, "network_requests": 0,
            "operating_database_writes": 0, "v1_library_accepted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
