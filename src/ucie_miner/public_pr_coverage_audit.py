"""Stage 17: explicitly requested, bounded live recheck of one approved public PR.

Read-only Stage13/14/15 ledgers and up to four anonymous public API GETs.
No automatic hourly hook, new marker, DB write, code execution, patch
retention, regression assertion, version inference or Rulepack promotion.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import json
import re
import sqlite3
import urllib.error
import urllib.request

from .core import NoRedirect, MiningError
from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError, _utc
from .public_evidence_chain_audit import (
    _history, _fix, _valid_fix, audit_external_evidence_chain,
)
from .public_evidence_routes import inspect_pr_changes, PublicEvidenceError
from .public_official_evidence import (
    _path as official_path, _schema as official_schema, RECORD_CAP,
)

MAX_FILE_PAGES = 3
PAGE_SIZE = 30
MAX_JSON_BYTES = 900_000
MIN_REMAINING = 12
_KINDS = ("release", "advisory", "document")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def public_pr_audit_url(source, number, *, page=None):
    if (source not in SOURCES or type(number) is not int
            or not 1 <= number <= 999999999):
        raise DiscoveryError("unapproved Stage 17 source or PR")
    prefix = f"https://api.github.com/repos/{source}/pulls/{number}"
    if page is None:
        return prefix
    if type(page) is not int or not 1 <= page <= MAX_FILE_PAGES:
        raise DiscoveryError("unapproved Stage 17 file page")
    return f"{prefix}/files?per_page={PAGE_SIZE}&page={page}"


def _approved_url(url):
    if type(url) is not str:
        return False
    for source in SOURCES:
        prefix = f"https://api.github.com/repos/{source}/pulls/"
        if not url.startswith(prefix):
            continue
        tail = url[len(prefix):]
        match = re.fullmatch(
            r"([1-9][0-9]{0,8})(?:/files\?per_page=30&page=([1-3]))?", tail)
        if match is None:
            return False
        number = int(match.group(1))
        page = int(match.group(2)) if match.group(2) else None
        return url == public_pr_audit_url(source, number, page=page)
    return False


def fetch_stage17_public(url):
    """Single allowlisted anonymous GET; never follow redirects or trust text."""
    if not _approved_url(url):
        raise DiscoveryError("Stage 17 URL denied")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "UCIE-STAGE17-READONLY/0.1",
    }, method="GET")
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=12) as response:
            if response.status != 200 or "json" not in response.headers.get("Content-Type", "").lower():
                raise DiscoveryError("Stage 17 upstream response rejected")
            raw = response.read(MAX_JSON_BYTES + 1)
            remaining = response.headers.get("X-RateLimit-Remaining")
    except (OSError, TimeoutError, urllib.error.HTTPError,
            urllib.error.URLError, MiningError) as exc:
        raise DiscoveryError("Stage 17 public GET unavailable") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise DiscoveryError("oversized Stage 17 upstream response")
    if remaining is not None:
        if (len(remaining) > 6 or not remaining.isascii()
                or not remaining.isdecimal()):
            raise DiscoveryError("invalid Stage 17 API quota header")
        remaining = int(remaining)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise DiscoveryError("invalid Stage 17 public JSON") from exc
    return data, remaining


def _transport(fetch, url):
    result = fetch(url)
    if (type(result) is not tuple or len(result) != 2
            or (result[1] is not None
                and (type(result[1]) is not int or result[1] < 0))):
        raise DiscoveryError("untrusted Stage 17 response envelope")
    return result


def _upstream_identity(source, number, record):
    if type(record) is not dict:
        raise DiscoveryError("invalid Stage 17 PR metadata")
    base = record.get("base")
    repo = base.get("repo") if type(base) is dict else None
    merge = record.get("merge_commit_sha")
    merged_at = record.get("merged_at")
    files = record.get("changed_files")
    if (type(record.get("number")) is not int or record["number"] != number
            or record.get("html_url") != f"https://github.com/{source}/pull/{number}"
            or type(repo) is not dict or repo.get("full_name") != source
            or record.get("state") != "closed"
            or type(merge) is not str or re.fullmatch(r"[0-9a-f]{40}", merge) is None
            or type(files) is not int or not 0 <= files <= 3000):
        raise DiscoveryError("invalid Stage 17 upstream PR identity")
    merged = _utc(merged_at)
    if merged > datetime.now(timezone.utc):
        raise DiscoveryError("future Stage 17 upstream merge time")
    return merge, files


def _official_source_inventory(root, source):
    """Same-source inventory only; never infer PR causality or versions."""
    path = official_path(root)
    if not path.exists():
        return {"present": False, "counts": {kind: 0 for kind in _KINDS}}
    try:
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro",
                                     uri=True, timeout=3)) as db:
            db.execute("PRAGMA query_only=ON")
            official_schema(db, new=False)
            total = db.execute("SELECT count(*) FROM official_revision").fetchone()[0]
            rows = db.execute("""
                SELECT evidence_kind,source,content_sha256,review_state
                FROM official_revision
            """).fetchall()
    except sqlite3.DatabaseError as exc:
        raise DiscoveryError("Stage 14 source inventory unavailable") from exc
    if total > RECORD_CAP:
        raise DiscoveryError("oversized Stage 14 source inventory")
    counts = {kind: 0 for kind in _KINDS}
    for kind, src, digest, status in rows:
        if (kind not in _KINDS or src not in SOURCES or
                type(digest) is not str or _HEX64.fullmatch(digest) is None
                or status != "PUBLIC_METADATA_UNVERIFIED"):
            raise DiscoveryError("invalid Stage 14 metadata evidence")
        if src == source:
            counts[kind] += 1
    return {"present": True, "counts": counts}


def _build_file_role(source, filename):
    """Small, strict metadata-only supplement to legacy Stage15 file features.

    Stage15 snapshots must remain comparable without schema migration.
    Root-level Autoconf source and generated configure scripts are not
    ordinary Python files, but can carry genuine build-system bug fixes.
    Classification is filename-only; never parse/execute upstream bytes.
    """
    if filename == "configure.ac":
        return "autoconf_source"
    if filename == "configure":
        return "generated_configure"
    if (source == "python/cpython"
            and filename.startswith("Misc/NEWS.d/next/Build/")
            and filename.endswith(".rst")):
        return "build_release_note"
    return "other"


def _snapshot_matches(first, row):
    return (first["patch_file_count"] == row[10]
            and first["test_file_count"] == row[9]
            and first["coverage"] == row[11]
            and json.dumps(first["tags"], separators=(",", ":")) == row[6]
            and json.dumps(first["removed_behavior_signals"], separators=(",", ":")) == row[7]
            and json.dumps(first["added_behavior_signals"], separators=(",", ":")) == row[8])


def audit_public_pr_evidence_once(root, source, number, *, fetch=None):
    """Recheck one Stage15-indexed merged PR on explicit operator request.

    Changed-file completeness describes the live GitHub *file listing*, not
    proof that every patch hunk was returned or independently reproduced.
    """
    public_pr_audit_url(source, number)
    chain = audit_external_evidence_chain(root)
    if chain["status"] != "STAGE16_LOCALLY_LINKED_BUT_UNVERIFIED_NO_GO":
        raise DiscoveryError("Stage 16 local evidence chain must be consistent")
    historical = _history(root)
    fixes = _fix(root)
    selected = [row for row in fixes or ()
                if row[0] == source and row[1] == number]
    if not selected or any(not _valid_fix(row) for row in selected):
        raise DiscoveryError("Stage 17 requires existing valid Stage 15 PR")
    merges = {row[2] for row in selected}
    if len(merges) != 1 or any(
            historical.get((source, number, row[3])) != (row[2], SOURCE_SKILL[source])
            for row in selected):
        raise DiscoveryError("ambiguous or unlinked Stage 17 PR revision")
    pinned = next(iter(merges))
    official = _official_source_inventory(root, source)
    if fetch is None:
        fetch = fetch_stage17_public
    requests = 0
    meta, remaining = _transport(fetch, public_pr_audit_url(source, number))
    requests += 1
    upstream_sha, changed_files = _upstream_identity(source, number, meta)
    result = {
        "source": source, "pr_number": number,
        "stage15_unverified_revisions": len(selected),
        "stage14_same_source_inventory": official,
        "stage14_linkage_state": "SAME_SOURCE_ONLY_NO_PR_CAUSAL_LINKAGE",
        "upstream_identity_rechecked": upstream_sha == pinned,
        "pr_changed_files_reported": changed_files,
        "pr_files_inspected": 0, "pr_file_pages_inspected": 0,
        "pr_file_listing_complete_at_observation": False,
        "stage15_first_page_snapshot_matches": False,
        "autoconf_source_files_observed": 0,
        "generated_configure_files_observed": 0,
        "build_release_note_files_observed": 0,
        "other_files_observed": 0,
        "build_file_classification_state": "FILENAME_ONLY_UNVERIFIED",
        "external_gets": requests, "max_external_gets": 1 + MAX_FILE_PAGES,
        "persistent_writes": 0, "external_code_executed": False,
        "raw_patch_retained": False, "upstream_merge_independently_attested": False,
        "official_release_inclusion_proven": False,
        "advisory_to_pr_link_proven": False,
        "document_change_semantics_verified": False,
        "independent_regression_verified": False,
        "license_approved": False, "approved_rules": 0,
        "model_weights_updated": False, "production_approved": False,
    }
    if upstream_sha != pinned:
        result["status"] = "STAGE17_UPSTREAM_MERGE_MISMATCH_NO_GO"
        return result
    if remaining is not None and remaining < MIN_REMAINING:
        result["status"] = "STAGE17_API_RATE_PAUSED_NO_GO"
        return result

    inspected = 0
    all_features = []
    seen_names = set()
    last_page = min(MAX_FILE_PAGES, (changed_files + PAGE_SIZE - 1) // PAGE_SIZE)
    for page in range(1, last_page + 1):
        entries, remaining = _transport(
            fetch, public_pr_audit_url(source, number, page=page))
        requests += 1
        if type(entries) is not list or len(entries) > PAGE_SIZE:
            raise DiscoveryError("invalid Stage 17 PR files page")
        expected = min(PAGE_SIZE, changed_files - inspected)
        if len(entries) != expected:
            result.update({
                "status": "STAGE17_FILE_COUNT_MISMATCH_NO_GO",
                "external_gets": requests,
                "pr_files_inspected": inspected,
                "pr_file_pages_inspected": page,
            })
            return result
        try:
            features = inspect_pr_changes(source, number, entries, merge_sha=pinned)
        except PublicEvidenceError as exc:
            raise DiscoveryError("invalid Stage 17 untrusted patch data") from exc
        # Filename-based build-system signal only. Do not change the Stage15
        # legacy feature digest or treat a changelog as executable source.
        counters = {
            "autoconf_source": "autoconf_source_files_observed",
            "generated_configure": "generated_configure_files_observed",
            "build_release_note": "build_release_note_files_observed",
            "other": "other_files_observed",
        }
        for entry in entries:
            if entry["filename"] in seen_names:
                raise DiscoveryError("duplicate Stage 17 PR file across pages")
            seen_names.add(entry["filename"])
            role = _build_file_role(source, entry["filename"])
            result[counters[role]] += 1
        all_features.append(features)
        inspected += len(entries)
        result["pr_files_inspected"] = inspected
        result["pr_file_pages_inspected"] = page
        result["external_gets"] = requests
        if remaining is not None and remaining < MIN_REMAINING and inspected < changed_files:
            result["status"] = "STAGE17_API_RATE_PAUSED_NO_GO"
            return result

    result["pr_file_listing_complete_at_observation"] = inspected == changed_files
    result["stage15_first_page_snapshot_matches"] = (
        bool(all_features) and all(_snapshot_matches(all_features[0], row)
                                   for row in selected))
    result["verified_file_list_vs_first_page_only"] = (
        "COMPLETE_BOUNDED_LISTING" if inspected == changed_files
        else "PARTIAL_MAX_THREE_PAGES")
    result["observed_supported_file_count"] = sum(
        features["changed_supported_file_count"] for features in all_features)
    result["observed_test_file_count"] = sum(
        features["test_file_count"] for features in all_features)
    result["status"] = (
        "STAGE17_LOCAL_FIRST_PAGE_HINT_MISMATCH_NO_GO"
        if all_features and not result["stage15_first_page_snapshot_matches"]
        else "STAGE17_PAGINATION_INCOMPLETE_NO_GO"
        if inspected != changed_files
        else "STAGE17_UPSTREAM_LISTING_RECHECKED_UNVERIFIED_NO_GO")
    return result
