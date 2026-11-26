"""UCIE V2 bounded Virtual Library learning: re-evaluate past hypotheses.

Only first-party SHA-pinned, review-only events. Derives two falsifiable,
narrower *candidate* hypotheses from an explicit failed privacy transfer;
never authenticates upstream revisions, performs tests or promotes rules.
"""
from __future__ import annotations

from hashlib import sha256
import json

from .ucie_v2_library_revision_ledger_v01 import (
    validate_review_history, ReviewHistoryError, STATES, HEX64,
)
from .ucie_v2_revision_impact_v01 import ASSETS, PINS
from .ucie_v2_b3_b4_b5_revision_review_v01 import B5_TESTS
from .ucie_v2_generalization_review_v01 import B4_TEST

SCHEMA = "UCIE_V2_VIRTUAL_LIBRARY_BOUNDED_HYPOTHESIS_IMPROVEMENT_V01"
ALLOWED_TESTS = frozenset(
    {name for asset in ASSETS.values() for name in asset["tests"]} |
    {B4_TEST} | set(B5_TESTS)
)
REJECTED_CLAIM = "ALL_BOUNDED_METADATA_PROCESSES_HIDE_SOURCE_NAMES"
EXPECTED_COUNTEREXAMPLE = "REJECTED_BY_EXPLICIT_DIFFERING_OUTPUT_CONTRACTS"
MAX_HISTORY = 32


class HypothesisImprovementError(ValueError):
    """Fail closed if a historical lifecycle field is untrusted or unsupported."""


def _hash(obj: object) -> str:
    return sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def _strings(value: object, allow: frozenset | None = None) -> bool:
    return (type(value) is list
            and all(type(x) is str and (allow is None or x in allow)
                    for x in value)
            and value == sorted(set(value)))


def _audit_event(event: dict) -> dict:
    bundle = event["bundle"]
    rev = bundle["revision"]
    machine = bundle["machine"]
    counter = machine["counterexample"]
    status = rev.get("review_status")
    if (status not in STATES
            or type(rev.get("candidate_source_authenticated")) is not bool
            or rev["candidate_source_authenticated"] is not False
            or type(rev.get("prior_synthetic_study_complete")) is not bool
            or type(rev.get("prior_synthetic_study_valid_for_candidate")) is not bool
            or not _strings(rev.get("changed_source_ids"), frozenset(PINS))
            or not _strings(rev.get("affected_assets"), frozenset(ASSETS))
            or not _strings(rev.get("proposed_affected_only_tests"), ALLOWED_TESTS)
            or type(rev.get("revision_candidate_signal_sha256")) is not str
            or HEX64.fullmatch(rev["revision_candidate_signal_sha256"]) is None
            or counter.get("claim") != REJECTED_CLAIM
            or counter.get("result") != EXPECTED_COUNTEREXAMPLE
            or machine.get("runtime_execution_enabled") is not False):
        raise HypothesisImprovementError("unsupported hypothesis or revision signal")
    changed = status == "REVIEW_HOLD_CANDIDATE_SOURCE_CHANGE"
    incomplete = status == "REVIEW_HOLD_INCOMPLETE_PAIRED_FIXTURE"
    if changed:
        if (not rev["changed_source_ids"] or not rev["affected_assets"]
                or B4_TEST not in rev["proposed_affected_only_tests"]
                or rev["prior_synthetic_study_valid_for_candidate"]):
            raise HypothesisImprovementError("hidden source-change HOLD")
    elif incomplete:
        if (rev["prior_synthetic_study_complete"]
                or rev["prior_synthetic_study_valid_for_candidate"]
                or rev["affected_assets"] or rev["changed_source_ids"]
                or rev["proposed_affected_only_tests"]):
            raise HypothesisImprovementError("incomplete-pair status drift")
    elif (not rev["prior_synthetic_study_complete"]
          or not rev["prior_synthetic_study_valid_for_candidate"]
          or rev["affected_assets"] or rev["changed_source_ids"]
          or rev["proposed_affected_only_tests"]):
        raise HypothesisImprovementError("unverified ACTIVE status drift")
    return {
        "sequence": event["sequence"],
        "bundle_sha256": bundle["content_sha256"],
        "status": status,
        "changed_source_ids": rev["changed_source_ids"],
        "affected_assets": rev["affected_assets"],
        "proposed_tests": rev["proposed_affected_only_tests"],
        "hypothesis_id": rev["hypothesis_id"],
        "source_change": changed,
        "incomplete": incomplete,
    }


