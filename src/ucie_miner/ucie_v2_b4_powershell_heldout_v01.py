"""B4 new HELD-OUT PowerShell transfer: source-bound, UCIE-authored, synthetic.

Unlike the original Python/Git->MCP demonstration this targets command
resolution with a loaded-session precondition. PowerShell/PowerShell v7.5.4
and official Microsoft Learn docs are approved public inputs ONLY, never
instructions to execute. No PowerShell is invoked in this Python module.
The separate disposable Windows CI runs an UCIE-owned native smoke test.

This is NOT an automatically inferred universal principle, verified
customer diagnosis, native PowerShell 7.5.4 certification, exportable
SkillBook or owner deployment approval.
"""
from __future__ import annotations

from hashlib import sha256
import json

SCHEMA = "UCIE_V2_B4_POWERSHELL_HELDOUT_REPROCESS_V01"
RECIPE_SCHEMA = "UCIE_V2_B4_FINITE_COMMAND_RESOLUTION_RECIPE_V01"
STATUS = "UCIE_ORIGINAL_CROSS_TECH_HELDOUT_DRAFT_NOT_APPROVED"
METHOD = "SOURCE_PINNED_FIRST_PARTY_CONDITIONAL_TRANSFER_AND_COUNTEREXAMPLES"
SOURCE_REPO = "PowerShell/PowerShell"
SOURCE_TAG = "v7.5.4"
SOURCE_COMMIT = "7c8d9e7e0ed2fc1f2caf50746fe9fef720ca2a0a"
SOURCE_PATH = "src/System.Management.Automation/engine/CommandDiscovery.cs"
SOURCE_BLOB_SHA = "e07520a1238db6c5e511153e06a05103d2fa15f1"
LICENSE_BLOB_SHA = "b2f52a2bad4e27e2d9c68a755abb74cb8943f2fa"
OFFICIAL_DOC = ("https://learn.microsoft.com/en-us/powershell/module/"
                "microsoft.powershell.core/about/about_command_precedence"
                "?view=powershell-7.5")
CASE_ID = "powershell-command"
ORDER = ("Alias", "Function", "Cmdlet", "Application")
SCENARIOS = (
    "ALIAS_OVER_CMDLET",
    "EXPLICIT_CMDLET_FILTER",
    "FUNCTION_OVER_CMDLET",
    "UNKNOWN_MODULE_LOAD_STATE",
    "PATH_QUALIFIED_OUT_OF_SCOPE",
    "MISSING_TYPE_HOLD",
)
EXPECTED = (
    "ALIAS_SHADOWS_CMDLET",
    "EXPLICIT_CMDLET_CONTRACT_FOUND",
    "FUNCTION_SHADOWS_CMDLET",
    "HOLD_SESSION_LOAD_STATE_UNKNOWN",
    "HOLD_PATH_QUALIFIED_DIFFERENT_RULE",
    "HOLD_NO_MATCHING_COMMAND_TYPE",
)
MAX_CANDIDATES = 4


class HeldoutPowerShellError(ValueError):
    """Reject forged provenance, unapproved IO and unsupported inference."""


