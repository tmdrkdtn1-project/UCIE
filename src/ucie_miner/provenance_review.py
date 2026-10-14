"""Stage 7 public PR provenance inspection: a read-only evidence check.

Only UCIE's pinned Stage 4 public PR sources may be queried. This verifies
metadata identity, not the semantics of a fix, patch safety, licensing,
independent regression tests, or approval. No raw patches are downloaded,
executed, saved or promoted; live reads require explicit opt-in.
"""
from __future__ import annotations

import hashlib
import json
import re

from .review import (
    ALLOWED, ReviewError, _check_timestamp, public_read_only_get,
)

HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
FIELDS = frozenset({"source", "pr_number", "public_url",
                    "merged_at", "evidence_sha256"})
MAX_INSPECTIONS = 40


def _validate(rows: object) -> list[dict]:
    if not isinstance(rows, list) or len(rows) > MAX_INSPECTIONS:
        raise ReviewError("invalid provenance review batch")
    keys = set()
    verified = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ReviewError("unexpected source metadata fields")
        source, number = row["source"], row["pr_number"]
        if (source not in ALLOWED or type(number) is not int
                or not 0 < number < 1_000_000
                or row["public_url"] != f"https://github.com/{source}/pull/{number}"
                or not isinstance(row["evidence_sha256"], str)
                or not HEX64.fullmatch(row["evidence_sha256"])):
            raise ReviewError("unapproved public source metadata")
        _check_timestamp(row["merged_at"])
        if (source, number) in keys:
            raise ReviewError("duplicate PR in provenance batch")
        keys.add((source, number))
        verified.append(row)
    return sorted(verified, key=lambda r: (r["source"], r["pr_number"]))


def inspect_public_prs(rows: object, *, verify_live: bool = False,
                       fetch=None) -> dict:
    """Anonymous public metadata-only inspection, no persistent changes.

    Dependency-injected fetchers are *synthetic only*: they can test
    comparison logic but never count as independent source verification.
    """
    checked = _validate(rows)
    if type(verify_live) is not bool:
        raise ReviewError("verify_live must be boolean")
    fetcher = public_read_only_get if fetch is None else fetch
    if not callable(fetcher):
        raise ReviewError("invalid metadata fetcher")
    result = []
    for row in checked:
        source, number = row["source"], row["pr_number"]
        state, observed_merge_sha = "NOT_CHECKED", None
        if verify_live:
            url = f"https://api.github.com/repos/{source}/pulls/{number}"
            try:
                data = fetcher(url)
                base = data.get("base") if isinstance(data, dict) else None
                repository = base.get("repo") if isinstance(base, dict) else None
                merge_sha = data.get("merge_commit_sha") if isinstance(data, dict) else None
                if (not isinstance(data, dict) or
                        data.get("number") != number or
                        type(data.get("number")) is not int or
                        data.get("merged") is not True or
                        data.get("merged_at") != row["merged_at"] or
                        data.get("html_url") != row["public_url"] or
                        not isinstance(repository, dict) or
                        repository.get("full_name") != source or
                        not isinstance(merge_sha, str) or
                        not HEX40.fullmatch(merge_sha)):
                    state = "SOURCE_MISMATCH"
                else:
                    observed_merge_sha = merge_sha
                    state = ("PUBLIC_API_METADATA_MATCHED" if fetch is None
                             else "SYNTHETIC_METADATA_MATCHED")
            except (ReviewError, TimeoutError, OSError, ValueError,
                    TypeError, KeyError):
                state = "SOURCE_UNAVAILABLE"
        digest_data = {
            "source": source, "pr_number": number,
            "merged_at": row["merged_at"],
            "miner_evidence_sha256": row["evidence_sha256"],
            "observed_merge_commit_sha": observed_merge_sha,
            "source_check": state,
        }
        fingerprint = hashlib.sha256(json.dumps(
            digest_data, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()
        result.append({
            **digest_data,
            "comparison_sha256": fingerprint,
            "metadata_check_only": True,
            "fix_independently_reproduced": False,
            "license_verified": False,
            "security_review_passed": False,
            "approved": False,
        })
    return {
        "schema": "UCIE_PUBLIC_PR_PROVENANCE_INSPECTION_V1",
        "items": result, "count": len(result),
        "live_checked": verify_live and fetch is None,
        "independently_verified_regressions": 0,
        "rules_promoted": 0,
        "persistent_writes": 0,
        "production_approved": False,
    }
