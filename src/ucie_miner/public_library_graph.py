"""UCIE Library bounded public-only knowledge graph and revision preview.

Derived only from independently authored, prevalidated public skill metadata.
Relations are taxonomy associations, never proof of causality, correctness,
license acceptance or release-version applicability. No IO, network, scheduler,
recipient identities, installable instructions, or production distribution.
"""
from __future__ import annotations

import hashlib
import json

from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError
from .public_library_catalog import preview_library_skill_catalog

SCHEMA = "UCIE_PUBLIC_LIBRARY_KNOWLEDGE_GRAPH_PREVIEW_V1"
SNAPSHOT_SCHEMA = "UCIE_PUBLIC_LIBRARY_REVISION_SNAPSHOT_PREVIEW_V1"
MAX_CARDS = 6  # Up to 3 public PRs and 3 direct Git commits, not a full index.


def _sha256(data: object) -> str:
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=True,
                           allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _identities(batch: dict) -> dict:
    """Extract bounded revision identity from validated batch input only."""
    entries = {}
    for item in batch["candidate_skill_queue"]:
        url = item["public_url"]
        if url in entries:
            raise DiscoveryError("duplicate public PR identity")
        entries[url] = {
            "source": item["source"],
            "skill_id": item["skill_id"],
            "revision_kind": "PR_MERGE_COMMIT_SHA",
            "revision_sha": item["pinned_merge_commit_sha"],
            "public_evidence_sha256": item["evidence_sha256"],
        }
    for item in batch.get("git_commit_skill_queue", []):
        url = item["public_url"]
        if url in entries:
            raise DiscoveryError("duplicate direct commit identity")
        entries[url] = {
            "source": "git/git",
            "skill_id": "git-workflow-prevention",
            "revision_kind": "GIT_DIRECT_COMMIT_SHA",
            "revision_sha": item["git_commit_sha"],
            "public_evidence_sha256": item["message_sha256"],
        }
    if len(entries) > MAX_CARDS:
        raise DiscoveryError("oversized public revision preview")
    return entries