def _canonical(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def finite_loaded_command_resolution(candidates: tuple[str, ...],
                                     *, requested_type: str | None = None,
                                     load_state: str = "KNOWN_LOADED",
                                     path_qualified: bool = False) -> dict:
    """Reason over caller-supplied finite command *types*, not command names.

    A type list is not a Get-Command session observation. The real source
    explicitly says precedence for *unqualified, loaded* commands; do not
    silently extrapolate to unloaded-module, path-qualified or ambiguous cases.
    """
    if (type(candidates) is not tuple
            or not 1 <= len(candidates) <= MAX_CANDIDATES
            or any(type(x) is not str or x not in ORDER for x in candidates)
            or len(set(candidates)) != len(candidates)
            or (requested_type is not None and
                (type(requested_type) is not str or requested_type not in ORDER))
            or type(load_state) is not str
            or load_state not in ("KNOWN_LOADED", "UNKNOWN")
            or type(path_qualified) is not bool):
        raise HeldoutPowerShellError("invalid finite typed command contract")
    winner = None
    if load_state != "KNOWN_LOADED":
        status = "HOLD_SESSION_LOAD_STATE_UNKNOWN"
    elif path_qualified:
        status = "HOLD_PATH_QUALIFIED_DIFFERENT_RULE"
    elif requested_type is not None:
        if requested_type not in candidates:
            status = "HOLD_NO_MATCHING_COMMAND_TYPE"
        else:
            winner = requested_type
            status = ("EXPLICIT_CMDLET_CONTRACT_FOUND"
                      if requested_type == "Cmdlet" else
                      "EXPLICIT_TYPE_CONTRACT_FOUND")
    else:
        winner = min(candidates, key=ORDER.index)
        if winner == "Alias" and "Cmdlet" in candidates:
            status = "ALIAS_SHADOWS_CMDLET"
        elif winner == "Function" and "Cmdlet" in candidates:
            status = "FUNCTION_SHADOWS_CMDLET"
        elif winner == "Application":
            status = "ONLY_APPLICATION_DISCOVERED"
        else:
            status = "UNQUALIFIED_TYPE_RESOLUTION_PREDICTED"
    return {
        "schema": RECIPE_SCHEMA, "status": status,
        "predicted_type": winner, "candidate_count": len(candidates),
        "session_state_read": False, "powershell_executed": False,
        "customer_command_or_code_read": False,
        "independent_qa_verified": False,
        "exact_target_version_verified": False,
        "network_requests": 0, "operating_database_writes": 0,
    }


def _parent_checks() -> dict:
    from .ucie_v2_generalization_transfer_v01 import (
        SCHEMA as B4_SCHEMA, FACETS, TARGET, METHOD as PARENT_METHOD,
        build_hypothesis, run_bounded_transfer,
    )
    from .local_b2_connected_workbench_v01 import (
        SCHEMA as B2_SCHEMA, STATUS as B2_STATUS, evaluate_case,
    )
    from .local_error_actionable_workflow_v01 import get_case
    from .ucie_v2_revision_impact_v01 import PINS, PY_BOOK, GIT_BOOK

    try:
        parent = build_hypothesis()
        trial = run_bounded_transfer(parent)
        guidance = get_case(CASE_ID)
        existing_issue = evaluate_case(CASE_ID, "issue")
        existing_control = evaluate_case(CASE_ID, "control")
    except (ValueError, KeyError, TypeError) as exc:
        raise HeldoutPowerShellError(
            "inherited B4 or first-party case already rejected evidence"
        ) from exc
    # The parent hypothesis itself is draft data: the lower-level transfer
    # fixture compares to build_hypothesis(), so a swapped builder could
    # otherwise smuggle in a third, unapproved SkillBook or a forged digest.
    # Lock ALL three identity fields for each of the TWO approved parents.
    parents = parent.get("parents")
    allowed_parents = {
        ("doc:python/cpython", PY_BOOK, PINS["doc:python/cpython"]),
        ("doc:git/git", GIT_BOOK, PINS["doc:git/git"]),
    }
    if (type(parents) is not list or len(parents) != 2
            or any(type(row) is not dict for row in parents)
            or {(row.get("source_id"), row.get("skillbook_id"),
                 row.get("document_sha256")) for row in parents} != allowed_parents
            or trial.get("parent_skillbooks") !=
                [row["skillbook_id"] for row in parents]
            or trial.get("hypothesis_id") != parent.get("hypothesis_id")
            or trial.get("content_sha256") != parent.get("content_sha256")):
        raise HeldoutPowerShellError("unreviewed B4 parent identity or source pin")
    if (parent.get("schema") != B4_SCHEMA
            or parent.get("method") != PARENT_METHOD
            or parent.get("target_case") != TARGET
            or parent.get("source_facts_independently_verified") is not False
            or parent.get("cross_source_model_generalization_verified") is not False
            or parent.get("export_allowed") is not False
            or parent.get("auto_promoted") is not False
            or parent.get("model_trained") is not False
            or set(parent.get("shared_candidate_facets", ())) != set(FACETS)
            or trial.get("positive_negative_control") !=
                ["CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"]
            or trial.get("independent_qa_verified") is not False
            or trial.get("export_allowed") is not False
            or trial.get("network_requests") != 0
            or trial.get("operating_database_writes") != 0
            or guidance.get("case_id") != CASE_ID
            or guidance.get("official_url") != OFFICIAL_DOC.split("?")[0]
            or existing_issue.get("schema") != B2_SCHEMA
            or existing_control.get("schema") != B2_SCHEMA
            or existing_issue.get("status") != B2_STATUS
            or existing_control.get("status") != B2_STATUS
            or existing_issue.get("result_code") != "ALIAS_SHADOWS_COMMAND"
            or existing_control.get("result_code") != "EXPECTED_CMDLET_CHOSEN"
            or existing_issue.get("fixture_origin") !=
                "UCIE_AUTHORED_FIXED_SYNTHETIC"
            or existing_control.get("fixture_origin") !=
                "UCIE_AUTHORED_FIXED_SYNTHETIC"
            or any(existing_issue.get(key) is not False for key in (
                "actual_user_environment_inspected", "human_review_approved",
                "customer_distribution_authorized"))
            or existing_issue.get("network_requests") != 0
            or existing_control.get("operating_database_writes") != 0):
        raise HeldoutPowerShellError("parent B4 / existing B2 evidence drift")
    return parent


def build_heldout_hypothesis() -> dict:
    """Generate original, review-only conditional transfer, pinned to old B4."""
    parent = _parent_checks()
    candidate = {
        "schema": SCHEMA, "status": STATUS, "method": METHOD,
        "source": {
            "owner": "Microsoft / PowerShell project",
            "repo": SOURCE_REPO, "tag": SOURCE_TAG,
            "tag_commit_sha": SOURCE_COMMIT, "path": SOURCE_PATH,
            "source_blob_sha": SOURCE_BLOB_SHA,
            "source_url": (
                "https://github.com/PowerShell/PowerShell/blob/" +
                SOURCE_COMMIT + "/" + SOURCE_PATH
            ),
            "official_command_precedence_document": OFFICIAL_DOC,
            "license_file": "LICENSE.txt",
            "license_blob_sha": LICENSE_BLOB_SHA,
            "license_review_state": "MIT_FILE_INSPECTED_REUSE_NOT_AUTHORIZED",
            "source_facts_independently_tested_on_pinned_binary": False,
        },
        "parent_hypothesis_id": parent["hypothesis_id"],
        "parent_content_sha256": parent["content_sha256"],
        "parent_skillbooks": [x["skillbook_id"] for x in parent["parents"]],
        "heldout_case_id": CASE_ID,
        "reprocessed_principle": (
            "호출자가 제공한 명령 후보 타입과 대상 타입을 명시적으로 구분하면 "
            "동명이인 명령의 예상 선택을 제한된 예제로 확인할 수 있다. "
            "단, 실제 세션 로드 상태와 이름·경로 확인 없이는 단정하지 않는다."
        ),
        "conditional_facets_transferred": [
            "EXPLICIT_CALLER_INPUT", "BOUNDED_MAX_ENTRIES",
            "FAIL_CLOSED_NEGATIVE_CONTROLS", "NO_IMPLICIT_CATALOG_EXECUTION",
        ],
        "nontransferable_claims": [
            "ALL_COMMANDS_WITH_SAME_NAME_ARE_ALWAYS_LOADED",
            "FIRST_VISIBLE_COMMAND_IS_ALWAYS_THE_INTENDED_CMDLET",
            "PATH_QUALIFIED_COMMANDS_FOLLOW_UNQUALIFIED_PRECEDENCE",
            "ALL_FINITE_TYPED_METADATA_IS_A_SECURITY_SANDBOX",
        ],
        "machine_recipe": {
            "callable": (
                "ucie_miner.ucie_v2_b4_powershell_heldout_v01."
                "finite_loaded_command_resolution"
            ),
            "input": "BOUNDED_UCIE_AUTHORED_COMMAND_TYPES_ONLY",
            "max_candidates": MAX_CANDIDATES,
            "no_command_names_or_shell": True,
            "positive": "EXPLICIT_CMDLET_FILTER",
            "negative": "ALIAS_OVER_CMDLET",
            "counterexample": "UNKNOWN_MODULE_LOAD_STATE",
        },
        "human_skillbook_chapter": {
            "id": "UCIE-SKILLBOOK-DRAFT-POWERSHELL-COMMAND-PRECEDENCE-004",
            "status": "ORIGINAL_BOUNDED_HELDOUT_DRAFT_UNREVIEWED",
            "scope": "LOADED_UNQUALIFIED_TYPED_COMMAND_CANDIDATES_ONLY",
            "limitations": (
                "외부 명령 실행·실제 세션 후보 조회·모듈 자동 로드·"
                "경로 지정 호출·재배포 사용권을 검증하지 않음"
            ),
        },
        "evidence_version": "v7.5.4_SOURCE_TAG_NOT_BINARY_QA",
        "rights": "NOT_APPROVED",
        "independent_qa": "NOT_VERIFIED",
        "owner_host_tested": False,
        "model_trained": False, "auto_promoted": False,
        "license_redistribution_approved": False,
        "export_allowed": False, "published": False,
        "network_requests": 0, "operating_database_writes": 0,
    }
    digest = sha256(_canonical(candidate)).hexdigest()
    return {
        **candidate,
        "hypothesis_id": "UCIE-B4-HELDOUT-PS-" + digest[:20],
        "content_sha256": digest,
    }


def evaluate_heldout_hypothesis(hypothesis: dict) -> dict:
    """Run 6 original positive/negative/failed-transfer controls, no shell."""
    if (type(hypothesis) is not dict or hypothesis != build_heldout_hypothesis()):
        raise HeldoutPowerShellError("untrusted or self-approved held-out payload")
    observations = (
        finite_loaded_command_resolution(("Cmdlet", "Alias")),
        finite_loaded_command_resolution(("Alias", "Cmdlet"),
                                         requested_type="Cmdlet"),
        finite_loaded_command_resolution(("Function", "Cmdlet")),
        finite_loaded_command_resolution(("Alias", "Cmdlet"),
                                         load_state="UNKNOWN"),
        finite_loaded_command_resolution(("Application", "Alias"),
                                         path_qualified=True),
        finite_loaded_command_resolution(("Alias",),
                                         requested_type="Cmdlet"),
    )
    statuses = tuple(row["status"] for row in observations)
    if (statuses != EXPECTED
            or any(row["powershell_executed"] is not False or
                   row["customer_command_or_code_read"] is not False or
                   row["network_requests"] != 0 or
                   row["operating_database_writes"] != 0
                   for row in observations)):
        raise HeldoutPowerShellError("actual negative/hold logic drift")
    return {
        "schema": SCHEMA,
        "status": "FIRST_PARTY_HELDOUT_SYNTHETIC_RECIPE_EXECUTED_REVIEW_ONLY",
        "hypothesis_id": hypothesis["hypothesis_id"],
        "content_sha256": hypothesis["content_sha256"],
        "heldout_case": CASE_ID,
        "source_tag_commit": SOURCE_COMMIT,
        "outcomes": list(statuses),
        "synthetic_cases_executed": len(statuses),
        "negative_overgeneralizations_rejected": 4,
        "native_powershell_run": False,
        "independent_upstream_qa_verified": False,
        "customer_session_examined": False,
        "general_autonomous_semantic_discovery_proven": False,
        "human_rights_security_released": False,
        "customer_export_authorized": False, "auto_promoted": False,
        "model_trained": False, "network_requests": 0,
        "operating_database_writes": 0,
    }