def reassess_library_hypotheses(history: dict) -> dict:
    """Create deterministic candidate queue and non-regression test proposal.

    Historical source-change HOLDs remain active until separately authenticated
    source updates and independently reviewed retests exist. This v01 has no
    input or authority path to clear them.
    """
    valid = validate_review_history(history)
    audits = [_audit_event(entry) for entry in valid["events"]]
    changed = [row for row in audits if row["source_change"]]
    latest = audits[-1] if audits else None
    unresolved = bool(changed)
    incomplete = bool(latest and latest["incomplete"])
    pinned_tests = sorted(set(test for row in changed
                              for test in row["proposed_tests"]))
    changed_sources = sorted(set(sid for row in changed
                                 for sid in row["changed_source_ids"]))
    affected = sorted(set(asset for row in changed for asset in row["affected_assets"]))
    if unresolved:
        lifecycle = "SOURCE_REVISION_HOLD_NOT_CLEARED_BY_SYNTHETIC_REPLAY"
    elif incomplete:
        lifecycle = "INCOMPLETE_LATEST_PAIRED_SYNTHETIC_STUDY_HOLD"
    elif latest:
        lifecycle = "BASELINE_SYNTHETIC_REVIEW_ONLY"
    else:
        lifecycle = "EMPTY_HISTORY_NO_HYPOTHESIS"
    candidates = []
    if latest:
        linked = valid["events"][-1]["bundle"]
        parent = linked["machine"]
        chapter = linked["chapter"]
        for kind, hypothesis, counterfactual, required in (
            (
                "BOUNDED_INPUT_TRANSFER_WITH_SOURCE_SPECIFIC_OUTPUT_GUARDS",
                "명시적 호출자 입력과 처리 상한은 제한적으로 전이할 수 있지만, 출력 정보 공개 범위는 출처별 계약으로 다시 검증해야 한다.",
                "서로 다른 출력 계약에도 모든 기술이 이름을 숨긴다는 주장은 거부한다.",
                ("CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"),
            ),
            (
                "MCP_TARGET_IN_MEMORY_THIRD_TECHNOLOGY_FALSIFICATION",
                "MCP 합성 응답의 제한된 입력·오류 계약만 시험하고 실제 SDK 호환성과 보안 보장을 일반화하지 않는다.",
                "실제 SDK 실행이나 외부 네트워크에서 검증된 것처럼 주장할 수 없다.",
                ("CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"),
            ),
        ):
            definition = {
                "candidate_kind": kind,
                "parent_hypothesis_id": latest["hypothesis_id"],
                "parent_hypothesis_sha256": parent["source_hypothesis_sha256"],
                "parent_bundle_sha256": latest["bundle_sha256"],
                "human_chapter_sha256": chapter["text_sha256"],
                "source_revision_ids": changed_sources,
                "proposed_hypothesis": hypothesis,
                "counterfactual_rejected": counterfactual,
                "synthetic_required_control_statuses": list(required),
            }
            digest = _hash(definition)
            candidates.append({
                **definition,
                "candidate_id": "UCIE-VLIB-REVIEW-" + digest[:20],
                "candidate_sha256": digest,
                "status": ("HOLD_UNRESOLVED_SOURCE_REVISION" if unresolved else
                           "HOLD_INCOMPLETE_SYNTHETIC_PAIR" if incomplete else
                           "READY_FOR_FIRST_PARTY_REVIEW_NOT_APPROVED"),
                "potential_engine_test_names": pinned_tests if unresolved else
                    sorted({B4_TEST} | set(B5_TESTS)),
                "negative_lesson_reused": REJECTED_CLAIM,
                "real_new_principle_discovered_by_model": False,
                "source_revision_independently_authenticated": False,
                "actual_tests_executed": False,
                "independent_qa_verified": False,
                "rights_approved": False,
                "automatic_promotion": False,
                "export_allowed": False,
            })
    payload = {
        "schema": SCHEMA,
        "history_head_sha256": valid["content_sha256"],
        "history_event_hash": valid["latest_hash"],
        "observed_review_events": len(audits),
        "historical_source_change_hold_count": len(changed),
        "review_lifecycle": lifecycle,
        "unresolved_changed_sources": changed_sources,
        "affected_existing_assets": affected,
        "bounded_retest_proposal": pinned_tests,
        "latest_bundle_sha256": latest["bundle_sha256"] if latest else None,
        "reusable_failed_transfer_claim": REJECTED_CLAIM if latest else None,
        "original_falsifiable_candidates": candidates,
        "generated_candidates_count": len(candidates),
        "review_only_not_autonomous_discovery": True,
        "earlier_negative_lessons_preserved": len(audits),
        "source_revision_authenticated": False,
        "real_user_study_completed": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "automatic_experiment_scheduled": False,
        "model_training_performed": False,
        "operating_database_writes": 0,
        "network_requests": 0,
        "customer_release_authorized": False,
    }
    return {**payload, "content_sha256": _hash(payload)}
