"""One-shot approved-public upstream identity check for a selected Library card.

Exactly one anonymous GitHub metadata GET, and only after explicit live
authorization. Does not download patches, execute code, create evidence,
validate release inclusion, attest regressions, or approve any Rulepack.
The existing signed review history is checked before the public request.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re
import urllib.error
import urllib.request

from .core import NoRedirect, MiningError
from .public_discovery import SOURCES, DiscoveryError, _utc
from .public_pr_coverage_audit import _upstream_identity
from .public_library_review_binding import inspect_library_review_closure

SCHEMA = "UCIE_LIBRARY_CANDIDATE_PUBLIC_IDENTITY_RECHECK_V1"
MAX_RESPONSE = 350_000
MIN_REMAINING = 12
_SHA40 = re.compile(r"[0-9a-f]{40}\Z")
_NUMBER = re.compile(r"[1-9][0-9]{0,8}\Z")


def _canonical_endpoint(card: dict) -> tuple[str, str, int | None]:
    source = card["source"]
    url = card["public_url"]
    sha = card["pinned_revision_sha"]
    if (source not in SOURCES or type(url) is not str
            or type(sha) is not str or not _SHA40.fullmatch(sha)):
        raise DiscoveryError("unapproved public revision identity")
    if source == "git/git" and url == (
            "https://github.com/git/git/commit/" + sha):
        return "https://api.github.com/repos/git/git/commits/" + sha, "COMMIT", None
    prefix = "https://github.com/" + source + "/pull/"
    if not url.startswith(prefix):
        raise DiscoveryError("unapproved public pull request address")
    number = url[len(prefix):]
    if not _NUMBER.fullmatch(number):
        raise DiscoveryError("noncanonical public pull request identity")
    return (f"https://api.github.com/repos/{source}/pulls/{number}",
            "PULL_REQUEST", int(number))


def _no_duplicate(pairs):
    item = {}
    for key, value in pairs:
        if key in item:
            raise DiscoveryError("duplicate public API object key")
        item[key] = value
    return item


def _fetch_public_exact(url: str):
    """Strict no-redirect HTTPS metadata GET, one request, no raw retention.

    The endpoint is constructed from a validated Library card before this
    function is called; additionally reject every nonallowlisted path.
    """
    if (type(url) is not str or not any(
            re.fullmatch(
                re.escape(f"https://api.github.com/repos/{source}/pulls/")
                + r"[1-9][0-9]{0,8}", url)
            for source in SOURCES)
            and not re.fullmatch(
                r"https://api\.github\.com/repos/git/git/commits/[0-9a-f]{40}",
                url)):
        raise DiscoveryError("public metadata API path denied")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "UCIE-LIBRARY-IDENTITY-READONLY/1",
    }, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(
                request, timeout=12) as response:
            if (response.status != 200
                    or "json" not in response.headers.get(
                        "Content-Type", "").lower()):
                raise DiscoveryError("public metadata response rejected")
            data = response.read(MAX_RESPONSE + 1)
            remaining = response.headers.get("X-RateLimit-Remaining")
    except (OSError, TimeoutError, urllib.error.HTTPError,
            urllib.error.URLError, MiningError) as exc:
        raise DiscoveryError("public metadata API unavailable") from exc
    if len(data) > MAX_RESPONSE:
        raise DiscoveryError("oversized public metadata response")
    if remaining is not None:
        if (type(remaining) is not str or len(remaining) > 6
                or not remaining.isascii() or not remaining.isdecimal()):
            raise DiscoveryError("bad public API rate header")
        remaining = int(remaining)
    try:
        parsed = json.loads(data.decode("utf-8"),
                            object_pairs_hook=_no_duplicate)
    except (UnicodeError, ValueError) as exc:
        raise DiscoveryError("invalid public API JSON") from exc
    return parsed, remaining


def _check_git_commit(url: str, sha: str, data: object) -> bool:
    if type(data) is not dict:
        raise DiscoveryError("invalid git/git API commit metadata")
    parents = data.get("parents")
    commit = data.get("commit")
    committer = commit.get("committer") if type(commit) is dict else None
    if (type(data.get("sha")) is not str
            or _SHA40.fullmatch(data["sha"]) is None
            or data.get("html_url") != url
            or type(parents) is not list or len(parents) != 1
            or type(parents[0]) is not dict
            or type(parents[0].get("sha")) is not str
            or _SHA40.fullmatch(parents[0]["sha"]) is None
            or type(committer) is not dict):
        raise DiscoveryError("untrusted direct git commit identity")
    instant = _utc(committer.get("date"))
    if instant > datetime.now(timezone.utc):
        raise DiscoveryError("future git commit timestamp")
    return data["sha"] == sha


def recheck_library_candidate_public_identity(
        root, current, public_url, *,
        owner_trust, qa_trust, expected_head_sha256,
        previous=None, at_time=None, live=False, fetch=None):
    """Cross-check one exact public revision against upstream current metadata.

    A matching remote SHA is an observed public API identity, *not* proof
    that a fix works, is released or licensed, or was independently QA'd.
    Injected transports are only offline tests and NEVER count as a live
    upstream observation; the caller still must explicitly set live=True.
    """
    if live is not True:
        raise DiscoveryError("explicit one-shot public live permission required")
    if type(public_url) is not str:
        raise DiscoveryError("exact public candidate URL required")

    prior = inspect_library_review_closure(
        root, current,
        owner_trust=owner_trust, qa_trust=qa_trust,
        expected_head_sha256=expected_head_sha256,
        previous=previous, at_time=at_time)
    selected = [card for card in prior["review_records"]
                if card["public_url"] == public_url]
    if len(selected) != 1:
        raise DiscoveryError("candidate absent from validated Library selection")
    card = selected[0]
    endpoint, kind, number = _canonical_endpoint(card)
    transport = _fetch_public_exact if fetch is None else fetch
    envelope = transport(endpoint)
    if (type(envelope) is not tuple or len(envelope) != 2
            or type(envelope[0]) is not dict
            or (envelope[1] is not None and
                (type(envelope[1]) is not int or envelope[1] < 0))):
        raise DiscoveryError("invalid public API transport response")
    data, remaining = envelope
    pinned = card["pinned_revision_sha"]
    if kind == "PULL_REQUEST":
        seen, _ = _upstream_identity(card["source"], number, data)
        matches = seen == pinned
    else:
        matches = _check_git_commit(public_url, pinned, data)
        seen = data["sha"]
    rate_paused = remaining is not None and remaining < MIN_REMAINING
    verdict = ("PUBLIC_API_RATE_LIMIT_PAUSED_NO_GO" if rate_paused else
               "PUBLIC_PINNED_REVISION_SHA_MISMATCH_NO_GO" if not matches else
               "PUBLIC_UPSTREAM_PINNED_IDENTITY_OBSERVED_QA_PENDING_NO_GO")
    return {
        "schema": SCHEMA,
        "status": verdict,
        "public_url": card["public_url"],
        "approved_source": card["source"],
        "skill_id": card["skill_id"],
        "reference_kind": kind,
        "pinned_revision_sha": pinned,
        "observed_revision_sha": seen,
        "public_revision_matches": matches,
        "reference_evidence_sha256": card["evidence_sha256"],
        "review_state": card["review_state"],
        "owner_revocation_kept_blocking":
            card["review_state"] == "OWNER_REVOKED_BLOCKED_NO_GO",
        "public_metadata_api_response_observed":
            fetch is None and not rate_paused,
        "test_transport_injected": fetch is not None,
        "http_get_attempts": 1,
        "raw_untrusted_source_retained": False,
        "raw_patch_executed": False,
        "release_inclusion_independently_verified": False,
        "license_independently_approved": False,
        "security_independently_approved": False,
        "candidate_specific_regression_qa_verified": False,
        "human_qa_independence_verified": False,
        "rule_candidate_approved": False,
        "automatic_rule_promotions": 0,
        "persistent_writes": 0,
        "other_project_accesses": 0,
        "production_approved": False,
    }
