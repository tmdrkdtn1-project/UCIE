"""UCIE Stage 9.7: discover -> dedupe -> enrich -> skill-knowledge review.

First-party coordinator for *explicit* one-shot, public-only, bounded reads.
No operating DB write, source checkout, code execution, timer registration,
weight learning, Rulepack signing or deployment. Upstream data is untrusted.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .public_discovery import (SOURCES, DiscoveryError, discover_all_feeds,
                               public_feed_get)
from .public_evidence_routes import fetch_public_evidence
from .public_intelligence import (public_intelligence_preview,
                                  read_prior_miner_ids)
from .public_knowledge_pipeline import (collect_public_knowledge_candidate,
                                        preview_public_knowledge_receipt)

SHA40 = re.compile(r"[0-9a-f]{40}")
MAX_ENRICH = 3


def _fingerprint(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=True, allow_nan=False,
        separators=(",", ":")
    ).encode("ascii")).hexdigest()


def _key_list(value, *, kind):
    if not isinstance(value, (list, tuple)) or len(value) > 1000:
        raise DiscoveryError("invalid bounded " + kind)
    distinct = set()
    for entry in value:
        if (not isinstance(entry, (list, tuple)) or len(entry) != 2
                or entry[0] not in SOURCES or type(entry[1]) is not int
                or not 1 <= entry[1] <= 999999999):
            raise DiscoveryError("invalid public PR pair")
        if tuple(entry) in distinct:
            raise DiscoveryError("duplicate public PR " + kind)
        distinct.add(tuple(entry))
    return distinct


def build_public_batch(*, metadata_fetch=public_feed_get,
                       evidence_fetch=fetch_public_evidence,
                       sources=SOURCES, root: Path | None = None,
                       opted_out_sources=(), opted_out_prs=(),
                       already_reviewed_prs=(),
                       review_feedback=None, max_enrich=2,
                       include_docs=True, include_advisories=True,
                       now=None, backfill_pages=1):
    """On-demand public research; at most 15 + 4*3 external GETs.

    Metadata and evidence fetch callbacks are explicitly injected for CI.
    No persistent state is modified, even on partial upstream API failure.
    Duplicates are tested against the read-only *operating* UCIE miner DB
    when a trusted UCIE project root is explicitly provided.
    """
    if (not isinstance(sources, (list, tuple)) or not sources
            or len(sources) > len(SOURCES) or len(set(sources)) != len(sources)
            or any(source not in SOURCES for source in sources)
            or not isinstance(opted_out_sources, (tuple, list))
            or len(set(opted_out_sources)) != len(opted_out_sources)
            or any(source not in SOURCES for source in opted_out_sources)
            or type(max_enrich) is not int or not 1 <= max_enrich <= MAX_ENRICH
            or type(backfill_pages) is not int
            or not 1 <= backfill_pages <= 3
            or type(include_docs) is not bool
            or type(include_advisories) is not bool):
        raise DiscoveryError("unsupported one-shot batch configuration")
    opts = set(opted_out_sources)
    denied = _key_list(opted_out_prs, kind="opt-outs")
    reviewed = _key_list(already_reviewed_prs, kind="review history")
    requested = tuple(source for source in sources if source not in opts)
    if not requested:
        raise DiscoveryError("no approved sources remain after opt-out")
    prior = set(read_prior_miner_ids(root)) if root is not None else set()
    seen = prior | reviewed
    # Opted-out upstreams MUST NOT be requested, including docs or advisories.
    feeds = discover_all_feeds(fetch=metadata_fetch,
                               sources=requested, now=now,
                               backfill_pages=backfill_pages)
    intelligence = public_intelligence_preview(
        feeds, seen_public_prs=tuple(sorted(seen)),
        opted_out_sources=tuple(sorted(opts)),
        opted_out_prs=tuple(sorted(denied)),
        review_feedback=review_feedback, limit=12,
    )
    # Never trust a ranking alone: bind every selected source/pr identity to
    # a declared public merged commit SHA from the actual feed receipt.
    leads = {}
    for feed in feeds["feeds"]:
        for lead in feed["leads"]:
            key = (lead["source"], lead["pr_number"])
            if key in leads:
                raise DiscoveryError("duplicate cross-feed public identity")
            leads[key] = lead
    selected, skipped, evidence_calls_budget = [], [], 0
    for choice in intelligence["priority"]["novel_review_queue"]:
        if len(selected) >= max_enrich:
            break
        key = (choice["source"], choice["pr_number"])
        raw = leads.get(key)
        if raw is None or key in seen or key in denied or key[0] in opts:
            raise DiscoveryError("ranked choice diverges from public feed")
        if (raw["public_url"] != choice["public_url"]
                or raw["skill_id"] != choice["skill_id"]):
            raise DiscoveryError("ranked candidate identity changed")
        sha = raw.get("merge_commit_sha")
        if not isinstance(sha, str) or not SHA40.fullmatch(sha):
            skipped.append({
                "source": key[0], "pr_number": key[1],
                "status": "UNPINNED_MERGE_SHA_NOT_ENRICHED",
            })
            continue
        receipt = collect_public_knowledge_candidate(
            key[0], key[1], merge_sha=sha,
            fetch=evidence_fetch, include_doc=include_docs,
            include_advisory=include_advisories,
        )
        if (receipt["source"] != key[0]
                or receipt["pr_number"] != key[1]
                or receipt["skill_knowledge_candidate"]["skill_id"] !=
                    choice["skill_id"]
                or receipt["skill_knowledge_candidate"][
                    "pinned_merge_commit_sha"] != sha):
            raise DiscoveryError("public enrichment/skill identity mismatch")
        manual = preview_public_knowledge_receipt(receipt)
        selected.append({
            "source": key[0],
            "pr_number": key[1],
            "public_url": raw["public_url"],
            "skill_id": choice["skill_id"],
            "public_priority_score": choice["priority_score"],
            "evidence_status": receipt["status"],
            "missing_evidence_types": receipt["missing_evidence_types"],
            "evidence_sha256": receipt["candidate_evidence_sha256"],
            "error_pattern_tags": list(receipt["skill_knowledge_candidate"]["error_pattern_tags"]),
            "safe_call_guidance": receipt["skill_knowledge_candidate"]["safe_call_guidance"],
            "pinned_merge_commit_sha": sha,
            "test_file_count": (receipt["patch_features"] or {}).get("test_file_count"),
            "patch_signal_status": (receipt["patch_features"] or {}).get("behavioral_transition", "NOT_COLLECTED"),
            "knowledge_review_status": manual["status"],
            "review_plan": receipt["skill_knowledge_candidate"]["regression_plan"],
            "regression_independently_verified": False,
            "skill_installed": False,
            "human_approval_received": False,
        })
        evidence_calls_budget += receipt["public_reads_max"]
    scheduled_reads_limit = len(requested) * backfill_pages + max_enrich * (2
        + int(include_docs) + int(include_advisories))
    # Receipt hashes are dedupe hints; not signatures or proof of upstream fix.
    return {
        "schema": "UCIE_PUBLIC_RESEARCH_BATCH_PREVIEW_V1",
        "status": "READ_ONLY_RESEARCH_CANDIDATES_NO_GO",
        "sources_requested": list(sources),
        "sources_fetched": list(requested),
        "source_optouts_prevented_network": sorted(opts),
        "existing_miner_duplicates_skipped": len(prior),
        "explicit_review_history_count": len(reviewed),
        "explicit_pr_optout_count": len(denied),
        "public_metadata_candidate_count": feeds["candidate_leads_total"],
        "enrichment_target_limit": max_enrich,
        "enriched_count": len(selected),
        "unproven_merge_skips": skipped,
        "candidate_skill_queue": selected,
        "candidate_queue_sha256": _fingerprint(selected),
        "metadata_gets_budget": feeds["public_reads_max"],
        "metadata_gets_upper_bound": len(requested) * backfill_pages,
        "backfill_pages_limit": backfill_pages,
        "enrichment_gets_budget": evidence_calls_budget,
        "overall_gets_upper_bound": scheduled_reads_limit,
        "source_data_and_patch_code_retained": False,
        "real_upstream_fix_independently_verified": False,
        "independent_reviewer_signoff_received": False,
        "model_weights_updated": False,
        "operating_database_writes": 0,
        "new_scheduler_registered": False,
        "knowledge_rules_auto_promoted": 0,
        "rulepack_signed": False,
        "production_approved": False,
    }


def review_batch_preview(receipt):
    """Strictly bounded read-only diagnostic of a submitted batch receipt."""
    if (not isinstance(receipt, dict)
            or receipt.get("schema") != "UCIE_PUBLIC_RESEARCH_BATCH_PREVIEW_V1"
            or receipt.get("status") != "READ_ONLY_RESEARCH_CANDIDATES_NO_GO"
            or receipt.get("production_approved") is not False
            or receipt.get("model_weights_updated") is not False
            or receipt.get("rulepack_signed") is not False
            or receipt.get("new_scheduler_registered") is not False
            or receipt.get("knowledge_rules_auto_promoted") != 0
            or receipt.get("operating_database_writes") != 0
            or receipt.get("real_upstream_fix_independently_verified") is not False
            or receipt.get("independent_reviewer_signoff_received") is not False
            or receipt.get("source_data_and_patch_code_retained") is not False
            or not isinstance(receipt.get("candidate_skill_queue"), list)
            or len(receipt["candidate_skill_queue"]) > MAX_ENRICH
            or receipt.get("enriched_count") != len(receipt["candidate_skill_queue"])
            or receipt.get("candidate_queue_sha256") !=
               _fingerprint(receipt["candidate_skill_queue"])):
        raise DiscoveryError("untrusted or forged research batch receipt")
    findings = []
    for item in receipt["candidate_skill_queue"]:
        if (not isinstance(item, dict)
                or item.get("source") not in SOURCES
                or type(item.get("pr_number")) is not int
                or item.get("public_url") !=
                    f"https://github.com/{item['source']}/pull/{item['pr_number']}"
                or item.get("evidence_status") not in (
                    "INCOMPLETE_PUBLIC_EVIDENCE",
                    "UNVERIFIED_PUBLIC_KNOWLEDGE_CANDIDATE")
                or item.get("human_approval_received") is not False
                or item.get("regression_independently_verified") is not False
                or item.get("skill_installed") is not False
                or item.get("knowledge_review_status") != "MANUAL_REVIEW_ONLY_NO_GO"):
            raise DiscoveryError("forged skill approval inside batch")
        findings.append({
            "public_pr": item["public_url"],
            "skill_id": item["skill_id"],
            "missing_public_evidence": item["missing_evidence_types"],
            "required_review": "INDEPENDENT_SOURCE_VERSION_LICENSE_AND_TESTS",
            "rule_status": "NO_GO",
        })
    return {
        "schema": "UCIE_PUBLIC_RESEARCH_BATCH_REVIEW_V1",
        "status": "MANUAL_CANDIDATE_REVIEW_PENDING",
        "candidate_count": len(findings),
        "review_tasks": findings,
        "no_silent_knowledge_import": True,
        "operational_go": False,
        "production_approved": False,
    }
