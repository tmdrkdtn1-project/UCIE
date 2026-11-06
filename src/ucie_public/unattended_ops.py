"""UCIE-only unattended-operations grant and preflight gate.

This module intentionally executes NOTHING. Host-owned Git and Windows
adapters must pass their exact observed state, use an OS-protected monotonic
serial/replay store, and enforce the same constraints again at execution.
Signing an operation does not approve arbitrary code, release or rule promotion.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from pathlib import PurePosixPath

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .policy import PolicyError
from .rulepack import canonical_json

SCHEMA = "UCIE_OWNER_UNATTENDED_OPERATION_GRANT_V1"
REPO = "tmdrkdtn1-project/UCIE"
TARGETS = {
    "GIT_BRANCH_PUBLISH": REPO,
    "C40_RECOVERY": "UCIE_C40_TUNNEL",
    "RULE_SHADOW_REVIEW": "UCIE_PUBLIC_RULE_SHADOW",
}
GRANT_FIELDS = frozenset({
    "schema", "project_id", "audience", "operation", "target",
    "task_id", "sequence", "nonce", "revision_sha",
    "issued_at", "expires_at",
})
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
NONCE = re.compile(r"[0-9a-f]{32}\Z")
TASK = re.compile(r"UCIE-[A-Z0-9][A-Z0-9_-]{5,63}\Z")
BRANCH = re.compile(r"automation/ucie-[a-z0-9][a-z0-9-]{2,50}\Z")
FORBIDDEN_NAMES = frozenset({
    ".env", ".git", ".gitmodules", "credentials", "secrets", "id_rsa",
    "id_ed25519", "settings.local.json", "token", "key.pem",
})
ALLOWED_PREFIXES = ("src/ucie_miner/", "src/ucie_public/", "scripts/",
                    "docs/", "tests/")
ALLOWED_SUFFIXES = frozenset({".py", ".ps1", ".md", ".json", ".txt"})
MAX_GRANT_BYTES = 2048
MAX_CHANGED_PATHS = 25
MAX_GRANT_LIFETIME = timedelta(minutes=15)


def _timestamp(s: object) -> datetime:
    if type(s) is not str or len(s) > 32 or not s.endswith("Z"):
        raise PolicyError("UCIE grant requires canonical UTC timestamp")
    try:
        value = datetime.fromisoformat(s[:-1] + "+00:00")
    except ValueError as exc:
        raise PolicyError("invalid UCIE grant timestamp") from exc
    if value.utcoffset() != timedelta(0) or value.microsecond:
        raise PolicyError("ambiguous UCIE grant timestamp")
    if value.strftime("%Y-%m-%dT%H:%M:%SZ") != s:
        raise PolicyError("noncanonical UCIE grant timestamp")
    return value


def verify_owner_operation_grant(
    signed_bytes: bytes, signature: bytes, trusted_public_key_pem: bytes, *,
    last_consumed_sequence: int, at_time: datetime | None = None,
) -> dict:
    """Verify strictly scoped detached Ed25519 owner authorization.

    The serial is an input from a separately trusted, durable *host* store;
    this read-only verifier cannot create a replay-resistant transaction.
    The executor must atomically claim serial+nonce before any side effect.
    """
    if (type(signed_bytes) is not bytes or
            not 1 <= len(signed_bytes) <= MAX_GRANT_BYTES or
            type(signature) is not bytes or len(signature) != 64 or
            type(trusted_public_key_pem) is not bytes or
            not 1 <= len(trusted_public_key_pem) <= 4096 or
            type(last_consumed_sequence) is not int or
            not 0 <= last_consumed_sequence <= 2**63 - 2):
        raise PolicyError("UCIE grant envelope or durable sequence invalid")
    try:
        key = serialization.load_pem_public_key(trusted_public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            raise PolicyError("UCIE owner trust key must be Ed25519")
        key.verify(signature, signed_bytes)
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise PolicyError("untrusted UCIE owner grant signature") from exc
    try:
        def reject_duplicate(pairs):
            result = {}
            for name, value in pairs:
                if name in result:
                    raise ValueError("duplicate signed grant field")
                result[name] = value
            return result
        data = json.loads(signed_bytes.decode("utf-8"),
                          object_pairs_hook=reject_duplicate)
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("invalid UCIE signed grant JSON") from exc
    if (type(data) is not dict or set(data) != GRANT_FIELDS or
            canonical_json(data) != signed_bytes or
            data["schema"] != SCHEMA or data["project_id"] != "UCIE" or
            data["audience"] != "UCIE_OWNER_ONLY" or
            type(data["operation"]) is not str or
            data["operation"] not in TARGETS or
            data["target"] != TARGETS[data["operation"]] or
            type(data["sequence"]) is not int or
            not last_consumed_sequence < data["sequence"] <= 2**63 - 1 or
            type(data["task_id"]) is not str or not TASK.fullmatch(data["task_id"]) or
            type(data["nonce"]) is not str or not NONCE.fullmatch(data["nonce"]) or
            type(data["revision_sha"]) is not str or
            not SHA40.fullmatch(data["revision_sha"])):
        raise PolicyError("UCIE signed grant wrong scope or replay")
    now = datetime.now(timezone.utc) if at_time is None else at_time
    if (not isinstance(now, datetime) or now.tzinfo is None or
            now.utcoffset() != timedelta(0)):
        raise PolicyError("UCIE approval clock must be UTC")
    issued, expires = _timestamp(data["issued_at"]), _timestamp(data["expires_at"])
    if (issued > now + timedelta(seconds=60) or
            expires <= now or expires <= issued or
            expires - issued > MAX_GRANT_LIFETIME):
        raise PolicyError("UCIE signed grant expired or improperly dated")
    # No secret, signature or trusted-key material is returned.
    return {
        "schema": SCHEMA,
        "operation": data["operation"],
        "target": data["target"],
        "task_id": data["task_id"],
        "sequence": data["sequence"],
        "nonce": data["nonce"],
        "revision_sha": data["revision_sha"],
        "grant_sha256": hashlib.sha256(signed_bytes).hexdigest(),
        "expires_at": data["expires_at"],
        "status": "SIGNED_SCOPE_VERIFIED_EXECUTION_NOT_AUTHORIZED",
        "durable_replay_claim_performed": False,
        "operation_executed": False,
        "rule_automatically_promoted": False,
    }


def _path_allowed(value: object) -> bool:
    if type(value) is not str or not 1 <= len(value) <= 160:
        return False
    if ("\\" in value or "\x00" in value or any(ord(c) < 32 for c in value)
            or value.startswith("/") or "//" in value):
        return False
    parts = value.split("/")
    if (any(p in ("", ".", "..") for p in parts) or
            any(p.casefold() in FORBIDDEN_NAMES or
                "secret" in p.casefold() or "credential" in p.casefold() or
                "token" in p.casefold() for p in parts)):
        return False
    path = PurePosixPath(value)
    return value.startswith(ALLOWED_PREFIXES) and path.suffix in ALLOWED_SUFFIXES


def preview_git_branch_publish(grant: dict, observed: dict) -> dict:
    """Pure preflight. NO git/subprocess, network, filesystem, or token use."""
    if (type(grant) is not dict or
            grant.get("status") != "SIGNED_SCOPE_VERIFIED_EXECUTION_NOT_AUTHORIZED" or
            grant.get("operation") != "GIT_BRANCH_PUBLISH" or
            grant.get("target") != REPO or
            type(observed) is not dict or
            set(observed) != {
                "repository", "base_sha", "branch", "changed_paths",
                "root_is_ucie", "worktree_clean_before_edit",
                "all_paths_regular_nonlinks", "protected_paths_unchanged",
                "secrets_scan_passed", "offline_tests_passed",
                "remote_owner_verified", "branch_nonexistent",
                "credentials_owner_scoped",
            }):
        raise PolicyError("untrusted UCIE Git publish observation")
    paths = observed["changed_paths"]
    if (observed["repository"] != REPO or
            observed["base_sha"] != grant["revision_sha"] or
            type(observed["branch"]) is not str or
            BRANCH.fullmatch(observed["branch"]) is None or
            type(paths) is not list or not 1 <= len(paths) <= MAX_CHANGED_PATHS or
            len(set(map(str, paths))) != len(paths) or
            not all(_path_allowed(p) for p in paths) or
            any(type(observed[k]) is not bool or observed[k] is not True
                for k in (
                    "root_is_ucie", "worktree_clean_before_edit",
                    "all_paths_regular_nonlinks", "protected_paths_unchanged",
                    "secrets_scan_passed", "offline_tests_passed",
                    "remote_owner_verified", "branch_nonexistent",
                    "credentials_owner_scoped",
                ))):
        raise PolicyError("UCIE Git publish preflight denied")
    return {
        "status": "UCIE_GIT_PREFLIGHT_READY_NO_PUSH",
        "task_id": grant["task_id"],
        "branch": observed["branch"],
        "base_sha": observed["base_sha"],
        "changed_path_count": len(paths),
        "signed_grant_sha256": grant["grant_sha256"],
        "os_durable_replay_claim_required": True,
        "git_commit_performed": False,
        "git_push_performed": False,
        "pr_created": False,
        "production_deployed": False,
    }


def preview_c40_recovery(grant: dict, observed: dict) -> dict:
    """Pure recovery plan; caller may not mistake a PID for functional health."""
    required = {
        "service_identity", "exact_binary_and_profile_sha_match",
        "owner_process_identity_verified", "single_owner_lock_held",
        "functional_mcp_probe_failed", "old_process_exited",
        "active_miner_jobs_zero", "cooldown_elapsed", "prior_attempts",
    }
    if (type(grant) is not dict or
            grant.get("status") != "SIGNED_SCOPE_VERIFIED_EXECUTION_NOT_AUTHORIZED" or
            grant.get("operation") != "C40_RECOVERY" or
            grant.get("target") != "UCIE_C40_TUNNEL" or
            type(observed) is not dict or set(observed) != required or
            observed["service_identity"] != "UCIE_C40_TUNNEL" or
            type(observed["prior_attempts"]) is not int or
            not 0 <= observed["prior_attempts"] < 2 or
            any(type(observed[k]) is not bool or observed[k] is not True
                for k in required - {"service_identity", "prior_attempts"})):
        raise PolicyError("UCIE C40 restart unsafe or not independently verified")
    return {
        "status": "UCIE_C40_RESTART_PREFLIGHT_READY_NO_RESTART",
        "task_id": grant["task_id"],
        "signed_grant_sha256": grant["grant_sha256"],
        "os_durable_replay_claim_required": True,
        "restart_performed": False,
        "functional_recovery_verified": False,
        "new_tunnel_registered": False,
    }


def preview_rule_shadow(grant: dict) -> dict:
    if (type(grant) is not dict or
            grant.get("status") != "SIGNED_SCOPE_VERIFIED_EXECUTION_NOT_AUTHORIZED" or
            grant.get("operation") != "RULE_SHADOW_REVIEW" or
            grant.get("target") != "UCIE_PUBLIC_RULE_SHADOW"):
        raise PolicyError("UCIE shadow review approval missing")
    return {
        "status": "UCIE_SHADOW_REVIEW_PREFLIGHT_ONLY_NO_PROMOTION",
        "task_id": grant["task_id"],
        "automatic_rule_promotions": 0,
        "owner_release_approval": False,
        "rulepack_signed": False,
        "operation_executed": False,
    }
