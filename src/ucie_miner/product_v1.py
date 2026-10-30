"""UCIE P9 one-command *integration preview* and independent draft consumer.

Closes the previous W01/W04/W06/W07/W08/P8/W09 fragmentation for honest
inspection, source-bound search, testable UCIE-authored consumer packaging,
and experience-readback. A preview or draft package is NOT a production
release/owner sign-off/independent QA approval or P9 V1 acceptance.

No network, operating DB writes, auto-promotion, scheduler, external/private
project data, new source route, model learning or signing key use.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
import os
import re
from pathlib import Path
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

from .source_registry import preview_source_registry
from .p9_pinned_public_review import lookup_pinned_review
from .library_search import search_existing_public_library
from .library_shelves import search_official_metadata_shelf
from .experience_application import experience_library_preview
from .capability_experience import read_capability_history
from .portable_exact import (search_public_metadata, SCHEMA as CONSUMER_SCHEMA,
                             VERSION as CONSUMER_VERSION, KINDS as CONSUMER_KINDS,
                             _pinned_public_pull)
from .capability_trials import evaluate_ucie_owned_recipe
from .public_discovery import SOURCE_SKILL
from .skill_profiles import PROFILE

SCHEMA = "UCIE_P9_PRODUCT_INTEGRATION_PREVIEW_V1"
PACK_SCHEMA = "UCIE_W09_DRAFT_INDEPENDENT_CONSUMER_V2"
PACKAGE_NAME = "ucie_portable_exact_1_1_0_DRAFT.zip"
MAX_SOURCE_BYTES = 16384
MAX_ZIP_BYTES = 32768


class ProductIntegrationError(ValueError):
    pass


def _root(root: Path) -> Path:
    if (not isinstance(root, Path) or root.is_symlink()
            or root.name.casefold() != "ucie" or not root.is_dir()):
        raise ProductIntegrationError("dedicated UCIE checkout required")
    runtime = root / "runtime"
    if runtime.is_symlink() or not runtime.is_dir():
        raise ProductIntegrationError("existing UCIE-only runtime required")
    return root


def _demo_input() -> list[dict]:
    """Never export any actual public PR data to a consumer draft."""
    rows = []
    for n, purpose in enumerate(("API_CONTRACT", "CONCURRENCY", "API_CONTRACT")):
        rows.append({
            "source_id": "repo:python/cpython", "domain": "Python",
            "kind": "PUBLIC_TECHNICAL_EVIDENCE", "purpose_code": purpose,
            "library_item_id": sha256(f"UCIE-DEMO-ID:{n}".encode()).hexdigest(),
            "public_url": "https://github.com/python/cpython/pull/" + str(n + 1),
            "evidence_sha256": sha256(f"UCIE-DEMO-EVIDENCE:{n}".encode()).hexdigest(),
            "human_approved": False, "export_allowed": False,
        })
    return rows


def portable_consumer_check() -> dict:
    """UCIE-authored sample: search parity, miss, single-vs-batch execution."""
    rows = _demo_input()
    key = ("repo:python/cpython", "Python",
           "PUBLIC_TECHNICAL_EVIDENCE", "API_CONTRACT")
    miss = key[:3] + ("NO_SUCH_EXPERIENCE",)
    first = search_public_metadata(rows, queries=(key,))
    second = search_public_metadata(rows, queries=(key, miss))
    expected = tuple(row["library_item_id"] for row in rows
                     if tuple(row[field] for field in (
                         "source_id", "domain", "kind", "purpose_code")) == key)
    got_single = tuple(x["library_item_id"] for x in first["results"][0]["items"])
    got_batch = tuple(x["library_item_id"] for x in second["results"][0]["items"])
    valid = (set(expected) == set(got_single) == set(got_batch)
             and first["strategy"] == "LINEAR_EXACT_SCAN"
             and second["strategy"] == "COMPOSITE_INDEX"
             and second["results"][1]["total_matches"] == 0)
    return {
        "status": ("FIRST_PARTY_PORTABLE_CONSUMER_DEMO_EQUIVALENT"
                   if valid else "FIRST_PARTY_PORTABLE_CONSUMER_DEMO_MISMATCH"),
        "consumer_schema": CONSUMER_SCHEMA,
        "input": "UCIE_AUTHOR_SYNTHETIC_ONLY",
        "standalone_import_independently_tested_here": False,
        "single_query_strategy": first["strategy"],
        "batch_strategy": second["strategy"],
        "positive_exact_match_count": len(expected),
        "zero_match_checked": second["results"][1]["total_matches"] == 0,
        "all_queries_equivalent": valid,
        "original_upstream_code_executed": False,
        "approved_or_exportable_public_candidates": 0,
    }


def _portable_public_ledger_handoff(public: dict, *, limit: int) -> dict:
    """Check whether the REAL W04 public metadata window is consumable by P7.

    The W04 reader must already have validated Stage10/12/15 source linkage.
    This does not package, transfer or approve upstream source code. It emits
    ONLY the same sanitized unapproved PR metadata available through W04.
    An approved git/git commit reference cannot be represented by the P7
    PR-only contract and is explicitly counted as unsupported.
    """
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ProductIntegrationError("invalid portable handoff page size")
    if public["status"] == "SOURCE_LINKAGE_INCOMPLETE_NO_GO":
        if public["items"] or public["returned_count"] != 0:
            raise ProductIntegrationError("incomplete W04 ledger carries results")
        return {
            "schema": "UCIE_P9_SOURCE_LINKED_PORTABLE_HANDOFF_V1",
            "status": "SOURCE_LINKAGE_INCOMPLETE_NO_GO",
            "consumer_payload": None,
            "source_window_items": 0, "portable_candidate_items": 0,
            "unsupported_reference_count": 0,
            "in_process_exact_search_equivalent": False,
            "independent_consumer_executed_here": False,
            "approved_or_exportable_items": 0,
            "network_requests": 0, "operating_database_writes": 0,
            "package_released": False, "v1_accepted": False,
        }
    if (public["status"] != "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"
            or type(public["items"]) is not list
            or type(public["returned_count"]) is not int
            or len(public["items"]) != public["returned_count"]
            or public["returned_count"] > limit):
        raise ProductIntegrationError("unexpected W04 portable source window")
    rows, unsupported = [], 0
    for item in public["items"]:
        if (type(item) is not dict
                or item["lifecycle"] != "UNVERIFIED_CANDIDATE_ONLY"
                or item["signature_status"] != "NOT_ATTESTED_BY_THIS_SEARCH"
                or item["human_approved"] is not False
                or item["export_allowed"] is not False):
            raise ProductIntegrationError("W04 public metadata trust boundary changed")
        source, url = item["source_id"], item["public_url"]
        if not _pinned_public_pull(source, url):
            # git/git commit evidence is legitimate W04 public metadata, but
            # the portable exact consumer currently accepts only PRs.
            prefix = "https://github.com/git/git/commit/"
            if (source != "repo:git/git" or type(url) is not str
                    or not url.startswith(prefix)
                    or len(url[len(prefix):]) != 40
                    or any(ch not in "0123456789abcdef"
                           for ch in url[len(prefix):])):
                raise ProductIntegrationError("unsupported or malformed W04 provenance")
            unsupported += 1
            continue
        rows.append({
            "source_id": source, "domain": item["domain"],
            "kind": item["kind"], "purpose_code": item["purpose_code"],
            "library_item_id": item["library_item_id"],
            "public_url": url, "evidence_sha256": item["evidence_sha256"],
            "human_approved": False, "export_allowed": False,
        })
    keys = sorted({(row["source_id"], row["domain"],
                    row["kind"], row["purpose_code"]) for row in rows})
    equivalent = False
    if keys:
        result = search_public_metadata(rows, queries=tuple(keys), limit=limit)
        if (result["production_release_approved"] is not False
                or result["approved_or_exportable_items"] != 0
                or result["catalog_count"] != len(rows)):
            raise ProductIntegrationError("portable consumer trust boundary changed")
        expected = {
            key: sorted((row["library_item_id"], row["public_url"],
                         row["evidence_sha256"]) for row in rows
                        if (row["source_id"], row["domain"],
                            row["kind"], row["purpose_code"]) == key)
            for key in keys
        }
        equivalent = all(
            len(got["items"]) == got["total_matches"]
            and sorted((row["library_item_id"], row["public_url"],
                        row["evidence_sha256"]) for row in got["items"])
            == expected[key]
            for key, got in zip(keys, result["results"])
        )
        if not equivalent or len(result["results"]) != len(keys):
            raise ProductIntegrationError("source-linked portable search mismatch")
    return {
        "schema": "UCIE_P9_SOURCE_LINKED_PORTABLE_HANDOFF_V1",
        "status": ("SOURCE_LINKED_PUBLIC_PR_METADATA_PORTABLE_PARITY_NO_GO"
                   if rows else "NO_PORTABLE_PUBLIC_PR_WINDOW_NO_GO"),
        "consumer_schema": CONSUMER_SCHEMA,
        "consumer_version": CONSUMER_VERSION,
        # This is inert metadata in a read-only response, not a published ZIP.
        "consumer_payload": {
            "items": rows, "queries": [list(key) for key in keys],
            "limit": limit,
        },
        "source_window_items": public["returned_count"],
        "portable_candidate_items": len(rows),
        "unsupported_reference_count": unsupported,
        "source_window_truncated": public.get("omitted_count", 0) > 0,
        "full_ledger_covered": False,
        "in_process_exact_search_equivalent": equivalent,
        "independent_consumer_executed_here": False,
        "approved_or_exportable_items": 0,
        "network_requests": 0, "operating_database_writes": 0,
        "package_released": False, "v1_accepted": False,
    }


def _bounded_catalog_view(*, query: str, domain: str | None, limit: int,
                          public: dict, official: dict, signed: dict | None,
                          p8: dict, w05: dict) -> dict:
    """One query over existing verified readers, not a new database/index.

    Each original reader owns its source, provenance and signature checks.
    This combines only the bounded pages already returned by those readers:
    a match count here is NEVER a claim about every ledger record.
    """
    needle = query.casefold()
    records = []

    def matches(*terms: object) -> bool:
        return not needle or needle in " ".join(
            value for value in terms if type(value) is str
        ).casefold()

    def add(shelf: str, entry: dict, *terms: object) -> None:
        if matches(*terms):
            records.append((shelf, entry))

    for item in public["items"]:
        if (item["human_approved"] is not False
                or item["export_allowed"] is not False
                or item["signature_status"] != "NOT_ATTESTED_BY_THIS_SEARCH"
                or item["lifecycle"] != "UNVERIFIED_CANDIDATE_ONLY"):
            raise ProductIntegrationError("public candidate trust boundary changed")
        add("PUBLIC_CANDIDATE", {
            "library_item_id": item["library_item_id"],
            "kind": item["kind"],
            "source_id": item["source_id"],
            "public_url": item["public_url"],
            "evidence_sha256": item["evidence_sha256"],
            "purpose_code": item["purpose_code"],
            "domain": item["domain"],
            "version_scope": item["version_scope_claim"],
            "source_license_status": item["license_status"],
            "verification": item["lifecycle"],
            "signature_status": item["signature_status"],
            "human_approved": False,
            "export_allowed": False,
        }, item["kind"], item["source_id"], item["public_url"],
            item["purpose_code"], item["domain"], item["skill_profile"],
            item["revision_hint"])

    # No source/domain lookup is invented for an official hash-only ledger.
    # Domain filtering intentionally excludes rows with no attested domain.
    if domain is None:
        for item in official["items"]:
            if (item["human_approved"] is not False
                    or item["export_allowed"] is not False
                    or item["lifecycle"] != "PUBLIC_METADATA_UNVERIFIED"):
                raise ProductIntegrationError("official metadata trust boundary changed")
            item_id = sha256(json.dumps((
                item["source_id"], item["kind"], item["source_reference"],
                item["content_sha256"]),
                separators=(",", ":"), ensure_ascii=True).encode("ascii")
            ).hexdigest()
            add("OFFICIAL_METADATA", {
                "library_item_id": item_id,
                "kind": item["kind"],
                "source_id": item["source_id"],
                "public_url": item["public_url"],
                "evidence_sha256": item["content_sha256"],
                "reference_scope": item["reference_scope"],
                "verification": item["lifecycle"],
                "human_approved": False,
                "export_allowed": False,
            }, item["kind"], item["source_id"], item["public_url"],
                item["source_reference"], item["reference_scope"])

        # Signed owner-risk rules are only included after original verifier
        # succeeds at read time. They are NOT independent QA or export grants.
        if (signed is not None
                and signed["status"] != "EXISTING_OWNER_SIGNED_RULEPACKS_VERIFIED_READ_ONLY"):
            raise ProductIntegrationError("signed Rulepack verifier status changed")
        for item in signed["items"] if signed is not None else ():
            if (item["verification"] != "OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME"
                    or item["independent_qa_approved"] is not False
                    or item["new_package_export_allowed"] is not False):
                raise ProductIntegrationError("signed Rulepack trust boundary changed")
            add("SIGNED_MANUAL_RULE", {
                "library_item_id": item["item_id"],
                "kind": "PREVENTION_RULE",
                "rule_id": item["rule_id"],
                "pack_serial": item["pack_serial"],
                "source_package_sha256": item["source_package_sha256"],
                "verification": item["verification"],
                "approval_basis": item["approval_basis"],
                "independent_qa_approved": False,
                "human_approved_for_general_export": False,
                "export_allowed": False,
            }, item["rule_id"], "PREVENTION_RULE", item["verification"])

        for item in p8["items"]:
            if item["production_adopted"] is not False:
                raise ProductIntegrationError("synthetic experience trust boundary changed")
            add("UCIE_SYNTHETIC_EXPERIENCE", {
                "library_item_id": item["library_item_id"],
                "kind": "UCIE_EXPERIENCE",
                "experiment_id": item["experiment_id"],
                "workload_id": item["workload_id"],
                "verification": "UCIE_FIRST_PARTY_SYNTHETIC_ONLY",
                "production_adopted": False,
                "export_allowed": False,
            }, item["experiment_id"], item["workload_id"],
                "UCIE_EXPERIENCE")

        # A recorded W05 trial is a UCIE experiment referencing a public
        # candidate, NEVER verification of that upstream engine/skill.
        for item in w05["items"]:
            if (item["upstream_capability_verified"] is not False
                    or item["approved_or_exportable"] is not False):
                raise ProductIntegrationError("upstream skill verification boundary changed")
            add("UCIE_CANDIDATE_TRIAL_EXPERIENCE", {
                "library_item_id": item["experience_id"],
                "kind": "UCIE_EXPERIENCE",
                "linked_candidate_kind": item["kind"],
                "source_id": item["source_id"],
                "public_url": item["public_url"],
                "purpose_code": item["purpose_code"],
                "verification": "UCIE_FIRST_PARTY_SYNTHETIC_UPSTREAM_UNVERIFIED",
                "upstream_capability_verified": False,
                "export_allowed": False,
            }, item["kind"], item["source_id"], item["public_url"],
                item["purpose_code"], "UCIE_EXPERIENCE")

    order = {
        "SIGNED_MANUAL_RULE": 0, "PUBLIC_CANDIDATE": 1,
        "OFFICIAL_METADATA": 2, "UCIE_CANDIDATE_TRIAL_EXPERIENCE": 3,
        "UCIE_SYNTHETIC_EXPERIENCE": 4,
    }
    records.sort(key=lambda row: (
        order[row[0]], row[1]["kind"],
        row[1].get("source_id", ""),
        row[1]["library_item_id"]))
    window_count = len(records)
    limited = [
        {"shelf": shelf, **item}
        for shelf, item in records[:limit]
    ]
    omitted_by_readers = (
        public.get("omitted_count", 0) > 0
        or official.get("omitted_count", 0) > 0
        or w05["recorded_count"] > w05["returned_count"]
    )
    return {
        "schema": "UCIE_P9_BOUNDED_UNIFIED_CATALOG_QUERY_V1",
        "status": "READ_ONLY_BOUNDED_MULTI_SHELF_SEARCH_NO_GO",
        "query": query, "domain_filter": domain,
        "limit": limit, "returned_count": len(limited),
        "matches_in_loaded_windows": window_count,
        "omitted_from_loaded_windows": max(0, window_count - limit),
        "source_window_truncated": omitted_by_readers,
        "full_catalog_match_count_known": False,
        "items": limited,
        "shelf_statuses": {
            "public_candidates": public["status"],
            "official_metadata": official["status"],
            "signed_rules": (signed["status"] if signed is not None
                             else "NOT_INSPECTED_NO_GO"),
            "ucie_experience": p8["status"],
            "linked_capability_experience": w05["status"],
        },
        "network_requests": 0, "operating_database_writes": 0,
        "new_approvals": 0, "new_signatures_created": 0,
        "full_library_implemented": False, "v1_accepted": False,
    }


REUSE_ITEM_ID = re.compile(r"[0-9a-f]{64}\\Z")


def _reuse_eligibility(*, catalog: dict, signed: dict | None,
                       selected_item_id: str | None) -> dict:
    """Read-only item selection using the already checked catalog + W07.

    This never promotes public metadata and never issues a new package.
    Manual references to pre-existing, freshly verified owner Rulepacks
    are distinct from approval for generic export.
    """
    if selected_item_id is not None and (
            type(selected_item_id) is not str
            or REUSE_ITEM_ID.fullmatch(selected_item_id) is None):
        raise ProductIntegrationError("invalid exact library item selection")
    if (catalog["status"] != "READ_ONLY_BOUNDED_MULTI_SHELF_SEARCH_NO_GO"
            or type(catalog["items"]) is not list
            or type(catalog["returned_count"]) is not int
            or len(catalog["items"]) != catalog["returned_count"]):
        raise ProductIntegrationError("unverified unified catalog eligibility source")
    verified = {}
    if signed is not None:
        if (signed.get("status") !=
                "EXISTING_OWNER_SIGNED_RULEPACKS_VERIFIED_READ_ONLY"
                or type(signed.get("items")) is not list
                or signed.get("signed_rule_count") != len(signed["items"])
                or signed.get("new_release_approved") is not False
                or signed.get("network_requests") != 0
                or signed.get("database_writes") != 0):
            raise ProductIntegrationError("original signed pack verifier required")
        for record in signed["items"]:
            if (record["verification"] !=
                    "OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME"
                    or record["approval_basis"] != "OWNER_RISK_ACCEPTED_CI_ONLY"
                    or record["independent_qa_approved"] is not False
                    or record["license_signoff"] is not False
                    or record["new_package_export_allowed"] is not False
                    or record["unattended_execution_allowed"] is not False
                    or REUSE_ITEM_ID.fullmatch(record["item_id"]) is None
                    or REUSE_ITEM_ID.fullmatch(record["source_package_sha256"])
                       is None
                    or record["item_id"] in verified):
                raise ProductIntegrationError("untrusted signed item eligibility")
            verified[record["item_id"]] = record
    choices = []
    ids = set()
    for row in catalog["items"]:
        item_id = row["library_item_id"]
        shelf = row["shelf"]
        if (type(item_id) is not str or REUSE_ITEM_ID.fullmatch(item_id) is None
                or item_id in ids):
            raise ProductIntegrationError("invalid or duplicate catalog item ID")
        ids.add(item_id)
        manual = shelf == "SIGNED_MANUAL_RULE"
        if manual:
            proof = verified.get(item_id)
            if (proof is None or row["verification"] != proof["verification"]
                    or row["pack_serial"] != proof["pack_serial"]
                    or row["rule_id"] != proof["rule_id"]
                    or row["source_package_sha256"] !=
                    proof["source_package_sha256"]
                    or row["independent_qa_approved"] is not False
                    or row["export_allowed"] is not False):
                raise ProductIntegrationError(
                    "unverified signed item in bounded catalog")
            reasons = [
                "EXISTING_OWNER_SIGNED_PACK_MANUAL_SCOPE_ONLY",
                "INDEPENDENT_QA_NOT_ATTESTED",
                "LEGAL_LICENSE_SIGNOFF_NOT_ATTESTED",
                "NEW_GENERIC_EXPORT_NOT_APPROVED",
            ]
            action = "REFERENCE_EXISTING_VERIFIED_PACK_MANUALLY"
        else:
            if row.get("export_allowed") is not False:
                raise ProductIntegrationError("unapproved catalog item export claim")
            reasons = [
                "NO_VERIFIED_APPROVED_REUSABLE_ARTIFACT",
                "VERSION_APPLICABILITY_NOT_CONFIRMED",
                "PER_REVISION_DISTRIBUTION_RIGHTS_NOT_CONFIRMED",
            ]
            action = "EVIDENCE_REVIEW_ONLY"
        choice = {
            "library_item_id": item_id, "shelf": shelf,
            "selection_status": (
                "EXISTING_OWNER_SIGNED_MANUAL_REFERENCE_ONLY"
                if manual else "CANDIDATE_OR_EXPERIENCE_REUSE_BLOCKED"),
            "permitted_action": action,
            "manual_reference_to_existing_pack_allowed": manual,
            "new_generic_package_export_allowed": False,
            "production_auto_apply_allowed": False,
            "version_evidence_status": (
                "EXISTING_SIGNED_PACKAGE_SHA256_PINNED_MANUAL_SCOPE_ONLY"
                if manual else "RUNTIME_VERSION_APPLICABILITY_UNVERIFIED"),
            "rights_verification_status": (
                "OWNER_RISK_MANUAL_SCOPE_NO_LEGAL_LICENSE_SIGNOFF"
                if manual else "PER_REVISION_DISTRIBUTION_RIGHTS_NOT_CONFIRMED"),
            "review_blockers": reasons,
        }
        if manual:
            choice["pack_serial"] = proof["pack_serial"]
            choice["source_package_sha256"] = proof["source_package_sha256"]
            choice["signed_scope"] = proof["signed_pack_manual_scope"]
            choice["current_signature_verification"] = proof["verification"]
            choice["approval_basis"] = proof["approval_basis"]
        else:
            choice["observed_verification"] = row["verification"]
            if shelf == "PUBLIC_CANDIDATE":
                if (row.get("version_scope") != "UNDETERMINED"
                        or row.get("source_license_status") !=
                        "NOT_ATTESTED_PER_REVISION"):
                    raise ProductIntegrationError(
                        "unverified public version or rights claim")
                choice["version_scope"] = row["version_scope"]
                choice["source_license_status"] = row["source_license_status"]
        choices.append(choice)
    selection = None
    if selected_item_id is not None:
        selection = next((x for x in choices
                          if x["library_item_id"] == selected_item_id), None)
        if selection is None:
            selection = {
                "library_item_id": selected_item_id,
                "selection_status": "NOT_IN_CURRENT_BOUNDED_QUERY_WINDOW_NO_GO",
                "permitted_action": "REFINE_QUERY_OR_BOUNDED_LIMIT",
                "manual_reference_to_existing_pack_allowed": False,
                "new_generic_package_export_allowed": False,
                "production_auto_apply_allowed": False,
                "not_found_in_full_catalog_proven": False,
            }
    return {
        "schema": "UCIE_V1_BOUNDED_REUSE_ELIGIBILITY_V1",
        "status": "INSPECTED_BOUNDED_ELIGIBILITY_NO_GENERIC_EXPORT",
        "items": choices,
        "returned_count": len(choices),
        "manual_reference_count_in_loaded_window": sum(
            x["manual_reference_to_existing_pack_allowed"] for x in choices),
        "new_generic_package_exportable_count": 0,
        "selected_item": selection,
        "catalog_window_truncated": bool(
            catalog["source_window_truncated"]
            or catalog["omitted_from_loaded_windows"] > 0),
        "full_catalog_inspected": False,
        "original_signed_verifier_used": signed is not None,
        "no_implicit_owner_approval_inferred": True,
        "network_requests": 0, "operating_database_writes": 0,
        "new_signatures_created": 0, "new_package_released": False,
        "v1_accepted": False,
    }


def _compare_existing_capability_experiences(*, history: dict,
                                             query: str, domain: str | None,
                                             limit: int) -> dict:
    """Compare verified UCIE-owned experiment receipts, not upstream code.

    The existing experience reader validates the allowlist and full append-only
    hash chain before returning these measurements. A shared synthetic recipe
    does NOT establish that either external project improvement was tested.
    """
    if (history["status"] != "UCIE_FIRST_PARTY_W05_EXPERIENCE_READ_ONLY"
            or type(limit) is not int or not 1 <= limit <= 20
            or type(query) is not str or len(query) > 80):
        raise ProductIntegrationError("invalid bounded capability comparison")
    shown = []
    for item in history["items"]:
        if (item["first_party_synthetic_only"] is not True
                or item["upstream_capability_verified"] is not False
                or item["approved_or_exportable"] is not False
                or item["equivalent"] is not True
                and item["decision"] == "RETEST_FIRST_PARTY_RECIPE"):
            raise ProductIntegrationError("untrusted capability experience status")
        source = item["source_id"]
        repo = source.removeprefix("repo:")
        if source != "repo:" + repo or repo not in SOURCE_SKILL:
            raise ProductIntegrationError("unapproved capability source")
        item_domain = PROFILE[SOURCE_SKILL[repo]]["domain"]
        if domain is not None and item_domain.casefold() != domain.casefold():
            continue
        if query and query.casefold() not in " ".join((
                item["kind"], item["purpose_code"], item["recipe_id"],
                source, item_domain, item["public_url"])).casefold():
            continue
        base, candidate = (item["baseline_operations"],
                           item["candidate_operations"])
        if (type(base) is not int or type(candidate) is not int
                or base <= 0 or not 0 < candidate <= 3 * base):
            raise ProductIntegrationError("invalid first-party trial measurement")
        reduction_ppm = ((base - candidate) * 1_000_000 // base
                         if item["equivalent"] else None)
        shown.append({
            "experience_id": item["experience_id"],
            "candidate_id": item["candidate_id"],
            "kind": item["kind"], "purpose_code": item["purpose_code"],
            "recipe_id": item["recipe_id"],
            "domain": item_domain, "source_id": source,
            "public_url": item["public_url"],
            "workload_sha256": item["workload_sha256"],
            "synthetic_rows": item["rows"],
            "synthetic_queries": item["queries"],
            "baseline_operations": base,
            "candidate_operations": candidate,
            "equivalent_on_ucie_synthetic": item["equivalent"],
            "within_trial_operation_reduction_ppm": reduction_ppm,
            "baseline_median_ns_diagnostic": item["baseline_median_ns"],
            "candidate_median_ns_diagnostic": item["candidate_median_ns"],
            "review_decision": item["decision"],
            "upstream_code_tested": False,
            "upstream_capability_verified": False,
            "general_performance_ranking_authorized": False,
            "owner_approved": False,
            "export_allowed": False,
        })
    shown.sort(key=lambda x: (x["kind"], x["purpose_code"],
                              x["source_id"], x["candidate_id"],
                              x["workload_sha256"]))
    grouped = {}
    for item in shown:
        # Matching purpose/recipe/identical workload permits reviewing
        # evidence together, not inferring cross-PR speed differences.
        key = (item["kind"], item["purpose_code"], item["recipe_id"],
               item["workload_sha256"])
        grouped.setdefault(key, 0)
        grouped[key] += 1
    return {
        "schema": "UCIE_V1_EXISTING_PUBLIC_CAPABILITY_TRIAL_COMPARISON_V1",
        "status": "FIRST_PARTY_SYNTHETIC_COMPARISON_ONLY_UPSTREAM_UNVERIFIED",
        "query": query, "domain_filter": domain,
        "items": shown[:limit],
        "matches_in_loaded_experience_window": len(shown),
        "returned_count": min(limit, len(shown)),
        "same_workload_review_groups": sum(v >= 2 for v in grouped.values()),
        "experience_window_truncated": (
            history["recorded_count"] > history["returned_count"]),
        "full_history_comparison_complete": False,
        "public_pr_code_executed": False,
        "cross_candidate_speed_ranked": False,
        "production_adopted": False,
        "network_requests": 0, "operating_database_writes": 0,
        "new_approvals": 0, "auto_promoted": False,
        "v1_accepted": False,
    }


def _revision_review_queue(*, p8: dict, w05: dict,
                           limit: int) -> dict:
    """Derive reproducible, unapproved Library revision review candidates.

    Both inputs MUST come from the original source-checked, hash-chain-checked
    UCIE experience readers. No experiment or upstream source is executed.
    The target is existing UCIE-authored code, never an upstream PR.
    """
    if (type(limit) is not int or not 1 <= limit <= 20
            or p8["status"] not in (
                "P8_HASH_CHAIN_EXPERIENCE_SEARCHABLE_NO_GO",
                "EXPERIENCE_REQUIRES_REVIEW_NO_GO")
            or w05["status"] != "UCIE_FIRST_PARTY_W05_EXPERIENCE_READ_ONLY"
            or type(p8["recorded_experiments"]) is not int
            or len(p8["items"]) != p8["recorded_experiments"]
            or type(w05["recorded_count"]) is not int
            or type(w05["returned_count"]) is not int
            or len(w05["items"]) != w05["returned_count"]
            or w05["recorded_count"] < w05["returned_count"]):
        raise ProductIntegrationError("untrusted UCIE experience review source")
    proposals = []

    def add(*, source_event: str, target: str, source_shelf: str,
            decision: str, next_action: str, hold: bool,
            public_link: dict | None = None) -> None:
        if (type(source_event) is not str or len(source_event) != 64
                or any(c not in "0123456789abcdef" for c in source_event)):
            raise ProductIntegrationError("invalid UCIE experience lineage hash")
        parts = ["UCIE_P8_LIBRARY_REVISION_REVIEW_V1", source_event, target,
                 decision]
        proposal_id = sha256(json.dumps(
            parts, ensure_ascii=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        proposal = {
            "proposal_id": proposal_id,
            "source_library_item_id": source_event,
            "target_ucie_component": target,
            "source_shelf": source_shelf,
            "original_experiment_decision": decision,
            "review_action": next_action,
            "review_state": ("HOLD_FOR_MANUAL_REVIEW_NOT_APPLIED" if hold
                             else "MORE_UCIE_TESTING_REQUIRED_NOT_APPLIED"),
            "evidence_scope": "UCIE_FIRST_PARTY_SYNTHETIC_ONLY",
            "independent_quality_assurance": False,
            "production_improvement_verified": False,
            "source_code_changed": False,
            "library_revision_written": False,
            "auto_promoted": False,
            "export_allowed": False,
        }
        if public_link is not None:
            proposal["public_candidate_identity_only"] = public_link
            proposal["upstream_capability_verified"] = False
        proposals.append(proposal)

    for item in p8["items"]:
        decision = item["decision"]
        if (item["kind"] != "UCIE_EXPERIENCE"
                or item["provenance"] !=
                "LOCAL_P8_HASH_CHAIN_NOT_THIRD_PARTY_ATTESTATION"
                or item["real_library_benefit_verified"] is not False
                or item["production_adopted"] is not False
                or item["independent_qa"] is not False
                or decision not in (
                    "SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING",
                    "REJECT_OR_REVISE_SYNTHETIC_CANDIDATE")):
            raise ProductIntegrationError("P8 synthetic revision trust boundary changed")
        positive = decision == "SYNTHETIC_CANDIDATE_WORTH_MORE_TESTING"
        if positive and not item["exact_results_equivalent"]:
            raise ProductIntegrationError("positive P8 revision lacks equivalence")
        add(
            source_event=item["library_item_id"],
            source_shelf="UCIE_SYNTHETIC_EXPERIENCE",
            target="ucie_miner.library_exact_index:EXACT_QUERY_POLICY",
            decision=decision,
            next_action=("RETEST_INDEX_POLICY_ON_DIVERSE_UCIE_WORKLOADS"
                         if positive else "HOLD_INDEX_POLICY_FOR_CORRECTION"),
            hold=not positive)

    for item in w05["items"]:
        decision = item["decision"]
        if (item["first_party_synthetic_only"] is not True
                or item["upstream_capability_verified"] is not False
                or item["approved_or_exportable"] is not False
                or decision not in (
                    "RETEST_FIRST_PARTY_RECIPE",
                    "HOLD_FOR_FIRST_PARTY_RECIPE_CORRECTION")
                or type(item["equivalent"]) is not bool):
            raise ProductIntegrationError("W05 revision trust boundary changed")
        positive = decision == "RETEST_FIRST_PARTY_RECIPE"
        if positive and (not item["equivalent"]
                         or item["baseline_operations"] <=
                         item["candidate_operations"]):
            raise ProductIntegrationError("positive W05 revision lacks own result")
        add(
            source_event=item["experience_id"],
            source_shelf="UCIE_CANDIDATE_TRIAL_EXPERIENCE",
            target="ucie_miner.capability_trials:" + item["recipe_id"],
            decision=decision,
            next_action=("RETEST_UCIE_OWNED_RECIPE_WITH_INDEPENDENT_WORKLOAD"
                         if positive else "HOLD_UCIE_OWNED_RECIPE_FOR_CORRECTION"),
            hold=not positive,
            public_link={
                "candidate_id": item["candidate_id"],
                "source_id": item["source_id"],
                "public_url": item["public_url"],
                "upstream_code_executed": False,
            })

    proposals.sort(key=lambda item: (
        item["review_state"] != "HOLD_FOR_MANUAL_REVIEW_NOT_APPLIED",
        item["target_ucie_component"], item["proposal_id"]))
    return {
        "schema": "UCIE_P8_LIBRARY_REVISION_REVIEW_QUEUE_V1",
        "status": "UNAPPROVED_REPRODUCIBLE_REVIEW_CANDIDATES_ONLY",
        "source": "ORIGINAL_UCIE_VERIFIED_EXPERIENCE_READERS",
        "candidate_count_in_loaded_window": len(proposals),
        "returned_count": min(limit, len(proposals)),
        "omitted_from_loaded_window": max(0, len(proposals) - limit),
        "source_window_truncated": (
            w05["recorded_count"] > w05["returned_count"]),
        "items": proposals[:limit],
        "new_revision_persisted": False,
        "reviewer_approved": False,
        "learning_model_changed": False,
        "network_requests": 0,
        "operating_database_writes": 0,
        "auto_promoted": False,
        "v1_accepted": False,
    }


def _evidence_readiness(*, sources: dict, public: dict,
                        official: dict, limit: int) -> dict:
    """Explain remaining P9 evidence gates for the current bounded read window.

    This reuses the existing W01/W04/W06 validators. Source linkage and a
    content SHA-256 are *not* upstream fixed-version verification, a license
    grant, independent QA, signature, or approval for distribution.
    """
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ProductIntegrationError("invalid evidence inspection limit")
    approved = {
        row["source_id"]: row
        for row in sources["sources"]
        if row["status"] == "ACTIVE_APPROVED"
    }
    if len(approved) != sources["active_source_count"]:
        raise ProductIntegrationError("UCIE source registry count mismatch")
    public_linked = public["status"] == "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"
    official_available = (
        official["status"] == "STAGE14_OFFICIAL_METADATA_READ_ONLY_UNVERIFIED_NO_GO"
    )
    if (type(public["items"]) is not list
            or type(official["items"]) is not list
            or len(public["items"]) != public["returned_count"]
            or len(official["items"]) != official["returned_count"]
            or len(public["items"]) > limit
            or len(official["items"]) > limit
            or (not public_linked and public["items"])
            or (not official_available and official["items"])):
        raise ProductIntegrationError("invalid bounded evidence reader response")
    rows = []
    for item in public["items"]:
        src = approved.get(item["source_id"])
        if (src is None or src["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY"
                or item["license_status"] != src["license_verdict"]
                or item["lifecycle"] != "UNVERIFIED_CANDIDATE_ONLY"
                or item["signature_status"] != "NOT_ATTESTED_BY_THIS_SEARCH"
                or item["human_approved"] is not False
                or item["export_allowed"] is not False
                or item["version_scope_claim"] != "UNDETERMINED"
                or type(item["evidence_sha256"]) is not str
                or len(item["evidence_sha256"]) != 64
                or any(c not in "0123456789abcdef"
                       for c in item["evidence_sha256"])
                or type(item["revision_hint"]) is not str
                or len(item["revision_hint"]) != 40
                or any(c not in "0123456789abcdef"
                       for c in item["revision_hint"])):
            raise ProductIntegrationError("untrusted W04 evidence readiness fields")
        pinned = lookup_pinned_review(
            source_id=item["source_id"], public_url=item["public_url"],
            merge_sha=item["revision_hint"])
        rows.append({
            "shelf": "W04_PUBLIC_CANDIDATE",
            "pinned_public_revision_review": pinned,
            "repository_license_observed_in_pinned_review": pinned is not None,
            "library_item_id": item["library_item_id"],
            "source_id": item["source_id"],
            "public_url": item["public_url"],
            "evidence_sha256": item["evidence_sha256"],
            "revision_hint": item["revision_hint"],
            "version_scope_claim": item["version_scope_claim"],
            "source_license_status": item["license_status"],
            "local_source_linkage_checked": True,
            "upstream_revision_independently_attested": False,
            "runtime_version_applicability_verified": False,
            "source_rights_for_export_verified": False,
            "independent_qa_verified": False,
            "export_allowed": False,
        })
    for item in official["items"]:
        src = approved.get(item["source_id"])
        if (src is None or item["lifecycle"] != "PUBLIC_METADATA_UNVERIFIED"
                or item["source_license_reviewed"] is not False
                or item["verified_applicability"] is not False
                or item["human_approved"] is not False
                or item["export_allowed"] is not False
                or type(item["content_sha256"]) is not str
                or len(item["content_sha256"]) != 64
                or any(c not in "0123456789abcdef"
                       for c in item["content_sha256"])
                or item["reference_scope"] not in (
                    "PINNED_OFFICIAL_DOCUMENT_CURRENT_URL",
                    "PUBLIC_REPOSITORY_RELEASE_INDEX_NOT_EXACT_RELEASE",
                    "PUBLIC_ADVISORY_IDENTIFIER_UNVERIFIED")):
            raise ProductIntegrationError("untrusted W06 official evidence readiness")
        rows.append({
            "shelf": "W06_OFFICIAL_METADATA",
            "source_id": item["source_id"],
            "public_url": item["public_url"],
            "content_sha256": item["content_sha256"],
            "reference_scope": item["reference_scope"],
            "local_source_linkage_checked": True,
            "exact_published_version_independently_attested": False,
            "runtime_version_applicability_verified": False,
            "source_rights_for_export_verified": False,
            "independent_qa_verified": False,
            "export_allowed": False,
        })
    blockers = []
    if not public_linked:
        blockers.append("W04_PUBLIC_EVIDENCE_LINKAGE_NOT_READY")
    if not official_available:
        blockers.append("W06_OFFICIAL_EVIDENCE_LEDGER_NOT_READY")
    pinned_count = sum(row.get("pinned_public_revision_review") is not None
                       for row in rows)
    if pinned_count:
        blockers.append("PINNED_RELEASE_ANCESTRY_OR_BACKPORT_NOT_PROVEN")
    if not rows:
        blockers.append("NO_MATCHING_EVIDENCE_IN_BOUNDED_READ_WINDOW")
    else:
        blockers.extend((
            "EXACT_UPSTREAM_VERSION_APPLICABILITY_NOT_VERIFIED",
            "PER_REVISION_SOURCE_RIGHTS_NOT_REVIEWED_FOR_EXPORT",
            "INDEPENDENT_EVIDENCE_QA_NOT_ATTESTED",
        ))
    return {
        "schema": "UCIE_P9_SOURCE_VERSION_RIGHTS_QA_READINESS_V1",
        "status": "INSPECTED_EVIDENCE_PENDING_REVIEW_NO_GO",
        "scope": "CURRENT_FILTERED_READ_WINDOWS_ONLY",
        "public_reader_source_linked": public_linked,
        "official_reader_available": official_available,
        "public_window_count": len(public["items"]),
        "official_window_count": len(official["items"]),
        "readiness_record_count": len(rows),
        "pinned_public_revision_observations_in_window": pinned_count,
        "public_revision_observation_scope": "THREE_EXACT_PUBLIC_PR_MERGE_SHAS_ONLY",
        "source_window_truncated": (
            (public.get("omitted_count", 0) > 0)
            or (official.get("omitted_count", 0) > 0)),
        "full_public_universe_inspected": False,
        "rows": rows,
        "review_blockers": blockers,
        "all_required_evidence_accepted": False,
        "new_authorizations": 0,
        "independent_verification_executed_here": False,
        "network_requests": 0,
        "database_writes": 0,
        "auto_promoted": False,
        "v1_accepted": False,
    }


def integrated_product_preview(root: Path, *, query: str = "",
                               domain: str | None = None,
                               limit: int = 5,
                               include_demo: bool = False,
                               signed_serial4: Path | None = None,
                               owner_public_trust: Path | None = None,
                               signed_serial5: Path | None = None,
                               select_item_id: str | None = None) -> dict:
    """Read all UCIE-owned shelves without assuming any one shelf is V1 PASS."""
    _root(root)
    if type(include_demo) is not bool:
        raise ProductIntegrationError("invalid demo request")
    if (signed_serial4 is None) != (owner_public_trust is None):
        raise ProductIntegrationError("existing signed pack and public trust must be paired")
    if signed_serial5 is not None and signed_serial4 is None:
        raise ProductIntegrationError("signed serial5 cannot stand alone")
    sources = preview_source_registry(include_research=False)
    public = search_existing_public_library(
        root, query=query, domain=domain, limit=limit, group_revisions=True)
    portable_handoff = _portable_public_ledger_handoff(public, limit=limit)
    official = search_official_metadata_shelf(root, limit=limit)
    p8 = experience_library_preview(root)
    w05 = read_capability_history(root, limit=limit)
    # Signed Rulepack inspection is an OPTIONAL feature. Do not load its
    # Serial5 verifier unless the user explicitly supplies pack/trust files.
    # Some existing UCIE Windows checkouts lack fifth_owner_addendum.py;
    # public library and portable first-party demo must still be usable.
    signed = None
    if signed_serial4 is not None:
        try:
            from .signed_rule_library import inspect_signed_library
        except ModuleNotFoundError as exc:
            raise ProductIntegrationError(
                "EXPLICIT_SIGNED_RULEPACK_VERIFIER_DEPENDENCY_MISSING_NO_GO"
            ) from exc
        signed = inspect_signed_library(
            root, serial4_pack=signed_serial4,
            owner_public_trust=owner_public_trust,
            serial5_pack=signed_serial5)
    standalone_demo = portable_consumer_check() if include_demo else None
    synthetic_trials = (
        [evaluate_ucie_owned_recipe(purpose) for purpose in (
            "ENGINE_INCREMENTAL_BUILD", "SKILL_TEST_AUTOMATION",
            "LEARNING_FEEDBACK_LOOP")] if include_demo else None)
    catalog = _bounded_catalog_view(
        query=query, domain=domain, limit=limit, public=public,
        official=official, signed=signed, p8=p8, w05=w05)
    comparison = _compare_existing_capability_experiences(
        history=w05, query=query, domain=domain, limit=limit)
    revision_review = _revision_review_queue(p8=p8, w05=w05, limit=limit)
    review_links = {
        item["source_library_item_id"]: item["proposal_id"]
        for item in revision_review["items"]
    }
    for item in catalog["items"]:
        if item["shelf"] in (
                "UCIE_SYNTHETIC_EXPERIENCE",
                "UCIE_CANDIDATE_TRIAL_EXPERIENCE"):
            item["revision_review_proposal_id"] = review_links.get(
                item["library_item_id"])
    evidence_readiness = _evidence_readiness(
        sources=sources, public=public, official=official, limit=limit)
    reuse = _reuse_eligibility(
        catalog=catalog, signed=signed, selected_item_id=select_item_id)
    public_ok = public["status"] == "READ_ONLY_UNVERIFIED_LIBRARY_SEARCH_NO_GO"
    official_ok = official["status"] == "STAGE14_OFFICIAL_METADATA_READ_ONLY_UNVERIFIED_NO_GO"
    # A missing local official ledger remains a transparent blocker, never a
    # silent success. Passing the synthetic demo does NOT release a package.
    blockers = []
    if not public_ok:
        blockers.append("SOURCE_LINKED_W04_LEDGER_UNAVAILABLE_OR_UNVERIFIED")
    if not official_ok:
        blockers.append("STAGE14_OFFICIAL_METADATA_NOT_READY")
    if signed is None:
        blockers.append("SIGNED_RULEPACK_OR_PUBLIC_TRUST_NOT_SUPPLIED")
    blockers.extend(evidence_readiness["review_blockers"])
    blockers.extend((
        "INDEPENDENT_PACKAGE_QA_NOT_ATTESTED",
        "PORTABLE_DRAFT_NOT_OWNER_APPROVED_FOR_RELEASE",
        "W05_UPSTREAM_CAPABILITY_NOT_VERIFIED",
        "P9_FULL_ACCEPTANCE_NOT_OBSERVED",
    ))
    return {
        "schema": SCHEMA, "status": "P9_INTEGRATED_READ_ONLY_PRODUCT_PREVIEW_NO_GO",
        "product": "UCIE_PRIVATE_FIRST_PARTY_PREVIEW",
        "source_registry": {
            "schema": sources["schema"],
            "approved_source_count": sources["active_source_count"],
            "source_allowlist_changed": False,
        },
        "unified_catalog_search": catalog,
        "reuse_eligibility": reuse,
        "source_version_rights_qa_readiness": evidence_readiness,
        "source_linked_portable_handoff": portable_handoff,
        "capability_experience_comparison": comparison,
        "library_revision_review_queue": revision_review,
        "public_candidate_library": public,
        "official_public_metadata_library": official,
        "signed_rules": {
            "status": ("EXISTING_OWNER_SIGNED_VERIFIED_READ_ONLY"
                       if signed is not None else "NOT_INSPECTED_NO_GO"),
            "verified_signed_rule_count": (
                signed["signed_rule_count"] if signed is not None else 0),
            "independent_qa_signed_off": False,
            "source_pack_metadata": (
                signed["source_pack_sha256s"] if signed is not None else {}),
        },
        "p8_owned_synthetic_experience": {
            "status": p8["status"],
            "recorded_experiments": p8["recorded_experiments"],
            "last_event_sha256": p8["last_event_sha256"],
            "next_unexecuted_workload": p8["next_unexecuted_workload"],
        },
        "w05_candidate_linked_experience": {
            "status": w05["status"],
            "recorded_count": w05["recorded_count"],
            "last_event_sha256": w05["last_event_sha256"],
        },
        "portable_first_party_consumer_demo": standalone_demo,
        "first_party_synthetic_experiments": synthetic_trials,
        "gates_blocking_product_acceptance": blockers,
        "default_live_public_fetch_enabled": False,
        "operating_database_writes": 0,
        "new_experience_writes": 0,
        "network_requests": 0, "new_signatures_created": 0,
        "scheduler_registered": False, "model_weights_changed": False,
        "candidate_auto_promoted": False,
        "package_released": False, "v1_accepted": False,
    }


def _portable_source() -> bytes:
    path = Path(__file__).with_name("portable_exact.py")
    if path.is_symlink() or not path.is_file():
        raise ProductIntegrationError("unsafe first-party portable source")
    source = path.read_bytes()
    if not 0 < len(source) <= MAX_SOURCE_BYTES:
        raise ProductIntegrationError("portable source changed or too large")
    if not source.startswith(b'"""UCIE-authored portable exact metadata lookup V1.'):
        raise ProductIntegrationError("unrecognized first-party portable source")
    return source


