"""Explicitly armed, owner-signed UCIE Draft-PR publisher integration.

This is a CODE PATH, not an installed service. Every call needs fresh owner
operation + manifest signatures, a separately pinned host signer and one-use
local claim. GitHub credentials never auto-load. Host signer must be stored in
an owner-protected OS trust boundary, with external anti-rollback enforcement.
No main push, force-update, merge, Rulepack or Windows process actions.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .policy import PolicyError
from .rulepack import canonical_json
from .unattended_github import (
    GH_API_REPO, verify_signed_publish_bundle,
)
from .unattended_github_http import UCIERestrictedGitHubHTTP
from .unattended_journal import claim_owner_grant_once
from .unattended_ops import REPO, SHA40, SHA64, _timestamp

TICKET_SCHEMA = "UCIE_WINDOWS_OWNER_HOST_TICKET_V1"
TICKET_KEYS = frozenset({
    "schema", "project_id", "audience", "task_id", "grant_sha256",
    "manifest_sha256", "branch", "base_sha", "external_epoch_sha256",
    "host_sid_sha256", "issued_at", "expires_at",
})


def verify_signed_host_ticket(raw: bytes, sig: bytes, host_public_pem: bytes,
                              expected: dict, *, at_time=None) -> dict:
    """Verify a separately provisioned host authority (NOT self-attestation).

    The trusted HOST public key must come from an OS-protected pinned file,
    not the task envelope. Authenticating an assertion does not independently
    prove that the host ACL, checkpoint, or OS process is currently healthy.
    """
    if (type(raw) is not bytes or not 1 <= len(raw) <= 2048 or
            type(sig) is not bytes or len(sig) != 64 or
            type(host_public_pem) is not bytes or
            not 1 <= len(host_public_pem) <= 4096 or
            type(expected) is not dict):
        raise PolicyError("UCIE host ticket envelope invalid")
    try:
        host_key = serialization.load_pem_public_key(host_public_pem)
        if not isinstance(host_key, Ed25519PublicKey):
            raise PolicyError("UCIE host signer not Ed25519")
        host_key.verify(sig, raw)
    except (TypeError, ValueError, InvalidSignature) as exc:
        raise PolicyError("UCIE host ticket signature invalid") from exc
    def unique(pairs):
        obj = {}
        for key, val in pairs:
            if key in obj:
                raise ValueError("duplicate host ticket key")
            obj[key] = val
        return obj
    try:
        ticket = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise PolicyError("UCIE host ticket invalid JSON") from exc
    if (type(ticket) is not dict or set(ticket) != TICKET_KEYS or
            canonical_json(ticket) != raw or
            ticket["schema"] != TICKET_SCHEMA or
            ticket["project_id"] != "UCIE" or
            ticket["audience"] != "UCIE_OWNER_ONLY" or
            any(ticket.get(k) != expected.get(k) for k in (
                "task_id", "grant_sha256", "manifest_sha256", "branch", "base_sha")) or
            type(ticket["external_epoch_sha256"]) is not str or
            SHA64.fullmatch(ticket["external_epoch_sha256"]) is None or
            type(ticket["host_sid_sha256"]) is not str or
            SHA64.fullmatch(ticket["host_sid_sha256"]) is None):
        raise PolicyError("UCIE host ticket scope or binding invalid")
    now = datetime.now(timezone.utc) if at_time is None else at_time
    if (not isinstance(now, datetime) or now.tzinfo is None or
            now.utcoffset() != timedelta(0)):
        raise PolicyError("UTC host verification required")
    issued = _timestamp(ticket["issued_at"])
    expires = _timestamp(ticket["expires_at"])
    if (issued > now + timedelta(seconds=30) or expires <= now or
            expires <= issued or expires - issued > timedelta(minutes=2)):
        raise PolicyError("UCIE host execution ticket expired or excessive")
    return {
        "status": "UCIE_SIGNED_HOST_TICKET_BOUND_OS_CHECKPOINT_NOT_RECHECKED",
        "host_ticket_sha256": hashlib.sha256(raw).hexdigest(),
        "external_epoch_sha256": ticket["external_epoch_sha256"],
        "host_sid_sha256": ticket["host_sid_sha256"],
        "task_id": ticket["task_id"],
        "operation_executed": False,
    }


def _remote_still_exact(transport, verified):
    root = GH_API_REPO
    main = transport("GET", root + "/git/ref/heads/main")
    if (main.get("ref") != "refs/heads/main" or
            type(main.get("object")) is not dict or
            main["object"].get("sha") != verified["base_sha"]):
        raise PolicyError("UCIE remote main SHA changed")
    commit = transport("GET", root + "/git/commits/" + verified["base_sha"])
    tree = commit.get("tree") if type(commit) is dict else None
    if type(tree) is not dict or type(tree.get("sha")) is not str or SHA40.fullmatch(tree["sha"]) is None:
        raise PolicyError("UCIE upstream tree not authenticated")
    existing = transport("GET", root + "/git/ref/heads/" + verified["branch"])
    if existing != {"http_status": 404}:
        raise PolicyError("UCIE branch already exists; reconcile, never overwrite")
    return tree["sha"]


def publish_one_owner_signed_draft(
    grant_raw: bytes, grant_sig: bytes, manifest_raw: bytes, manifest_sig: bytes,
    owner_public_pem: bytes, host_ticket_raw: bytes, host_ticket_sig: bytes,
    host_trust_public_pem: bytes, files: dict[str, bytes], journal_dir: Path,
    github_token: str, *, armed: bool = False, at_time=None,
    transport=None,
) -> dict:
    """Run one bounded UCIE GitHub Draft PR publication after trust bootstrap.

    Default unarmed. A production owner-host caller must first verify exact
    SID/ACL, pinned host trust key, external monotonic revocation checkpoint,
    short-lived repo-scoped token and safe public-only source review. Test
    transport may be supplied *only* with synthetic_only marker. No automatic
    retry is safe after atomic claim; reconcile ambiguous remote state.
    """
    if armed is not True:
        raise PolicyError("UCIE live publisher disarmed until owner host installation")
    verified = verify_signed_publish_bundle(
        grant_raw, grant_sig, manifest_raw, manifest_sig, owner_public_pem,
        files, last_consumed_sequence=0, at_time=at_time)
    # Caller must supply separate independently trusted host signer; do not
    # allow the task's OWNER key to substitute the HOST's OS-protected key.
    if owner_public_pem == host_trust_public_pem:
        raise PolicyError("owner and host signing boundaries must differ")
    ticket = verify_signed_host_ticket(
        host_ticket_raw, host_ticket_sig, host_trust_public_pem,
        verified, at_time=at_time)
    # Explicit credential input; no environment or git credential helpers.
    # Even a mock transport must satisfy the token shape first.
    if (type(github_token) is not str or not 20 <= len(github_token) <= 1200 or
            not github_token.isascii() or any(c.isspace() for c in github_token)):
        raise PolicyError("owner GitHub credential injection invalid")
    if transport is not None and getattr(transport, "ucie_synthetic_only", None) is not True:
        raise PolicyError("injected live GitHub transport forbidden")
    api = transport if transport is not None else UCIERestrictedGitHubHTTP(
        github_token, branch=verified["branch"], base_sha=verified["base_sha"],
        allow_live=True)
    # Read-only remote preflight BEFORE consuming the one-shot grant.
    tree_sha = _remote_still_exact(api, verified)
    receipt = claim_owner_grant_once(
        journal_dir, grant_raw, grant_sig, owner_public_pem, at_time=at_time)
    if (receipt["task_id"] != verified["task_id"] or
            receipt["grant_sha256"] != verified["grant_sha256"] or
            receipt["sequence"] != verified["sequence"]):
        raise PolicyError("UCIE host durable grant claim mismatch")

    root = GH_API_REPO
    entries = []
    for path in sorted(files):
        blob = api("POST", root + "/git/blobs", {
            "content": base64.b64encode(files[path]).decode("ascii"),
            "encoding": "base64"})
        if type(blob.get("sha")) is not str or SHA40.fullmatch(blob["sha"]) is None:
            raise PolicyError("GitHub blob creation did not attest SHA")
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = api("POST", root + "/git/trees", {
        "base_tree": tree_sha, "tree": entries})
    if type(tree.get("sha")) is not str or SHA40.fullmatch(tree["sha"]) is None:
        raise PolicyError("GitHub tree creation did not attest SHA")
    commit = api("POST", root + "/git/commits", {
        "message": verified["commit_message"], "tree": tree["sha"],
        "parents": [verified["base_sha"]]})
    newsha = commit.get("sha")
    if type(newsha) is not str or SHA40.fullmatch(newsha) is None:
        raise PolicyError("GitHub commit SHA not authenticated")
    created = api("POST", root + "/git/refs", {
        "ref": "refs/heads/" + verified["branch"], "sha": newsha})
    if (created.get("ref") != "refs/heads/" + verified["branch"] or
            type(created.get("object")) is not dict or
            created["object"].get("sha") != newsha):
        raise PolicyError("UCIE created branch inconsistent; reconcile manually")
    pr = api("POST", root + "/pulls", {
        "title": verified["pr_title"],
        "head": verified["branch"], "base": "main", "draft": True,
        "body": "UCIE owner-signed bounded public-only candidate. CI and independent review pending; no rule approval or auto-merge.",
        "maintainer_can_modify": False})
    if (type(pr.get("number")) is not int or pr["number"] <= 0 or
            type(pr.get("base")) is not dict or pr["base"].get("ref") != "main" or
            type(pr.get("head")) is not dict or
            pr["head"].get("ref") != verified["branch"] or
            pr.get("draft") is not True):
        raise PolicyError("UCIE GitHub PR metadata mismatch; manual review")
    synthetic = transport is not None
    return {
        "status": ("UCIE_SYNTHETIC_OWNER_DRAFT_SEQUENCE_ONLY" if synthetic
                   else "UCIE_GITHUB_DRAFT_API_RESPONSE_OBSERVED_POST_CI_PENDING"),
        "task_id": verified["task_id"],
        "branch": verified["branch"],
        "commit_sha": newsha,
        "pr_number": pr["number"],
        "grant_sha256": verified["grant_sha256"],
        "host_ticket_sha256": ticket["host_ticket_sha256"],
        "journal_claimed": True,
        "network_calls_real": not synthetic,
        "remote_pr_independently_rechecked": False,
        "owner_host_acl_independently_tested_here": False,
        "external_anchor_independently_rechecked_here": False,
        "ci_tested": False,
        "rulepack_approved": False,
        "auto_merged": False,
        "production_approved": False,
    }
