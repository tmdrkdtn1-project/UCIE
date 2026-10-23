"""UCIE-only signed GitHub branch/PR publisher, no OS agent installation.

The owner signs BOTH a short-lived UCIE operation grant and exact file manifest.
Transport is explicitly injected by a separately authorized host; no implicit
network access, no arbitrary shell, never edits main and never auto-merges.
A host must independently prove ACL/monotonic anti-rollback and claim the grant
before a real transport is supplied. Synthetic tests use in-memory transport.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import PurePosixPath
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .policy import PolicyError
from .rulepack import canonical_json
from .unattended_ops import (
    REPO, BRANCH, SHA40, SHA64, _path_allowed, verify_owner_operation_grant,
)

MANIFEST_SCHEMA = "UCIE_GITHUB_SIGNED_PUBLISH_MANIFEST_V1"
MANIFEST_KEYS = frozenset({
    "schema", "task_id", "grant_sha256", "repository", "base_sha",
    "branch", "files_sha256", "commit_message", "pr_title",
})
MAX_FILES = 25
MAX_FILE_BYTES = 65536
MAX_TOTAL_BYTES = 262144
MAX_MANIFEST_BYTES = 4096
GH_API_REPO = "/repos/tmdrkdtn1-project/UCIE"


def _read_json(payload: bytes, size: int) -> dict:
    if type(payload) is not bytes or not 1 <= len(payload) <= size:
        raise PolicyError("UCIE signed publisher envelope invalid")
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate signed publisher field")
            out[key] = value
        return out
    try:
        data = json.loads(payload.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise PolicyError("invalid UCIE signed publisher JSON") from exc
    if type(data) is not dict or canonical_json(data) != payload:
        raise PolicyError("publisher JSON not canonical")
    return data


def verify_signed_publish_bundle(
    grant_bytes: bytes, grant_signature: bytes,
    manifest_bytes: bytes, manifest_signature: bytes,
    trust_public_pem: bytes, files: dict, *,
    last_consumed_sequence: int, at_time: datetime | None = None,
) -> dict:
    """Pure exact-content owner verification; no filesystem or HTTP."""
    grant = verify_owner_operation_grant(
        grant_bytes, grant_signature, trust_public_pem,
        last_consumed_sequence=last_consumed_sequence, at_time=at_time)
    if grant["operation"] != "GIT_BRANCH_PUBLISH" or grant["target"] != REPO:
        raise PolicyError("not a UCIE Git publication grant")
    if type(manifest_signature) is not bytes or len(manifest_signature) != 64:
        raise PolicyError("invalid publisher signature")
    try:
        trust = serialization.load_pem_public_key(trust_public_pem)
        if not isinstance(trust, Ed25519PublicKey):
            raise PolicyError("wrong UCIE publisher trust key")
        trust.verify(manifest_signature, manifest_bytes)
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise PolicyError("untrusted UCIE signed publish manifest") from exc
    manifest = _read_json(manifest_bytes, MAX_MANIFEST_BYTES)
    if (set(manifest) != MANIFEST_KEYS or
            manifest["schema"] != MANIFEST_SCHEMA or
            manifest["repository"] != REPO or
            manifest["task_id"] != grant["task_id"] or
            manifest["grant_sha256"] != grant["grant_sha256"] or
            manifest["base_sha"] != grant["revision_sha"] or
            type(manifest["branch"]) is not str or
            BRANCH.fullmatch(manifest["branch"]) is None or
            type(manifest["commit_message"]) is not str or
            not 1 <= len(manifest["commit_message"]) <= 100 or
            not manifest["commit_message"].startswith("ucie(automation): ") or
            "\n" in manifest["commit_message"] or
            type(manifest["pr_title"]) is not str or
            not 1 <= len(manifest["pr_title"]) <= 100 or
            not manifest["pr_title"].startswith("UCIE automation: ") or
            "\n" in manifest["pr_title"]):
        raise PolicyError("UCIE signed publication mismatches owner grant")
    expected = manifest["files_sha256"]
    if (type(files) is not dict or type(expected) is not dict or
            not 1 <= len(files) <= MAX_FILES or set(expected) != set(files)):
        raise PolicyError("unexpected UCIE source patch files")
    total = 0
    for path, body in files.items():
        if (not _path_allowed(path) or type(body) is not bytes or
                not 1 <= len(body) <= MAX_FILE_BYTES or
                type(expected[path]) is not str or
                SHA64.fullmatch(expected[path]) is None or
                hashlib.sha256(body).hexdigest() != expected[path]):
            raise PolicyError("source file outside signed UCIE file digest")
        # Only UTF-8 text enters the publisher; never binary/executable.
        try:
            body.decode("utf-8")
        except UnicodeError as exc:
            raise PolicyError("publisher accepts UTF-8 text only") from exc
        total += len(body)
    if total > MAX_TOTAL_BYTES:
        raise PolicyError("UCIE publisher source payload over limit")
    return {
        "status": "UCIE_SIGNED_GITHUB_BUNDLE_VERIFIED_NO_NETWORK",
        "task_id": grant["task_id"],
        "sequence": grant["sequence"],
        "repository": REPO,
        "base_sha": grant["revision_sha"],
        "branch": manifest["branch"],
        "files_sha256": dict(sorted(expected.items())),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "grant_sha256": grant["grant_sha256"],
        "commit_message": manifest["commit_message"],
        "pr_title": manifest["pr_title"],
        "content_files_count": len(files),
        "network_calls": 0,
        "main_changed": False,
        "owner_host_credential_verified": False,
        "external_rollback_anchor_verified": False,
        "remote_branch_published": False,
    }


def plan_github_publish(verified: dict, *, observed: dict) -> dict:
    """Pure remote-observation binding: no API calls."""
    if (type(verified) is not dict or
            verified.get("status") != "UCIE_SIGNED_GITHUB_BUNDLE_VERIFIED_NO_NETWORK" or
            type(observed) is not dict or set(observed) != {
                "repository", "remote_main_sha", "remote_main_tree_sha",
                "branch_exists", "ci_matrix_green", "owner_credentials_scoped",
                "secrets_scan_clean", "protected_paths_unchanged",
            } or observed["repository"] != REPO or
            observed["remote_main_sha"] != verified["base_sha"] or
            type(observed["remote_main_tree_sha"]) is not str or
            SHA40.fullmatch(observed["remote_main_tree_sha"]) is None or
            observed["branch_exists"] is not False or
            any(observed[key] is not True for key in (
                "ci_matrix_green", "owner_credentials_scoped",
                "secrets_scan_clean", "protected_paths_unchanged"))):
        raise PolicyError("UCIE remote branch publisher preflight NO_GO")
    return {
        "status": "UCIE_GITHUB_PUBLISH_PLAN_ONLY_NO_REMOTE_MUTATION",
        "repository": REPO,
        "branch": verified["branch"],
        "base_sha": verified["base_sha"],
        "base_tree_sha": observed["remote_main_tree_sha"],
        "file_count": verified["content_files_count"],
        "manifest_sha256": verified["manifest_sha256"],
        "required_owner_grant_sha256": verified["grant_sha256"],
        "remote_write_performed": False,
        "production_approved": False,
    }


def simulate_github_publish(verified: dict, files: dict, transport) -> dict:
    """Stage actual GitHub REST method contracts through an INJECTED transport.

    This function must only be called with a UCIE-owned disposable *mock*.
    It is not the live host publisher. No default urllib or token accessor,
    and it cannot register or use credentials. GitHub create-ref and PR
    contract is exercised, but the result remains SYNTHETIC ONLY.
    """
    if (type(verified) is not dict or
            verified.get("status") != "UCIE_SIGNED_GITHUB_BUNDLE_VERIFIED_NO_NETWORK" or
            type(files) is not dict or
            set(files) != set(verified["files_sha256"]) or
            transport is None or not callable(transport) or
            getattr(transport, "ucie_synthetic_only", None) is not True):
        raise PolicyError("UCIE publisher simulation input mismatch")
    for p, b in files.items():
        if type(b) is not bytes or hashlib.sha256(b).hexdigest() != verified["files_sha256"][p]:
            raise PolicyError("publisher payload changed after signature check")
    def call(method, path, payload=None):
        if type(path) is not str or not path.startswith(GH_API_REPO + "/"):
            raise PolicyError("foreign GitHub API route denied")
        result = transport(method, path, payload)
        if type(result) is not dict:
            raise PolicyError("malformed GitHub response in synthetic publisher")
        return result

    main = call("GET", GH_API_REPO + "/git/ref/heads/main")
    if (main.get("ref") != "refs/heads/main" or
            type(main.get("object")) is not dict or
            main["object"].get("sha") != verified["base_sha"]):
        raise PolicyError("remote main has moved")
    commit = call("GET", GH_API_REPO + "/git/commits/" + verified["base_sha"])
    if (type(commit.get("tree")) is not dict or
            type(commit["tree"].get("sha")) is not str or
            SHA40.fullmatch(commit["tree"]["sha"]) is None):
        raise PolicyError("remote base tree invalid")
    # A collision is not treated as permission to modify a prior branch.
    collision = call("GET", GH_API_REPO + "/git/ref/heads/" + verified["branch"])
    if collision.get("http_status") != 404:
        raise PolicyError("automation branch already exists")
    entries = []
    for path in sorted(files):
        body = files[path]
        blob = call("POST", GH_API_REPO + "/git/blobs",
                    {"content": base64.b64encode(body).decode("ascii"), "encoding": "base64"})
        if type(blob.get("sha")) is not str or SHA40.fullmatch(blob["sha"]) is None:
            raise PolicyError("invalid created blob SHA")
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = call("POST", GH_API_REPO + "/git/trees", {
        "base_tree": commit["tree"]["sha"], "tree": entries})
    if type(tree.get("sha")) is not str or SHA40.fullmatch(tree["sha"]) is None:
        raise PolicyError("invalid created tree")
    created = call("POST", GH_API_REPO + "/git/commits", {
        "message": verified["commit_message"], "tree": tree["sha"],
        "parents": [verified["base_sha"]]})
    if type(created.get("sha")) is not str or SHA40.fullmatch(created["sha"]) is None:
        raise PolicyError("invalid created commit")
    ref = call("POST", GH_API_REPO + "/git/refs", {
        "ref": "refs/heads/" + verified["branch"], "sha": created["sha"]})
    if (ref.get("ref") != "refs/heads/" + verified["branch"] or
            type(ref.get("object")) is not dict or
            ref["object"].get("sha") != created["sha"]):
        raise PolicyError("created ref was not the approved UCIE branch")
    pr = call("POST", GH_API_REPO + "/pulls", {
        "title": verified["pr_title"],
        "head": verified["branch"], "base": "main", "draft": True,
        "body": "UCIE owner-signed isolated source candidate. CI and review required. "
                "No rule approval, no auto merge or deployment.",
        "maintainer_can_modify": False})
    if (type(pr.get("number")) is not int or pr["number"] <= 0 or
            pr.get("base", {}).get("ref") != "main" or
            pr.get("head", {}).get("ref") != verified["branch"] or
            pr.get("draft") is not True):
        raise PolicyError("synthetic GitHub PR response not a Draft PR")
    return {
        "status": "UCIE_SYNTHETIC_GITHUB_PUBLISH_SEQUENCE_ONLY",
        "branch": verified["branch"],
        "commit_sha": created["sha"],
        "pr_number": pr["number"],
        "transport_calls_injected": True,
        "real_github_network_requests": 0,
        "production_deployed": False,
        "automatic_rule_promotions": 0,
        "remote_write_verified": False,
    }
