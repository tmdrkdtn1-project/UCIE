"""UCIE first-party evidence quality assessment and review-loop preview.

Consumes ONLY the already-validated public Library graph. This is a bounded,
deterministic, read-only review agenda, NOT accuracy scoring, independent QA,
signed approval, a Rulepack, a scheduler, or persistent learning.
"""
from __future__ import annotations

import hashlib
import json

from .public_discovery import SOURCES, SOURCE_SKILL, DiscoveryError
from .public_library_graph import preview_library_knowledge_graph
from .skill_profiles import PROFILE

SCHEMA = "UCIE_LIBRARY_MULTIDIMENSION_REVIEW_PREVIEW_V1"
STATUS = "PUBLIC_LIBRARY_EVIDENCE_ASSESSMENT_UNVERIFIED_NO_GO"
RECHECK = frozenset({
    "NEW_IN_BATCH_SCOPE",
    "MERGE_IDENTITY_CHANGED_RECHECK",
    "PUBLIC_EVIDENCE_FINGERPRINT_CHANGED",
})
GATES = (
    "EXACT_UPSTREAM_RELEASE_VERSION_AND_INCLUSION",
    "SOURCE_LICENSE_INDEPENDENT_REVIEW",
    "SECURITY_INDEPENDENT_REVIEW",
    "ISOLATED_REGRESSION_REPRODUCTION",
    "INDEPENDENT_QA_EVIDENCE_AND_IDENTITY",
    "EXPLICIT_OWNER_APPROVAL",
)


