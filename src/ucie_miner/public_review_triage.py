"""Stage12: deterministic multiaxis review preview from already validated UCIE rows.

Only public-source IDs, pinned hashes, reviewed static tag vocabularies, and
UCIE-authored guidance are used. A high review priority is NEVER a claim of
high confidence in the upstream fix. No external GET, database writes, learned
weights, private sources, executable patch handling, or rule promotion.
"""
from __future__ import annotations

import re

from .public_discovery import (
    CATEGORIES, DiscoveryError, SOURCES, SOURCE_SKILL,
)
from .public_evidence_routes import TAGS as PR_TAGS, TRANSITION_SIGNALS
from .skill_profiles import PROFILE

MAX_TRIAGE_ROWS = 20_000
MAX_PREVIEW = 12
SHA40 = r"[a-f0-9]{40}"
SHA64 = r"[a-f0-9]{64}"
PR_REF = re.compile(r"pr:([1-9][0-9]{0,8}):" + SHA40)
GIT_REF = re.compile(r"commit:" + SHA40)
FIX_REF = re.compile(
    r"fix-pr:([1-9][0-9]{0,8}):" + SHA40 + ":" + SHA64
)

# Review urgency only: NEVER a probability, confidence, security severity or
# evidence-backed guarantee of behavior.
REVIEW_WEIGHTS = {
    "SECURITY": 5,
    "CRASH": 5,
    "CONCURRENCY": 4,
    "EXCEPTION_HANDLING": 4,
    "API_CONTRACT": 4,
    "REGRESSION": 4,
    "TEST_REGRESSION": 3,
    "VERSION_COMPAT": 3,
    "COMPATIBILITY": 3,
    "TESTING": 2,
}
EVIDENCE_LEVELS = (
    "PUBLIC_PR_METADATA_UNVERIFIED",
    "PUBLIC_GIT_COMMIT_METADATA_UNVERIFIED",
    "STRUCTURED_PATCH_SIGNAL_UNVERIFIED",
)
ALLOWED_HINTS = frozenset(
    ["PATCH_OBSERVED_ADD_" + x for x in TRANSITION_SIGNALS]
    + ["PATCH_OBSERVED_REMOVE_" + x for x in TRANSITION_SIGNALS]
    + [
        "PATCH_OBSERVED_DELTA_" + x + "_" + y
        for x in TRANSITION_SIGNALS
        for y in TRANSITION_SIGNALS
        if x != y
    ]
)


def triage_unverified_review_rows(rows, *, limit=12):
    """Make a bounded, non-persistent human review agenda for six-field rows.

    Rows must originate from the separately validated Stage10 and Stage15
    local readers. Validate again at this public boundary to fail closed if
    a caller supplies fabricated source identities, tags or phase hints.
    """
    if (not isinstance(rows, (list, tuple))
            or len(rows) > MAX_TRIAGE_ROWS
            or type(limit) is not int or not 1 <= limit <= MAX_PREVIEW):
        raise DiscoveryError("invalid bounded review triage request")
    classified = []
    seen = set()
    by_source = {source: 0 for source in SOURCES}
    by_level = {level: 0 for level in EVIDENCE_LEVELS}
    by_pattern = {tag: 0 for tag in REVIEW_WEIGHTS}
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 6:
            raise DiscoveryError("invalid public review row shape")
        source, reference, skill, evidence, tags, hint = row
        if (type(source) is not str or source not in SOURCES
                or type(skill) is not str or skill != SOURCE_SKILL[source]
                or type(reference) is not str or len(reference) > 160
                or type(evidence) is not str
                or re.fullmatch(SHA64, evidence) is None
                or not isinstance(tags, list)
                or len(tags) > len(REVIEW_WEIGHTS)
                or any(type(tag) is not str for tag in tags)
                or len(set(tags)) != len(tags)
                or hint is not None and (
                    type(hint) is not str or hint not in ALLOWED_HINTS)):
            raise DiscoveryError("untrusted review triage identity or signals")

        if PR_REF.fullmatch(reference):
            level = EVIDENCE_LEVELS[0]
            allowed_tags = PR_TAGS
        elif GIT_REF.fullmatch(reference) and source == "git/git":
            level = EVIDENCE_LEVELS[1]
            allowed_tags = CATEGORIES
        elif FIX_REF.fullmatch(reference):
            level = EVIDENCE_LEVELS[2]
            allowed_tags = PR_TAGS
        else:
            raise DiscoveryError("untrusted public review evidence reference")
        if (any(tag not in allowed_tags or tag not in REVIEW_WEIGHTS
                for tag in tags)
                or (hint is not None and level != EVIDENCE_LEVELS[2])):
            raise DiscoveryError("misattributed public review tags")
        identity = (source, reference, evidence)
        if identity in seen:
            raise DiscoveryError("duplicate unverified review evidence")
        seen.add(identity)
        by_source[source] += 1
        by_level[level] += 1
        for tag in tags:
            by_pattern[tag] += 1
        priority = max((REVIEW_WEIGHTS[tag] for tag in tags), default=0)
        classified.append({
            "source": source,
            "reference": reference,
            "evidence_sha256": evidence,
            "skill_id": skill,
            "evidence_level": level,
            "error_pattern_tags": sorted(tags),
            "patch_transition_hint": hint,
            "review_priority_score": priority,
            "review_priority_band": (
                "REVIEW_FIRST" if priority >= 4 else
                "NORMAL_REVIEW" if priority >= 2 else
                "LOW_SIGNAL_REVIEW"
            ),
            "human_review_action": PROFILE[skill]["recommended_action"],
            "independent_fix_verified": False,
            "release_inclusion_verified": False,
            "license_approved": False,
            "rule_approved": False,
        })

    classified.sort(key=lambda item: (
        -item["review_priority_score"],
        # Richer structured hints get a review tie-break only, NOT higher
        # probability that the purported fix actually works.
        -(item["evidence_level"] == EVIDENCE_LEVELS[2]),
        SOURCES.index(item["source"]), item["reference"],
        item["evidence_sha256"],
    ))
    return {
        "schema": "UCIE_PUBLIC_MULTIAXIS_REVIEW_TRIAGE_V1",
        "status": "UNVERIFIED_REVIEW_AGENDA_ONLY",
        "triaged_revisions": len(classified),
        "source_counts": by_source,
        "evidence_level_counts": by_level,
        "pattern_signal_counts": by_pattern,
        "selected_for_review": classified[:limit],
        "selected_count": min(limit, len(classified)),
        "priority_is_confidence": False,
        "upstream_fix_verified": False,
        "source_origin_independently_attested": False,
        "release_inclusion_verified": False,
        "license_approved": False,
        "human_approval_required": True,
        "external_api_gets": 0,
        "persistent_writes": 0,
        "auto_promoted": False,
        "production_approved": False,
    }
