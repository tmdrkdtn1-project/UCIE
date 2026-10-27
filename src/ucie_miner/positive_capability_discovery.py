"""UCIE W05: find positive development capabilities from approved public PR metadata.

Distinct from existing error-fix mining: *title cues only* for beneficial
engine, skill, learning-logic designs. A candidate is NEVER a working/reusable
package, verified improvement, executable upstream code or approved Rulepack.
No raw PR title/body/patch is emitted, retained or executed. One exact existing
GitHub feed route/source and injected callback; no implicit network, DB or timer.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re

from .library_entry import build_library_entry
from .public_discovery import (
    SOURCES, DiscoveryError, PR_CAP, MAX_TITLE, SHA40, _utc, public_feed_url,
)
from .source_registry import get_source, SourceRegistryError

SCHEMA = "UCIE_W05_POSITIVE_PUBLIC_CAPABILITY_DISCOVERY_V1"
MAX_SOURCES = 5
MAX_CANDIDATES = 30
MAX_AGE_DAYS_RECENT = 365

# First-party heuristic labels, not findings. Positive technical patterns
# distinct from historical fixes; no arbitrary title text in outputs.
SIGNALS = (
    ("LEARNING_LOGIC", "LEARNING_FEEDBACK_LOOP",
     re.compile(r"\b(?:adaptive (?:training|learning)|feedback (?:loop|learning)|training pipeline|learning pipeline)\b", re.I)),
    ("DEVELOPMENT_ENGINE", "ENGINE_INCREMENTAL_BUILD",
     re.compile(r"\b(?:incremental (?:build|compilation)|build cache|build optimizer|compilation cache)\b", re.I)),
    ("DEVELOPMENT_ENGINE", "ENGINE_WORKFLOW_ORCHESTRATION",
     re.compile(r"\b(?:workflow engine|task orchestrator|build orchestration|ci pipeline)\b", re.I)),
    ("REUSABLE_SKILL", "SKILL_TEST_AUTOMATION",
     re.compile(r"\b(?:test automation|testing utility|test helper|linting workflow|code formatter)\b", re.I)),
    ("REUSABLE_SKILL", "SKILL_RELEASE_AUTOMATION",
     re.compile(r"\b(?:release automation|release workflow|dependency update automation)\b", re.I)),
)
REPAIR = re.compile(
    r"\b(?:fix|fixed|fixes|bug|bugfix|regression|repair|revert|crash|error|security|vulnerability|hotfix)\b", re.I)


def _validate_merge(row: object, source: str, at: datetime) -> tuple | None:
    if type(row) is not dict:
        raise DiscoveryError("untrusted merged PR metadata row")
    number, title, merged_at = row.get("number"), row.get("title"), row.get("merged_at")
    if (type(number) is not int or not 1 <= number <= 999999999
            or type(title) is not str or not 1 <= len(title) <= MAX_TITLE):
        raise DiscoveryError("invalid bounded public PR identity/title")
    if merged_at is None:
        return None  # not a merged public change
    merged = _utc(merged_at)
    if merged > at:
        raise DiscoveryError("future-dated upstream merge")
    if (row.get("html_url") != f"https://github.com/{source}/pull/{number}"
            or type(row.get("base")) is not dict
            or type(row["base"].get("repo")) is not dict
            or row["base"]["repo"].get("full_name") != source):
        raise DiscoveryError("unapproved public PR identity")
    merge_sha = row.get("merge_commit_sha")
    if merge_sha is None:
        return number, title, merged_at, None, (at - merged).days
    if type(merge_sha) is not str or SHA40.fullmatch(merge_sha) is None:
        raise DiscoveryError("invalid pinned merge commit SHA")
    return number, title, merged_at, merge_sha, (at - merged).days


def classify_public_capability_metadata(source_rows: object, *,
                                        source_id: str,
                                        now: datetime | None = None) -> dict:
    """Normalize only positive public technical *cues*, no claimed usable code."""
    try:
        src = get_source(source_id)
    except SourceRegistryError as exc:
        raise DiscoveryError("unapproved W05 public source") from exc
    if src["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
        raise DiscoveryError("W05 only accepts existing GitHub public PR metadata")
    repo = source_id.removeprefix("repo:")
    if repo not in SOURCES or type(source_rows) is not list or len(source_rows) > PR_CAP:
        raise DiscoveryError("oversized or unsupported positive metadata feed")
    instant = datetime.now(timezone.utc) if now is None else now
    if type(instant) is not datetime or instant.tzinfo is None:
        raise DiscoveryError("aware UTC discovery instant required")
    instant = instant.astimezone(timezone.utc)
    seen_prs, candidates, ambiguous, repairs, unpinned, unmerged = set(), [], 0, 0, 0, 0
    for row in source_rows:
        valid = _validate_merge(row, repo, instant)
        number = row.get("number") if type(row) is dict else None
        if number in seen_prs:
            raise DiscoveryError("duplicate PR number in approved feed")
        seen_prs.add(number)
        if valid is None:
            unmerged += 1
            continue
        number, title, merged_at, sha, age = valid
        if REPAIR.search(title):
            repairs += 1
            continue
        matched = [(kind, purpose) for kind, purpose, cue in SIGNALS
                   if cue.search(title)]
        if not matched:
            continue
        if len(matched) != 1:
            ambiguous += 1
            continue
        if sha is None:
            unpinned += 1
            continue
        kind, purpose = matched[0]
        title_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()
        metadata = [repo, number, sha, merged_at, title_hash, kind, purpose]
        digest = hashlib.sha256(json.dumps(
            metadata, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")).hexdigest()
        entry = build_library_entry({
            "kind": kind, "source_id": source_id,
            "evidence_reference": f"pr:{number}:{sha}",
            "evidence_sha256": digest,
            "purpose_code": purpose,
            "version_scope": "UNDETERMINED",
            "dependencies": [],
        })
        candidates.append({
            "library_item_id": entry["library_item_id"],
            "kind": kind,
            "source_id": source_id,
            "public_url": entry["public_url"],
            "reference": entry["evidence_reference"],
            "merge_commit_sha": sha,
            "merged_at_utc": merged_at,
            "upstream_age_days": age,
            "freshness_bucket": ("RECENT_UPSTREAM_MERGE" if age <= MAX_AGE_DAYS_RECENT
                                 else "HISTORICAL_PUBLIC_EVIDENCE"),
            "title_sha256": title_hash,
            "evidence_sha256": digest,
            "purpose_code": purpose,
            "skill_profile": entry["skill_profile"],
            "domain": entry["domain"],
            "evidence_strength": "MERGED_PR_TITLE_CUE_ONLY",
            "actual_capability_verified": False,
            "benefit_measured": False,
            "learning_logic_executable": False,
            "license_independently_reviewed": False,
            "approved": False,
            "export_allowed": False,
            "recommended_next_action": "REVIEW_PINNED_PUBLIC_CHANGE_AND_SAFE_FIRST_PARTY_EVALUATION",
        })
    candidates.sort(key=lambda x: (
        x["upstream_age_days"], x["source_id"], x["public_url"], x["purpose_code"],
    ))
    if len(candidates) > MAX_CANDIDATES:
        raise DiscoveryError("positive candidate result exceeded bounded cap")
    return {
        "schema": SCHEMA,
        "status": "POSITIVE_CAPABILITY_HINTS_UNVERIFIED_NO_GO",
        "source_id": source_id,
        "source_rows_examined": len(source_rows),
        "candidate_count": len(candidates),
        "nonmerged_count": unmerged,
        "unclassified_or_repair_count": len(source_rows) - len(candidates) - unmerged - ambiguous - unpinned,
        "repair_title_count": repairs,
        "ambiguous_positive_cue_count": ambiguous,
        "unpinned_positive_cue_count": unpinned,
        "candidates": candidates,
        "untrusted_source_titles_retained": False,
        "raw_patch_or_code_retained": False,
        "network_requests": 0,
        "database_writes": 0,
        "model_weights_changed": False,
        "auto_promoted": False,
        "production_approved": False,
    }


def discover_positive_capabilities(*, source_ids: tuple[str, ...],
                                   fetch, now: datetime | None = None) -> dict:
    """One existing approved PR feed per source via caller-supplied callback.

    This W05 one-shot researcher is NOT installed into the hourly collector.
    Callback may perform GET only if separately allowed by existing policy.
    """
    if (type(source_ids) is not tuple or not 1 <= len(source_ids) <= MAX_SOURCES
            or len(set(source_ids)) != len(source_ids) or not callable(fetch)):
        raise DiscoveryError("invalid bounded W05 collection request")
    planned = []
    for source_id in source_ids:
        if type(source_id) is not str:
            raise DiscoveryError("invalid public source identity")
        try:
            source = get_source(source_id)
        except SourceRegistryError as exc:
            raise DiscoveryError("unapproved source cannot be fetched") from exc
        if source["source_kind"] != "INDEPENDENT_PUBLIC_REPOSITORY":
            raise DiscoveryError("not a public PR feed source")
        repo = source_id.removeprefix("repo:")
        planned.append((source_id, public_feed_url(repo)))
    outputs = []
    for source_id, url in planned:
        receipt = classify_public_capability_metadata(
            fetch(url), source_id=source_id, now=now)
        outputs.append(receipt)
    return {
        "schema": SCHEMA,
        "status": "POSITIVE_DISCOVERY_RESEARCH_ONLY_NO_GO",
        "sources": outputs,
        "sources_checked": len(outputs),
        "existing_feed_callback_calls": len(planned),
        "candidate_count": sum(item["candidate_count"] for item in outputs),
        "actually_contacted_network": "CALLER_CALLBACK_CONTROLLED",
        "new_api_route_added": False,
        "database_writes": 0,
        "model_weights_changed": False,
        "auto_promoted": False,
        "production_approved": False,
    }
