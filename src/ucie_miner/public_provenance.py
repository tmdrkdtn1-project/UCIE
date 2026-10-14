"""Strict, read-only upstream provenance cross-check for pinned public sources.

Independent API lookups are caller-injected and cannot validate license permissions.
The output is a source-authenticated metadata candidate, not a verified fix.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from .core import MiningError, PUBLIC_SOURCES, fetch_public_json
from .evidence import SOURCES


def _pr_detail_url(source: str, number: int) -> str:
    if source not in PUBLIC_SOURCES or source not in SOURCES:
        raise MiningError("source outside approved collector scope")
    if type(number) is not int or number < 1:
        raise MiningError("invalid PR number")
    return f"https://api.github.com/repos/{source}/pulls/{number}"


def crosscheck_pr_metadata(
    source: str, list_item: object, *,
    fetch=fetch_public_json,
) -> dict:
    """Fetch exact PR detail and require public API metadata consistency.

    No patch/license is fetched, no tokens are used, and no source text is kept.
    """
    if not isinstance(list_item, dict):
        raise MiningError("invalid list PR record")
    number = list_item.get("number")
    url = _pr_detail_url(source, number)
    detail = fetch(url)
    if not isinstance(detail, dict):
        raise MiningError("invalid PR detail")
    canonical = f"https://github.com/{source}/pull/{number}"
    if (detail.get("number") != number or detail.get("html_url") != canonical
            or detail.get("state") != "closed"
            or detail.get("merged") is not True
            or detail.get("merged_at") != list_item.get("merged_at")
            or not isinstance(detail.get("merged_at"), str)):
        raise MiningError("PR metadata mismatch")
    commit = detail.get("merge_commit_sha")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise MiningError("missing merged commit SHA")
    if not isinstance(detail.get("updated_at"), str):
        raise MiningError("missing update timestamp")
    # No caller-supplied license value is accepted as an authoritative fact.
    return {"status": "PUBLIC_PR_METADATA_CROSSCHECKED",
            "source": source, "pr_number": number, "url": canonical,
            "merge_commit_sha": commit, "merged_at": detail["merged_at"],
            "updated_at": detail["updated_at"],
            "license_verified": False, "fix_verified": False,
            "rule_promoted": False}
