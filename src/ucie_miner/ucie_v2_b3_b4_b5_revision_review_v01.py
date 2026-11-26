"""Revision-aware B3/B4/B5 evidence lineage, bounded and non-executing.

A candidate upstream digest is an unauthenticated signal. Even when a
synthetic comparison is complete, it cannot be reused as current evidence
when its parent source, hypothesis, or target capsule may have changed.
"""
from __future__ import annotations

from . import ucie_v2_revision_impact_v01 as b3
from .ucie_v2_b5_b4_evidence_join_v01 import source_linked_synthetic_review
from .ucie_v2_generalization_review_v01 import (
    assess_hypothesis_revision, B4_TEST,
)

SCHEMA = "UCIE_V2_B3_B4_B5_REVISION_SENSITIVE_REVIEW_V01"
B5_TESTS = (
    "test_ucie_v2_b5_comparison_contract_v01.py",
    "test_ucie_v2_b5_paired_controls_v01.py",
    "test_ucie_v2_b5_b4_evidence_join_v01.py",
    "test_ucie_v2_b3_b4_b5_revision_review_v01.py",
)
DEPENDENCIES = frozenset((b3.PY_BOOK, b3.GIT_BOOK, b3.PRINCIPLE,
                           b3.MCP_ASSET, b3.MCP_SKILLBOOK))


class RevisionSensitiveStudyError(ValueError):
    """Fail closed on incompatible source or receipt contracts."""


def review_revision_sensitive_study(records: tuple[dict, ...],
                                    signals: tuple[dict, ...]) -> dict:
    """Link actual source-pinned B4 and paired B5 to B3 affected-only advice.

    Neither candidate source SHA nor synthetic metrics prove actual upstream
    behavior, human usability, rights, QA, or competitive superiority.
    """
    linked = source_linked_synthetic_review(records)
    b4 = assess_hypothesis_revision(signals)
    if (linked.get("status") not in (
                "PAIRED_SYNTHETIC_WITH_PINNED_B4_REVIEW_ONLY",
                "PAIRED_SYNTHETIC_INCOMPLETE_HOLD")
            or type(linked.get("source_lineage")) is not list
            or {row.get("source_id") for row in linked["source_lineage"]
                if type(row) is dict} != {"doc:python/cpython", "doc:git/git"}
            or linked.get("real_competitive_advantage_verified") is not False
            or linked.get("human_study_completed") is not False
            or linked.get("auto_promoted") is not False
            or linked.get("customer_release_authorized") is not False
            or linked.get("network_requests") != 0
            or linked.get("operating_database_writes") != 0
            or b4.get("schema") !=
                    "UCIE_V2_B4_GENERALIZATION_REVIEW_AND_REVISION_V01"
            or b4.get("hypothesis_id") != linked.get("hypothesis_id")
            or b4.get("previous_hypothesis_sha256") !=
                    linked.get("hypothesis_content_sha256")
            or b4.get("source_revision_authenticated") is not False
            or b4.get("source_or_test_auto_executed") is not False
            or b4.get("retest_auto_scheduled") is not False
            or b4.get("auto_promoted") is not False
            or b4.get("network_requests") != 0
            or b4.get("operating_database_writes") != 0):
        raise RevisionSensitiveStudyError("revision, lineage or authority drift")

    impacted = set(b4.get("affected_assets", ()))
    if not impacted.issubset(DEPENDENCIES):
        raise RevisionSensitiveStudyError("unbounded affected asset")
    changed = b4.get("changed_candidate_source_ids")
    if (type(changed) is not list
            or not set(changed).issubset(b3.PINS)
            or type(b4.get("bounded_proposed_test_files")) is not list):
        raise RevisionSensitiveStudyError("unbounded change signals")
    needs_retest = bool(impacted)
    complete = linked["status"] == "PAIRED_SYNTHETIC_WITH_PINNED_B4_REVIEW_ONLY"
    proposed = set(b4["bounded_proposed_test_files"])
    if needs_retest:
        if not b4.get("b4_hypothesis_impacted") or B4_TEST not in proposed:
            raise RevisionSensitiveStudyError("affected hypothesis hidden")
        proposed.update(B5_TESTS)
    elif b4.get("b4_hypothesis_impacted"):
        raise RevisionSensitiveStudyError("unexpected affected hypothesis")
    status = ("SOURCE_CHANGE_CANDIDATE_HOLD_PAIRED_STUDY_STALE"
              if needs_retest else
              "SYNTHETIC_PAIR_INCOMPLETE_HOLD"
              if not complete else
              "UNCHANGED_PINNED_SYNTHETIC_REVIEW_ONLY")
    return {
        "schema": SCHEMA,
        "status": status,
        "study_case_id": linked["case_id"],
        "hypothesis_id": linked["hypothesis_id"],
        "previous_hypothesis_sha256": linked["hypothesis_content_sha256"],
        "candidate_hypothesis_sha256": "NOT_COMPUTED",
        "target_capsule_id": linked["target_capsule_id"],
        "previous_source_lineage": linked["source_lineage"],
        "candidate_changed_source_ids": changed,
        "impacted_existing_assets": sorted(impacted),
        "proposed_affected_only_test_files": sorted(proposed),
        "original_b5_synthetic_study_complete": complete,
        "b5_synthetic_evidence_current_for_candidate": complete and not needs_retest,
        "candidate_source_sha_authenticated": False,
        "candidate_b4_generalization_verified": False,
        "real_human_observations": 0,
        "real_competitive_advantage_verified": False,
        "independent_qa_verified": False,
        "owner_host_accepted": False,
        "automatic_scheduling": False,
        "auto_promoted": False,
        "customer_release_authorized": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
