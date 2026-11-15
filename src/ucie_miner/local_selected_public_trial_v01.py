"""UCIE owner Local V1: safe, source-selected public candidate -> first-party trial.

A W04 candidate is *real public provenance*, NOT a verified upstream fix.
Only two explicit first-party bounded demonstrations can be selected, and only
from an independently re-selected W04 review worksheet. Never uses a URL or
PR title as executable code, input, arbitrary path, author permission or
performance proof. No customer release, external network, or operating DB write.
"""
from __future__ import annotations

import re

from .local_v1_priority_v01 import require_local_work
from .local_v1_public_review_v01 import (
    SCHEMA as REVIEW_SCHEMA, ALLOWED_SOURCES,
)
from .rule_candidates import REQUIRED_GATES

SCHEMA = "UCIE_OWNER_SOURCE_SELECTED_FIRST_PARTY_TRIAL_V01"
STATUS = "RELATED_UCIE_SYNTHETIC_RESULT_NOT_UPSTREAM_VERIFICATION"
CASE_SCANDIR = "PYTHON_SCANDIR_GUARDED_FIRST_PARTY"
CASE_MCP = "MCP_PROMPTS_GET_FIXED_SYNTHETIC"
ID = re.compile(r"[0-9a-f]{64}\Z")


class SourceSelectedTrialError(ValueError):
    """Incomplete or mismatched evidence must not turn into a trial claim."""


def _checked_worksheet(brief: dict) -> None:
    require_local_work("ERROR_PREVENTION")
    if (type(brief) is not dict
            or brief.get("schema") != REVIEW_SCHEMA
            or brief.get("status") != "SOURCE_BOUND_MANUAL_REVIEW_DRAFT_NOT_APPROVED"
            or brief.get("source_id") not in ALLOWED_SOURCES
            or type(brief.get("library_item_id")) is not str
            or ID.fullmatch(brief["library_item_id"]) is None
            or type(brief.get("evidence_sha256")) is not str
            or ID.fullmatch(brief["evidence_sha256"]) is None
            or type(brief.get("pattern_code")) is not str
            or type(brief.get("public_url")) is not str
            or not brief["public_url"].startswith(
                "https://github.com/" + brief["source_id"][5:] + "/")
            or type(brief.get("required_gates")) is not dict
            or set(brief["required_gates"]) != set(REQUIRED_GATES)
            or any(v != "NOT_VERIFIED" for v in brief["required_gates"].values())
            or any(brief.get(flag) is not False for flag in (
                "regression_executed", "source_fix_independently_verified",
                "owner_approval_recorded", "automatic_rule_promotion",
                "upstream_code_executed", "customer_or_other_project_inspected",
                "export_allowed"))
            or brief.get("network_requests") != 0
            or brief.get("operating_database_writes") != 0):
        raise SourceSelectedTrialError("source-bound candidate review is not trustworthy")


def available_trial(brief: dict) -> dict:
    """Return a *related* UCIE trial, never PR-specific patch validation."""
    _checked_worksheet(brief)
    case = None
    source, pattern, url = (
        brief["source_id"], brief["pattern_code"], brief["public_url"])
    if (source == "repo:python/cpython"
            and pattern == "PY_SCANDIR_SHARED_ITERATOR_RACE"):
        case = CASE_SCANDIR
    elif source == "repo:modelcontextprotocol/python-sdk" and pattern == "API_CONTRACT":
        # MCP API-contract candidates share a TOPIC, not proven prompts/get
        # implementation. We offer one explicitly distinct reference example.
        case = CASE_MCP
    reference = None
    if case == CASE_SCANDIR:
        reference = "https://docs.python.org/3/library/os.html"
    elif case == CASE_MCP:
        from .mcp_prompt_regression_v01 import SOURCE_PR
        reference = SOURCE_PR
    return {
        "schema": SCHEMA,
        "status": STATUS if case else "NO_RELATED_APPROVED_FIRST_PARTY_TRIAL_AVAILABLE",
        "case": case,
        "available": case is not None,
        "illustrative_reference_url": reference,
        "same_exact_public_reference_as_example": (
            url == reference if reference is not None else False),
        "same_pattern_domain_only_not_same_fix_verified": True,
        "selected_public_candidate_id": brief["library_item_id"],
        "selected_public_candidate_url": url,
        "selected_public_evidence_sha256": brief["evidence_sha256"],
        "related_only_not_source_fix_verification": True,
        "external_code_executed": False,
        "source_fix_independently_verified": False,
        "regression_executed_on_upstream": False,
        "human_approved": False,
        "auto_promoted": False,
        "customer_distribution_authorized": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }


