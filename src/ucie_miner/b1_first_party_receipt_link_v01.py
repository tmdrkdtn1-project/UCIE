"""UCIE B1/B2 first-party synthetic trial proof, opt-in and review-only.

Runs only two bounded UCIE-authored recipe fixtures. The Python sample uses
an ephemeral OS temporary directory; this is NOT a read of the user's project.
Source-document tags are NOT runtime-tested versions. No export/release.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json

from .b1_b2_b3_truth_journey_v01 import build_truth_journey
from .b1_b4_skillbook_capsule_link_v01 import build_pinned_b1_capsules
from .skillbook_principle_composer_v01 import (
    DEMO_SCHEMA, PRINCIPLE_ID, run_first_party_synthetic_comparison,
)
from .local_v1_priority_v01 import require_local_work

SCHEMA = "UCIE_B1_FIRST_PARTY_SYNTHETIC_RECEIPT_LINK_V01"


class FirstPartyReceiptError(ValueError):
    pass


def run_scoped_receipt(case_id: str, source_tag: str | None = None) -> dict:
    """Opt-in actual first-party synthetic trial; no claims about client systems."""
    require_local_work("VIRTUAL_LIBRARY")
    journey = build_truth_journey(case_id, source_tag)
    found = [c for c in build_pinned_b1_capsules()
             if c["case_id"] == journey["case_id"]]
    if len(found) != 1 or found[0]["capsule_id"] != journey["capsule_id"]:
        raise FirstPartyReceiptError("CAPSULE_IDENTITY_DRIFT")
    cap = found[0]
    # Actual first-party algorithm with UCIE-created synthetic inputs.
    trial = run_first_party_synthetic_comparison()
    if (type(trial) is not dict or trial.get("schema") != DEMO_SCHEMA
            or trial.get("principle_id") != PRINCIPLE_ID
            or trial.get("status") != "FIRST_PARTY_COMPARISON_RECIPE_OBSERVED_NO_RELEASE"
            or trial.get("directory_origin") != "SELF_CREATED_TEMPORARY_ONLY"
            or trial.get("git_input_origin") != "UCIE_AUTHOR_SYNTHETIC_BYTES_ONLY"
            or trial.get("scandir_regular_file_count") != 2
            or trial.get("git_parsed_status_entries") != 2
            or trial.get("git_names_returned") is not False
            or trial.get("scandir_names_returned_to_external_consumer") is not False
            or trial.get("independent_qa_verified") is not False
            or trial.get("rights_approved") is not False
            or trial.get("export_allowed") is not False
            or trial.get("external_project_access") is not False
            or trial.get("network_requests") != 0
            or trial.get("operating_database_writes") != 0):
        raise FirstPartyReceiptError("SYNTHETIC_TRIAL_CONTRACT_DRIFT")
    # This shared comparison is not a per-source test receipt; retain that
    # distinction even when this case is one of the two parent source records.
    result = {
        "schema": SCHEMA,
        "case_id": journey["case_id"],
        "capsule_id": journey["capsule_id"],
        "capsule_sha256": journey["capsule_sha256"],
        "source_id": cap["source_id"],
        "source_tag": cap["source_tag"],
        "source_document_sha256": cap["source_document_sha256"],
        "linked_skillbook_id": journey["skillbook_id"],
        "parent_principle_id": PRINCIPLE_ID,
        "trial_schema": trial["schema"],
        "trial_kind": "UCIE_FIRST_PARTY_TWO_RECIPE_SYNTHETIC_COMPARISON",
        "trial_executed": True,
        "trial_environment": "EPHEMERAL_UCIE_AUTHORED_FIXTURES_ONLY",
        "observed_scandir_count": trial["scandir_regular_file_count"],
        "observed_git_record_count": trial["git_parsed_status_entries"],
        "case_specific_runtime_trial": False,
        "actual_runtime_version_verified": False,
        "tested_python_or_git_version": None,
        "source_revision_decision": journey["source_revision_decision"],
        "runtime_applicability": "UNKNOWN_NO_PROOF",
        "b3_revision_authenticated": False,
        "b3_retests_executed": False,
        "first_party_observation_not_independent_qa": True,
        "independent_qa_verified": False,
        "rights_approved": False,
        "export_allowed": False,
        "owner_approved": False,
        "network_requests": 0,
        "customer_project_reads": 0,
        "operating_database_writes": 0,
        "release_approved": False,
    }
    canonical = json.dumps(result, sort_keys=True, ensure_ascii=True,
                           allow_nan=False, separators=(",", ":")).encode("ascii")
    return {**result, "receipt_sha256": sha256(canonical).hexdigest()}


def render_receipt_guidance(receipt: dict) -> str:
    """Explicit receipt display, not a new HTTP action or automatic test."""
    if type(receipt) is not dict:
        raise FirstPartyReceiptError("INVALID_RECEIPT")
    expected_case = receipt.get("case_id")
    expected_tag = receipt.get("source_tag")
    if type(expected_case) is not str or type(expected_tag) is not str:
        raise FirstPartyReceiptError("INVALID_RECEIPT_ID")
    # DO NOT rerun side-effectful synthetic trial when rendering. Validate
    # the deterministic structural receipt and existing B1 source identity.
    found = [c for c in build_pinned_b1_capsules()
             if c["case_id"] == expected_case]
    if len(found) != 1:
        raise FirstPartyReceiptError("UNKNOWN_CASE")
    cap = found[0]
    required = {
        "schema": SCHEMA,
        "case_id": cap["case_id"],
        "capsule_id": cap["capsule_id"],
        "capsule_sha256": cap["content_sha256"],
        "source_id": cap["source_id"],
        "source_tag": cap["source_tag"],
        "source_document_sha256": cap["source_document_sha256"],
        "trial_schema": DEMO_SCHEMA,
        "trial_kind": "UCIE_FIRST_PARTY_TWO_RECIPE_SYNTHETIC_COMPARISON",
        "trial_executed": True,
        "trial_environment": "EPHEMERAL_UCIE_AUTHORED_FIXTURES_ONLY",
        "observed_scandir_count": 2,
        "observed_git_record_count": 2,
        "case_specific_runtime_trial": False,
        "actual_runtime_version_verified": False,
        "tested_python_or_git_version": None,
        "runtime_applicability": "UNKNOWN_NO_PROOF",
        "first_party_observation_not_independent_qa": True,
        "independent_qa_verified": False,
        "rights_approved": False,
        "export_allowed": False,
        "owner_approved": False,
        "release_approved": False,
        "network_requests": 0,
        "customer_project_reads": 0,
        "operating_database_writes": 0,
    }
    if (set(receipt) != set(required) | {
            "linked_skillbook_id", "parent_principle_id",
            "source_revision_decision", "b3_revision_authenticated",
            "b3_retests_executed", "receipt_sha256"}):
        raise FirstPartyReceiptError("RECEIPT_SHAPE_DRIFT")
    if (any(receipt.get(key) != value for key, value in required.items())
            or receipt["parent_principle_id"] != PRINCIPLE_ID
            or receipt["b3_revision_authenticated"] is not False
            or receipt["b3_retests_executed"] is not False
            or receipt["source_revision_decision"] not in (
                "UNKNOWN_NO_PROOF", "SOURCE_REVISION_MISMATCH_HOLD")):
        raise FirstPartyReceiptError("RECEIPT_PROOF_DRIFT")
    journey = build_truth_journey(expected_case, expected_tag)
    if (receipt["linked_skillbook_id"] != journey["skillbook_id"]
            or receipt["source_revision_decision"]
                != journey["source_revision_decision"]):
        # Unknown requested source tag is not reconstructible from receipt.
        # Exact source-tag path is required for this display.
        raise FirstPartyReceiptError("JOURNEY_DRIFT")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    digest = sha256(json.dumps(body, sort_keys=True, ensure_ascii=True,
                               allow_nan=False, separators=(",", ":")).encode("ascii")).hexdigest()
    if digest != receipt["receipt_sha256"]:
        raise FirstPartyReceiptError("RECEIPT_HASH_DRIFT")
    e = lambda x: escape(str(x), quote=True)
    return (
        '<section aria-label="UCIE 자체 예제 검증 기록">'
        '<h2>UCIE가 만든 예제에서는 확인했습니다</h2>'
        '<p>서로 다른 두 가지 기술 예제를 UCIE 자체 입력으로 실행했습니다. '
        '실제 PC 프로그램 버전에서 되는지는 아직 확인하지 않았습니다.</p>'
        '<p>출처 버전 일치만으로 프로그램 호환성을 판단하지 않습니다.</p>'
        '<p>독립 검증·사용권·고객 배포는 미승인입니다.</p>'
        '<details><summary>왜 이렇게 안내하나요?</summary>'
        '<p>Capsule: ' + e(receipt["capsule_id"]) + '</p>'
        '<p>시험 기록 SHA-256: ' + e(receipt["receipt_sha256"]) + '</p>'
        '</details></section>'
    )
