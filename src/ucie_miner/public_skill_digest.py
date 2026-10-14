"""UCIE Stage 9.9: read-only per-skill knowledge digest, across two public batches.

Only first-party summary fields, hashes, public PR identity and pre-authored
safety guidance. No imported upstream code, executable scripts, persistent
learning, external repositories, scheduled notifications or signed Rulepack.
Previous-run receipts must be explicitly supplied; UCIE never silently reads
private history or writes a persistent feedback record.
"""
from __future__ import annotations

from .public_batch import review_batch_preview, _fingerprint
from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError
from .skill_profiles import PROFILE
from .public_evidence_routes import TAGS

MAX_BATCH_ITEMS = 3


def _map_candidate_batch(receipt):
    """Verify candidate-only receipt, retaining only allowlisted metadata."""
    review_batch_preview(receipt)
    items = receipt["candidate_skill_queue"]
    if not isinstance(items, list) or len(items) > MAX_BATCH_ITEMS:
        raise DiscoveryError("oversized submitted public skill queue")
    mapping = {}
    for item in items:
        source, pr, skill = (item.get("source"),
                             item.get("pr_number"),
                             item.get("skill_id"))
        if (source not in SOURCES or type(pr) is not int or pr < 1
                or skill != SOURCE_SKILL[source]
                or not isinstance(item.get("pinned_merge_commit_sha"), str)
                or len(item["pinned_merge_commit_sha"]) != 40
                or any(c not in "0123456789abcdef"
                       for c in item["pinned_merge_commit_sha"])
                or not isinstance(item.get("evidence_sha256"), str)
                or len(item["evidence_sha256"]) != 64
                or any(c not in "0123456789abcdef"
                       for c in item["evidence_sha256"])
                or not isinstance(item.get("error_pattern_tags"), list)
                or len(item["error_pattern_tags"]) > len(TAGS)
                or any(type(t) is not str or t not in TAGS
                       for t in item["error_pattern_tags"])
                or len(set(item["error_pattern_tags"])) != len(item["error_pattern_tags"])
                or not isinstance(item.get("missing_evidence_types"), list)
                or any(t not in ("patch", "release", "document", "advisory")
                       for t in item["missing_evidence_types"])
                or len(set(item["missing_evidence_types"])) != len(item["missing_evidence_types"])
                or item.get("patch_signal_status") not in (
                    "HINT_ONLY_NOT_VERIFIED", "NOT_COLLECTED")
                or (item.get("test_file_count") is not None and
                    (type(item["test_file_count"]) is not int
                     or not 0 <= item["test_file_count"] <= 30))
                or item.get("safe_call_guidance") != PROFILE[skill]["safe_call"]
                or item.get("review_plan") != PROFILE[skill]["recommended_action"]
                or item.get("human_approval_received") is not False
                or item.get("regression_independently_verified") is not False
                or item.get("skill_installed") is not False):
            raise DiscoveryError("untrusted or inconsistent public skill item")
        key = (source, pr)
        if key in mapping:
            raise DiscoveryError("duplicate public PR in skill digest")
        mapping[key] = item
    return mapping


def compare_public_skill_batches(current, previous=None):
    """Compute within-scope novelty, never 'deletion' from incomplete feeds."""
    latest = _map_candidate_batch(current)
    previous_entries = {} if previous is None else _map_candidate_batch(previous)
    groups = {SOURCE_SKILL[source]: {
        "source": source,
        "domain": PROFILE[SOURCE_SKILL[source]]["domain"],
        "current_candidate_count": 0,
        "new_candidates": 0,
        "changed_evidence": 0,
        "unchanged_candidates": 0,
        "needs_manual_review": 0,
    } for source in SOURCES}
    items = []
    important = 0
    for key in sorted(latest, key=lambda k: (SOURCES.index(k[0]), k[1])):
        item, before = latest[key], previous_entries.get(key)
        if before is None:
            category = "NEW_IN_BATCH_SCOPE"
        elif before["pinned_merge_commit_sha"] != item["pinned_merge_commit_sha"]:
            category = "MERGE_IDENTITY_CHANGED_RECHECK"
        elif before["evidence_sha256"] != item["evidence_sha256"]:
            category = "PUBLIC_EVIDENCE_FINGERPRINT_CHANGED"
        else:
            category = "UNCHANGED_WITHIN_BATCH_SCOPE"
        group = groups[item["skill_id"]]
        group["current_candidate_count"] += 1
        group["needs_manual_review"] += 1
        if category == "NEW_IN_BATCH_SCOPE":
            group["new_candidates"] += 1
            important += 1
        elif category == "UNCHANGED_WITHIN_BATCH_SCOPE":
            group["unchanged_candidates"] += 1
        else:
            group["changed_evidence"] += 1
            important += 1
        items.append({
            "public_url": item["public_url"],
            "skill_id": item["skill_id"],
            "change_classification": category,
            "public_error_pattern_tags": sorted(set(item["error_pattern_tags"])),
            "safe_call_guidance": PROFILE[item["skill_id"]]["safe_call"],
            "manual_regression_plan": PROFILE[item["skill_id"]]["recommended_action"],
            "evidence_status": item["evidence_status"],
            "missing_evidence_types": item["missing_evidence_types"],
            "actual_upstream_fix_verified": False,
            "source_license_independently_approved": False,
            "human_signoff_received": False,
        })
    not_seen_keys = sorted(
        set(previous_entries) - set(latest),
        key=lambda k: (SOURCES.index(k[0]), k[1]))
    not_seen = [{
        "public_url": f"https://github.com/{source}/pull/{number}",
        "status": "NOT_IN_THIS_BOUNDED_SELECTION_NOT_DELETED",
    } for source, number in not_seen_keys]
    return {
        "schema": "UCIE_PUBLIC_SKILL_KNOWLEDGE_DIGEST_V1",
        "status": "PUBLIC_RESEARCH_REVIEW_ONLY_NO_GO",
        "skill_groups": [groups[SOURCE_SKILL[s]] for s in SOURCES],
        "candidate_tasks": items,
        "previously_selected_not_seen": not_seen,
        "candidate_count": len(items),
        "important_changes_in_selected_scope": important,
        "notify_if_manually_scheduled": important > 0,
        "digest_sha256": _fingerprint(items),
        "digest_sha256_is_signature": False,
        "real_world_accuracy_verified": False,
        "model_weights_updated": False,
        "persistent_learning_performed": False,
        "user_private_data_processed": False,
        "external_code_executed": False,
        "approved_rules_added": 0,
        "operating_database_writes": 0,
        "scheduler_registered": False,
        "production_approved": False,
    }
