"""Stage 6/7: deterministic, non-executable rule candidate and approval gate.

No shell commands, rulepack signing, deployment, external code execution,
network access, database writes, or status promotion. This is a preview only.
"""
from __future__ import annotations

import hashlib
import json

from .patterns import PatternError

GUIDANCE = {
    "API_CONTRACT": ("Validate accepted arguments and rejected inputs",
                     "Synthetic valid and invalid API inputs"),
    "EXCEPTION_HANDLING": ("Guard documented exceptional paths",
                           "Synthetic error and cleanup paths"),
    "EXPLICIT_ENCODING": ("Specify explicit supported text encoding",
                          "UTF-8 and invalid-encoding negative cases"),
    "DEPENDENCY_VERSION": ("Check pinned version and compatible runtime",
                           "Pinned and unsupported version fixtures"),
    "RESOURCE_CLEANUP": ("Close resources deterministically",
                         "Repeated open-close and failure cleanup fixtures"),
    # Pinned Stage 4 review families: guidance and test *plans*, not patches.
    "PS_SSH_PATH_WITHOUT_RUNSPACE": (
        "Check SSH path behavior without assuming an active Runspace",
        "Null-Runspace and SSH path fixtures across supported PowerShell versions"),
    "PS_FUZZY_GET_COMMAND_DUPLICATES": (
        "Deduplicate fuzzy CommandInfo results by Name, CommandType and Source before use; never invoke discovered commands",
        "Synthetic duplicate and near-match command fixtures"),
    "PS_RESOLVE_PATH_DOT_PREFIX": (
        "Derive anchored relative paths with Path.GetRelativePath; reject escapes and preserve dot-prefixed filenames",
        "Dot-prefix, parent-directory and platform-specific path fixtures"),
    "PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO": (
        "Replace only the literal Python -X disable_remote_debug with -X disable-remote-debug; verify target interpreter behavior before relying on the control",
        "Separate isolated Python process checks: baseline enabled, misspelled option still enabled, corrected option disabled where supported"),
    "PY_SCANDIR_SHARED_ITERATOR_RACE": (
        "Never concurrently share a raw scandir iterator; serialize every next() and close() with a single owned lock",
        "Guarded concurrent next()/close() and end-of-stream fixtures; raw native crash remains NO-GO"),
    "PY_QSBR_THREADSTATE_SLOT_LEAK": (
        "Review balanced thread-state slot acquisition and release paths",
        "Repeated thread-state lifecycle and interrupted cleanup fixtures"),
    "PY_COMPREHENSION_COMPILER_ERROR_CLEANUP": (
        "Preserve compiler failure state while releasing temporary resources",
        "Malformed comprehension and compiler exceptional-path fixtures"),
    "PY_AST_REPR_FIELDS_LOOKUP": (
        "Review AST repr field lookup and missing-field behavior",
        "Missing, unusual and invalid AST field fixtures"),
    "PY_WEAKREF_FREE_THREADED_RACE": (
        "Review lifetime and synchronization of free-threaded weak references",
        "Concurrent weakref access, finalization and cleanup fixtures"),
}
REQUIRED_GATES = ("source_authenticated", "license_verified",
                  "security_review_passed", "independent_regression_passed",
                  "human_approved")


def candidate_rulepack(group_preview: object) -> dict:
    if (not isinstance(group_preview, dict)
            or set(group_preview) != {"schema", "pr_count", "family_count",
                "families", "persistent_writes", "rules_promoted",
                "production_approved"}
            or group_preview["schema"] != "UCIE_PATTERN_GROUP_PREVIEW_V1"
            or group_preview["persistent_writes"] != 0
            or group_preview["rules_promoted"] != 0
            or group_preview["production_approved"] is not False
            or not isinstance(group_preview["families"], list)
            or group_preview["family_count"] != len(group_preview["families"])):
        raise PatternError("invalid Stage 5 preview")
    proposals = []
    for family in group_preview["families"]:
        if (not isinstance(family, dict)
                or set(family) != {"source", "canonical_pr_number", "pr_numbers",
                     "pattern_code", "fingerprint_sha256", "status",
                     "requires_independent_validation"}
                or family["status"] != "UNVERIFIED_CANDIDATE_ONLY"
                or family["requires_independent_validation"] is not True
                or family["pattern_code"] not in GUIDANCE):
            raise PatternError("unapproved family or unknown rule template")
        guidance, regression = GUIDANCE[family["pattern_code"]]
        proposals.append({
            "source": family["source"],
            "canonical_pr_number": family["canonical_pr_number"],
            "evidence_fingerprint": family["fingerprint_sha256"],
            "rule_code": family["pattern_code"],
            "safe_fix_guidance": guidance,
            "regression_test_plan": regression,
            "executable_command": None,
            "status": "UNVERIFIED_CANDIDATE_ONLY",
            "required_gates": {gate: "NOT_VERIFIED" for gate in REQUIRED_GATES},
        })
    digest = hashlib.sha256(json.dumps(proposals, sort_keys=True,
        separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"schema": "UCIE_RULEPACK_PREVIEW_V1", "digest_sha256": digest,
            "proposals": proposals, "signed": False, "published": False,
            "approval": False, "auto_promoted": False,
            "regressions_executed": 0}


def approval_gate(candidate_pack: object) -> dict:
    """Fail-closed observation: no production approval API exists in Stage 7."""
    if (not isinstance(candidate_pack, dict)
            or candidate_pack.get("schema") != "UCIE_RULEPACK_PREVIEW_V1"
            or candidate_pack.get("signed") is not False
            or candidate_pack.get("published") is not False
            or candidate_pack.get("approval") is not False
            or candidate_pack.get("auto_promoted") is not False):
        raise PatternError("invalid candidate pack")
    return {"schema": "UCIE_APPROVAL_GATE_V1",
            "status": "BLOCKED_PENDING_INDEPENDENT_VERIFICATION",
            "reason": "No independently verified evidence, regression approval or signing authorization",
            "production_signed": False,
            "deploy_allowed": False}
