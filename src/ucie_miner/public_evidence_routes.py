"""Stage 9.1-9.3: narrowly allowlisted public code/document/release APIs.

One-shot anonymous reads only. Public text is UNTRUSTED, never executed.
Output is metadata, digests, and coarse error-family tags, not source copies.
"""
from __future__ import annotations

from html.parser import HTMLParser
import hashlib
import json
import re
import urllib.error
import urllib.request

from .core import NoRedirect, MiningError
from .public_discovery import SOURCES, DiscoveryError

MAX_JSON_BYTES = 900_000
MAX_DOC_BYTES = 1_500_000
MAX_FILES = 30
MAX_RELEASES = 10
MAX_ADVISORIES = 10
HEX40 = re.compile(r"[a-f0-9]{40}")
HEX64 = re.compile(r"[a-f0-9]{64}")
TAGS = {
    "EXCEPTION_HANDLING": re.compile(r"\b(?:raise|except|catch|throw|error|invalid.params)\b", re.I),
    "CONCURRENCY": re.compile(r"\b(?:race|thread|lock|scandir|deadlock|atomic|mutex)\b", re.I),
    "API_CONTRACT": re.compile(r"\b(?:parameter|argument|schema|validation|request|response|api)\b", re.I),
    "VERSION_COMPAT": re.compile(r"\b(?:version|deprecat|compatible|python 3\.15|upgrade)\b", re.I),
    "TEST_REGRESSION": re.compile(r"\b(?:test|assert|pytest|unittest|pester)\b", re.I),
}
# Fixed category features only: untrusted code text is never emitted or
# rephrased as a runnable correction command.
TRANSITION_SIGNALS = {
    "GENERIC_EXCEPTION": re.compile(r"\\b(?:ValueError|RuntimeError|Exception)\\b"),
    "PROTOCOL_ERROR_CODE": re.compile(r"\\b(?:INVALID_PARAMS|MCPError)\\b"),
    "RECURSION_LIMIT_CLEANUP": re.compile(r"\\b(?:addCleanup|setrecursionlimit)\\b"),
    "THREAD_SERIALIZATION": re.compile(r"\\b(?:Lock|RLock|mutex|lock\\.)\\b"),
    "RUNNER_BINARY_CONFLICT": re.compile(r"\\b(?:fusermount3|podman|setuid)\\b", re.I),
}
EXTENSIONS = (".py", ".pyi", ".ps1", ".psm1", ".psd1", ".c", ".h", ".sh",
              ".yml", ".yaml", ".json", ".md", ".toml", ".go", ".rs")

# Exact, official public documentation, reviewed independently from the feed.
DOC_ENDPOINTS = {
    "python/cpython": (
        "https://docs.python.org/3/library/os.html",
        "os.scandir"),
    "PowerShell/PowerShell": (
        "https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/resolve-path?view=powershell-7.6",
        "Resolve-Path"),
    "git/git": (
        "https://git-scm.com/docs/git",
        "git"),
    "modelcontextprotocol/python-sdk": (
        "https://modelcontextprotocol.io/specification/2025-11-25",
        "MCP"),
    "actions/runner-images": (
        "https://docs.github.com/en/actions/reference/runners",
        "runner"),
}


class PublicEvidenceError(ValueError):
    pass


def github_evidence_url(source, kind, number=None):
    if source not in SOURCES:
        raise PublicEvidenceError("unapproved public source")
    root = f"https://api.github.com/repos/{source}"
    if kind == "files":
        if type(number) is not int or not 1 <= number <= 999999999:
            raise PublicEvidenceError("invalid public PR number")
        return f"{root}/pulls/{number}/files?per_page=30"
    if number is not None:
        raise PublicEvidenceError("extra PR id is forbidden")
    if kind == "releases":
        return f"{root}/releases?per_page=10"
    if kind == "advisories":
        return f"{root}/security-advisories?per_page=10"
    raise PublicEvidenceError("unapproved GitHub evidence route")


def _safe_url(url):
    if not isinstance(url, str):
        return False
    for source in SOURCES:
        if url in (github_evidence_url(source, "releases"),
                   github_evidence_url(source, "advisories")):
            return True
        prefix = f"https://api.github.com/repos/{source}/pulls/"
        if url.startswith(prefix):
            number = url[len(prefix):]
            if re.fullmatch(r"[1-9][0-9]{0,8}/files\?per_page=30", number):
                return True
    return url in {item[0] for item in DOC_ENDPOINTS.values()}


