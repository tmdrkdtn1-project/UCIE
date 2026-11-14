"""Time-bounded standing owner policies for UCIE-only Draft PR and C40 recovery.

Pure signed owner policy verification. Not an executor, not a grant to sign
Rulepacks, not OS-protected revocation storage. Trusted externally maintained
epoch/checkpoint is required at every use.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from .policy import PolicyError
from .rulepack import canonical_json
from .unattended_ops import REPO, SHA40, SHA64, _timestamp, _path_allowed
from .unattended_c40_supervisor import SCHEMA as WATCHDOG_SCHEMA

SCHEMA = "UCIE_OWNER_REVOKABLE_STANDING_POLICY_V1"
FIELDS = frozenset({
    "schema", "project_id", "audience", "policy_id", "sequence",
    "purpose", "target", "issued_at", "expires_at",
    "external_revocation_epoch_sha256", "scope",
})
PURPOSES = frozenset({"GITHUB_DRAFT_PUBLISH", "C40_AUTORECOVERY"})
POLICY_ID = re.compile(r"UCIE-POLICY-[A-Z0-9-]{6,48}\Z")
MAX_BYTES = 3072
GIT_SCOPE = {
    "base_branch": "main",
    "branch_prefix": "automation/ucie-",
    "allowed_roots": [
        "src/ucie_miner/", "src/ucie_public/", "docs/", "tests/",
    ],
    "max_files_per_pr": 20,
    "max_prs_per_day": 3,
    "draft_only": True,
    "auto_merge": False,
}
C40_FIELDS = frozenset({
    "binary_sha256", "profile_sha256", "max_restarts_per_hour",
    "max_restarts_per_day", "cooldown_minutes", "new_tunnel_allowed",
})


def verify_standing_ucie_policy(
    raw: bytes, sig: bytes, pub_pem: bytes, *, external_epoch_sha256: str,
    last_policy_sequence: int, at_time: datetime | None = None,
) -> dict:
    if (type(raw) is not bytes or not 1 <= len(raw) <= MAX_BYTES or
            type(sig) is not bytes or len(sig) != 64 or
            type(pub_pem) is not bytes or not 1 <= len(pub_pem) <= 4096 or
            type(external_epoch_sha256) is not str or
            SHA64.fullmatch(external_epoch_sha256) is None or
            type(last_policy_sequence) is not int or
            not 0 <= last_policy_sequence <= 2**63 - 2):
        raise PolicyError("UCIE standing policy invalid envelope or external anchor")
    try:
        key = serialization.load_pem_public_key(pub_pem)
        if not isinstance(key, Ed25519PublicKey):
            raise PolicyError("wrong UCIE standing policy trust key")
        key.verify(sig, raw)
    except (ValueError, InvalidSignature, TypeError) as exc:
        raise PolicyError("UCIE standing policy owner signature invalid") from exc
    def unique(pairs):
        out = {}
        for name, value in pairs:
            if name in out:
                raise ValueError("duplicate policy JSON field")
            out[name] = value
        return out
    try:
        policy = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeError, ValueError) as exc:
        raise PolicyError("malformed UCIE standing policy JSON") from exc
    if (type(policy) is not dict or
            set(policy) != FIELDS or canonical_json(policy) != raw or
            policy["schema"] != SCHEMA or
            policy["project_id"] != "UCIE" or
            policy["audience"] != "UCIE_OWNER_ONLY" or
            type(policy["policy_id"]) is not str or
            POLICY_ID.fullmatch(policy["policy_id"]) is None or
            type(policy["sequence"]) is not int or
            not last_policy_sequence < policy["sequence"] <= 2**63 - 1 or
            policy["external_revocation_epoch_sha256"] != external_epoch_sha256 or
            policy["purpose"] not in PURPOSES or
            type(policy["scope"]) is not dict):
        raise PolicyError("UCIE standing policy revoked, stale or foreign")
    now = datetime.now(timezone.utc) if at_time is None else at_time
    if (not isinstance(now, datetime) or now.tzinfo is None or
            now.utcoffset() != timedelta(0)):
        raise PolicyError("UTC required for UCIE policy review")
    issued, expires = _timestamp(policy["issued_at"]), _timestamp(policy["expires_at"])
    duration = timedelta(days=7 if policy["purpose"] == "GITHUB_DRAFT_PUBLISH" else 30)
    if (issued > now + timedelta(seconds=60) or
            expires <= now or expires <= issued or expires - issued > duration):
        raise PolicyError("UCIE standing policy expired or overlong")
    if policy["purpose"] == "GITHUB_DRAFT_PUBLISH":
        if policy["target"] != REPO or policy["scope"] != GIT_SCOPE:
            raise PolicyError("UCIE standing Git policy exceeds Draft PR permissions")
    else:
        c40 = policy["scope"]
        if (policy["target"] != "UCIE_C40_TUNNEL" or
                set(c40) != C40_FIELDS or
                type(c40["binary_sha256"]) is not str or
                SHA64.fullmatch(c40["binary_sha256"]) is None or
                type(c40["profile_sha256"]) is not str or
                SHA64.fullmatch(c40["profile_sha256"]) is None or
                c40["max_restarts_per_hour"] != 2 or
                c40["max_restarts_per_day"] != 4 or
                c40["cooldown_minutes"] != 20 or
                c40["new_tunnel_allowed"] is not False):
            raise PolicyError("UCIE C40 standing policy exceeds recovery budget")
    return {
        "status": "UCIE_OWNER_STANDING_POLICY_VERIFIED_NO_EXECUTION",
        "policy_sha256": hashlib.sha256(raw).hexdigest(),
        "policy_id": policy["policy_id"],
        "sequence": policy["sequence"],
        "purpose": policy["purpose"],
        "target": policy["target"],
        "expires_at": policy["expires_at"],
        "revocation_epoch_matched_external": True,
        "external_epoch_storage_independently_verified": False,
        "host_owner_acl_verified": False,
        "auto_merge_authorized": False,
        "auto_rule_promotion_authorized": False,
        "operation_executed": False,
    }


def preview_standing_git_publish(policy: dict, files: list[str], *,
                                 prs_today: int, approved_ci: bool) -> dict:
    if (type(policy) is not dict or
            policy.get("status") != "UCIE_OWNER_STANDING_POLICY_VERIFIED_NO_EXECUTION" or
            policy.get("purpose") != "GITHUB_DRAFT_PUBLISH" or
            policy.get("target") != REPO or
            type(files) is not list or not 1 <= len(files) <= 20 or
            len(set(files)) != len(files) or
            any(not _path_allowed(p) or p.startswith("scripts/") for p in files) or
            type(prs_today) is not int or not 0 <= prs_today < 3 or
            approved_ci is not True):
        raise PolicyError("standing UCIE Git publish conditions not satisfied")
    return {
        "status": "UCIE_STANDING_DRAFT_PR_PREFLIGHT_ONLY",
        "policy_sha256": policy["policy_sha256"],
        "changed_files": len(files),
        "draft_only": True,
        "main_push": False,
        "automatic_merge": False,
        "operating_database_writes": 0,
        "real_github_requests": 0,
    }


def preview_standing_c40_recovery(policy: dict, watchdog: dict, *,
                                  restarts_last_day: int) -> dict:
    if (type(policy) is not dict or
            policy.get("status") != "UCIE_OWNER_STANDING_POLICY_VERIFIED_NO_EXECUTION" or
            policy.get("purpose") != "C40_AUTORECOVERY" or
            policy.get("target") != "UCIE_C40_TUNNEL" or
            type(watchdog) is not dict or
            watchdog.get("schema") != WATCHDOG_SCHEMA or
            watchdog.get("status") != "UCIE_C40_OWNER_SIGNED_RECOVERY_REQUIRED" or
            type(restarts_last_day) is not int or
            not 0 <= restarts_last_day < 4):
        raise PolicyError("C40 standing recovery budget/health gate refused")
    return {
        "status": "UCIE_STANDING_C40_RECOVERY_PREFLIGHT_ONLY",
        "policy_sha256": policy["policy_sha256"],
        "requires_separate_host_process_and_functional_postprobe": True,
        "service_restarted": False,
        "new_tunnel_registered": False,
        "other_project_accesses": 0,
    }
