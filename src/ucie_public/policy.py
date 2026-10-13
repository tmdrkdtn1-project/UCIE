"""Strict public-only knowledge boundary for the phase-1 demonstrator.

These checks are defensive-in-depth, not substitutes for OS/VM isolation.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

class PolicyError(ValueError):
    pass

ALLOWED_DOMAINS = frozenset({
    "python.org", "docs.python.org", "learn.microsoft.com",
    "docs.github.com", "git-scm.com", "spec.modelcontextprotocol.io",
    "modelcontextprotocol.io", "packaging.python.org",
})
ALLOWED_CATEGORIES = frozenset({
    "python", "powershell", "windows", "git", "mcp_api", "security"
})
REQUIRED_FIELDS = frozenset({
    "id", "title", "category", "problem", "guidance", "source",
    "environments", "probe"
})
SOURCE_FIELDS = frozenset({"kind", "url", "citation"})
PROBE_FIELDS = frozenset({"kind", "snippet"})
REJECTED_KEYS = frozenset({
    "project", "project_id", "project_name", "repository", "repo_url", "workspace",
    "conversation", "chat_history", "tenant", "tenant_id", "internal_log", "trace_id",
    "customer", "employee", "email", "token", "api_key", "credential",
    "private_code", "raw_code", "raw_log", "github_token", "access_token",
})
REJECTED_TEXT = [
    re.compile(r"\b(?:private[ _-]?project[ _-]?[a-z0-9]+|project[ _-]?[a-z0-9]+[ _-]?private|tenant[ _-]?secret|internal[ _-]?workroom)\b", re.I),
    re.compile(r"(?:[A-Za-z]:\\|\\\\[^\\\s]+\\|/Users/|/home/|/mnt/data/)", re.I),
    re.compile(r"(?:ghp_|github_pat_|sk-[A-Za-z0-9]{12,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)", re.I),
    re.compile(r"(?:Bearer\s+[A-Za-z0-9\-_.]{10,})", re.I),
]


def _string_safety(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"missing or empty text in {field}")
    if len(value) > 4000:
        raise PolicyError(f"oversized text in {field}")
    for pattern in REJECTED_TEXT:
        if pattern.search(value):
            raise PolicyError(f"private/sensitive marker in {field}")


def _source_url_is_public(url: str) -> bool:
    try:
        split = urlsplit(url)
        return (split.scheme == "https" and split.hostname in ALLOWED_DOMAINS and
                split.username is None and split.password is None and
                split.port in (None, 443) and not split.fragment and
                bool(split.path.startswith("/")))
    except (ValueError, TypeError):
        return False


def validate_entry(item: object) -> dict:
    if not isinstance(item, dict):
        raise PolicyError("entry must be a JSON object")
    if set(item) != REQUIRED_FIELDS:
        raise PolicyError(f"entry fields mismatch; missing={sorted(REQUIRED_FIELDS - set(item))}, extra={sorted(set(item) - REQUIRED_FIELDS)}")
    if any(k.casefold() in REJECTED_KEYS for k in item):
        raise PolicyError("private field present")
    if not isinstance(item["id"], str) or not re.fullmatch(r"PUB-[A-Z0-9-]{4,60}", item["id"]):
        raise PolicyError("invalid public knowledge id")
    if item["category"] not in ALLOWED_CATEGORIES:
        raise PolicyError("category not allowlisted")
    for field in ("title", "problem", "guidance"):
        _string_safety(item[field], field)
    if (not isinstance(item["environments"], list) or not item["environments"] or
        len(item["environments"]) > 12):
        raise PolicyError("environment list invalid")
    for env in item["environments"]:
        _string_safety(env, "environment")
    source = item["source"]
    if not isinstance(source, dict) or set(source) != SOURCE_FIELDS:
        raise PolicyError("source fields invalid")
    if source["kind"] != "official_public_documentation":
        raise PolicyError("project/private/synthetic provenance forbidden in common pack")
    if not _source_url_is_public(source["url"]):
        raise PolicyError("source URL not on pinned official public host list")
    _string_safety(source["citation"], "citation")
    probe = item["probe"]
    if not isinstance(probe, dict) or set(probe) != PROBE_FIELDS:
        raise PolicyError("probe fields invalid")
    if probe["kind"] != "python_ast_parse":
        raise PolicyError("only harmless non-executing AST parsing probes supported in phase 1")
    _string_safety(probe["snippet"], "probe.snippet")
    if len(probe["snippet"]) > 1500:
        raise PolicyError("probe too long")
    return item


def approved_local_directory(repo_root: Path, selected: Path) -> Path:
    """Only packaged, curated public entry directory is reachable through CLI."""
    allow = (repo_root / "curated_public").resolve(strict=True)
    p = selected.resolve(strict=True)
    if p != allow or selected.is_symlink():
        raise PolicyError("refusing unapproved source directory")
    if not p.is_dir():
        raise PolicyError("approved source is not a directory")
    return p


def load_curated(repo_root: Path, selected: Path | None = None) -> list[dict]:
    directory = approved_local_directory(repo_root, selected or (repo_root / "curated_public"))
    files = sorted(directory.iterdir())
    if not files or len(files) > 200:
        raise PolicyError("missing or excessive curated sources")
    for f in files:
        if f.is_symlink() or not f.is_file() or f.suffix != ".json":
            raise PolicyError("non-JSON, symlink, or directory inside public sources")
        if f.stat().st_size > 32768:
            raise PolicyError("oversized input item")
    import json
    items = []
    seen = set()
    for f in files:
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PolicyError("invalid JSON input") from exc
        validate_entry(obj)
        if obj["id"] in seen:
            raise PolicyError("duplicate id")
        seen.add(obj["id"])
        items.append(obj)
    return items
