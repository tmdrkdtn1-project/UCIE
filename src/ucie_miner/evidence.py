"""Offline Stage-2 public evidence evaluation. No network, execution, or promotion.

Inputs are caller-supplied snapshots from explicitly pinned public repositories.
A syntactically valid receipt is NEVER proof that upstream metadata is authentic.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .core import MiningError

SOURCES = {
    "python/cpython": "Python Software Foundation",
    "PowerShell/PowerShell": "Microsoft",
    "git/git": "Git project maintainers",
    "modelcontextprotocol/python-sdk": "Model Context Protocol maintainers",
    "actions/runner-images": "GitHub",
}
CATEGORIES = {"python", "powershell", "windows", "git", "mcp_api"}
SAFE_LICENSES = {"MIT", "Apache-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
                 "GPL-3.0-only", "PSF-2.0", "BSD-3-Clause", "NOASSERTION"}
MAX_PATCH = 50000
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
INJECTION = re.compile(
    r"(?i)(ignore (?:all |previous |prior )?instructions|"
    r"system prompt|developer message|reveal (?:the |your )?(?:secret|token|key)|"
    r"exfiltrat|curl\\s+[^\\n]*\\|\\s*(?:sh|bash)|"
    r"invoke-expression|remove-item\\s+-recurse)"
)
SECRET = re.compile(
    r"(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"Bearer\\s+[A-Za-z0-9_.-]{16,})", re.I
)
RULES = (
    ("EXPLICIT_ENCODING", re.compile(r"(?i)encoding\\s*=|\\b(?:utf-8|cp1252|cp949)\\b"), "Explicitly specify the documented file encoding"),
    ("EXCEPTION_HANDLING", re.compile(r"(?i)\\b(?:except|catch|throw|raise|finally)\\b"), "Check exception handling and failing-path behavior"),
    ("API_CONTRACT", re.compile(r"(?i)\\b(?:schema|header|validation|argument|parameter)\\b"), "Validate the API contract and negative inputs"),
    ("DEPENDENCY_VERSION", re.compile(r"(?i)\\b(?:version|dependency|runner|image)\\b"), "Pin and compare tool/runtime versions"),
)


def _utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise MiningError("timestamp absent")
    try:
        dt = datetime.strptime(value, UTC_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise MiningError("timestamp must be UTC ISO8601") from exc
    if dt > datetime.now(timezone.utc):
        raise MiningError("future timestamp")
    return dt


def _url(source: str, number: int, url: object) -> None:
    if not isinstance(url, str) or len(url) > 250:
        raise MiningError("invalid canonical URL")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "github.com"
            or parsed.path != f"/{source}/pull/{number}"
            or parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise MiningError("URL outside exact approved PR")


def validate_evidence(record: object) -> dict:
    """Strict metadata gate; authenticity still needs independent upstream check."""
    required = {"source", "number", "url", "category", "merged_at",
                "updated_at", "commit", "license", "license_url", "files"}
    if not isinstance(record, dict) or set(record) != required:
        raise MiningError("unexpected evidence schema")
    source = record["source"]
    if source not in SOURCES:
        raise MiningError("unapproved upstream")
    num = record["number"]
    if type(num) is not int or num < 1:
        raise MiningError("invalid PR number")
    _url(source, num, record["url"])
    if record["category"] not in CATEGORIES:
        raise MiningError("unapproved category")
    merged, updated = _utc(record["merged_at"]), _utc(record["updated_at"])
    if updated < merged:
        raise MiningError("updated before merged")
    if not isinstance(record["commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", record["commit"]):
        raise MiningError("missing exact commit")
    if record["license"] not in SAFE_LICENSES:
        raise MiningError("license unknown or unsupported")
    if (record["license_url"] != f"https://github.com/{source}/blob/{record['commit']}/LICENSE"
            and record["license_url"] != f"https://github.com/{source}/blob/{record['commit']}/LICENSE.txt"):
        raise MiningError("unverified license URL form")
    files = record["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= 30:
        raise MiningError("invalid file count")
    for file in files:
        if not isinstance(file, dict) or set(file) != {"filename", "patch"}:
            raise MiningError("unexpected file schema")
        name, patch = file["filename"], file["patch"]
        if not isinstance(name, str) or not 1 <= len(name) <= 300 or ".." in name.split("/"):
            raise MiningError("invalid filename")
        if not isinstance(patch, str) or len(patch.encode("utf-8")) > MAX_PATCH:
            raise MiningError("invalid patch")
        if INJECTION.search(patch) or SECRET.search(patch):
            raise MiningError("untrusted instructions or credentials in patch")
    return record


def evaluate(record: object, seen: set[str] | None = None) -> dict:
    """Return bounded metadata and generic validation candidates; never raw patches."""
    item = validate_evidence(record)
    source, number = item["source"], item["number"]
    key = f"{source}#{number}@{item['commit']}"
    if seen is not None and key in seen:
        return {"status": "DUPLICATE", "evidence_key": key}
    h = hashlib.sha256()
    patterns: set[str] = set()
    test_changed = False
    for file in item["files"]:
        name, patch = file["filename"], file["patch"]
        h.update(name.encode("utf-8") + b"\\0" + patch.encode("utf-8") + b"\\0")
        if re.search(r"(^|/)(test|tests|testing)(/|_|\\.|$)", name, re.I):
            test_changed = True
        lines = [line[1:] for line in patch.splitlines()
                 if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
        for label, pattern, _ in RULES:
            if any(pattern.search(line) for line in lines):
                patterns.add(label)
    if seen is not None:
        seen.add(key)
    return {
        "status": "UNVERIFIED_CANDIDATE_ONLY",
        "evidence_key": key,
        "source_class": "INDEPENDENT_PUBLIC_UPSTREAM",
        "owner": SOURCES[source],
        "url": item["url"],
        "category": item["category"],
        "merged_at": item["merged_at"],
        "updated_at": item["updated_at"],
        "commit": item["commit"],
        "license_claim": item["license"],
        "license_url": item["license_url"],
        "evidence_sha256": h.hexdigest(),
        "pattern_candidates": sorted(patterns),
        "regression_candidates": [
            guidance for label, _, guidance in RULES if label in patterns
        ] + (["Re-run upstream changed tests in an isolated environment"] if test_changed else
             ["Request an upstream regression test before promotion"]),
        "metadata_authenticated": False,
        "patch_executed": False,
        "test_pass": False,
        "rule_promoted": False,
    }
