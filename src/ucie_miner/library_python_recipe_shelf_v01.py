"""UCIE W03/W04 bounded cross-shelf search: one official-doc TEST_RECIPE.

This is an in-memory, review-only shelf, not a new crawler, persistent index,
verified CPython fix, or releaseable SkillBook. The existing W04 ledger is
queried separately with its original Stage10/12/15 source-linkage gates.
An official documentation URL and a merged public PR are DIFFERENT sources
of evidence and are never combined into a fictitious approved finding.
"""
from __future__ import annotations

import re

from .library_search import SCHEMA as W04_SCHEMA
from .python_scandir_review_v01 import _source_bound_entry, SOURCE_ID
from .source_registry import get_source

SCHEMA = "UCIE_W03_W04_PYTHON_REFERENCE_RECIPE_SHELF_V01"
QUERY = re.compile(r"[\w .-]{0,80}\Z", re.UNICODE)
SHA64 = re.compile(r"[a-f0-9]{64}\Z")
RELEVANT_PR = "PY_SCANDIR_SHARED_ITERATOR_RACE"
PUBLIC_URL = re.compile(
    r"https://github\.com/python/cpython/pull/[1-9][0-9]{0,8}\Z"
)
TOKENS = (
    "python", "cpython", "os.scandir", "scandir", "iterator",
    "thread", "concurrency", "lock", "반복자", "파일", "동시", "스레드", "안전",
)
SHELF_STATUS = "SOURCE_BOUND_TEST_RECIPE_UNVERIFIED_REVIEW_ONLY"
NOT_FOUND = "NO_FIRST_PARTY_RECIPE_MATCH"
COMPARISON_STATUS = "DIFFERENT_EVIDENCE_TYPES_REVIEW_ONLY"


class PythonRecipeShelfError(ValueError):
    """Any unrecognized source/search/W04 comparison must fail closed."""


def _matches(query: str) -> bool:
    if type(query) is not str or QUERY.fullmatch(query) is None:
        raise PythonRecipeShelfError("UCIE bounded review-only query required")
    needle = query.casefold().strip()
    if not needle:
        return True
    if len(needle) < 2:
        return False
    # Fixed UCIE-owned query vocabulary; no arbitrary text indexing.
    return any(needle in token or token in needle for token in TOKENS)


def search_python_reference_recipe(query: str) -> dict:
    """Search a reviewed first-party TEST_RECIPE without executing it."""
    matched = _matches(query)
    result = {
        "schema": SCHEMA,
        "status": NOT_FOUND,
        "query": query.casefold().strip(),
        "total_matches": 0,
        "returned_count": 0,
        "items": [],
        "shelf": "FIRST_PARTY_OFFICIAL_DOC_TEST_RECIPES",
        "source_revision_verified": False,
        "external_code_executed": False,
        "synthetic_trial_executed_during_search": False,
        "human_approved": False,
        "export_allowed": False,
        "auto_promoted": False,
        "search_index_persisted": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "customer_release_authorized": False,
    }
    if not matched:
        return result
    source, entry = _source_bound_entry()
    if (source.get("source_id") != SOURCE_ID
            or source.get("status") != "ACTIVE_APPROVED"
            or entry.get("schema") != "UCIE_W02_PUBLIC_LIBRARY_ENTRY_V1"
            or entry.get("source_id") != SOURCE_ID
            or entry.get("kind") != "TEST_RECIPE"
            or entry.get("purpose_code") != "SCANDIR_SERIALIZED_ITERATION"
            or entry.get("entry_status") != "UNVERIFIED_CANDIDATE_ONLY"
            or entry.get("approval_status") != "NOT_APPROVED"
            or entry.get("source_license_status") != "NOT_ATTESTED_PER_REVISION"
            or entry.get("revision_hint") != "PUBLIC_DOCUMENT_REVISION_NOT_PINNED"
            or entry.get("version_scope_claim") != "UNDETERMINED"
            or entry.get("human_approved") is not False
            or entry.get("export_allowed") is not False
            or entry.get("auto_promoted") is not False):
        raise PythonRecipeShelfError("unapproved W01/W02 source contract drift")
    identity = entry.get("library_item_id")
    if type(identity) is not str or SHA64.fullmatch(identity) is None:
        raise PythonRecipeShelfError("untrusted recipe identity")
    item = {
        "library_item_id": identity,
        "title": "Python os.scandir 반복자 안전 사용 · UCIE 합성시험",
        "kind": "TEST_RECIPE",
        "source_id": SOURCE_ID,
        "source_kind": "OFFICIAL_PUBLIC_DOCUMENT",
        "public_url": entry["public_url"],
        "domain": entry["domain"],
        "purpose_code": entry["purpose_code"],
        "revision_hint": entry["revision_hint"],
        "version_scope_claim": entry["version_scope_claim"],
        "source_license_status": entry["source_license_status"],
        # A self-created hash of the URL is NOT a hash of document bytes.
        "reference_sha256": entry["evidence_sha256"],
        "reference_digest_scope": "UCIE_REFERENCE_STRING_ONLY_NOT_DOCUMENT_BYTES",
        "trial_status": "AVAILABLE_USER_INITIATED_SYNTHETIC_ONLY",
        "engine_route": "/local/engine?purpose=PYTHON_SCANDIR_SAFE",
        "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
        "human_approved": False,
        "export_allowed": False,
    }
    return dict(result, status=SHELF_STATUS, total_matches=1,
                returned_count=1, items=[item])