def fetch_public_evidence(url):
    """Only exact approved GET paths, no auth headers, redirects or user paths."""
    if not _safe_url(url):
        raise PublicEvidenceError("requested resource outside approved public routes")
    is_doc = url in {x[0] for x in DOC_ENDPOINTS.values()}
    cap = MAX_DOC_BYTES if is_doc else MAX_JSON_BYTES
    request = urllib.request.Request(url, method="GET", headers={
        "Accept": "text/html" if is_doc else "application/vnd.github+json",
        "User-Agent": "UCIE-PUBLIC-EVIDENCE/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=12) as response:
            if response.status != 200:
                raise PublicEvidenceError("approved public GET not successful")
            ctype = response.headers.get("Content-Type", "").lower()
            if (is_doc and "html" not in ctype) or (
                    not is_doc and "json" not in ctype):
                raise PublicEvidenceError("unexpected public response media type")
            raw = response.read(cap + 1)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            TimeoutError, MiningError) as exc:
        raise PublicEvidenceError("approved public GET unavailable") from exc
    if len(raw) > cap:
        raise PublicEvidenceError("public response exceeded byte cap")
    if is_doc:
        return raw.decode("utf-8", errors="replace")
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise PublicEvidenceError("invalid JSON in public evidence") from exc


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def inspect_pr_changes(source, number, entries, *, merge_sha=None):
    """Extract patch *features* and digests; never retain or execute patch."""
    github_evidence_url(source, "files", number)
    if merge_sha is not None and (
            not isinstance(merge_sha, str) or not HEX40.fullmatch(merge_sha)):
        raise PublicEvidenceError("invalid public merge identity")
    if not isinstance(entries, list) or len(entries) > MAX_FILES:
        raise PublicEvidenceError("oversized or invalid PR files")
    count, patch_files, tests, added, removed = 0, 0, 0, 0, 0
    cues = set()
    before_signals, after_signals = set(), set()
    file_records = []
    for item in entries:
        if not isinstance(item, dict):
            raise PublicEvidenceError("malformed public file")
        filename, patch = item.get("filename"), item.get("patch")
        change = item.get("status")
        if (not isinstance(filename, str) or not 1 <= len(filename) <= 280
                or "\x00" in filename or filename.startswith("/")
                or ".." in filename.replace("\\", "/").split("/")
                or change not in ("added", "modified", "removed", "renamed",
                                   "copied", "changed", "unchanged")):
            raise PublicEvidenceError("invalid public patch path or status")
        # No raw path or code is persisted: paths can contain instructions.
        path_hash = _sha(filename)
        file_kind = next((e for e in EXTENSIONS
                          if filename.casefold().endswith(e)), "other")
        if file_kind == "other":
            continue
        count += 1
        is_test = bool(re.search(
            r"(^|/)(tests?|testing|__tests__)(/|_|\.|$)", filename.lower()))
        if is_test:
            tests += 1
        patch_sha = None
        if patch is not None:
            if not isinstance(patch, str) or len(patch.encode("utf-8")) > 65_536:
                raise PublicEvidenceError("oversized or invalid untrusted patch")
            patch_files += 1
            patch_sha = _sha(patch)
            for line in patch.splitlines():
                if line.startswith(("+++", "---")) or not line.startswith(("+", "-")):
                    continue
                if line[0] == "+":
                    added += 1
                else:
                    removed += 1
                body = line[1:500]
                cues.update(key for key, expr in TAGS.items() if expr.search(body))
                target = after_signals if line[0] == "+" else before_signals
                target.update(k for k, pattern in TRANSITION_SIGNALS.items()
                              if pattern.search(body))
        file_records.append({
            "path_sha256": path_hash, "extension": file_kind,
            "change_type": change, "patch_sha256": patch_sha,
            "test_path": is_test,
        })
    return {
        "schema": "UCIE_MINIMAL_PUBLIC_PATCH_FEATURES_V1",
        "source": source, "pr_number": number,
        "public_url": f"https://github.com/{source}/pull/{number}",
        "merge_commit_sha": merge_sha,
        "approved_source": True, "changed_supported_file_count": count,
        "patch_file_count": patch_files, "test_file_count": tests,
        "added_line_count": added, "removed_line_count": removed,
        "tags": sorted(cues),
        "removed_behavior_signals": sorted(before_signals),
        "added_behavior_signals": sorted(after_signals),
        "behavioral_transition": "HINT_ONLY_NOT_VERIFIED",
        "file_features": file_records,
        "coverage": "TRUNCATED_PAGINATION_POSSIBLE" if len(entries) == MAX_FILES
                    else "BOUNDED_FIRST_PAGE_ONLY",
        "code_patch_retained": False, "external_code_executed": False,
        "fix_verified": False, "license_approved": False,
        "rule_approved": False, "persistent_writes": 0,
    }


class _DocHints(HTMLParser):
    def __init__(self, marker):
        super().__init__(convert_charrefs=True)
        self.marker = marker.casefold()
        self.found_marker = False
        self.in_script = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.in_script += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.in_script = max(0, self.in_script - 1)
    def handle_data(self, data):
        if not self.in_script and self.marker in data.casefold():
            self.found_marker = True


def inspect_official_document(source, text):
    if source not in DOC_ENDPOINTS:
        raise PublicEvidenceError("unapproved official document source")
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_DOC_BYTES:
        raise PublicEvidenceError("oversized or invalid official HTML")
    url, marker = DOC_ENDPOINTS[source]
    parser = _DocHints(marker)
    try:
        parser.feed(text)
        parser.close()
    except ValueError as exc:
        raise PublicEvidenceError("invalid HTML document") from exc
    return {
        "schema": "UCIE_OFFICIAL_DOC_FINGERPRINT_V1",
        "source": source, "official_url": url,
        "sha256": _sha(text), "required_topic": marker,
        "topic_marker_found": parser.found_marker,
        "content_parsed_as_untrusted_data": True,
        "document_authenticity_attested": False,
        "applicability_reviewed": False, "full_text_retained": False,
        "license_approved": False, "persistent_writes": 0,
    }


def inspect_public_releases(source, rows):
    github_evidence_url(source, "releases")
    if not isinstance(rows, list) or len(rows) > MAX_RELEASES:
        raise PublicEvidenceError("invalid public release feed")
    output = []
    for item in rows:
        if not isinstance(item, dict):
            raise PublicEvidenceError("invalid public release")
        tag = item.get("tag_name")
        draft, prerelease = item.get("draft"), item.get("prerelease")
        if (not isinstance(tag, str) or not 1 <= len(tag) <= 80
                or type(draft) is not bool or type(prerelease) is not bool):
            raise PublicEvidenceError("malformed public release metadata")
        if draft:
            continue
        output.append({
            "tag_sha256": _sha(tag), "tag_marker": (
                tag if re.fullmatch(r"v?[0-9]+(?:\.[0-9A-Za-z-]+){1,4}", tag)
                else "UNRECOGNIZED_TAG"),
            "public_url": (f"https://github.com/{source}/releases"),
            "published_at": item.get("published_at")
                            if isinstance(item.get("published_at"), str) else None,
            "prerelease": prerelease,
            "fix_included_in_release": "UNDETERMINED",
        })
    return {
        "schema": "UCIE_PUBLIC_RELEASE_FINGERPRINTS_V1", "source": source,
        "releases": output, "record_count": len(output),
        "release_inclusion_proven": False, "license_approved": False,
        "persistent_writes": 0,
    }


def inspect_public_advisories(source, rows):
    github_evidence_url(source, "advisories")
    if not isinstance(rows, list) or len(rows) > MAX_ADVISORIES:
        raise PublicEvidenceError("invalid public advisories feed")
    output = []
    for item in rows:
        if not isinstance(item, dict):
            raise PublicEvidenceError("invalid published advisory")
        ghsa = item.get("ghsa_id")
        if not isinstance(ghsa, str) or not re.fullmatch(
                r"GHSA-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}-[23456789cfghjmpqrvwx]{4}", ghsa):
            raise PublicEvidenceError("invalid GHSA identity")
        output.append({
            "ghsa_id": ghsa, "public_url": f"https://github.com/advisories/{ghsa}",
            "severity": item.get("severity") if item.get("severity") in (
                "low", "moderate", "high", "critical") else "UNVERIFIED",
            "published_at": item.get("published_at")
                            if isinstance(item.get("published_at"), str) else None,
            "security_fix_reproduced": False,
            "independent_advisory_review": "PENDING",
        })
    return {
        "schema": "UCIE_PUBLIC_SECURITY_ADVISORIES_V1", "source": source,
        "advisories": output, "record_count": len(output),
        "independent_security_reviewed": False,
        "persistent_writes": 0,
    }
