"""UCIE-authored portable exact metadata lookup V1.

This intentionally has NO dependency on ucie_miner, third-party libraries,
network, disk, user accounts, private projects, source code, or credentials.
It can run in an isolated consumer directory with Python stdlib alone.

Input is a bounded array of already-sanitized *public* evidence metadata. The
consumer still must check source rights and approval separately; this is a
pure data search primitive, NOT an executable upstream skill or signed rule.
"""
from __future__ import annotations

from typing import Any

VERSION = "1.0.0"
SCHEMA = "UCIE_PORTABLE_EXACT_PUBLIC_METADATA_LOOKUP_V1"
MAX_ITEMS = 1000
MAX_QUERIES = 32
MAX_RETURNED = 20
SOURCES = frozenset({
    "repo:python/cpython", "repo:PowerShell/PowerShell",
    "repo:git/git", "repo:modelcontextprotocol/python-sdk",
    "repo:actions/runner-images",
})
DOMAINS = frozenset({"Python", "PowerShell", "Git", "MCP/API", "GitHub Actions Runner"})
KINDS = frozenset({"PUBLIC_TECHNICAL_EVIDENCE", "PREVENTION_RULE"})
PURPOSE_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
HEX = frozenset("0123456789abcdef")
FIELDS = frozenset({
    "source_id", "domain", "kind", "purpose_code",
    "library_item_id", "public_url", "evidence_sha256",
    "export_allowed", "human_approved",
})


class PortableLookupError(ValueError):
    pass


def _purpose(x: Any) -> bool:
    return (type(x) is str and 3 <= len(x) <= 64 and x[0] in
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ" and all(ch in PURPOSE_CHARS for ch in x))


def _hex64(x: Any) -> bool:
    return type(x) is str and len(x) == 64 and all(c in HEX for c in x)


def _key(source: Any, domain: Any, kind: Any, purpose: Any):
    if (type(source) is not str or source not in SOURCES
            or type(domain) is not str or domain not in DOMAINS
            or type(kind) is not str or kind not in KINDS
            or not _purpose(purpose)):
        raise PortableLookupError("approved public exact-key metadata required")
    return (source, domain, kind, purpose)


def search_public_metadata(items: list[dict], *,
                           queries: tuple[tuple[str, str, str, str], ...],
                           limit: int = 10) -> dict:
    """Safely search a caller-provided, bounded set of UNVERIFIED metadata.

    A single key query uses a scan. Multiple keys build one ephemeral index
    only when N+Q < N*Q. Both preserve identical ordering and eligibility.
    All source items remain unapproved and cannot be exported by this API.
    """
    if (type(items) is not list or len(items) > MAX_ITEMS
            or type(queries) is not tuple or not 1 <= len(queries) <= MAX_QUERIES
            or type(limit) is not int or not 1 <= limit <= MAX_RETURNED):
        raise PortableLookupError("bounded input required")
    keys = tuple(_key(*q) if type(q) is tuple and len(q) == 4
                 else _key(None, None, None, None) for q in queries)
    rows = []
    for row in items:
        if type(row) is not dict or set(row) != FIELDS:
            raise PortableLookupError("only complete sanitized public metadata allowed")
        key = _key(row["source_id"], row["domain"], row["kind"], row["purpose_code"])
        if (not _hex64(row["library_item_id"])
                or not _hex64(row["evidence_sha256"])
                or type(row["public_url"]) is not str
                or not row["public_url"].startswith(
                    "https://github.com/" + row["source_id"][5:] + "/pull/")
                or type(row["export_allowed"]) is not bool
                or row["export_allowed"]
                or type(row["human_approved"]) is not bool
                or row["human_approved"]):
            raise PortableLookupError("candidate approval/source provenance not attested")
        rows.append((key, row["library_item_id"], row["public_url"],
                     row["evidence_sha256"]))
    # Sort by immutable metadata fields for deterministic output independent
    # of input order and Python hash seeds. No source title is stored.
    rows.sort()
    cost_scan = len(rows) * len(keys)
    cost_index = len(rows) + len(keys)
    indexed = cost_index < cost_scan
    table = {}
    if indexed:
        for key, item_id, url, digest in rows:
            table.setdefault(key, []).append((item_id, url, digest))
    found = []
    for key in keys:
        hits = table.get(key, ()) if indexed else (
            (item_id, url, digest) for k, item_id, url, digest in rows if k == key)
        hits = list(hits)
        found.append({
            "query": dict(zip(("source_id", "domain", "kind", "purpose_code"), key)),
            "total_matches": len(hits), "returned_count": min(len(hits), limit),
            "items": [{"library_item_id": a, "public_url": b, "evidence_sha256": c,
                       "human_approved": False, "export_allowed": False}
                      for a, b, c in hits[:limit]],
        })
    return {
        "schema": SCHEMA, "version": VERSION, "strategy": (
            "COMPOSITE_INDEX" if indexed else "LINEAR_EXACT_SCAN"),
        "catalog_count": len(rows), "query_count": len(keys),
        "estimated_scan_operations": cost_scan,
        "estimated_index_operations": cost_index,
        "elapsed_time_improvement_guaranteed": False,
        "results": found, "network_requests": 0, "database_writes": 0,
        "original_upstream_code_executed": False,
        "approved_or_exportable_items": 0,
        "production_release_approved": False,
    }
