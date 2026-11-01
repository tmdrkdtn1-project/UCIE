"""UCIE V0.8: explicit public source identity and official-doc-byte probes.

This module is strictly opt-in. It uses only exact public GitHub API routes
for the FIVE approved upstream repos, and official-document URLs already
admitted by V0.5 source-linked claim receipts. It never executes, stores or
interprets external code, PR bodies, page HTML, or arbitrary instructions.

Matching a merge SHA or hashing a public HTML response does NOT establish
version applicability, independent fix regression, security, legal license
approval or a signed/prepared rule. No persistent writes.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from .core import NoRedirect, MiningError
from .library_review_records_v05 import (
    CLAIM_ONLY, PUBLIC_DOC_HOSTS, _public_evidence_url,
)
from .public_discovery import SOURCES

SCHEMA = "UCIE_PUBLIC_SOURCE_EVIDENCE_PROBE_V08"
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
PR_PATH = re.compile(r"https://github\.com/([^/?#]+/[^/?#]+)/pull/([1-9][0-9]{0,9})\Z")
COMMIT_PATH = re.compile(r"https://github\.com/([^/?#]+/[^/?#]+)/commit/([0-9a-f]{40})\Z")
PR_SIZE = 262144
DOC_SIZE = 262144
GATES_NOT_VERIFIED = {
    "VERSION_APPLICABILITY": "NOT_VERIFIED",
    "LICENSE": "NOT_VERIFIED",
    "INDEPENDENT_REGRESSION": "NOT_VERIFIED",
    "SECURITY_REVIEW": "NOT_VERIFIED",
    "OWNER_SIGNOFF": "NOT_VERIFIED",
}


class ProbeError(ValueError):
    pass


def _public_get(url: str, *, max_bytes: int, json_only: bool) -> bytes:
    """Anonymous no-redirect, no-proxy, limited official bytes only."""
    if type(url) is not str or type(max_bytes) is not int or not 0 < max_bytes <= PR_SIZE:
        raise ProbeError("invalid bounded public fetch request")
    parts = urlsplit(url)
    if json_only:
        # Only the exact API URL constructed from allowlisted repo/PR/commit.
        matched = re.fullmatch(
            r"https://api\.github\.com/repos/([^/?#]+/[^/?#]+)/(?:pulls/[1-9][0-9]{0,9}|commits/[0-9a-f]{40})", url)
        if matched is None or matched.group(1) not in SOURCES:
            raise ProbeError("GitHub API route outside approved repositories")
    else:
        if (parts.scheme != "https" or parts.hostname not in PUBLIC_DOC_HOSTS
                or parts.username is not None or parts.password is not None
                or parts.port is not None or parts.query or parts.fragment
                or not re.fullmatch(r"/[A-Za-z0-9._/~:-]{1,190}", parts.path)
                or "//" in parts.path or ".." in parts.path or "%" in parts.path):
            raise ProbeError("document route outside official public hosts")
    request = urllib.request.Request(
        url, headers={
            "Accept": "application/vnd.github+json" if json_only else "text/html, text/plain;q=0.9",
            "Accept-Encoding": "identity",
            "User-Agent": "UCIE-PUBLIC-SOURCE-CHECK/0.1",
        }, method="GET")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect)
    try:
        with opener.open(request, timeout=10) as response:
            if response.status != 200:
                raise ProbeError("public source did not return HTTP 200")
            mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            allowed = {"application/json", "application/vnd.github+json"} if json_only else {
                "text/html", "text/plain", "text/markdown",
            }
            if mime not in allowed or response.headers.get("Content-Encoding", "identity") != "identity":
                raise ProbeError("unexpected public content type or encoding")
            claimed_len = response.headers.get("Content-Length")
            if claimed_len is not None and (
                    not claimed_len.isascii() or not claimed_len.isdecimal()
                    or int(claimed_len) > max_bytes):
                raise ProbeError("public content length exceeds limit")
            raw = response.read(max_bytes + 1)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError, MiningError) as exc:
        raise ProbeError("approved public endpoint unavailable") from exc
    if len(raw) > max_bytes:
        raise ProbeError("public response exceeded byte bound")
    return raw


def _get_json(url: str) -> object:
    raw = _public_get(url, max_bytes=PR_SIZE, json_only=True)
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ProbeError("invalid public API JSON") from exc


def _get_document_bytes(url: str) -> bytes:
    return _public_get(url, max_bytes=DOC_SIZE, json_only=False)


def _identity_preflight(row: object) -> tuple[str, str, str]:
    if type(row) is not dict or row.get("human_approved") is not False or row.get("export_allowed") is not False:
        raise ProbeError("unverified source-bound row required")
    sid = row.get("source_id")
    revision = row.get("revision_hint")
    url = row.get("public_url")
    if (type(sid) is not str or not sid.startswith("repo:")
            or sid[5:] not in SOURCES or type(revision) is not str
            or HEX40.fullmatch(revision) is None or type(url) is not str):
        raise ProbeError("missing pinned approved public source")
    repo = sid[5:]
    pr = PR_PATH.fullmatch(url)
    commit = COMMIT_PATH.fullmatch(url)
    if pr is not None and pr.group(1) == repo:
        return repo, "PR", str(int(pr.group(2)))
    if commit is not None and commit.group(1) == repo and commit.group(2) == revision:
        return repo, "COMMIT", revision
    raise ProbeError("public PR/commit reference is unbound or unsupported")


def _utc_timestamp(value: object) -> bool:
    if type(value) is not str or not 1 <= len(value) <= 35:
        return False
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0


def inspect_public_source_revision(row: dict, *, fetch_json=None) -> dict:
    """Actual anonymous metadata identity check; no fix semantics."""
    repo, kind, key = _identity_preflight(row)
    revision = row["revision_hint"]
    url = "https://api.github.com/repos/" + repo + (
        "/pulls/" + key if kind == "PR" else "/commits/" + key)
    fetch = _get_json if fetch_json is None else fetch_json
    try:
        data = fetch(url)
    except (ProbeError, ValueError, OSError):
        return {
            "schema": SCHEMA, "status": "PUBLIC_METADATA_UNAVAILABLE_NO_GO",
            "source_id": row["source_id"], "revision_hint": revision,
            "request_url": url, "metadata_observed": False,
            "identity_matched": False, "fix_verified": False,
            "gates": dict(GATES_NOT_VERIFIED), "auto_promoted": False,
        }
    if type(data) is not dict:
        raise ProbeError("public metadata response shape invalid")
    if kind == "PR":
        base = data.get("base")
        inner = base.get("repo") if type(base) is dict else None
        actual_repo = inner.get("full_name") if type(inner) is dict else None
        matched = (
            data.get("number") == int(key)
            and type(data.get("number")) is int
            and data.get("state") == "closed"
            and _utc_timestamp(data.get("merged_at"))
            and actual_repo == repo
            and data.get("merge_commit_sha") == revision
        )
    else:
        # A commit endpoint is scoped to the exact approved repository URL.
        matched = data.get("sha") == revision and type(data.get("sha")) is str
    return {
        "schema": SCHEMA,
        "status": (
            "PUBLIC_MERGE_IDENTITY_MATCHED_NOT_FIX_VERIFIED" if kind == "PR"
            and matched else
            "PUBLIC_COMMIT_IDENTITY_MATCHED_NOT_FIX_VERIFIED" if kind == "COMMIT"
            and matched else "PUBLIC_REVISION_MISMATCH_NO_GO"
        ),
        "source_id": row["source_id"],
        "revision_hint": revision,
        "request_url": url,
        "metadata_observed": True,
        "identity_matched": bool(matched),
        "fix_verified": False,
        "gates": dict(GATES_NOT_VERIFIED),
        "auto_promoted": False,
        "content_saved": False,
    }


def inspect_claimed_official_document(receipt: dict, row: dict, *,
                                       fetch_bytes=None) -> dict:
    """Independently compute the bytes SHA of an ALREADY SUBMITTED official URL.

    This only compares one HTTP response body against the caller's V0.5 claim.
    It does not authenticate the document author's signature, the version,
    licensing, regression, security or a release.
    """
    if (type(receipt) is not dict or type(row) is not dict
            or receipt.get("status") != CLAIM_ONLY
            or receipt.get("independent_verification") is not False
            or receipt.get("item_id") != row.get("library_item_id")
            or receipt.get("source_id") != row.get("source_id")
            or receipt.get("source_sha256") not in row.get("evidence_revision_sha256s", ())
            or type(receipt.get("claimed_document_sha256")) is not str
            or HEX64.fullmatch(receipt["claimed_document_sha256"]) is None):
        raise ProbeError("official document receipt not bound to current UCIE source")
    url = _public_evidence_url(
        receipt.get("public_evidence_url"), source_id=row["source_id"])
    if urlsplit(url).hostname not in PUBLIC_DOC_HOSTS:
        raise ProbeError("only approved official document routes eligible for byte probe")
    fetch = _get_document_bytes if fetch_bytes is None else fetch_bytes
    try:
        raw = fetch(url)
    except (ProbeError, ValueError, OSError):
        return {
            "schema": SCHEMA, "status": "PUBLIC_DOCUMENT_UNAVAILABLE_NO_GO",
            "receipt_id": receipt["receipt_id"],
            "public_content_checked": False, "claimed_sha_matched": False,
            "fix_verified": False, "gates": dict(GATES_NOT_VERIFIED),
        }
    if type(raw) is not bytes or len(raw) > DOC_SIZE:
        raise ProbeError("unbounded or non-byte official document response")
    actual_sha = sha256(raw).hexdigest()
    matched = actual_sha == receipt["claimed_document_sha256"]
    return {
        "schema": SCHEMA,
        "status": ("OFFICIAL_RESPONSE_BYTES_SHA_MATCH_NOT_TRUST_SIGNOFF"
                   if matched else "OFFICIAL_RESPONSE_BYTES_SHA_MISMATCH_NO_GO"),
        "receipt_id": receipt["receipt_id"], "actual_http_body_sha256": actual_sha,
        "public_content_checked": True, "claimed_sha_matched": matched,
        "fix_verified": False, "license_signoff": False,
        "released_version_verified": False,
        "gates": dict(GATES_NOT_VERIFIED),
        "external_content_stored": False,
    }
