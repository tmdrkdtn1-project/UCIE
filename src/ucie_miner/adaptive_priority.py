"""Stage 9: explainable, reversible prioritization from public-only leads.

Adaptive *selection*, not model weight training, persistent memory, autonomous
rule promotion, or reinforcement from private repositories. Does not save or
execute candidate content. Allows opt-out of any source and exact PR.
"""
from __future__ import annotations

import hashlib
import json

from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError

MAX_LEADS = 100
TAG_PRIORITY = {"SECURITY": 60, "CRASH": 45, "REGRESSION": 30,
                "COMPATIBILITY": 18, "TESTING": 5}


def _sha(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


def prioritize_public_leads(discovery, *, seen_public_prs=(),
                            opted_out_sources=(), opted_out_prs=(),
                            review_feedback=None, limit=12):
    """Compute deterministic candidate queue with explicit trust gates.

    Feedback is transient, explicit, structured *human ratings*, not scraped
    model instructions, private telemetry or durable machine learning.
    """
    if (not isinstance(discovery, dict)
            or discovery.get("schema") != "UCIE_MULTI_SOURCE_PUBLIC_DISCOVERY_V1"
            or discovery.get("persistent_writes") != 0
            or discovery.get("production_approved") is not False
            or not isinstance(discovery.get("feeds"), list)
            or len(discovery["feeds"]) > len(SOURCES)
            or type(limit) is not int or not 1 <= limit <= 30):
        raise DiscoveryError("invalid public discovery receipt")
    for name, seq in (("seen", seen_public_prs), ("source opt-outs", opted_out_sources),
                      ("PR opt-outs", opted_out_prs)):
        if not isinstance(seq, (tuple, list, set, frozenset)) or len(seq) > 1000:
            raise DiscoveryError("invalid bounded " + name)
    allowed = set(SOURCES)
    skips = set(opted_out_sources)
    if any(s not in allowed for s in skips):
        raise DiscoveryError("opt-out source unknown")
    def valid_key(k):
        return (isinstance(k, (list, tuple)) and len(k) == 2
                and k[0] in allowed and type(k[1]) is int
                and 1 <= k[1] <= 999999999)
    if any(not valid_key(v) for v in seen_public_prs) or any(
            not valid_key(v) for v in opted_out_prs):
        raise DiscoveryError("invalid public PR identity")
    seen = {tuple(x) for x in seen_public_prs}
    denied = {tuple(x) for x in opted_out_prs}

    choices = {} if review_feedback is None else review_feedback
    if (not isinstance(choices, dict) or len(choices) > 100
            or any(not valid_key(k) or v not in ("NEEDS_REVIEW", "LOW_SIGNAL", "SKIP")
                   for k, v in choices.items())):
        raise DiscoveryError("invalid explicit feedback")
    seen_in_payload = set()
    leads = []
    feed_sources = set()
    for feed in discovery["feeds"]:
        if (not isinstance(feed, dict)
                or feed.get("schema") != "UCIE_APPROVED_PUBLIC_DISCOVERY_V1"
                or feed.get("source") not in allowed
                or feed["source"] in feed_sources
                or feed.get("persistent_writes") != 0
                or feed.get("production_approved") is not False
                or feed.get("raw_text_retained") is not False
                or feed.get("proposals_promoted") != 0
                or not isinstance(feed.get("leads"), list)
                or type(feed.get("lead_count")) is not int
                or feed["lead_count"] != len(feed["leads"])):
            raise DiscoveryError("malformed feed receipt")
        feed_sources.add(feed["source"])
        for lead in feed["leads"]:
            if not isinstance(lead, dict):
                raise DiscoveryError("malformed candidate lead")
            source, number = lead.get("source"), lead.get("pr_number")
            key = (source, number)
            if (source != feed["source"] or type(number) is not int
                    or not 1 <= number <= 999999999
                    or key in seen_in_payload
                    or lead.get("skill_id") != SOURCE_SKILL[source]
                    or lead.get("public_url") !=
                    f"https://github.com/{source}/pull/{number}"
                    or lead.get("status") != "UNVERIFIED_PUBLIC_LEAD"
                    or lead.get("independent_fix_verified") is not False
                    or lead.get("license_checked") is not False
                    or type(lead.get("age_days")) is not int
                    or not 0 <= lead["age_days"] <= 90
                    or not isinstance(lead.get("tags"), list)
                    or not lead["tags"]
                    or any(t not in TAG_PRIORITY for t in lead["tags"])
                    or not isinstance(lead.get("title_sha256"), str)
                    or len(lead["title_sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in lead["title_sha256"])):
                raise DiscoveryError("untrusted public lead")
            seen_in_payload.add(key)
            if key in seen or key in denied or source in skips:
                continue
            feedback = choices.get(key)
            if feedback == "SKIP":
                continue
            weight = sum(TAG_PRIORITY[t] for t in set(lead["tags"]))
            freshness = max(0, 21 - lead["age_days"])
            feedback_delta = (15 if feedback == "NEEDS_REVIEW" else
                              -25 if feedback == "LOW_SIGNAL" else 0)
            # Novelty is calculated within this ephemeral run only; source
            # history is not a source for personal or private training.
            score = weight + freshness + feedback_delta
            leads.append({
                "source": source, "pr_number": number,
                "public_url": lead["public_url"],
                "skill_id": lead["skill_id"],
                "tags": list(lead["tags"]),
                "priority_score": score,
                "priority_reason": "PUBLIC_METADATA_HEURISTIC_ONLY",
                "review_feedback": feedback or "NONE",
                "rule_candidate_state": "NOT_REVIEWED",
                "independent_fix_verified": False,
                "auto_promoted": False,
                "production_approved": False,
            })
    if len(seen_in_payload) > MAX_LEADS:
        raise DiscoveryError("too many public lead records")
    # Prevent all top items from a single repo: round-robin on five public
    # source queues. This is explicit diversity policy, not model training.
    by_source = {}
    for lead in sorted(leads, key=lambda x: (
            -x["priority_score"], x["source"], x["pr_number"])):
        by_source.setdefault(lead["source"], []).append(lead)
    output = []
    while len(output) < limit and any(by_source.values()):
        for source in SOURCES:
            if by_source.get(source):
                output.append(by_source[source].pop(0))
                if len(output) >= limit:
                    break
    return {
        "schema": "UCIE_ADAPTIVE_PUBLIC_PRIORITY_PREVIEW_V1",
        "status": "CANDIDATES_ONLY",
        "ranking_method": "DETERMINISTIC_PUBLIC_TAGS_AND_TRANSIENT_FEEDBACK",
        "source_diversity": "APPROVED_SOURCE_ROUND_ROBIN",
        "leads_considered": len(seen_in_payload),
        "novel_review_queue": output,
        "review_queue_count": len(output),
        "queue_sha256": _sha(output),
        "opted_out_sources": sorted(skips),
        "opted_out_pr_count": len(denied),
        "persistent_feedback_learning": False,
        "model_weights_updated": False,
        "rules_auto_promoted": 0,
        "persisted_records": 0,
        "production_approved": False,
    }
