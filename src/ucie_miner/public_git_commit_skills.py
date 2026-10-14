"""Official git/git public commit discovery, distinct from PR-only staging.

Git's upstream workflow is commit-centric. This prevents the Git skill lane
from appearing empty merely because there are no newly merged PRs. Never
turn a commit into a fabricated PR ID; no patch is executed or retained.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re

from .public_discovery import CATEGORIES, DiscoveryError
from .public_evidence_routes import fetch_public_evidence
from .skill_profiles import PROFILE

GIT_SOURCE = "git/git"
GIT_COMMITS_URL = "https://api.github.com/repos/git/git/commits?per_page=20"
HEX40 = re.compile(r"[0-9a-f]{40}")
MAX_COMMITS = 20
MAX_MESSAGE_BYTES = 20000


def analyze_git_commits(rows, *, now=None):
    """Return hash-only public Git fix leads and first-party skill questions."""
    if not isinstance(rows, list) or len(rows) > MAX_COMMITS:
        raise DiscoveryError("oversized or invalid approved Git commit feed")
    timepoint = datetime.now(timezone.utc) if now is None else now
    if not isinstance(timepoint, datetime) or timepoint.tzinfo is None:
        raise DiscoveryError("UTC observation time required")
    timepoint = timepoint.astimezone(timezone.utc)
    output, seen = [], set()
    for item in rows:
        if not isinstance(item, dict):
            raise DiscoveryError("malformed public Git commit metadata")
        sha = item.get("sha")
        if not isinstance(sha, str) or not HEX40.fullmatch(sha) or sha in seen:
            raise DiscoveryError("invalid/duplicate public Git commit identity")
        seen.add(sha)
        public_url = f"https://github.com/git/git/commit/{sha}"
        if item.get("html_url") != public_url:
            raise DiscoveryError("noncanonical Git commit URL")
        inner = item.get("commit")
        if not isinstance(inner, dict):
            raise DiscoveryError("missing public Git commit metadata")
        message = inner.get("message")
        committer = inner.get("committer")
        parents = item.get("parents")
        if (not isinstance(message, str)
                or not 1 <= len(message.encode("utf-8")) <= MAX_MESSAGE_BYTES
                or not isinstance(committer, dict)
                or not isinstance(parents, list)
                or len(parents) > 3
                or not all(isinstance(p, dict)
                           and isinstance(p.get("sha"), str)
                           and HEX40.fullmatch(p["sha"]) for p in parents)):
            raise DiscoveryError("invalid Git commit content metadata")
        timestamp = committer.get("date")
        if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
            raise DiscoveryError("missing Git UTC commit timestamp")
        try:
            merged = datetime.fromisoformat(timestamp[:-1] + "+00:00")
        except ValueError as exc:
            raise DiscoveryError("invalid public Git commit timestamp") from exc
        if merged > timepoint:
            raise DiscoveryError("future Git commit metadata")
        if (timepoint - merged).days > 90:
            continue
        # Merge commit bodies may mention other changes, so only direct
        # non-merge commits with exactly one parent are skill candidates.
        if len(parents) != 1:
            continue
        title = message.split("\n", 1)[0].strip()
        tags = sorted(k for k, pattern in CATEGORIES.items() if pattern.search(title))
        if not tags:
            continue
        profile = PROFILE["git-workflow-prevention"]
        output.append({
            "source": GIT_SOURCE,
            "git_commit_sha": sha,
            "public_url": public_url,
            "message_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
            "committed_at": timestamp,
            "error_category_tags": tags,
            "skill_id": "git-workflow-prevention",
            "domain": profile["domain"],
            "review_question": profile["review_question"],
            "safe_call_guidance": profile["safe_call"],
            "regression_review_plan": profile["recommended_action"],
            "source_commit_verified_behavior": False,
            "released_version_inclusion_verified": False,
            "status": "UNVERIFIED_PUBLIC_GIT_COMMIT_LEAD",
        })
    return {
        "schema": "UCIE_APPROVED_GIT_COMMIT_SKILL_DISCOVERY_V1",
        "source": GIT_SOURCE,
        "public_api_route": GIT_COMMITS_URL,
        "records_examined": len(rows),
        "git_fix_lead_count": len(output),
        "git_skill_tasks": output,
        "raw_commit_messages_retained": False,
        "external_code_executed": False,
        "persistent_writes": 0,
        "model_weights_updated": False,
        "approved_rules_added": 0,
        "production_approved": False,
    }


def discover_git_commit_skills(*, fetch=fetch_public_evidence,
                               now=None):
    """Explicit caller-only one public GET to git/git; no state changes."""
    return analyze_git_commits(fetch(GIT_COMMITS_URL), now=now)
