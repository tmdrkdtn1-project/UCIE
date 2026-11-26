"""UCIE V2 B4 fourth-technology bridge: reviewed PowerShell 7.6.6 negative.

Reuses existing W01/W02 registry and historical P9 exact PR/native release
receipt. Native bug reproduction != fixed release or future compatibility.
No new network fetch, external code execution, rights grant or source intake.
"""
from __future__ import annotations

from .source_registry import ACTIVE, get_source
from .library_entry import build_library_entry
from .p9_pinned_public_review import lookup_pinned_review

SOURCE_ID = "repo:PowerShell/PowerShell"
PR_URL = "https://github.com/PowerShell/PowerShell/pull/28087"
MERGE_SHA = "373f6a7b7972a0a4b73bfd9737a0d768d28b347e"
RECORD_ID = "powershell-resolvepath"
SCHEMA = "UCIE_V2_B4_GATED_POWERSHELL_TRANSFER_V01"


class FourthTechnologyError(ValueError):
    """Never promote a native negative control into a current fix claim."""


def reviewed_powershell_record() -> dict:
    source = get_source(SOURCE_ID)
    if (source["status"] != ACTIVE
            or source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY"
            or source["fetch_authorized_by_this_registry"] is not False
            or source["license_verdict"] != "NOT_ATTESTED_PER_REVISION"):
        raise FourthTechnologyError("PowerShell registry scope drift")

    source_review = lookup_pinned_review(
        source_id=SOURCE_ID, public_url=PR_URL, merge_sha=MERGE_SHA)
    if source_review is None:
        raise FourthTechnologyError("missing exact P9 pinned PowerShell source")
    windows = source_review.get("official_windows_release_runtime_observation")
    comparison = source_review.get("examined_tag_source_patch")
    if (source_review.get("merge_sha") != MERGE_SHA
            or source_review.get("upstream_release_tag") != "v7.6.6"
            or source_review.get("approved_or_exportable") is not False
            or source_review.get("release_contains_fix_verified") is not False
            or source_review.get("independent_qa_completed") is not False
            or source_review.get("per_file_third_party_license_cleared") is not False
            or type(windows) is not dict
            or windows.get("status") !=
               "PINNED_RELEASE_WINDOWS_X64_BUG_REPRODUCED_NO_GO"
            or windows.get("runtime_version") != "7.6.6"
            or windows.get("actual_release_binary_executed") is not True
            or windows.get("independent_qa_completed") is not False
            or windows.get("native_behavior") !=
               "DOT_PREFIX_BUG_OBSERVED_ON_RUNNER"
            or type(comparison) is not dict
            or comparison.get("runtime_fix_coverage_verified") is not False
            or comparison.get("equivalent_backport_excluded") is not False):
        raise FourthTechnologyError("wrong release/independent proof boundary")

    candidate = build_library_entry({
        "kind": "TEST_RECIPE",
        "source_id": SOURCE_ID,
        "evidence_reference": "pr:28087:" + MERGE_SHA,
        "evidence_sha256": windows["release_binary_sha256"],
        "purpose_code": "POWERSHELL_DOT_PREFIX_VERSION_REPRO",
        "version_scope": "7.6.6",
        "dependencies": [],
    })
    if (candidate["revision_hint"] != MERGE_SHA
            or candidate["public_url"] != PR_URL
            or candidate["entry_status"] != "UNVERIFIED_CANDIDATE_ONLY"
            or candidate["version_applicability_verified"] is not False
            or candidate["export_allowed"] is not False
            or candidate["human_approved"] is not False
            or candidate["owner_signed"] is not False):
        raise FourthTechnologyError("W02 library rights/revision drift")
    return {
        "record_id": RECORD_ID,
        "source_id": SOURCE_ID,
        "source_pin": MERGE_SHA,
        "technology": "PowerShell",
        "mechanisms": ["VERSION_PINNED_TRIAL", "OUTPUT_CONTRACT_VALIDATION"],
        "counterexamples": ["HISTORICAL_TRIAL_NOT_CURRENT_COMPATIBILITY"],
        "review_origin": "UCIE_P9_NATIVE_RELEASE_NEGATIVE_CONTROL",
    }


def build_four_technology_review() -> dict:
    """Source-gated fourth record enters the existing shared composer."""
    from .ucie_v2_b4_multisource_hypothesis_v01 import (
        compose_hypotheses, pinned_records,
    )
    fourth = reviewed_powershell_record()
    result = compose_hypotheses(pinned_records() + [fourth])
    version_hypothesis = next(
        (x for x in result["hypotheses"]
         if x["claim"] == "VERSION_PINNED_TRIAL"), None)
    if (result["record_count"] != 4
            or version_hypothesis is None
            or set(version_hypothesis["supporting_records"]) !=
               {"mcp-prompts", RECORD_ID}
            or result["customer_release_authorized"] is not False
            or result["independent_qa_verified"] is not False):
        raise FourthTechnologyError("invalid cross-technology synthesis")
    return {
        "schema": SCHEMA,
        "source_pinned_synthesis": result,
        "source_review_scope":
            "POWERSHELL_7_6_6_WINDOWS_X64_BUG_REPRODUCTION_NOT_FIX",
        "actual_native_windows_trial_is_historical": True,
        "new_native_trial_executed": False,
        "claims_current_sdk_or_fixed_version": False,
        "source_fetched_now": False,
        "approved_for_export": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }
