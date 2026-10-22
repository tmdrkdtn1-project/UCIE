"""Bounded UCIE PUBLIC_ONLY library skill catalog preview (no distribution).

Transforms already validated five-source research batches into first-party
technical catalog cards. These are research tasks, never installable skills.
No network, disk, recipient lookup, scheduler, signing or cross-project access.
"""
from __future__ import annotations

import hashlib
import json

from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError
from .public_skill_digest import compare_public_skill_batches
from .skill_profiles import PROFILE

SCHEMA = "UCIE_PUBLIC_LIBRARY_SKILL_CATALOG_PREVIEW_V1"
REVIEW_GATE = "INDEPENDENT_SOURCE_VERSION_LICENSE_SECURITY_REGRESSION_AND_OWNER_SIGNOFF"
_ALLOWED_CHANGE = frozenset({
    "NEW_IN_BATCH_SCOPE",
    "MERGE_IDENTITY_CHANGED_RECHECK",
    "PUBLIC_EVIDENCE_FINGERPRINT_CHANGED",
    "UNCHANGED_WITHIN_BATCH_SCOPE",
})
_ALLOWED_TAGS = frozenset({
    "SECURITY", "CRASH", "REGRESSION", "COMPATIBILITY", "TESTING",
})


def _digest(data: object) -> str:
    raw = json.dumps(data, ensure_ascii=True, allow_nan=False, sort_keys=True,
                     separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def preview_library_skill_catalog(current: dict, previous: dict | None = None) -> dict:
    """Prepare deterministic, non-installable public research catalog cards.

    Existing batch/digest validators enforce bounded approved source identities,
    canonical public URLs, pinned revisions, trusted first-party guidance and
    all NO_GO gates. No third-party title, patch or arbitrary text is emitted.
    """
    digest = compare_public_skill_batches(current, previous)
    if (digest.get("schema") != "UCIE_PUBLIC_SKILL_KNOWLEDGE_DIGEST_V1"
            or digest.get("status") != "PUBLIC_RESEARCH_REVIEW_ONLY_NO_GO"
            or digest.get("production_approved") is not False
            or digest.get("approved_rules_added") != 0
            or digest.get("persistent_learning_performed") is not False):
        raise DiscoveryError("unapproved public skill digest")

    topic_map = {}
    for source in SOURCES:
        skill_id = SOURCE_SKILL[source]
        profile = PROFILE[skill_id]
        topic_map[skill_id] = {
            "skill_id": skill_id,
            "domain": profile["domain"],
            "approved_public_source": source,
            "review_question": profile["review_question"],
            "safe_call_guidance": profile["safe_call"],
            "manual_review_plan": profile["recommended_action"],
            "candidate_count": 0,
            "research_cards": [],
            "installable_skill_count": 0,
        }

    seen = set()
    for entry in digest["candidate_tasks"]:
        if not isinstance(entry, dict):
            raise DiscoveryError("invalid skill catalog card")
        skill_id = entry.get("skill_id")
        url = entry.get("public_url")
        tags = entry.get("public_error_pattern_tags")
        classification = entry.get("change_classification")
        if (skill_id not in topic_map
                or not isinstance(url, str)
                or url in seen
                or classification not in _ALLOWED_CHANGE
                or not isinstance(tags, list)
                or len(set(tags)) != len(tags)
                or any(type(t) is not str or t not in _ALLOWED_TAGS for t in tags)
                or entry.get("safe_call_guidance") !=
                    PROFILE[skill_id]["safe_call"]
                or entry.get("manual_regression_plan") !=
                    PROFILE[skill_id]["recommended_action"]
                or entry.get("actual_upstream_fix_verified") is not False
                or entry.get("source_license_independently_approved") is not False
                or entry.get("human_signoff_received") is not False):
            raise DiscoveryError("untrusted or approved-looking skill catalog card")
        seen.add(url)
        source = topic_map[skill_id]["approved_public_source"]
        is_git = entry.get("evidence_kind") == "GIT_DIRECT_COMMIT"
        if is_git:
            if skill_id != "git-workflow-prevention" or not url.startswith(
                    "https://github.com/git/git/commit/"):
                raise DiscoveryError("invalid direct commit catalog identity")
        elif not url.startswith("https://github.com/" + source + "/pull/"):
            raise DiscoveryError("invalid public PR catalog identity")
        card = {
            "card_id_sha256": hashlib.sha256(url.encode("ascii")).hexdigest(),
            "public_reference_url": url,
            "reference_kind": "GIT_DIRECT_COMMIT" if is_git else "MERGED_PR",
            "change_in_bounded_selection": classification,
            "technical_tags": sorted(tags),
            "safe_call_guidance": PROFILE[skill_id]["safe_call"],
            "required_review": REVIEW_GATE,
            "status": "UNVERIFIED_RESEARCH_ONLY_NOT_INSTALLABLE",
            "source_verified_as_fix": False,
            "skill_ready_for_delivery": False,
        }
        topic = topic_map[skill_id]
        topic["research_cards"].append(card)
        topic["candidate_count"] += 1

    topics = list(topic_map.values())
    for topic in topics:
        topic["research_cards"].sort(
            key=lambda x: (x["public_reference_url"], x["reference_kind"]))
    if sum(t["candidate_count"] for t in topics) != digest["candidate_count"]:
        raise DiscoveryError("catalog candidate count mismatch")

    # Not a signed artifact, a publishable Rulepack, or a recipient-specific
    # payload. No project information is accepted or referenced.
    payload = {
        "schema": SCHEMA,
        "status": "PUBLIC_RESEARCH_CATALOG_PREVIEW_NO_GO",
        "knowledge_digest_sha256": digest["digest_sha256"],
        "topic_count": len(topics),
        "candidate_count": digest["candidate_count"],
        "changed_candidate_count": digest["important_changes_in_selected_scope"],
        "topics": topics,
        "candidate_selection_scope": "BOUNDED_BATCH_NOT_COMPLETE_LIBRARY",
        "not_seen_means_deleted": False,
        "delivery": {
            "mode": "RECIPIENT_PULL_AFTER_SEPARATE_INDEPENDENT_APPROVAL",
            "review_gate": REVIEW_GATE,
            "available_signed_skill_count": 0,
            "installable_skills": [],
            "auto_install": False,
            "auto_inject_into_projects": False,
            "scheduler_registered": False,
            "ready_for_recipient_distribution": False,
        },
        "external_code_executed": False,
        "operating_database_writes": 0,
        "model_weights_updated": False,
        "auto_promoted_rules": 0,
        "production_approved": False,
    }
    payload["catalog_sha256"] = _digest(payload)
    payload["catalog_sha256_is_signature"] = False
    return payload