def run_selected_trial(brief: dict) -> dict:
    """Explicit user GET starts one safe UCIE-owned exercise only."""
    option = available_trial(brief)
    if not option["available"]:
        raise SourceSelectedTrialError("no trustworthy related first-party experiment")
    if option["case"] == CASE_SCANDIR:
        from .python_scandir_review_v01 import (
            run_python_scandir_review, SCHEMA as PY_SCHEMA,
        )
        out = run_python_scandir_review()
        trial = out.get("synthetic_trial")
        if (out.get("schema") != PY_SCHEMA
                or out.get("status") !=
                "UCIE_OWNED_SYNTHETIC_SCANDIR_TRIAL_PASS_NOT_APPROVED"
                or out.get("source_id") != "doc:python/cpython"
                or out.get("official_document_url") !=
                "https://docs.python.org/3/library/os.html"
                or out.get("documentation_revision_status") !=
                "PUBLIC_DOCUMENT_REVISION_NOT_PINNED"
                or out.get("candidate_status") != "UNVERIFIED_CANDIDATE_ONLY"
                or out.get("source_executed") is not False
                or any(out.get(f) is not False for f in (
                    "human_approved", "export_allowed", "auto_promoted",
                    "customer_release_authorized"))
                or out.get("network_requests") != 0
                or out.get("operating_database_writes") != 0
                or type(trial) is not dict
                or trial.get("synthetic_file_count") != 4
                or trial.get("concurrent_guarded_consumers") != 2
                or any(trial.get(k) is not True for k in (
                    "unique_entries_match", "sequential_control_match",
                    "closed_iterator_stops", "temporary_synthetic_files_removed"))
                or any(trial.get(k) is not False for k in (
                    "unsafe_raw_iterator_race_executed",
                    "external_repository_source_executed",
                    "customer_or_other_project_files_opened"))):
            raise SourceSelectedTrialError("guarded Python synthetic trial scope drift")
        result_label = "UCIE 임시 파일 4개를 잠금으로 보호해 두 소비자가 누락·중복 없이 순회하고 종료 후 차단 확인"
        details = {"synthetic_files": 4, "guarded_consumers": 2,
                   "matching_entries": True, "after_close_stops": True}
    elif option["case"] == CASE_MCP:
        from .mcp_prompt_regression_v01 import (
            synthetic_demonstration, SCHEMA as MCP_SCHEMA, SOURCE_PR,
            UPSTREAM_MERGE_SHA,
        )
        out = synthetic_demonstration()
        if (out.get("schema") != MCP_SCHEMA
                or out.get("status") !=
                "SYNTHETIC_WIRE_CONTRACT_ONLY_NO_SDK_EXECUTION"
                or out.get("source_pr") != SOURCE_PR
                or out.get("source_merge_sha") != UPSTREAM_MERGE_SHA
                or out.get("first_fixed_release") != "NOT_VERIFIED"
                or out.get("cases") != 8
                or out.get("contract_matches") != 6
                or out.get("non_input_controls") != 2
                or out.get("synthetic_pre_fix_violations_detected") != 4
                or out.get("independent_sdk_regression") != "NOT_EXECUTED"
                or any(out.get(k) is not False for k in (
                    "per_revision_rights_approved", "auto_promoted",
                    "customer_release_authorized"))
                or out.get("network_requests") != 0
                or out.get("persistent_writes") != 0):
            raise SourceSelectedTrialError("MCP synthetic wire trial scope drift")
        result_label = "UCIE 자체 MCP JSON-RPC 사례 8개 검사: 계약 일치 6개·서버 오류 대조 2개"
        details = {"synthetic_cases": 8, "contract_matches": 6,
                   "non_input_controls": 2, "pre_fix_synthetic_violations": 4}
    else:
        raise SourceSelectedTrialError("unregistered first-party trial")
    return {
        **option,
        "status": STATUS,
        "executed_first_party_synthetic": True,
        "observed_result": result_label,
        "counts": details,
        "external_code_executed": False,
        "source_fix_independently_verified": False,
        "regression_executed_on_upstream": False,
        "human_approved": False,
        "auto_promoted": False,
        "customer_distribution_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