def build_draft_package_bytes() -> tuple[bytes, dict]:
    """No write. Produce deterministic UCIE-authored DRAFT, never a signed release."""
    source = _portable_source()
    fingerprint = sha256(source).hexdigest()
    manifest = {
        "schema": PACK_SCHEMA,
        "package_id": "UCIE_PORTABLE_EXACT_PUBLIC_METADATA",
        "version": "1.1.0",
        "code_file": "portable_exact.py",
        "consumer_api_version": CONSUMER_VERSION,
        "supported_unverified_metadata_kinds": sorted(CONSUMER_KINDS),
        "code_sha256": fingerprint,
        "runtime_dependency": "PYTHON_STANDARD_LIBRARY_ONLY",
        "tested_platform_claim": "NOT_INDEPENDENTLY_ATTESTED",
        "upstream_public_code_included": False,
        "user_project_data_included": False,
        "api_keys_or_credentials_included": False,
        "source_license_signoff": False,
        "owner_release_authorized": False,
        "independent_qa_signed_off": False,
        "signed": False,
        "status": "DRAFT_FIRST_PARTY_CONSUMER_NOT_APPROVED_FOR_DISTRIBUTION",
    }
    readme = (
        "UCIE AUTHORED DRAFT - NOT RELEASED, NOT LICENSE ATTESTED\n"
        "Python standard library only. This bundle contains no third-party\n"
        "PR code, user project data, keys, or verified upstream skills.\n"
        "Only sanitized approved public-source metadata accepted by\n"
        "search_public_metadata(items, queries=tuple_of_exact_four_field_keys).\n"
        "Engine, skill and learning-logic records are UNVERIFIED METADATA.\n"
        "No source import, upstream code execution or endorsement.\n"
        "This draft cannot claim package release/signature/third-party QA.\n"
    ).encode("ascii")
    in_mem = io.BytesIO()
    with ZipFile(in_mem, "w", compression=ZIP_DEFLATED) as z:
        for name, data in (
            ("portable_exact.py", source),
            ("MANIFEST.json", json.dumps(
                manifest, sort_keys=True, separators=(",", ":")).encode("ascii")),
            ("README.txt", readme),
        ):
            info = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    payload = in_mem.getvalue()
    if len(payload) > MAX_ZIP_BYTES:
        raise ProductIntegrationError("draft package exceeds bound")
    return payload, manifest