def preview_library_knowledge_graph(current: dict,
                                    previous: dict | None = None) -> dict:
    """Taxonomy links, evidence revision tracking and unsigned snapshot.

    Validates current and previous receipts through the same strict catalog
    entrypoint; altered signatures, approvals, URLs and safe-call guidance
    fail closed before the graph or snapshot is assembled.
    """
    catalog = preview_library_skill_catalog(current, previous)
    old_catalog = (None if previous is None else
                   preview_library_skill_catalog(previous))
    identities = _identities(current)
    previous_identities = (_identities(previous)
                           if old_catalog is not None else {})

    cards = {}
    shelves = {}
    for shelf in catalog["topics"]:
        skill = shelf["skill_id"]
        if skill in shelves or shelf["approved_public_source"] not in SOURCES:
            raise DiscoveryError("invalid or duplicate technical library shelf")
        if SOURCE_SKILL[shelf["approved_public_source"]] != skill:
            raise DiscoveryError("skill source relation mismatch")
        shelves[skill] = shelf
        for card in shelf["research_cards"]:
            url = card["public_reference_url"]
            if url in cards or url not in identities:
                raise DiscoveryError("unbound public research card")
            identity = identities[url]
            if (identity["skill_id"] != skill
                    or identity["source"] != shelf["approved_public_source"]):
                raise DiscoveryError("card revision source mismatch")
            cards[url] = (skill, card, identity)
    if (len(cards) != catalog["candidate_count"]
            or set(cards) != set(identities)
            or len(shelves) != len(SOURCES)):
        raise DiscoveryError("public card identity reconciliation failed")

    # Every edge is an explicit classification, not inferred behavior.
    nodes = []
    edges = []
    tags = set()
    for source in SOURCES:
        skill = SOURCE_SKILL[source]
        nodes.append({
            "id": "skill:" + skill,
            "kind": "FIRST_PARTY_TECHNICAL_SKILL_DOMAIN",
            "public_source": source,
            "domain": shelves[skill]["domain"],
        })
    change_events = []
    for url in sorted(cards):
        skill, card, revision = cards[url]
        cid = "reference:" + card["card_id_sha256"]
        nodes.append({
            "id": cid,
            "kind": "UNVERIFIED_PUBLIC_RESEARCH_REFERENCE",
            "public_url": url,
            "source": revision["source"],
            "skill_id": skill,
            "revision_kind": revision["revision_kind"],
            "pinned_revision_sha": revision["revision_sha"],
            "evidence_fingerprint_sha256": revision["public_evidence_sha256"],
            "reported_upstream_release_version": None,
            "release_inclusion_verified": False,
            "source_fix_independently_verified": False,
            "review_only": True,
        })
        edges.append({
            "from": cid, "to": "skill:" + skill,
            "relation": "CLASSIFIED_BY_APPROVED_SOURCE_MAPPING",
            "independent_accuracy_proven": False,
        })
        for tag in card["technical_tags"]:
            tags.add(tag)
            edges.append({
                "from": cid, "to": "tag:" + tag,
                "relation": "BOUNDED_METADATA_TAG_MATCH",
                "independent_accuracy_proven": False,
            })
        change_events.append({
            "public_url": url,
            "classification": card["change_in_bounded_selection"],
            "revision_kind": revision["revision_kind"],
            "pinned_revision_sha": revision["revision_sha"],
            "previous_pinned_revision_sha": (
                previous_identities[url]["revision_sha"]
                if url in previous_identities else None),
            "evidence_fingerprint_sha256": revision["public_evidence_sha256"],
            "previous_evidence_fingerprint_sha256": (
                previous_identities[url]["public_evidence_sha256"]
                if url in previous_identities else None),
            "actual_technology_version_verified": False,
            "eligible_for_skill_install": False,
        })
    for tag in sorted(tags):
        nodes.append({
            "id": "tag:" + tag, "kind": "FIRST_PARTY_BOUNDED_TECHNICAL_TAG",
        })

    # Share-tag associations are symmetric, noncausal and deterministic.
    urls = sorted(cards)
    for index, left_url in enumerate(urls):
        left = cards[left_url][1]
        for right_url in urls[index + 1:]:
            right = cards[right_url][1]
            common = sorted(set(left["technical_tags"]) &
                            set(right["technical_tags"]))
            if common:
                edges.append({
                    "from": "reference:" + left["card_id_sha256"],
                    "to": "reference:" + right["card_id_sha256"],
                    "relation": "SHARED_METADATA_TAGS_NO_CAUSAL_CLAIM",
                    "shared_tags": common,
                    "independent_accuracy_proven": False,
                })
    nodes.sort(key=lambda x: x["id"])
    edges.sort(key=lambda x: (x["from"], x["to"], x["relation"]))
    change_events.sort(key=lambda x: x["public_url"])

    # This snapshot is a comparison receipt only. Zero installable skills.
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "status": "UNSIGNED_CANDIDATE_REVISION_PREVIEW_NO_GO",
        "based_on_catalog_sha256": catalog["catalog_sha256"],
        "prior_catalog_sha256": (old_catalog["catalog_sha256"]
                                 if old_catalog is not None else None),
        "candidate_count": len(change_events),
        "change_events": change_events,
        "previously_selected_not_seen": [{
            "public_url": url,
            "status": "NOT_IN_THIS_BOUNDED_SELECTION_NOT_DELETED",
        } for url in sorted(set(previous_identities) - set(cards))],
        "bounded_absence_is_deletion": False,
        "source_release_versions_verified": False,
        "approved_skill_payloads": [],
        "distribution_authorized": False,
        "digital_signature": None,
        "scheduler_registered": False,
        "recipient_projects_contacted": 0,
        "operating_database_writes": 0,
    }
    snapshot["snapshot_sha256"] = _sha256(snapshot)
    snapshot["snapshot_sha256_is_signature"] = False

    output = {
        "schema": SCHEMA,
        "status": "PUBLIC_METADATA_RELATIONSHIP_PREVIEW_NO_GO",
        "source_scope": list(SOURCES),
        "catalog_sha256": catalog["catalog_sha256"],
        "skill_domain_count": len(shelves),
        "reference_count": len(cards),
        "tag_node_count": len(tags),
        "nodes": nodes,
        "edges": edges,
        "relationship_claim_scope": "TAXONOMY_COOCCURRENCE_NOT_CAUSATION",
        "revision_snapshot": snapshot,
        "external_code_executed": False,
        "network_requests": 0,
        "persistent_learning_performed": False,
        "cross_project_reads_or_writes": 0,
        "approved_rules_added": 0,
        "production_approved": False,
    }
    output["graph_sha256"] = _sha256(output)
    output["graph_sha256_is_signature"] = False
    return output
