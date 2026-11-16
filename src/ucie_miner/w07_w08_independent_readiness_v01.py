"""UCIE W07/W08 read-only admission-preflight, NEVER a rule approval.

Reuses the actual W07 Serial4/5 signed-package verifiers and the W05/P8
real-public-metadata benchmark; independently checks a bounded UCIE-owned
held-out exact-key casebook. A cryptographic signature is NOT a license
signoff, independent QA approval, general-purpose skill or release permit.

No public GET, external source execution, model updates, signer access,
database writes, automatic rule promotion or scheduler changes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from .capability_evidence_trial_board_v01 import (
    SCHEMA as BOARD_SCHEMA, evaluation_board, REQUIREMENTS,
)
from .capability_evaluator import (
    CatalogItem, CatalogQuery, build_exact_index, indexed_search,
)
from .signed_rule_library import (
    SCHEMA as SIGNED_SCHEMA, SignedLibraryError, inspect_signed_library,
    ALLOWED_RULES, RULE_ORDER, RULE_ID,
)

SCHEMA = "UCIE_W07_W08_INDEPENDENT_READINESS_READONLY_V01"
CLOSED = "W07_W08_READ_ONLY_QA_REVIEW_REQUIRED_NO_GO"
PARTIAL = "W07_W08_SOURCE_OR_BENCHMARK_INCOMPLETE_NO_GO"
SHA = re.compile(r"[a-f0-9]{64}\Z")
EXPECTED_PACK_STATES = {"EXISTING_OWNER_SIGNED_RULEPACKS_VERIFIED_READ_ONLY"}
MISSING_SIGNOFFS = (
    "INDEPENDENT_HUMAN_QA_ON_EXACT_RULE_AND_SUPPORTED_VERSIONS",
    "RULE_SPECIFIC_REGRESSION_AND_NEGATIVE_SECURITY_VALIDATION",
    "SOURCE_PIN_VERSION_AND_LICENSE_SIGNOFF",
    "OWNER_EXPLICIT_RELEASE_APPROVAL",
    "PRODUCTION_HOST_AND_CONSUMER_REVERIFICATION",
)


class ReadinessError(ValueError):
    """Wrong first-party evidence scope or a safety/identity drift."""


def _heldout_exact_key_oracle() -> dict:
    """Independent manually specified oracle on UCIE-authored in-memory data.

    These are synthetic identifiers only; they are not real public PR rows,
    not a test of the full substring search and not an external code trial.
    """
    records = (
        CatalogItem("S001", "repo:python/cpython", "PYTHON", "REUSABLE_SKILL", "TEST"),
        CatalogItem("S002", "repo:python/cpython", "PYTHON", "REUSABLE_SKILL", "TEST"),
        CatalogItem("S003", "repo:python/cpython", "PYTHON", "DEVELOPMENT_ENGINE", "TEST"),
        CatalogItem("S004", "repo:PowerShell/PowerShell", "POWERSHELL", "REUSABLE_SKILL", "TEST"),
        CatalogItem("S005", "repo:git/git", "GIT", "LEARNING_LOGIC", "TRACE"),
        CatalogItem("S006", "repo:git/git", "GIT", "LEARNING_LOGIC", "TRACE"),
        CatalogItem("S007", "repo:actions/runner-images", "CI", "REUSABLE_SKILL", "TEST"),
        CatalogItem("S008", "repo:modelcontextprotocol/python-sdk", "MCP", "REUSABLE_SKILL", "API"),
    )
    # Explicit expected IDs are intentionally independent from the index
    # implementation. Include duplicate-key collisions and negative cases.
    cases = (
        (CatalogQuery("repo:python/cpython", "PYTHON", "REUSABLE_SKILL", "TEST"), ("S001","S002")),
        (CatalogQuery("repo:python/cpython", "PYTHON", "DEVELOPMENT_ENGINE", "TEST"), ("S003",)),
        (CatalogQuery("repo:git/git", "GIT", "LEARNING_LOGIC", "TRACE"), ("S005","S006")),
        (CatalogQuery("repo:PowerShell/PowerShell", "POWERSHELL", "REUSABLE_SKILL", "TEST"), ("S004",)),
        (CatalogQuery("repo:actions/runner-images", "CI", "REUSABLE_SKILL", "TEST"), ("S007",)),
        (CatalogQuery("repo:modelcontextprotocol/python-sdk", "MCP", "REUSABLE_SKILL", "API"), ("S008",)),
        (CatalogQuery("repo:python/cpython", "PYTHON", "REUSABLE_SKILL", "ABSENT"), ()),
        (CatalogQuery("repo:git/git", "PYTHON", "LEARNING_LOGIC", "TRACE"), ()),
        (CatalogQuery("repo:unapproved/stranger", "GIT", "LEARNING_LOGIC", "TRACE"), ()),
    )
    index, built = build_exact_index(records)
    if (type(built) is not int or built != len(records)
            or type(index) is not dict):
        raise ReadinessError("UCIE index construction contract drift")
    mismatches = 0
    for query, expected in cases:
        # Independent linear reference, a second oracle beyond the declared
        # expected tuple. This catches swapped source keys and bad grouping.
        actual_reference = tuple(
            row.synthetic_id for row in records
            if (row.source_id, row.domain, row.kind, row.purpose) ==
               (query.source_id, query.domain, query.kind, query.purpose))
        indexed, steps = indexed_search(index, query)
        if (actual_reference != expected or indexed != expected
                or type(steps) is not int or steps != 1):
            mismatches += 1
    if mismatches:
        raise ReadinessError("held-out exact-key index regression detected")
    payload = [[r.synthetic_id,r.source_id,r.domain,r.kind,r.purpose]
               for r in records]
    payload.extend(
        [[q.source_id,q.domain,q.kind,q.purpose,*ids]
         for q,ids in cases])
    return {
        "scope": "UCIE_AUTHORED_DETERMINISTIC_HELDOUT_EXACT_KEY_ORACLE_ONLY",
        "casebook_sha256": sha256(json.dumps(
            payload, separators=(",",":"), ensure_ascii=True).encode("ascii")
        ).hexdigest(),
        "synthetic_record_count":len(records),
        "heldout_query_count":len(cases),
        "negative_query_count":sum(not ids for _,ids in cases),
        "duplicate_exact_key_cases_included":True,
        "mismatched_expected_results":0,
        "untrusted_upstream_code_executed":False,
        "independent_human_qa_approved":False,
    }


def _checked_real_benchmark(root: Path, *, queries: int, repeats: int) -> dict:
    evidence = evaluation_board(root, queries=queries, repeats=repeats)
    if (type(evidence) is not dict
            or evidence.get("schema") != BOARD_SCHEMA
            or evidence.get("network_requests") != 0
            or evidence.get("operating_database_writes") != 0
            or evidence.get("model_weights_changed") is not False
            or evidence.get("auto_promoted") is not False
            or evidence.get("customer_release_authorized") is not False
            or evidence.get("w05_candidate_benefit_measured") is not False
            or evidence.get("w05_candidate_promoted") is not False
            or evidence.get("w05_hypothesis_count") != 0
            or evidence.get("w05_candidates_loaded_from") !=
                "NONE_NOT_A_ZERO_CAPABILITY_CLAIM"
            or evidence.get("w05_required_real_candidate_gates") != list(REQUIREMENTS)
            or evidence.get("status") not in (
                "FIRST_PARTY_EXACT_KEY_BENCHMARK_REVIEW_ONLY",
                "P8_SOURCE_LINKAGE_INCOMPLETE_NO_GO")):
        raise ReadinessError("W05/P8 first-party evaluation trust scope drift")
    first=evidence["first_party_catalog_benchmark"]
    ok=evidence["status"]=="FIRST_PARTY_EXACT_KEY_BENCHMARK_REVIEW_ONLY"
    if ok:
        rows=first.get("real_public_metadata_rows")
        baseline=first.get("baseline_scan_operations")
        indexed=first.get("candidate_index_build_and_lookup_operations")
        reduction=first.get("operation_reduction")
        if (first.get("scope") !=
              "UCIE_OWNED_EXACT_KEY_INDEX_VS_LINEAR_ON_LINKED_METADATA"
                or first.get("status") !=
                    "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED"
                or type(rows) is not int or rows < 1
                or type(baseline) is not int or baseline != rows*queries
                or type(indexed) is not int or indexed != rows+queries
                or type(reduction) is not int or reduction != baseline-indexed
                or reduction <= 0
                or first.get("mismatched_query_results") != 0
                or first.get("queries") != queries
                or first.get("repeats") != repeats
                or first.get("full_library_search_speed_verified") is not False
                or first.get("time_guaranteed_faster") is not False
                or first.get("external_upstream_candidate_tested") is not False
                or first.get("production_index_applied") is not False):
            raise ReadinessError("forged or inconsistent real first-party P8 counts")
    else:
        if (first.get("operation_reduction") is not None
                or first.get("production_index_applied") is not False):
            raise ReadinessError("unlinked P8 cannot carry a measured gain")
    return {
        "status":evidence["status"],
        "only_first_party_exact_key_workload_tested":True,
        "source_linkage_present":ok,
        "metadata_rows":first.get("real_public_metadata_rows") if ok else None,
        "queries":queries,"repeats":repeats,
        "reference_operations":first.get("baseline_scan_operations") if ok else None,
        "index_build_and_lookup_operations":first.get(
            "candidate_index_build_and_lookup_operations") if ok else None,
        "reduction_in_operation_count":first.get("operation_reduction") if ok else None,
        "exact_result_mismatches":0 if ok else None,
        "full_library_search_speed_verified":False,
        "upstream_candidate_benefit_measured":False,
        "production_index_applied":False,
    }


def _checked_signed_rules(root: Path, *, serial4_pack: Path | None,
                          owner_public_trust: Path | None,
                          serial5_pack: Path | None) -> dict:
    if serial4_pack is None and owner_public_trust is None and serial5_pack is None:
        return {
            "status":"EXACT_SIGNED_PACKS_NOT_SUPPLIED_NO_GO",
            "original_crypto_reverified":False,
            "verified_manual_rule_references":0,
            "rule_ids":[],"source_pack_sha256s":{},
        }
    if (not isinstance(serial4_pack,Path)
            or not isinstance(owner_public_trust,Path)
            or serial5_pack is not None and not isinstance(serial5_pack,Path)):
        raise ReadinessError("signed rule verification requires exact two owner file paths")
    signed=inspect_signed_library(
        root, serial4_pack=serial4_pack,
        owner_public_trust=owner_public_trust,
        serial5_pack=serial5_pack)
    items=signed.get("items")
    hashes=signed.get("source_pack_sha256s")
    if (signed.get("schema")!=SIGNED_SCHEMA
            or signed.get("status") not in EXPECTED_PACK_STATES
            or signed.get("network_requests")!=0
            or signed.get("database_writes")!=0
            or signed.get("new_release_approved") is not False
            or signed.get("v1_library_accepted") is not False
            or signed.get("private_signing_key_accessed") is not False
            or signed.get("new_signatures_created")!=0
            or signed.get("unsigned_candidate_records_imported")!=0
            or type(items) is not list or len(items) not in (4,5)
            or signed.get("signed_rule_count")!=len(items)
            or type(hashes) is not dict
            or type(hashes.get("serial4")) is not str
            or SHA.fullmatch(hashes["serial4"]) is None):
        raise ReadinessError("first-party original signature verifier contract drift")
    expected_ids=list(RULE_ORDER)+([RULE_ID] if len(items)==5 else [])
    if [row.get("rule_id") for row in items] != expected_ids:
        raise ReadinessError("exact Serial4/5 rule order changed")
    expected_hash_keys={"serial4"} | (
        {"serial5_addendum"} if len(items)==5 else set())
    if (set(hashes)!=expected_hash_keys
            or any(type(value) is not str or SHA.fullmatch(value) is None
                   for value in hashes.values())):
        raise ReadinessError("signed owner package digest set drift")
    for row in items:
        if type(row) is not dict:
            raise ReadinessError("invalid signed Rulepack row")
        serial=row.get("pack_serial")
        if serial not in (4,5) or type(serial) is not int:
            raise ReadinessError("unknown signed Rulepack serial")
        dig=hashes["serial4"] if serial==4 else hashes.get("serial5_addendum")
        if (row.get("rule_id") not in ALLOWED_RULES or dig is None
                or row.get("source_package_sha256")!=dig
                or row.get("item_id")!=sha256(
                    (row["rule_id"]+":"+dig).encode("ascii")).hexdigest()
                or (serial==5 and (
                    row.get("parent_serial")!=4 or
                    row.get("parent_package_sha256")!=hashes["serial4"]))
                or row.get("verification")!="OWNER_SIGNED_VERIFIED_AT_INSPECTION_TIME"
                or row.get("approval_basis")!="OWNER_RISK_ACCEPTED_CI_ONLY"
                or row.get("independent_qa_approved") is not False
                or row.get("license_signoff") is not False
                or row.get("new_package_export_allowed") is not False
                or row.get("unattended_execution_allowed") is not False):
            raise ReadinessError("signed rule source hash/QA claim drift")
    return {
        "status":"EXISTING_MANUAL_RULE_SIGNATURES_REVERIFIED_QA_STILL_REQUIRED",
        "original_crypto_reverified":True,
        "verified_manual_rule_references":len(items),
        "rule_ids":[row["rule_id"] for row in items],
        "source_pack_sha256s":hashes,
    }


def independent_review_board(
        root: Path, *, queries: int=32, repeats: int=3,
        serial4_pack: Path | None=None,
        owner_public_trust: Path | None=None,
        serial5_pack: Path | None=None) -> dict:
    """Perform fresh UCIE-owned observation; never accept caller QA JSON."""
    if (not isinstance(root,Path) or root.is_symlink()
            or not root.is_dir() or root.name.casefold()!="ucie"
            or type(queries) is not int or not 8 <= queries <= 96
            or type(repeats) is not int or not 1 <= repeats <= 5):
        raise ReadinessError("bounded UCIE-only first-party review required")
    heldout=_heldout_exact_key_oracle()
    observed=_checked_real_benchmark(root,queries=queries,repeats=repeats)
    signed=_checked_signed_rules(
        root,serial4_pack=serial4_pack,
        owner_public_trust=owner_public_trust,serial5_pack=serial5_pack)
    complete=(observed["source_linkage_present"]
              and signed["original_crypto_reverified"])
    # This unsignable digest is for review correspondence only,
    # absolutely not an approval, a release token or a trust anchor.
    receipt_bytes=json.dumps({
        "schema":SCHEMA,
        "heldout_casebook_sha256":heldout["casebook_sha256"],
        "metadata_rows":observed["metadata_rows"],
        "queries":queries,"repeats":repeats,
        "reference_operations":observed["reference_operations"],
        "index_operations":observed["index_build_and_lookup_operations"],
        "signed_pack_sha256s":signed["source_pack_sha256s"],
        "rule_ids":signed["rule_ids"],
    },sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii")
    return {
        "schema":SCHEMA,
        "status":CLOSED if complete else PARTIAL,
        "first_party_independent_oracle":heldout,
        "real_metadata_benchmark":observed,
        "existing_w07_signed_manual_rule_references":signed,
        "qa_handoff_evidence_sha256":sha256(receipt_bytes).hexdigest(),
        "qa_handoff_digest_is_authorization":False,
        "independent_human_qa_approved":False,
        "rule_specific_supported_versions_qa_approved":False,
        "license_and_rights_signoff":False,
        "explicit_owner_new_release_approval":False,
        "remaining_release_gates":list(MISSING_SIGNOFFS),
        "unverified_rule_candidates_approved":0,
        "new_production_rulepack_signed":False,
        "new_generic_package_export_allowed":False,
        "automatic_rule_application_allowed":False,
        "network_requests":0,"operating_database_writes":0,
        "source_code_executed_from_public_repos":False,
        "model_weights_changed":False,"auto_promoted":False,
        "v1_accepted":False,"customer_release_authorized":False,
    }


def main()->int:
    parser=argparse.ArgumentParser(description="UCIE W07/W08 read-only QA admission board")
    parser.add_argument("--ucie-root",required=True,type=Path)
    parser.add_argument("--queries",type=int,default=32)
    parser.add_argument("--repeats",type=int,default=3)
    parser.add_argument("--serial4-pack",type=Path)
    parser.add_argument("--owner-public-trust",type=Path)
    parser.add_argument("--serial5-pack",type=Path)
    args=parser.parse_args()
    try:
        output=independent_review_board(
            args.ucie_root,queries=args.queries,repeats=args.repeats,
            serial4_pack=args.serial4_pack,
            owner_public_trust=args.owner_public_trust,
            serial5_pack=args.serial5_pack)
    except (ReadinessError,SignedLibraryError,OSError,ValueError) as exc:
        print(json.dumps({
            "schema":SCHEMA,"status":"READONLY_REVIEW_FAIL_CLOSED",
            "error_type":type(exc).__name__,
            "network_requests":0,"operating_database_writes":0,
            "new_generic_package_export_allowed":False,
            "customer_release_authorized":False,
        },sort_keys=True))
        return 2
    print(json.dumps(output,sort_keys=True,ensure_ascii=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
