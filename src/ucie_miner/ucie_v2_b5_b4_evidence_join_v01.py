"""B5 paired comparison joined to original B4 cross-source proof and controls.

No real-user, customer, external source or independently certified result.
"""
from __future__ import annotations
import re
from .ucie_v2_b5_paired_controls_v01 import assess_synthetic_pairs
from .ucie_v2_b5_comparison_contract_v01 import CASE_ID, SCHEMA as B5_SCHEMA
from .ucie_v2_generalization_transfer_v01 import (
    FACETS, SCHEMA as B4_SCHEMA, build_hypothesis, run_bounded_transfer,
)

SCHEMA = "UCIE_V2_B5_B4_SOURCE_LINKED_SYNTHETIC_REVIEW_V01"
SOURCES = frozenset(("doc:python/cpython", "doc:git/git"))
CONTROLS = ["CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"]
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class B5SourceJoinError(ValueError):
    """Fail closed if B4 lineage, synthetic controls, or approval claims drift."""


def source_linked_synthetic_review(records: tuple[dict, ...]) -> dict:
    paired = assess_synthetic_pairs(records)  # authoritative original B5 row validation
    h = build_hypothesis()                      # original B4, not caller-provided facts
    t = run_bounded_transfer(h)                 # UCIE authored bounded synthetic controls
    parents = h.get("parents")
    if (h.get("schema") != B4_SCHEMA
            or type(parents) is not list or len(parents) != 2
            or any(type(p) is not dict for p in parents)
            or {p.get("source_id") for p in parents} != SOURCES
            or type(h.get("content_sha256")) is not str
            or HEX64.fullmatch(h["content_sha256"]) is None
            or not str(h.get("hypothesis_id", "")).startswith("UCIE-B4-HYP-")
            or h.get("shared_candidate_facets") != sorted(FACETS)
            or any(type(p.get("document_sha256")) is not str
                   or HEX64.fullmatch(p["document_sha256"]) is None
                   or p.get("independent_qa") is not False
                   or p.get("rights_approved") is not False for p in parents)
            or "MCP-PROMPTS" not in str(h.get("target_capsule_id", ""))
            or h.get("cross_source_model_generalization_verified") is not False
            or h.get("export_allowed") is not False
            or h.get("auto_promoted") is not False
            or h.get("model_trained") is not False
            or t.get("schema") != B4_SCHEMA
            or t.get("hypothesis_id") != h.get("hypothesis_id")
            or t.get("content_sha256") != h.get("content_sha256")
            or t.get("positive_negative_control") != CONTROLS
            or t.get("overbroad_output_privacy_claim_rejected") is not True
            or t.get("real_upstream_sdk_rerun") is not False
            or t.get("independent_qa_verified") is not False
            or t.get("candidate_automatically_approved") is not False
            or t.get("export_allowed") is not False
            or t.get("network_requests") != 0
            or t.get("operating_database_writes") != 0):
        raise B5SourceJoinError("B4 source, bounded controls, or approval drift")
    if paired["synthetic_summary"].get("schema") != B5_SCHEMA:
        raise B5SourceJoinError("B5 comparison contract drift")
    return {
        "schema": SCHEMA,
        "status": ("PAIRED_SYNTHETIC_WITH_PINNED_B4_REVIEW_ONLY"
                   if paired["status"] == "SYNTHETIC_PAIRED_CONTROL_CONTRACT_ONLY"
                   else "PAIRED_SYNTHETIC_INCOMPLETE_HOLD"),
        "case_id": CASE_ID,
        "hypothesis_id": h["hypothesis_id"],
        "hypothesis_content_sha256": h["content_sha256"],
        "target_capsule_id": h["target_capsule_id"],
        "source_lineage": sorted([{
            "source_id": p["source_id"], "skillbook_id": p["skillbook_id"],
            "document_sha256": p["document_sha256"],
        } for p in parents], key=lambda row: row["source_id"]),
        "bounded_b4_control_statuses": CONTROLS[:],
        "nontransferable_privacy_claim_rejected": True,
        "paired_synthetic_summary": paired,
        "human_study_completed": False,
        "real_upstream_sdk_rerun": False,
        "independent_qa_verified": False,
        "real_competitive_advantage_verified": False,
        "license_export_approved": False,
        "owner_host_accepted": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
