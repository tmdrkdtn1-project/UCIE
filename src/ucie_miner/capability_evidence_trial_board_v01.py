"""UCIE W05/W08 first-party measurement board, separate from PR title cues.

Measures ONLY UCIE-authored exact-key index work on the already source-
linked PUBLIC METADATA catalog, using existing P8 benchmark. Never
attributes that result to an upstream engine/skill candidate or claims
actual skill quality, version applicability, security remediation or
production permission. Optional W05 candidates are OFFLINE cues only.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from .experience_application import (
    SCHEMA as P8_SCHEMA, benchmark_existing_ucie_public_catalog,
    MIN_QUERIES, MAX_QUERIES, MAX_REPEATS,
)
from .positive_capability_discovery import (
    SCHEMA as W05_SCHEMA, classify_public_capability_metadata,
)
from .public_source_adapter import adapter_plan

SCHEMA = "UCIE_W05_W08_FIRST_PARTY_EVIDENCE_TRIAL_BOARD_V01"
REQUIREMENTS = (
    "SOURCE_REVISION_EXACT_SHA_ATTESTED",
    "SOURCE_LICENSE_AND_REDISTRIBUTION_REVIEW",
    "FIRST_PARTY_CANDIDATE_IMPLEMENTATION_REVIEW",
    "BASELINE_AND_CANDIDATE_SAME_WORKLOAD_TEST",
    "NEGATIVE_SECURITY_AND_REGRESSION_TESTS",
    "INDEPENDENT_QA_AND_EXPLICIT_OWNER_APPROVAL",
)


class CapabilityTrialBoardError(ValueError):
    pass


def evaluation_board(root: Path, *, positive_snapshot: dict | None = None,
                     now: datetime | None = None,
                     queries: int = 32, repeats: int = 3) -> dict:
    if (type(queries) is not int
            or not MIN_QUERIES <= queries <= MAX_QUERIES
            or type(repeats) is not int or not 1 <= repeats <= MAX_REPEATS
            or not isinstance(root, Path)
            or root.is_symlink() or root.name.casefold() != "ucie"
            or not root.is_dir()):
        raise CapabilityTrialBoardError("bounded dedicated UCIE evaluation required")
    hypotheses = []
    source_id = None
    if positive_snapshot is not None:
        if (type(positive_snapshot) is not dict
                or set(positive_snapshot) != {"source_id", "rows"}
                or type(positive_snapshot["source_id"]) is not str
                or type(positive_snapshot["rows"]) is not list
                or len(positive_snapshot["rows"]) > 20):
            raise CapabilityTrialBoardError("only one approved offline public snapshot")
        source_id = positive_snapshot["source_id"]
        p = adapter_plan(source_id)
        if (p.get("registry_grants_network_permission") is not False
                or p.get("transport_invoked") is not False
                or p.get("persistent_writes") != 0):
            raise CapabilityTrialBoardError("W03 source adapter drift")
        classification = classify_public_capability_metadata(
            positive_snapshot["rows"],source_id=source_id,now=now)
        if (classification.get("schema") != W05_SCHEMA
                or classification.get("status") !=
                "POSITIVE_CAPABILITY_HINTS_UNVERIFIED_NO_GO"
                or classification.get("database_writes") != 0
                or classification.get("network_requests") != 0
                or classification.get("model_weights_changed") is not False
                or classification.get("auto_promoted") is not False
                or classification.get("candidate_count") != len(
                    classification.get("candidates", []))):
            raise CapabilityTrialBoardError("W05 classification not trustworthy")
        for row in classification["candidates"]:
            if (row.get("evidence_strength") != "MERGED_PR_TITLE_CUE_ONLY"
                    or row.get("actual_capability_verified") is not False
                    or row.get("benefit_measured") is not False
                    or row.get("export_allowed") is not False
                    or row.get("license_independently_reviewed") is not False):
                raise CapabilityTrialBoardError("unverified title cue falsely approved")
            hypotheses.append({
                "library_item_id":row["library_item_id"],
                "source_id":row["source_id"],"kind":row["kind"],
                "public_url":row["public_url"],
                "merge_commit_sha":row["merge_commit_sha"],
                "evidence_sha256":row["evidence_sha256"],
                "candidate_evidence_level":"MERGED_PR_TITLE_CUE_ONLY",
                "candidate_benefit_measured":False,
                "source_license_verified":False,
                "ready_for_adoption":False,
            })
    benchmark = benchmark_existing_ucie_public_catalog(
        root,queries=queries,repeats=repeats)
    if (benchmark.get("schema") != P8_SCHEMA
            or benchmark.get("network_requests") != 0
            or benchmark.get("operating_database_writes") != 0
            or benchmark.get("production_index_applied") is not False
            or benchmark.get("v1_accepted") is not False):
        raise CapabilityTrialBoardError("first-party P8 read-only benchmark drift")
    eligible = (benchmark.get("status") ==
                "REAL_PUBLIC_METADATA_EXACT_QUERY_EQUIVALENT_UNAPPROVED")
    if eligible and (type(benchmark.get("real_public_catalog_items")) is not int
                     or benchmark["real_public_catalog_items"] < 1
                     or benchmark.get("mismatched_query_results") != 0
                     or benchmark.get("full_w04_substring_search_benchmarked") is not False
                     or benchmark.get("upstream_code_executed") is not False
                     or benchmark.get("automatic_learning_or_promotion") is not False
                     or benchmark.get("approved_or_exportable_items") != 0):
        raise CapabilityTrialBoardError("P8 exact-key result scope drift")
    summary = ({
        "scope":"UCIE_OWNED_EXACT_KEY_INDEX_VS_LINEAR_ON_LINKED_METADATA",
        "status":benchmark["status"],
        "real_public_metadata_rows":benchmark["real_public_catalog_items"],
        "queries":benchmark["query_count"],
        "repeats":benchmark["repetitions"],
        "mismatched_query_results":benchmark["mismatched_query_results"],
        "baseline_scan_operations":benchmark["baseline_scan_operations"],
        "candidate_index_build_and_lookup_operations":
            benchmark["candidate_index_build_and_lookup_operations"],
        "operation_reduction":benchmark["operation_reduction"],
        "time_guaranteed_faster":False,
        "full_library_search_speed_verified":False,
        "external_upstream_candidate_tested":False,
        "production_index_applied":False,
    } if eligible else {
        "scope":"UCIE_OWNED_EXACT_KEY_INDEX_VS_LINEAR_ON_LINKED_METADATA",
        "status":benchmark["status"],
        "real_public_metadata_rows":0,
        "upstream_candidate_tested":False,
        "operation_reduction":None,
        "production_index_applied":False,
    })
    return {
        "schema":SCHEMA,
        "status":("FIRST_PARTY_EXACT_KEY_BENCHMARK_REVIEW_ONLY"
                  if eligible else "P8_SOURCE_LINKAGE_INCOMPLETE_NO_GO"),
        "w05_source_id":source_id,
        "w05_candidates_loaded_from":"IN_MEMORY_OFFLINE_UNVERIFIED"
            if positive_snapshot is not None else "NONE_NOT_A_ZERO_CAPABILITY_CLAIM",
        "w05_unverified_hypotheses":hypotheses,
        "w05_hypothesis_count":len(hypotheses),
        "w05_required_real_candidate_gates":list(REQUIREMENTS),
        "first_party_catalog_benchmark":summary,
        "w05_candidate_benefit_measured":False,
        "upstream_source_code_executed":False,
        "upstream_revision_or_license_approved":False,
        "w05_candidate_promoted":False,
        "network_requests":0,"operating_database_writes":0,
        "model_weights_changed":False,"auto_promoted":False,
        "v1_accepted":False,"customer_release_authorized":False,
    }


def main() -> int:
    p=argparse.ArgumentParser(description="UCIE W05 external-vs-local improvement evidence")
    p.add_argument("--queries",type=int,default=32)
    p.add_argument("--repeats",type=int,default=3)
    a=p.parse_args()
    try:
        result=evaluation_board(
            Path(__file__).resolve().parents[2],
            queries=a.queries,repeats=a.repeats)
    except (ValueError,OSError) as exc:
        print(json.dumps({
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "error_type":type(exc).__name__,
            "network_requests":0,"operating_database_writes":0,
            "customer_release_authorized":False,
        },sort_keys=True))
        return 2
    print(json.dumps(result,sort_keys=True,ensure_ascii=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