def verify_existing_draft(root: Path) -> dict:
    """Read-only byte-for-byte verification against UCIE's canonical draft.

    No signature or external provenance is inferred from a matching hash.
    This deliberately accepts only the current first-party package version.
    """
    _root(root)
    export_dir = root / "runtime" / "exports"
    target = export_dir / PACKAGE_NAME
    if (export_dir.is_symlink() or not export_dir.is_dir()
            or target.is_symlink() or not target.is_file()):
        raise ProductIntegrationError("UCIE-local canonical draft is missing or unsafe")
    size = target.stat().st_size
    if not 0 < size <= MAX_ZIP_BYTES:
        raise ProductIntegrationError("UCIE-local draft exceeds bounded size")
    actual = target.read_bytes()
    expected, manifest = build_draft_package_bytes()
    if actual != expected:
        raise ProductIntegrationError("UCIE-local draft bytes differ from current source")
    return {
        "schema": PACK_SCHEMA,
        "status": "UCIE_LOCAL_DRAFT_BYTES_VERIFIED_NOT_RELEASED",
        "relative_path": "runtime/exports/" + PACKAGE_NAME,
        "version": manifest["version"],
        "consumer_api_version": manifest["consumer_api_version"],
        "supported_unverified_metadata_kinds":
            manifest["supported_unverified_metadata_kinds"],
        "sha256": sha256(actual).hexdigest(),
        "code_sha256": manifest["code_sha256"],
        "canonical_local_source_match": True,
        "independent_signature_verified": False,
        "independent_consumer_qa_attested": False,
        "production_release_approved": False,
        "source_rights_independently_reviewed": False,
        "operating_database_writes": 0,
        "network_requests": 0,
        "new_signatures_created": 0,
        "auto_promoted": False,
        "v1_accepted": False,
    }


