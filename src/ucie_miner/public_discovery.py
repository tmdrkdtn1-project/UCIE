"""Stage 9: new public-only cross-domain *discovery* (not Rulepack learning).

Operates on public merged PR metadata from exactly five independently owned,
previously approved public repos. Never reads patches, code, user files,
credentials, external projects, or operating databases, and never persists
lead content or installs a scheduler.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
import urllib.error
import urllib.request

from .core import NoRedirect, MiningError

SOURCES = (
    "python/cpython",
    "PowerShell/PowerShell",
    "git/git",
    "modelcontextprotocol/python-sdk",
    "actions/runner-images",
)
SOURCE_SKILL = {
    "python/cpython": "python-runtime-safety",
    "PowerShell/PowerShell": "powershell-safe-calls",
    "git/git": "git-workflow-prevention",
    "modelcontextprotocol/python-sdk": "mcp-api-compatibility",
    "actions/runner-images": "runner-environment-drift",
}
CATEGORIES = {
    "SECURITY": re.compile(r"\b(?:cve|security|vulnerability|exploit|injection)\b", re.I),
    "CRASH": re.compile(r"\b(?:crash|segfault|deadlock|race|hang|panic)\b", re.I),
    "REGRESSION": re.compile(r"\b(?:regression|bugfix|bug|fix|fixed|repair|invalid|missing|incorrect)\b", re.I),
    "COMPATIBILITY": re.compile(r"\b(?:compatibility|breaking|breaks|deprecat(?:e|ion|ed)|migration|version|sdk|support)\b", re.I),
    "TESTING": re.compile(r"\b(?:test|flaky|ci|runner)\b", re.I),
}
PR_CAP = 20
MAX_RESPONSE = 800_000
SHA40 = re.compile(r"[a-f0-9]{40}")
MAX_TITLE = 400


class DiscoveryError(ValueError):
    pass


MAX_BACKFILL_PAGES = 3

def public_feed_url(source: str, page: int = 1) -> str:
    if source not in SOURCES or type(page) is not int or not 1 <= page <= MAX_BACKFILL_PAGES:
        raise DiscoveryError("unapproved public source or page")
    url = ("https://api.github.com/repos/" + source +
           "/pulls?state=closed&sort=updated&direction=desc&per_page=20")
    return url if page == 1 else url + f"&page={page}"


def public_feed_get(url: str) -> object:
    """Anonymous exact-URL GET; never follow redirects or remote instructions."""
    if (not isinstance(url, str) or url not in {
            public_feed_url(source, page)
            for source in SOURCES
            for page in range(1, MAX_BACKFILL_PAGES + 1)}):
        raise DiscoveryError("URL outside approved public metadata routes")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "UCIE-PUBLIC-INTELLIGENCE/0.1",
    }, method="GET")
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=12) as response:
            if response.status != 200:
                raise DiscoveryError("public feed not successful")
            if "json" not in response.headers.get("Content-Type", ""):
                raise DiscoveryError("unexpected public feed type")
            raw = response.read(MAX_RESPONSE + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError) as exc:
        raise DiscoveryError("approved public feed unavailable") from exc
    except MiningError as exc:
        raise DiscoveryError("redirect rejected") from exc
    if len(raw) > MAX_RESPONSE:
        raise DiscoveryError("public feed too large")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise DiscoveryError("invalid public metadata JSON") from exc


def _utc(ts: str) -> datetime:
    if not isinstance(ts, str) or len(ts) > 35 or not ts.endswith("Z"):
        raise DiscoveryError("missing UTC merge timestamp")
    try:
        dt = datetime.fromisoformat(ts[:-1] + "+00:00")
    except ValueError as exc:
        raise DiscoveryError("invalid merge time") from exc
    if dt.utcoffset().total_seconds() != 0:
        raise DiscoveryError("invalid offset")
    return dt


def discover_public_leads(source_rows: object, *, source: str,
                          now: datetime | None = None) -> dict:
    """Convert untrusted public PR list to small hash-only, advisory leads."""
    if source not in SOURCES or not isinstance(source_rows, list) or len(source_rows) > PR_CAP:
        raise DiscoveryError("unapproved feed or excessive rows")
    instant = datetime.now(timezone.utc) if now is None else now
    if not isinstance(instant, datetime) or instant.tzinfo is None:
        raise DiscoveryError("timezone-aware observation time required")
    instant = instant.astimezone(timezone.utc)
    leads, seen = [], set()
    for item in source_rows:
        if not isinstance(item, dict):
            raise DiscoveryError("invalid public pull object")
        number = item.get("number")
        title = item.get("title")
        merged_at = item.get("merged_at")
        if (type(number) is not int or not 1 <= number <= 999999999
                or not isinstance(title, str) or not 1 <= len(title) <= MAX_TITLE):
            raise DiscoveryError("invalid PR metadata")
        if number in seen:
            raise DiscoveryError("duplicate public PR")
        seen.add(number)
        if merged_at is None:
            continue
        merged = _utc(merged_at)
        if merged > instant:
            raise DiscoveryError("future public merge metadata")
        url = f"https://github.com/{source}/pull/{number}"
        if item.get("html_url") != url:
            raise DiscoveryError("public PR URL is noncanonical")
        base = item.get("base")
        if not isinstance(base, dict):
            raise DiscoveryError("missing public base repository")
        repository = base.get("repo")
        if not isinstance(repository, dict) or repository.get("full_name") != source:
            raise DiscoveryError("wrong merge target repository")
        sha = item.get("merge_commit_sha")
        if sha is not None and (not isinstance(sha, str) or not SHA40.fullmatch(sha)):
            raise DiscoveryError("invalid public merge SHA")
        tags = sorted(name for name, pattern in CATEGORIES.items() if pattern.search(title))
        # No opaque title is stored or reemitted. In particular, malicious
        # instructions inside public PR titles never become execution input.
        if not tags:
            continue
        age_days = max(0, (instant - merged).days)
        if age_days > 90:
            continue
        leads.append({
            "source": source,
            "pr_number": number,
            "public_url": url,
            "merged_at": merged_at,
            "merge_commit_sha": sha,
            "title_sha256": hashlib.sha256(title.encode("utf-8")).hexdigest(),
            "tags": tags,
            "skill_id": SOURCE_SKILL[source],
            "age_days": age_days,
            "status": "UNVERIFIED_PUBLIC_LEAD",
            "license_checked": False,
            "independent_fix_verified": False,
        })
    return {
        "schema": "UCIE_APPROVED_PUBLIC_DISCOVERY_V1",
        "source": source,
        "leads": leads,
        "lead_count": len(leads),
        "records_examined": len(source_rows),
        "raw_text_retained": False,
        "network_fetch_performed": False,
        "proposals_promoted": 0,
        "production_approved": False,
        "persistent_writes": 0,
    }


def discover_all_feeds(*, fetch=public_feed_get,
                       sources: tuple[str, ...] = SOURCES,
                       now: datetime | None = None,
                       backfill_pages: int = 1) -> dict:
    """Bounded public-page discovery. A short page stops further requests.

    Approved public API data stays inert and source hashes only. Backfill
    allows up to 60 closed PRs/source when the first 20 lack useful fixes.
    """
    if (not isinstance(sources, tuple) or not sources
            or len(sources) > len(SOURCES) or len(set(sources)) != len(sources)
            or any(s not in SOURCES for s in sources)
            or type(backfill_pages) is not int
            or not 1 <= backfill_pages <= MAX_BACKFILL_PAGES):
        raise DiscoveryError("unapproved or excessive public discovery")
    feeds, actual_requests = [], 0
    for source in sources:
        collected, observed_count, identities = [], 0, set()
        for page in range(1, backfill_pages + 1):
            rows = fetch(public_feed_url(source, page))
            actual_requests += 1
            receipt = discover_public_leads(rows, source=source, now=now)
            observed_count += receipt["records_examined"]
            for lead in receipt["leads"]:
                identity = lead["pr_number"]
                if identity in identities:
                    raise DiscoveryError("duplicate public PR across feed pages")
                identities.add(identity)
                collected.append(lead)
            if receipt["records_examined"] < PR_CAP:
                break
        feeds.append({
            "schema": "UCIE_APPROVED_PUBLIC_DISCOVERY_V1",
            "source": source,
            "leads": collected,
            "lead_count": len(collected),
            "records_examined": observed_count,
            "raw_text_retained": False,
            "network_fetch_performed": False,
            "proposals_promoted": 0,
            "production_approved": False,
            "persistent_writes": 0,
        })
    return {
        "schema": "UCIE_MULTI_SOURCE_PUBLIC_DISCOVERY_V1",
        "feeds": feeds,
        "sources_attempted": list(sources),
        "public_reads_max": actual_requests,
        "public_reads_upper_bound": len(sources) * backfill_pages,
        "backfill_pages_limit": backfill_pages,
        "candidate_leads_total": sum(f["lead_count"] for f in feeds),
        "automatic_rule_training": False,
        "production_approved": False,
        "persistent_writes": 0,
    }
