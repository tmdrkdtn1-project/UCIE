"""B4 executable first-party falsification and review-only asset revision.

Runs UCIE-authored benign exact-version matching trials. No external SDK,
public source code, host project file or native PowerShell command is run.
A synthetic improvement may justify a DRAFT, never release or source claims.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re

from .local_v1_priority_v01 import require_local_work
from .ucie_v2_b4_typed_mechanism_annotation_v01 import (
    ORIGIN, compare_draft_annotations,
)
from .ucie_v2_b4_w02_evidence_intake_gate_v01 import triage_w02_evidence

SCHEMA = "UCIE_V2_B4_EXECUTABLE_FALSIFICATION_REVISION_V01"
LEDGER_SCHEMA = "UCIE_V2_B4_FALSIFICATION_CHAIN_V01"
MAX_CASES = 24
MAX_EVENTS = 16
VERSION_RE = re.compile(r"[0-9]+(?:\.[0-9]+){1,3}\Z")
TRIAL_ORIGIN = "UCIE_FIRST_PARTY_BENIGN_VERSION_FIXTURE"
CLAIM = "VERSION_PINNED_TRIAL"


class FalsificationError(ValueError):
    """Forbid any unsupported source proof or synthetic-to-release escalation."""


def _hash(data: object) -> str:
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False)
                  .encode("utf-8")).hexdigest()


def _source_candidates() -> list[dict]:
    # Metadata-only W02 candidate fixtures. These digests are *not*
    # independent authentication of upstream revisions or rights.
    return [
        {
            "kind": "TEST_RECIPE", "source_id": "repo:PowerShell/PowerShell",
            "evidence_reference":
                "pr:28087:373f6a7b7972a0a4b73bfd9737a0d768d28b347e",
            "evidence_sha256":
                "bfb46af89433268872ddb43d1ca7a3f433452ee91ed356a9786940f90118e285",
            "purpose_code": "PINNED_VERSION_EXPERIMENT",
            "version_scope": "7.6.6", "dependencies": [],
        },
        {
            "kind": "TEST_RECIPE", "source_id": "repo:python/cpython",
            "evidence_reference":
                "pr:153462:999a046b24cff4ba0e72b574196721f66bd08237",
            # Explicit synthetic placeholder, never described as verified.
            "evidence_sha256": "a" * 64,
            "purpose_code": "PINNED_VERSION_EXPERIMENT",
            "version_scope": "3.15.0", "dependencies": [],
        },
    ]


def _draft_annotations(records: list[dict]) -> list[dict]:
    queue = triage_w02_evidence(records)["review_queue"]
    return [
        {
            "library_item_id": row["library_item_id"],
            "evidence_sha256": row["evidence_sha256"],
            "mechanisms": [CLAIM],
            "preconditions": ["EXACT_VERSION_REQUIRED",
                              "POSITIVE_NEGATIVE_CONTROL_REQUIRED"],
            "counterexamples":
                ["HISTORICAL_TRIAL_NOT_CURRENT_COMPATIBILITY"],
            "origin": ORIGIN, "status": "REVIEW_ONLY_UNVERIFIED",
        }
        for row in queue
    ]


def _trial_specs() -> list[dict]:
    # All strings and expected labels are UCIE-authored; nothing remote runs.
    return [
        {"case_id": "ps-exact", "technology": "PowerShell",
         "target_version": "7.6.6", "observed_version": "7.6.6",
         "expected": True, "control": "POSITIVE"},
        {"case_id": "ps-prefix-spoof", "technology": "PowerShell",
         "target_version": "7.6.6", "observed_version": "7.6.60",
         "expected": False, "control": "NEGATIVE"},
        {"case_id": "ps-other", "technology": "PowerShell",
         "target_version": "7.6.6", "observed_version": "7.6.5",
         "expected": False, "control": "UNCHANGED"},
        {"case_id": "py-exact", "technology": "Python",
         "target_version": "3.15.0", "observed_version": "3.15.0",
         "expected": True, "control": "POSITIVE"},
        {"case_id": "py-prefix-spoof", "technology": "Python",
         "target_version": "3.15.0", "observed_version": "3.15.00",
         "expected": False, "control": "NEGATIVE"},
        {"case_id": "py-other", "technology": "Python",
         "target_version": "3.15.0", "observed_version": "3.14.0",
         "expected": False, "control": "UNCHANGED"},
    ]


def _legacy_prefix_match(target: str, observed: str) -> bool:
    """UCIE-authored intentionally weak baseline for regression comparison."""
    return observed.startswith(target)


def _bounded_exact_match(target: str, observed: str) -> bool:
    """Working first-party candidate: match complete numeric version token."""
    return bool(VERSION_RE.fullmatch(target) and
                VERSION_RE.fullmatch(observed) and target == observed)


def evaluate_first_party_trials(cases: list[dict]) -> dict:
    """Execute only controlled string comparison, not a technology runtime."""
    require_local_work("VIRTUAL_LIBRARY")
    if type(cases) is not list or not 1 <= len(cases) <= MAX_CASES:
        raise FalsificationError("bounded first-party test cohort required")
    valid = {x["case_id"]: x for x in _trial_specs()}
    seen = set()
    rows = []
    for case in cases:
        if (type(case) is not dict or set(case) != set(next(iter(valid.values())))
                or type(case.get("case_id")) is not str
                or case["case_id"] not in valid or case != valid[case["case_id"]]
                or case["case_id"] in seen):
            raise FalsificationError("unreviewed, duplicate, or altered fixture")
        seen.add(case["case_id"])
        expected = case["expected"]
        baseline = _legacy_prefix_match(case["target_version"],
                                        case["observed_version"])
        challenger = _bounded_exact_match(case["target_version"],
                                          case["observed_version"])
        rows.append({
            "case_id": case["case_id"], "control": case["control"],
            "technology": case["technology"], "expected": expected,
            "baseline_observed": baseline,
            "challenger_observed": challenger,
            "baseline_correct": baseline is expected,
            "challenger_correct": challenger is expected,
            "source": TRIAL_ORIGIN,
        })
    rows.sort(key=lambda x: x["case_id"])
    counts = {
        "baseline_correct": sum(x["baseline_correct"] for x in rows),
        "challenger_correct": sum(x["challenger_correct"] for x in rows),
        "baseline_false_accepts": sum(
            x["baseline_observed"] and not x["expected"] for x in rows),
        "challenger_false_accepts": sum(
            x["challenger_observed"] and not x["expected"] for x in rows),
        "baseline_false_rejects": sum(
            not x["baseline_observed"] and x["expected"] for x in rows),
        "challenger_false_rejects": sum(
            not x["challenger_observed"] and x["expected"] for x in rows),
    }
    return {
        "trial_origin": TRIAL_ORIGIN,
        "cases": rows, "case_count": len(rows),
        "counts": counts, "first_party_pure_python_executed": True,
        "upstream_runtime_executed": False,
        "independent_qa_verified": False,
    }


def build_falsification_revision_batch() -> dict:
    """Bounded end-to-end W02->B4->trial->revision->SkillBook/engine drafts."""
    require_local_work("VIRTUAL_LIBRARY")
    records = _source_candidates()
    review = compare_draft_annotations(records, _draft_annotations(records))
    proposals = review["test_proposals"]
    if (len(proposals) != 1 or proposals[0]["mechanism"] != CLAIM
            or proposals[0]["distinct_technology_count"] != 2
            or review["source_revision_authenticated"] is not False
            or review["actual_first_party_trials_executed"] is not False):
        raise FalsificationError("wrong source boundary or proposal")
    trials = evaluate_first_party_trials(_trial_specs())
    cases = trials["cases"]
    expected_controls = {
        "PowerShell": {"POSITIVE", "NEGATIVE", "UNCHANGED"},
        "Python": {"POSITIVE", "NEGATIVE", "UNCHANGED"},
    }
    for technology, expected in expected_controls.items():
        if {c["control"] for c in cases if c["technology"] == technology} != expected:
            raise FalsificationError("unbalanced first-party control cohort")
    before, after = (trials["counts"]["baseline_correct"],
                     trials["counts"]["challenger_correct"])
    before_fp = trials["counts"]["baseline_false_accepts"]
    after_fp = trials["counts"]["challenger_false_accepts"]
    improved = (after > before and after_fp < before_fp
                and trials["counts"]["challenger_false_rejects"] <=
                    trials["counts"]["baseline_false_rejects"]
                and all(x["challenger_correct"] for x in cases)
                and all(x["baseline_correct"] and x["challenger_correct"]
                        for x in cases if x["control"] == "UNCHANGED"))
    review_option = ("PROPOSE_REVISION_FOR_INDEPENDENT_REVIEW"
                     if improved else "HOLD_OR_REJECT_NO_SAFE_SYNTHETIC_GAIN")
    hypothesis = proposals[0]
    candidate_core = {
        "hypothesis_id": hypothesis["hypothesis_id"],
        "source_review_sha256": review["content_sha256"],
        "trial_digest": _hash(trials),
        "claim": CLAIM,
        "review_option": review_option,
        "observed_first_party_gain": improved,
        "baseline_correct": before, "candidate_correct": after,
        "baseline_false_accepts": before_fp,
        "candidate_false_accepts": after_fp,
        "preconditions": ["EXACT_VERSION_REQUIRED",
                          "POSITIVE_NEGATIVE_CONTROL_REQUIRED"],
        "negative_lessons": [
            "VERSION_PREFIX_IS_NOT_EXACT_APPLICABILITY",
            "HISTORICAL_TRIAL_DOES_NOT_PROVE_CURRENT_UPSTREAM_FIX",
        ],
    }
    revision_sha = _hash(candidate_core)
    revision = {
        **candidate_core,
        "revision_id": "UCIE-V2-B4-REV-" + revision_sha[:20],
        "revision_sha256": revision_sha,
        "source_revision_authenticated": False,
        "engine_activated": False,
        "original_skillbook_replaced": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "customer_release_authorized": False,
    }
    chapter = (
        "UCIE 독립 초안: 버전 적용 범위는 완전한 숫자 토큰으로 확인하고 "
        "접두 문자열 일치로 호환성을 판단하지 않는다. Python 및 PowerShell "
        "이름을 붙인 UCIE 자체의 무해한 문자열 예제에서만 시험했다. "
        "이는 해당 런타임 자체의 결함 수정, 최신 릴리스 포함 여부, "
        "다른 플랫폼 호환성을 증명하지 않는다. 부정 사례를 유지하며 "
        "독립 QA 및 사용권 승인 전 배포하지 않는다."
    )
    engine = {
        "kind": "UCIE_FIRST_PARTY_INERT_ENGINE_CONTRACT_DRAFT",
        "algorithm": "EXACT_NUMERIC_VERSION_TOKEN_MATCH",
        "input_contract": "TWO_BOUNDED_VERSION_STRINGS",
        "output_contract": "BOOLEAN_EXACT_MATCH",
        "negative_cases": ["PREFIX_SPOOF", "DIFFERENT_VERSION"],
        "replay_test_module":
            "tests/test_ucie_v2_b4_falsification_revision_batch_v01.py",
        "runtime_execution_enabled": False,
        "external_sdk_execution_allowed": False,
        "rights_approved": False, "export_allowed": False,
    }
    payload = {
        "schema": SCHEMA, "origin": TRIAL_ORIGIN,
        "annotation_review_sha256": review["content_sha256"],
        "test_proposal_id": hypothesis["hypothesis_id"],
        "test_summary": trials, "revision": revision,
        "skillbook_chapter_draft": {
            "kind": "UCIE_ORIGINAL_HUMAN_SKILLBOOK_DRAFT",
            "text": chapter,
            "text_sha256": sha256(chapter.encode("utf-8")).hexdigest(),
            "publication_authorized": False,
        },
        "machine_engine_draft": engine,
        "first_party_synthetic_trials_executed": True,
        "actual_upstream_python_or_powershell_tested": False,
        "source_revision_authenticated": False,
        "independent_qa_verified": False,
        "rights_approved": False,
        "owner_release_authorized": False,
        "auto_promotion": False,
        "model_training_performed": False,
        "history_persisted": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
    return {**payload, "content_sha256": _hash(payload)}


def new_in_memory_revision_ledger() -> dict:
    core = {
        "schema": LEDGER_SCHEMA, "events": [],
        "count": 0, "head": None, "persisted": False,
        "owner_approved": False, "customer_export_authorized": False,
    }
    return {**core, "content_sha256": _hash(core)}


def validate_in_memory_revision_ledger(ledger: dict) -> dict:
    empty = new_in_memory_revision_ledger()
    if (type(ledger) is not dict or set(ledger) != set(empty)
            or ledger["schema"] != LEDGER_SCHEMA
            or ledger["persisted"] is not False
            or ledger["owner_approved"] is not False
            or ledger["customer_export_authorized"] is not False
            or type(ledger["events"]) is not list
            or len(ledger["events"]) > MAX_EVENTS):
        raise FalsificationError("invalid or forged revision ledger")
    previous = None
    seen = set()
    for i, event in enumerate(ledger["events"], 1):
        if (type(event) is not dict or set(event) != {
                "sequence", "previous_hash", "bundle", "event_hash"}
                or type(event["sequence"]) is not int
                or event["sequence"] != i
                or event["previous_hash"] != previous
                or event["bundle"] != build_falsification_revision_batch()):
            raise FalsificationError("unrecognized or tampered revision event")
        digest = event["bundle"]["content_sha256"]
        if digest in seen:
            raise FalsificationError("duplicate revision event")
        seen.add(digest)
        if event["event_hash"] != _hash({
                k: v for k, v in event.items() if k != "event_hash"}):
            raise FalsificationError("broken revision hash chain")
        previous = event["event_hash"]
    if (type(ledger["count"]) is not int
            or ledger["count"] != len(ledger["events"])
            or ledger["head"] != previous
            or ledger["content_sha256"] != _hash({
                k: v for k, v in ledger.items() if k != "content_sha256"})):
        raise FalsificationError("ledger digest mismatch")
    return deepcopy(ledger)


def append_revision_for_review(ledger: dict, bundle: dict) -> dict:
    state = validate_in_memory_revision_ledger(ledger)
    canonical = build_falsification_revision_batch()
    if type(bundle) is not dict or bundle != canonical:
        raise FalsificationError("not a canonical first-party revision")
    if any(e["bundle"]["content_sha256"] == bundle["content_sha256"]
           for e in state["events"]):
        return state
    if len(state["events"]) >= MAX_EVENTS:
        raise FalsificationError("bounded history capacity reached")
    event = {
        "sequence": len(state["events"]) + 1,
        "previous_hash": state["head"],
        "bundle": deepcopy(bundle),
    }
    event["event_hash"] = _hash(event)
    state["events"].append(event)
    state["count"] = len(state["events"])
    state["head"] = event["event_hash"]
    state["content_sha256"] = _hash({
        k: v for k, v in state.items() if k != "content_sha256"})
    return validate_in_memory_revision_ledger(state)
