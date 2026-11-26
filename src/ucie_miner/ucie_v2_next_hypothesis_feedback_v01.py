"""UCIE V2 Virtual Library: actually feed prior revision lessons into next drafts.

A bounded first-party learning-feedback step, not a model update, upstream
finding, customer fix, or production SkillBook mutation. The *next* draft
depends on the latest validated revision history, not only the original B4
template. Earlier rejected options and unresolved source-HOLD constraints
are retained as explicit review guards.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ucie_v2_hypothesis_reassessment_v01 import (
    reassess_library_hypotheses, REJECTED_CLAIM, ALLOWED_TESTS,
)
from .ucie_v2_revision_review_history_v01 import validate_revision_history
from .ucie_v2_library_revision_ledger_v01 import validate_review_history

SCHEMA = "UCIE_V2_REVISION_INFORMED_NEXT_HYPOTHESES_V01"
MAX_HISTORY_EVENTS = 32
MAX_NEXT_CANDIDATES = 2
OPTIONS = frozenset(("HOLD", "REVISE_DRAFT",
                     "RETAIN_REVIEW_ONLY", "REJECT_SYNTHETIC_CHALLENGER"))

GUARDS = {
    "HOLD": "이전 불충분한 근거 또는 출처 변경 보류를 해제하지 말 것",
    "REVISE_DRAFT": "합성시험 관측값만으로 실제 효과·권리·배포를 승인하지 말 것",
    "RETAIN_REVIEW_ONLY": "새로운 독립 근거 없이 기존 가설을 승격하지 말 것",
    "REJECT_SYNTHETIC_CHALLENGER": "회귀가 확인된 변경안의 동일 재도입을 차단할 것",
}
NEXT_TEST = {
    "HOLD": "PIN_AND_EVIDENCE_REVIEW_BEFORE_SYNTHETIC_RETEST",
    "REVISE_DRAFT": "COUNTEREXAMPLE_GUARDED_SAME_CASE_RETEST",
    "RETAIN_REVIEW_ONLY": "NEW_INDEPENDENT_EVIDENCE_REQUIRED",
    "REJECT_SYNTHETIC_CHALLENGER": "REJECTED_CHANGE_REGRESSION_REPRODUCTION",
}


class NextHypothesisError(ValueError):
    """Reject out-of-lineage or fake-success revision learning."""


def _digest(obj: object) -> str:
    return sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def next_hypotheses_from_revisions(history: dict, reviews: dict) -> dict:
    """Source -> current original candidates -> revision history -> next drafts.

    Never silently overwrite prior hypotheses. All derived candidates are
    bounded review objects with explicit parent SHAs and next test purpose.
    """
    pinned = validate_review_history(history)
    ledger = validate_revision_history(pinned, reviews)
    base = reassess_library_hypotheses(pinned)
    existing = base["original_falsifiable_candidates"]
    if (len(existing) > MAX_NEXT_CANDIDATES
            or ledger["count"] > MAX_HISTORY_EVENTS):
        raise NextHypothesisError("unbounded review history or candidates")
    by_id = {x["candidate_id"]: x for x in existing}
    source_hold = bool(base["unresolved_changed_sources"])
    latest = {}
    all_rejected = set()
    all_holds = set()
    for event in ledger["events"]:
        report = event["report"]
        if report["history_head_sha256"] != pinned["content_sha256"]:
            raise NextHypothesisError("mixed library source")
        drafts = report["revision_drafts"]
        if {d["candidate_id"] for d in drafts} != set(by_id):
            raise NextHypothesisError("missing or foreign revision arm")
        for d in drafts:
            original = by_id[d["candidate_id"]]
            if (d["parent_candidate_sha256"] != original["candidate_sha256"]
                    or d["parent_hypothesis_id"] != original["parent_hypothesis_id"]
                    or d["revision_hypothesis_text"] != original["proposed_hypothesis"]
                    or d["counterexample_preserved"] != REJECTED_CLAIM
                    or type(d["proposed_test_names"]) is not list
                    or not set(d["proposed_test_names"]).issubset(ALLOWED_TESTS)
                    or d["review_option"] not in OPTIONS
                    or (source_hold and d["review_option"] != "HOLD")
                    or (d["review_option"] == "HOLD"
                        and d["observed_synthetic_gain"]
                        and not d["source_hold_not_cleared"])
                    or (d["review_option"] == "REVISE_DRAFT"
                        and not d["observed_synthetic_gain"])
                    or (d["review_option"] == "REJECT_SYNTHETIC_CHALLENGER"
                        and d["observed_synthetic_nonworsening"])):
                raise NextHypothesisError("revision attempt violates original contracts")
            cid = d["candidate_id"]
            latest[cid] = (event["sequence"], d)
            if d["review_option"] == "REJECT_SYNTHETIC_CHALLENGER":
                all_rejected.add(cid)
            if d["review_option"] == "HOLD":
                all_holds.add(cid)
    candidates = []
    for original in existing:
        cid = original["candidate_id"]
        info = latest.get(cid)
        last = info[1] if info else None
        option = last["review_option"] if last else "HOLD"
        if source_hold:
            status = "HOLD_UNRESOLVED_SOURCE_REVISION"
        elif original["status"] == "HOLD_INCOMPLETE_SYNTHETIC_PAIR":
            status = "HOLD_INCOMPLETE_SYNTHETIC_EVIDENCE"
        elif not last:
            status = "HOLD_NO_REVISION_RETEST_EVIDENCE"
        elif option == "REJECT_SYNTHETIC_CHALLENGER":
            status = "REJECT_LATEST_CHALLENGER_REVIEW_ONLY"
        elif option == "HOLD":
            status = "HOLD_PRIOR_RETEST"
        elif option == "REVISE_DRAFT":
            status = "NEXT_REVISION_DRAFT_REQUIRES_INDEPENDENT_REVIEW"
        else:
            status = "RETAIN_DRAFT_AWAIT_INDEPENDENT_EVIDENCE"
        rejected_before = cid in all_rejected
        constraints = [
            REJECTED_CLAIM,
            GUARDS[option],
            "승인된 두 원본 출처의 서로 다른 출력 계약을 보존할 것",
        ]
        if rejected_before:
            constraints.append("과거 기각된 개선안을 새로운 근거 없이 다시 승인하지 말 것")
        if source_hold:
            constraints.append("미인증 출처 변경을 합성시험만으로 해결했다고 표시하지 말 것")
        revision_note = {
            "REVISE_DRAFT": "관측된 합성 회귀 감소를 확인하되 범용 적용은 보류한다.",
            "RETAIN_REVIEW_ONLY": "기존 가설의 제한적 적용 범위를 유지한다.",
            "REJECT_SYNTHETIC_CHALLENGER": "최신 개선 후보를 배제하고 실패 반례를 재현한다.",
            "HOLD": "근거 보완 전에는 새 효과를 주장하지 않는다.",
        }[option]
        proposal = {
            "candidate_id": cid,
            "source_candidate_sha256": original["candidate_sha256"],
            "source_hypothesis_id": original["parent_hypothesis_id"],
            "source_library_history_sha256": pinned["content_sha256"],
            "revision_history_sha256": ledger["content_sha256"],
            "last_revision_sha256": last["revision_sha256"] if last else None,
            "revision_iteration": info[0] if info else 0,
            "next_hypothesis_text": original["proposed_hypothesis"] + " " + revision_note,
            "next_review_status": status,
            "next_test_kind": NEXT_TEST[option],
            "test_names_review_only": (list(last["proposed_test_names"]) if last
                                       else list(original["potential_engine_test_names"])),
            "reusable_negative_constraints": constraints,
            "earlier_rejected_challenger_seen": rejected_before,
            "earlier_hold_seen": cid in all_holds,
            "source_change_hold_active": source_hold,
        }
        candidates.append({
            **proposal,
            "next_draft_id": "UCIE-V2-NEXT-" + _digest(proposal)[:24],
            "next_draft_sha256": _digest(proposal),
            "actual_external_test_pass": False,
            "independently_verified": False,
            "signed_rule_applied": False,
            "owner_approved": False,
            "customer_release_authorized": False,
        })
    result = {
        "schema": SCHEMA,
        "source_library_history_sha256": pinned["content_sha256"],
        "revision_history_sha256": ledger["content_sha256"],
        "originated_revision_events": ledger["count"],
        "next_candidate_count": len(candidates),
        "next_candidates": candidates,
        "feedback_from_previous_revision_consumed": ledger["count"] > 0,
        "prior_negatives_still_binding": True,
        "technical_source_authenticated": False,
        "independent_qa_verified": False,
        "automatic_model_training": False,
        "automatic_rule_promotion": False,
        "operating_database_writes": 0,
        "network_requests": 0,
    }
    return {**result, "content_sha256": _digest(result)}