def compare_with_w04_window(recipe: dict, public: dict | None) -> dict:
    """Compare explicit evidence provenance, never validity/ranking/approval.

    W04 candidate rows are already validated by Local V1 _search; this
    function independently checks essential W04 trust and source boundaries.
    An incomplete W04 ledger must NEVER be reported as an empty valid index.
    """
    if (type(recipe) is not dict or recipe.get("schema") != SCHEMA
            or recipe.get("status") not in (SHELF_STATUS, NOT_FOUND)
            or recipe.get("network_requests") != 0
            or recipe.get("operating_database_writes") != 0
            or recipe.get("human_approved") is not False
            or recipe.get("export_allowed") is not False
            or recipe.get("auto_promoted") is not False
            or type(recipe.get("items")) is not list
            or len(recipe["items"]) != recipe.get("returned_count")
            or len(recipe["items"]) > 1):
        raise PythonRecipeShelfError("forged in-memory recipe shelf")
    base = {
        "schema": SCHEMA,
        "status": "W04_NOT_REQUESTED_OR_NO_RECIPE",
        "comparison_scope": "OFFICIAL_DOC_REFERENCE_VS_PINNED_PUBLIC_PR",
        "source_id": SOURCE_ID,
        "official_doc_count": recipe["returned_count"],
        "relevant_public_pr_count_in_page": 0,
        "relevant_public_prs": [],
        "different_evidence_types": True,
        "comparison_is_upstream_fix_validation": False,
        "reference_version_certified": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "auto_promoted": False,
    }
    if public is None or not recipe["items"]:
        return base
    if (type(public) is not dict or public.get("schema") != W04_SCHEMA
            or public.get("network_requests") != 0
            or public.get("operating_database_writes") != 0
            or public.get("approved_or_exportable_items") != 0
            or public.get("auto_promoted") is not False
            or type(public.get("items")) is not list
            or type(public.get("returned_count")) is not int
            or type(public.get("total_matches")) is not int
            or public["total_matches"] < public["returned_count"]
            or len(public["items"]) != public["returned_count"]
            or len(public["items"]) > 10):
        raise PythonRecipeShelfError("untrusted or unbounded W04 comparison")
    if public.get("status") == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        if public["items"] or public["returned_count"] != 0:
            raise PythonRecipeShelfError("incomplete W04 evidence must not display")
        return dict(base, status="W04_SOURCE_LINKAGE_INCOMPLETE_NO_COMPARISON")
    if public.get("status") != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO":
        raise PythonRecipeShelfError("unsupported W04 source state")
    get_source("repo:python/cpython")
    relevant = []
    for row in public["items"]:
        if (type(row) is not dict
                or row.get("lifecycle") != "UNVERIFIED_CANDIDATE_ONLY"
                or row.get("human_approved") is not False
                or row.get("export_allowed") is not False):
            raise PythonRecipeShelfError("W04 approval or shape drift")
        if (row.get("source_id") != "repo:python/cpython"
                or row.get("purpose_code") != RELEVANT_PR):
            continue
        # Unclassified W04 preview rows remain in the original public shelf;
        # only an explicitly typed public candidate participates in comparison.
        if row.get("kind") is None:
            continue
        if (type(row.get("public_url")) is not str
                or PUBLIC_URL.fullmatch(row["public_url"]) is None
                or type(row.get("library_item_id")) is not str
                or SHA64.fullmatch(row["library_item_id"]) is None
                or row.get("kind") not in (
                    "PREVENTION_RULE", "PUBLIC_TECHNICAL_EVIDENCE")):
            raise PythonRecipeShelfError("W04 Python PR source/reference mismatch")
        relevant.append({
            "library_item_id": row["library_item_id"],
            "source_id": "repo:python/cpython",
            "public_url": row["public_url"],
            "kind": row.get("kind"),
            "purpose_code": RELEVANT_PR,
            "lifecycle": "UNVERIFIED_CANDIDATE_ONLY",
            "human_approved": False,
            "export_allowed": False,
        })
    relevant = sorted(relevant, key=lambda x: (x["public_url"],
                                               x["library_item_id"]))[:3]
    return dict(base, status=COMPARISON_STATUS,
                relevant_public_pr_count_in_page=len(relevant),
                relevant_public_prs=relevant)
