"""UCIE V2 original Virtual Library integrated iterative review learning.

One bounded, deterministic transaction in memory:
pinned original evidence -> revision history -> paired synthetic retest ->
append-only review -> newly constrained hypothesis -> original SkillBook addendum.
No dynamic upstream execution, operational writes, model training, approvals or
automatic replacement of a signed/owner-approved original.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ucie_v2_library_revision_ledger_v01 import validate_review_history
from .ucie_v2_feedback_registry_v01 import validate_feedback_registry
from .ucie_v2_revision_review_history_v01 import (
    validate_revision_history, append_revision_review, review_revision_lessons,
)
from .ucie_v2_hypothesis_revision_retest_v01 import revise_and_retest_hypotheses
from .ucie_v2_next_hypothesis_feedback_v01 import next_hypotheses_from_revisions
from .ucie_v2_hypothesis_reassessment_v01 import REJECTED_CLAIM, ALLOWED_TESTS

SCHEMA = "UCIE_V2_INTEGRATED_ITERATIVE_LIBRARY_LEARNING_V01"
MAX_CANDIDATES = 2


class IterativeLearningError(ValueError):
    """A review-only synthetic change cannot bypass original source contracts."""


def _digest(data: object) -> str:
    return sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def advance_virtual_library_review_cycle(
    source_history: dict,
    feedback_registry: dict,
    revision_history: dict,
    before_fixtures: dict,
    after_fixtures: dict,
    *,
    fixture_sha256: str,
    expected_revision_head_sha256: str,
) -> dict:
    """Compose a single all-or-nothing first-party review iteration.

    Fixtures are caller-supplied synthetic observations, NOT executions of
    generated code. Compare only identical case IDs/truth/baseline/source.
    If the exact review report already exists, do not create a duplicate
    event or imply new evidence.
    """
    pinned = validate_review_history(source_history)
    validate_feedback_registry(pinned, feedback_registry)
    prior = validate_revision_history(pinned, revision_history)
    if (type(expected_revision_head_sha256) is not str
            or expected_revision_head_sha256 != prior["content_sha256"]):
        raise IterativeLearningError("stale or unpinned revision head")
    previous = next_hypotheses_from_revisions(pinned, prior)
    if previous["revision_history_sha256"] != prior["content_sha256"]:
        raise IterativeLearningError("previous draft lineage mismatch")
    proposed = revise_and_retest_hypotheses(
        pinned, feedback_registry, before_fixtures, after_fixtures,
        fixture_sha256=fixture_sha256,
    )
    if (proposed["history_head_sha256"] != pinned["content_sha256"]
            or proposed["registry_sha256"] != feedback_registry["content_sha256"]
            or proposed["customer_release_authorized"] is not False
            or proposed["automatic_rule_promotion"] is not False
            or proposed["independent_qa_verified"] is not False):
        raise IterativeLearningError("revision source or permission drift")
    updated = append_revision_review(pinned, prior, proposed)
    next_drafts = next_hypotheses_from_revisions(pinned, updated)
    lessons = review_revision_lessons(pinned, updated)
    was_new = updated["count"] == prior["count"] + 1
    if updated["count"] not in (prior["count"], prior["count"] + 1):
        raise IterativeLearningError("unexpected append operation")
    source_candidates = {
        c["candidate_id"]: c for c in previous["next_candidates"]
    }
    next_candidates = {
        c["candidate_id"]: c for c in next_drafts["next_candidates"]
    }
    if (len(source_candidates) != len(next_candidates)
            or len(next_candidates) > MAX_CANDIDATES
            or set(source_candidates) != set(next_candidates)
            or len(proposed["revision_drafts"]) != len(next_candidates)):
        raise IterativeLearningError("candidate count or lineage changed")
    addenda = []
    for draft in proposed["revision_drafts"]:
        cid = draft["candidate_id"]
        updated_candidate = next_candidates[cid]
        old_candidate = source_candidates[cid]
        if (updated_candidate["source_candidate_sha256"]
                != old_candidate["source_candidate_sha256"]
                or updated_candidate["source_change_hold_active"]
                   != old_candidate["source_change_hold_active"]
                or updated_candidate["last_revision_sha256"]
                   != draft["revision_sha256"] and was_new):
            raise IterativeLearningError("revised candidate lost provenance")
        if (type(updated_candidate["test_names_review_only"]) is not list
                or not set(updated_candidate["test_names_review_only"])
                           .issubset(ALLOWED_TESTS)
                or REJECTED_CLAIM not in updated_candidate[
                    "reusable_negative_constraints"]):
            raise IterativeLearningError("missing negative source contract")
        text = (
            "UCIE 가상도서관 원본 SkillBook 개정 검토 초안\n"
            f"원본 후보: {cid}\n"
            f"이전 버전: {old_candidate['next_draft_sha256']}\n"
            f"다음 버전: {updated_candidate['next_draft_sha256']}\n"
            f"검토 판정: {draft['review_option']}\n"
            f"재시험 방향: {updated_candidate['next_test_kind']}\n"
            f"개정 가설: {updated_candidate['next_hypothesis_text']}\n"
            "반례 유지: 모든 제한형 메타데이터가 이름을 숨긴다는 일반화는 기각\n"
            "출처 SHA 독립 확인 및 권리/실사용자 QA 전 운영·배포 불가"
        )
        addenda.append({
            "candidate_id": cid,
            "original_candidate_sha256": old_candidate[
                "source_candidate_sha256"],
            "previous_next_draft_sha256": old_candidate["next_draft_sha256"],
            "new_next_draft_sha256": updated_candidate["next_draft_sha256"],
            "previous_source_revision_hold_preserved": updated_candidate[
                "source_change_hold_active"],
            "review_status": updated_candidate["next_review_status"],
            "proposed_test_names": updated_candidate["test_names_review_only"],
            "original_human_skillbook_addendum": text,
            "addendum_sha256": sha256(text.encode("utf-8")).hexdigest(),
            "signed_skillbook_modified": False,
            "rule_or_engine_adopted": False,
            "independent_qa_verified": False,
        })
    addenda.sort(key=lambda a: a["candidate_id"])
    payload = {
        "schema": SCHEMA,
        "original_source_history_sha256": pinned["content_sha256"],
        "original_feedback_registry_sha256": feedback_registry["content_sha256"],
        "previous_revision_history_sha256": prior["content_sha256"],
        "revision_report_sha256": proposed["content_sha256"],
        "next_revision_history": updated,
        "next_revision_history_sha256": updated["content_sha256"],
        "new_revision_event_appended": was_new,
        "replayed_existing_observation": not was_new,
        "previous_next_draft_sha256": previous["content_sha256"],
        "next_generation_draft": next_drafts,
        "next_generation_sha256": next_drafts["content_sha256"],
        "preserved_negative_lessons": lessons["lessons_count"],
        "original_skillbook_addenda": addenda,
        "source_history_mutated": False,
        "feedback_registry_mutated": False,
        "signed_original_skillbook_modified": False,
        "real_sdk_executed": False,
        "real_customer_benefit_verified": False,
        "rights_approved": False,
        "independent_qa_verified": False,
        "model_training_performed": False,
        "automatic_rule_promotion": False,
        "customer_release_authorized": False,
        "jobs_scheduled": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**payload, "content_sha256": _digest(payload)}
