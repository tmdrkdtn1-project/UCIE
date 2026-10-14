"""Stage 5: bounded, offline-only evidence family grouping (no DB writes).

Grouping by a curated canonical PR is allowed only after a consistent
one-to-one mapping. Heuristic pattern matches are suggestions, never identity
or independent validation.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import re

from .evidence import SOURCES

PATTERN = re.compile(r"[A-Z][A-Z0-9_]{2,63}\\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\\Z")
MAX_ROWS = 10000


class PatternError(ValueError):
    pass


def group_patterns(rows: object) -> dict:
    """Pure deterministic preview of manually curated, unverified families.

    Exact input keys: source, pr_number, canonical_pr_number,
    pattern_code, evidence_sha256, status.
    """
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise PatternError("invalid candidate batch size")
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    seen: set[tuple[str, int]] = set()
    required = {"source", "pr_number", "canonical_pr_number",
                "pattern_code", "evidence_sha256", "status"}
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            raise PatternError("invalid metadata schema")
        source, number, canonical = (row["source"], row["pr_number"],
                                     row["canonical_pr_number"])
        if (source not in SOURCES or type(number) is not int or number < 1
                or type(canonical) is not int or canonical < 1
                or not isinstance(row["pattern_code"], str)
                or not PATTERN.fullmatch(row["pattern_code"])
                or not isinstance(row["evidence_sha256"], str)
                or not SHA256.fullmatch(row["evidence_sha256"])
                or row["status"] != "UNVERIFIED_CANDIDATE_ONLY"):
            raise PatternError("unapproved/unverified metadata")
        item_key = (source, number)
        if item_key in seen:
            raise PatternError("duplicate PR identity")
        seen.add(item_key)
        groups[(source, canonical)].append(row)
    output = []
    for (source, canonical), family in sorted(groups.items()):
        if (source, canonical) not in seen:
            raise PatternError("canonical evidence missing")
        pattern_codes = {r["pattern_code"] for r in family}
        if len(pattern_codes) != 1:
            raise PatternError("conflicting pattern family")
        pr_ids = sorted(r["pr_number"] for r in family)
        evidence_digests = sorted(r["evidence_sha256"] for r in family)
        fingerprint = hashlib.sha256(
            json.dumps([source, canonical, sorted(pattern_codes), evidence_digests],
                       separators=(",", ":"), ensure_ascii=True).encode("ascii")
        ).hexdigest()
        output.append({"source": source, "canonical_pr_number": canonical,
                       "pr_numbers": pr_ids, "pattern_code": next(iter(pattern_codes)),
                       "fingerprint_sha256": fingerprint,
                       "status": "UNVERIFIED_CANDIDATE_ONLY",
                       "requires_independent_validation": True})
    return {"schema": "UCIE_PATTERN_GROUP_PREVIEW_V1",
            "pr_count": len(rows), "family_count": len(output),
            "families": output, "persistent_writes": 0, "rules_promoted": 0,
            "production_approved": False}