def explicitly_export_draft(root: Path) -> dict:
    """Explicit local-only draft, NO production install or third-party distribution."""
    _root(root)
    payload, manifest = build_draft_package_bytes()
    dest = root / "runtime" / "exports"
    if dest.is_symlink():
        raise ProductIntegrationError("unsafe exports path")
    if not dest.exists():
        dest.mkdir(mode=0o700)
    if not dest.is_dir():
        raise ProductIntegrationError("exports path must be a UCIE directory")
    target = dest / PACKAGE_NAME
    if target.is_symlink():
        raise ProductIntegrationError("unsafe package link")
    content_hash = sha256(payload).hexdigest()
    if target.exists():
        if not target.is_file() or target.read_bytes() != payload:
            raise ProductIntegrationError("cannot overwrite existing draft package")
        written = False
    else:
        try:
            with target.open("xb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError as exc:
            raise ProductIntegrationError("draft created by another writer") from exc
        written = True
    return {
        "schema": PACK_SCHEMA,
        "status": "UCIE_ONLY_DRAFT_WRITTEN_NOT_RELEASED" if written else
                  "SAME_UCIE_ONLY_DRAFT_ALREADY_PRESENT_NOT_RELEASED",
        "relative_path": "runtime/exports/" + PACKAGE_NAME,
        "sha256": content_hash,
        "code_sha256": manifest["code_sha256"],
        "created": written, "production_release_approved": False,
        "standalone_consumer_qa_attested": False,
        "upstream_source_code_copied": False, "other_project_data_accessed": False,
        "operating_database_writes": 0, "network_requests": 0,
        "new_signatures_created": 0, "auto_promoted": False,
        "v1_accepted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UCIE P9 single read-only product entrypoint and opt-in UCIE-owned draft export")
    parser.add_argument("--ucie-root", type=Path, required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--domain")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--serial4-pack", type=Path)
    parser.add_argument("--owner-public-trust", type=Path)
    parser.add_argument("--serial5-pack", type=Path)
    parser.add_argument("--select-item", dest="select_item_id",
                        help="Exact 64-char library ID in the bounded query window")
    parser.add_argument("--export-draft", action="store_true",
                        help="Explicitly write ONE UCIE-only draft zip (not a release)")
    parser.add_argument("--verify-draft", action="store_true",
                        help="Verify existing local draft against exact current UCIE source; no writes")
    args = parser.parse_args()
    try:
        if args.export_draft or args.verify_draft:
            if (args.export_draft and args.verify_draft or
                    args.query or args.domain or args.demo or args.serial4_pack or
                    args.owner_public_trust or args.serial5_pack
                    or args.select_item_id is not None or args.limit != 5):
                raise ProductIntegrationError("draft operation cannot combine other flags")
            out = (explicitly_export_draft(args.ucie_root) if args.export_draft
                   else verify_existing_draft(args.ucie_root))
        else:
            out = integrated_product_preview(
                args.ucie_root, query=args.query, domain=args.domain,
                limit=args.limit, include_demo=args.demo,
                signed_serial4=args.serial4_pack,
                owner_public_trust=args.owner_public_trust,
                signed_serial5=args.serial5_pack,
                select_item_id=args.select_item_id)
    except (ValueError, OSError) as exc:
        print(json.dumps({
            "schema": SCHEMA, "status": "P9_PRODUCT_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "network_requests": 0, "operating_database_writes": 0,
            "package_released": False, "v1_accepted": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(out, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