def _sha256(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()


def preview_library_evidence_assessment(
        current: dict, previous: dict | None = None) -> dict:
    """Turn validated public metadata changes into safe manual review tasks.

    No caller-provided confidence/approval score is trusted. Graph and catalog
    reconstruct allowed source, revision, pattern tags, and change class from
    canonical UCIE metadata. A SHA or signed *claim* is not QA proof.
    Changed items generate review work; unchanged selected revisions generate
    no duplicate notification. Absence from a bounded batch is not deletion.
    """
    graph = preview_library_knowledge_graph(current, previous)
    if (graph.get("schema") !=
            "UCIE_PUBLIC_LIBRARY_KNOWLEDGE_GRAPH_PREVIEW_V1"
            or graph.get("production_approved") is not False
            or graph.get("approved_rules_added") != 0
            or graph.get("persistent_learning_performed") is not False
            or graph.get("cross_project_reads_or_writes") != 0):
        raise DiscoveryError("untrusted or elevated UCIE Library graph")

    references = {}
    tag_map = {}
    for node in graph["nodes"]:
        if node["kind"] == "UNVERIFIED_PUBLIC_RESEARCH_REFERENCE":
            url = node["public_url"]
            source = node["source"]
            skill = node["skill_id"]
            if (url in references or source not in SOURCES
                    or SOURCE_SKILL[source] != skill
                    or skill not in PROFILE
                    or node["source_fix_independently_verified"] is not False
                    or node["release_inclusion_verified"] is not False):
                raise DiscoveryError("unbound or purportedly approved public reference")
            references[url] = node
            tag_map[node["id"]] = []
    for edge in graph["edges"]:
        if edge["relation"] == "BOUNDED_METADATA_TAG_MATCH":
            if edge["from"] not in tag_map or not edge["to"].startswith("tag:"):
                raise DiscoveryError("unbound public classification edge")
            tag_map[edge["from"]].append(edge["to"][4:])

    events = {}
    for event in graph["revision_snapshot"]["change_events"]:
        url = event["public_url"]
        if url in events or url not in references:
            raise DiscoveryError("invalid public revision change event")
        events[url] = event
    if len(events) != len(references) or len(references) > 6:
        raise DiscoveryError("public evidence selection is not bounded")

    cards = []
    review_queue = []
    for url in sorted(references):
        node = references[url]
        event = events[url]
        skill_id = node["skill_id"]
        change = event["classification"]
        if change not in RECHECK | {"UNCHANGED_WITHIN_BATCH_SCOPE"}:
            raise DiscoveryError("unsupported public evidence revision state")
        tags = sorted(tag_map[node["id"]])
        if len(tags) != len(set(tags)):
            raise DiscoveryError("duplicate public metadata classification")

        # This is an evidence coverage classification, not a numerical
        # confidence score or a claim that a fix works in a released version.
        dimensions = {
            "technology_domain": PROFILE[skill_id]["domain"],
            "public_source": node["source"],
            "reference_kind": node["revision_kind"],
            "bounded_error_pattern_tags": tags,
            "revision_change": change,
            "source_identity": "APPROVED_REFERENCE_FORMAT_ONLY",
            "revision_identity": "PINNED_METADATA_NOT_RUNTIME_VERIFIED",
            "evidence_fingerprint": "SHA256_COMPARISON_NOT_ATTESTATION",
            "source_version_applicability": "NOT_ESTABLISHED",
            "source_license": "NOT_INDEPENDENTLY_REVIEWED",
            "security": "NOT_INDEPENDENTLY_REVIEWED",
            "regression": "NOT_REPRODUCED_IN_ISOLATED_RUNNER",
            "independent_qa": "NOT_ESTABLISHED",
            "owner_authorization": "NOT_RECEIVED",
            "confidence_class": "UNVERIFIED_METADATA_ONLY_NO_NUMERIC_SCORE",
        }
        required = [{"gate": name, "state": "NOT_VERIFIED"}
                    for name in GATES]
        fingerprint = _sha256({
            "public_url": url,
            "pinned_revision_sha": node["pinned_revision_sha"],
            "evidence_sha256": node["evidence_fingerprint_sha256"],
            "classification": change,
        })
        card = {
            "review_id_sha256": fingerprint,
            "public_url": url,
            "source": node["source"],
            "skill_id": skill_id,
            "pinned_revision_sha": node["pinned_revision_sha"],
            "evidence_sha256": node["evidence_fingerprint_sha256"],
            "dimensions": dimensions,
            "missing_verification_gates": required,
            "regression_plan": PROFILE[skill_id]["recommended_action"],
            "safe_review_guidance": PROFILE[skill_id]["safe_call"],
            "next_action": (
                "INDEPENDENT_REVISION_AND_EVIDENCE_RECHECK"
                if change in RECHECK else
                "KEEP_PENDING_NO_DUPLICATE_NOTIFICATION"),
            "review_state": "UNVERIFIED_MANUAL_REVIEW_REQUIRED",
            "rule_candidate_auto_created": False,
            "release_or_install_authorized": False,
        }
        cards.append(card)
        if change in RECHECK:
            review_queue.append({
                "review_id_sha256": fingerprint,
                "public_url": url,
                "source": node["source"],
                "skill_id": skill_id,
                "change_classification": change,
                "required_gates": list(GATES),
                "review_action": card["next_action"],
                "regression_plan": card["regression_plan"],
                "status": "PENDING_INDEPENDENT_REVIEW_NO_GO",
                "safe_call_executed": False,
                "rule_candidate_auto_created": False,
                "auto_approved": False,
            })

    unchanged_count = len(cards) - len(review_queue)
    output = {
        "schema": SCHEMA,
        "status": STATUS,
        "approved_public_sources": list(SOURCES),
        "upstream_graph_sha256": graph["graph_sha256"],
        "current_reference_count": len(cards),
        "new_or_changed_review_count": len(review_queue),
        "unchanged_without_duplicate_alert_count": unchanged_count,
        "cards": cards,
        "manual_review_queue": review_queue,
        "previously_selected_not_seen": (
            graph["revision_snapshot"]["previously_selected_not_seen"]),
        "not_seen_means_deleted": False,
        "confidence_scale": "EVIDENCE_GAPS_ONLY_NOT_PROBABILITY",
        "closure_stage": "CLASSIFIED_AND_QUEUED_AWAITING_INDEPENDENT_QA",
        "independent_qa_executed": False,
        "verified_prevention_rules": 0,
        "rules_auto_promoted": 0,
        "signed_rulepacks": 0,
        "installable_skills": [],
        "network_requests": 0,
        "files_or_databases_written": 0,
        "external_or_private_project_reads": 0,
        "persistent_learning_performed": False,
        "scheduler_registered": False,
        "production_approved": False,
    }
    output["assessment_sha256"] = _sha256(output)
    output["assessment_sha256_is_signature"] = False
    return output
