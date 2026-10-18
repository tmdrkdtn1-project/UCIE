"""Stage18 first-rule, operator-invoked CPython -X safety reproduction.

Only UCIE's already-authored inert runtime probe may execute, never a PR-
provided command, patch, model, script or private project. Stage17 candidate
binding is mandatory. One-shot stdout is NOT an independent QA attestation,
signature, owner consent or production authorization.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from .automated_candidate_qa import SAFE_STEPS
from .stage17_review_docket import SCHEMA as STAGE17_SCHEMA, inspect_stage17_review
from .verification_handoff import PINNED_RULES

SCHEMA = "UCIE_STAGE18_FIRST_RULE_RUNTIME_REPRO_V1"
RULE_ID = "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO"
UPSTREAM = "python/cpython"
PR = 159014
MERGE_SHA = "91248026c8a41910098032dd23f9a05ad2d9b513"
DOCS = ("Doc/howto/remote_debugging.rst", "Doc/using/cmdline.rst")
PR_URL = f"https://github.com/{UPSTREAM}/pull/{PR}"
PIN = (UPSTREAM, PR, MERGE_SHA)
if PINNED_RULES.get(PIN) != RULE_ID:
    raise RuntimeError("Stage18 first rule does not match pinned Stage12 identity")

# Official publicly reviewed CPython information, not re-fetched or signed by
# this OFFLINE command. Release tags and backport merges are distinct scopes.
SOURCE_FACTS = {
    "upstream_pr_url": PR_URL,
    "upstream_merge_sha": MERGE_SHA,
    "upstream_merged_utc": "2026-10-14T13:18:20Z",
    "change_type": "DOCUMENTATION_ONLY",
    "documentation_files": list(DOCS),
    "corrected_documentation_occurrences": 4,
    "v3_15_0_tag_utc": "2026-10-09T11:16:41Z",
    "v3_15_0_docs_contained_old_spelling": True,
    "v3_15_0_binary_behavior_changed_by_this_pr": False,
    "python_3_14_docs_backport_merge_sha":
        "0d214f87921ab9b858cda64c290d89081335772f",
    "python_3_15_docs_backport_merge_sha":
        "cf0c41f716871a8d19d56916e0be59d3beb887d5",
    "upstream_license_document": "https://github.com/python/cpython/blob/v3.15.0/LICENSE",
    "license_claim": "Python Software Foundation License Version 2",
    "license_signoff": False,
    "release_inclusion_independently_attested": False,
}
STATUS_PENDING = "LOCAL_OBSERVATION_NOT_REQUESTED_NO_GO"
STATUS_CONFIRMED = "LOCAL_RUNTIME_BEHAVIOR_OBSERVED_REVIEW_REQUIRED"
STATUS_FAILED = "LOCAL_RUNTIME_BEHAVIOR_NOT_CONFIRMED_NO_GO"
STATUS_MISSING = "STAGE17_FIRST_RULE_NOT_READY_NO_GO"


def _observe_xoption(option: str | None) -> bool:
    """Hardened fixed probe with no shell, network, untrusted args or writes."""
    arguments = [sys.executable, "-I", "-B"]
    if option is not None:
        if option not in ("disable_remote_debug", "disable-remote-debug"):
            raise ValueError("unapproved Stage18 -X option")
        arguments += ["-X", option]
    arguments += [
        "-c", "import sys; print(sys.is_remote_debug_enabled())",
    ]
    env = os.environ.copy()
    env.pop("PYTHON_DISABLE_REMOTE_DEBUG", None)
    result = subprocess.run(
        arguments, capture_output=True, text=True, check=False,
        timeout=8, env=env,
    )
    if (result.returncode != 0 or result.stderr.strip()
            or result.stdout.strip() not in ("True", "False")):
        raise ValueError("Stage18 safe local runtime probe unavailable")
    return result.stdout.strip() == "True"


def reproduce_local_xoption() -> dict:
    """Explicit single-run local verification of three fixed safe cases."""
    if (sys.implementation.name != "cpython"
            or sys.version_info[:2] != (3, 15)
            or not hasattr(sys, "is_remote_debug_enabled")):
        return {
            "status": "UNSUPPORTED_CPYTHON_RUNTIME_NO_GO",
            "runtime_version": None, "platform": sys.platform,
            "baseline_enabled": None, "wrong_option_enabled": None,
            "correct_option_enabled": None,
        }
    version = sys.version.split()[0]
    try:
        base = _observe_xoption(None)
        wrong = _observe_xoption("disable_remote_debug")
        right = _observe_xoption("disable-remote-debug")
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return {
            "status": "LOCAL_PROBE_ERROR_NO_GO",
            "error_type": type(exc).__name__, "runtime_version": version,
            "platform": sys.platform, "baseline_enabled": None,
            "wrong_option_enabled": None, "correct_option_enabled": None,
        }
    return {
        "status": (STATUS_CONFIRMED if (base, wrong, right) ==
                   (True, True, False) else STATUS_FAILED),
        "runtime_version": version, "platform": sys.platform,
        "baseline_enabled": base, "wrong_option_enabled": wrong,
        "correct_option_enabled": right,
    }


def build_first_rule_report(docket: object, observed: dict | None = None) -> dict:
    """Purely reconcile candidate ID and bounded local observation; never GO."""
    if (type(docket) is not dict or docket.get("schema") != STAGE17_SCHEMA
            or type(docket.get("items")) is not list
            or type(docket.get("candidate_count")) is not int
            or docket["candidate_count"] != len(docket["items"])
            or type(docket.get("docket_sha256")) is not str
            or len(docket["docket_sha256"]) != 64
            or docket.get("approved_rules_added") != 0
            or docket.get("production_approved") is not False
            or docket.get("independent_qa_pass_count") != 0
            or docket.get("stage16_candidate_snapshot_at_ci_verified") is not False):
        raise ValueError("untrusted Stage17 review dossier")
    candidates = [entry for entry in docket["items"]
                  if type(entry) is dict and entry.get("rule_id") == RULE_ID]
    if len(candidates) > 1:
        raise ValueError("ambiguous Stage18 candidate identity")
    selected = candidates[0] if candidates else None
    ready = (
        docket.get("status") ==
            "CANDIDATES_READY_FOR_INDEPENDENT_REVIEW_NO_APPROVAL"
        and selected is not None
        and selected.get("source") == UPSTREAM
        and selected.get("pinned_public_pr") == PR_URL
        and selected.get("triage") ==
            "PINNED_TEMPLATE_INDEPENDENT_REVIEW_REQUIRED"
        and selected.get("safe_synthetic_test_step") == SAFE_STEPS[RULE_ID][0]
        and selected.get("independent_qa") == "NOT_PERFORMED"
        and selected.get("candidate_level_ci_binding") == "NOT_ATTESTED"
        and selected.get("human_approval") is False
        and selected.get("deploy_allowed") is False
    )
    if selected is not None:
        for key in ("candidate_id_sha256", "evidence_sha256"):
            value = selected.get(key)
            if (type(value) is not str or len(value) != 64 or
                    any(c not in "0123456789abcdef" for c in value)):
                raise ValueError("invalid Stage18 candidate fingerprint")
    if observed is not None:
        if (type(observed) is not dict
                or observed.get("status") not in (
                    STATUS_CONFIRMED, STATUS_FAILED,
                    "LOCAL_PROBE_ERROR_NO_GO",
                    "UNSUPPORTED_CPYTHON_RUNTIME_NO_GO")):
            raise ValueError("untrusted local probe summary")
        if observed.get("status") == STATUS_CONFIRMED and (
                observed.get("baseline_enabled") is not True
                or observed.get("wrong_option_enabled") is not True
                or observed.get("correct_option_enabled") is not False
                or type(observed.get("runtime_version")) is not str
                or not observed["runtime_version"].startswith("3.15.")):
            raise ValueError("forged Stage18 behavior status")
    runtime = observed if observed is not None else {"status": STATUS_PENDING}
    status = (STATUS_MISSING if not ready else runtime["status"])
    report = {
        "schema": SCHEMA,
        "status": status,
        "rule_id": RULE_ID,
        "candidate_id_sha256": selected["candidate_id_sha256"] if ready else None,
        "evidence_sha256": selected["evidence_sha256"] if ready else None,
        "stage17_docket_sha256": docket["docket_sha256"],
        "stage16_aggregate_ci_run_id": docket.get("stage16_ci_run_id"),
        "ci_test_is_owner_authored": True,
        "candidate_specific_ci_attested": False,
        "pinned_official_metadata": SOURCE_FACTS,
        "source_facts_rechecked_by_this_offline_command": False,
        "local_probe": runtime,
        "local_probe_is_operator_host_observation": observed is not None,
        "local_probe_independent_of_owner": False,
        "independent_qa": "NOT_PERFORMED",
        "independent_security_qa": "NOT_PERFORMED",
        "license_signoff": False,
        "affected_release_coverage": "NOT_INDEPENDENTLY_ATTESTED",
        "owner_approval": False,
        "approved_rules_added": 0,
        "auto_promoted": False,
        "rulepack_signed": False,
        "production_approved": False,
        "deploy_allowed": False,
        "new_public_gets": 0,
        "persistent_writes": 0,
        "digest_is_signature": False,
    }
    report["report_sha256"] = hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return report


def inspect_first_rule(root: Path, *, local_probe: bool = False) -> dict:
    """Never auto-run; guard Stage17 before optional inert subprocess calls."""
    docket = inspect_stage17_review(root)
    preview = build_first_rule_report(docket)
    if not local_probe or preview["status"] == STATUS_MISSING:
        return preview
    observed = reproduce_local_xoption()
    return build_first_rule_report(docket, observed)
