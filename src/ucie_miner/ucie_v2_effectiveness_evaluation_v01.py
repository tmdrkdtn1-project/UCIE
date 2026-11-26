"""UCIE V2 bounded metric evaluation and evidence-aware research priorities.

An offline, owner-authored test fixture is not a real customer study. This
module measures synthetic confusion matrices and paired regression separately,
then gates review scheduling against old source holds and independent QA.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math

from .ucie_v2_feedback_registry_v01 import (
    validate_feedback_registry, prioritize_review_experiments,
)
from .ucie_v2_library_revision_ledger_v01 import validate_review_history

SCHEMA = "UCIE_V2_BOUNDED_EFFECTIVENESS_EVALUATION_V01"
MAX_CASES = 128
MAX_ID = 72
LABELS = frozenset(("RISK", "SAFE"))
ORIGIN = "UCIE_FIRST_PARTY_SYNTHETIC_REPLAY_ONLY"
STATUS = frozenset(("CORRECT", "FALSE_POSITIVE", "FALSE_NEGATIVE", "TRUE_NEGATIVE"))
FIELDS = frozenset(("case_id", "ground_truth", "baseline_prediction",
                    "challenger_prediction", "origin", "source_sha256"))
CANONICAL_SOURCES = frozenset(("doc:python/cpython", "doc:git/git",
                               "repo:modelcontextprotocol/python-sdk"))


class EvaluationError(ValueError):
    """Reject ungrounded performance, target leakage or released-rule claims."""


def digest(obj: object) -> str:
    return sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False
                             ).encode("utf-8")).hexdigest()


def _ratio(numer: int, denom: int) -> dict:
    # Record denominator even when no observations exist. Never treat 0/0 as 100%.
    return {"numerator": numer, "denominator": denom,
            "value": (numer / denom) if denom else None}


def _validate_cases(cases: object, *, source_sha256: str) -> list[dict]:
    if (type(source_sha256) is not str or len(source_sha256) != 64
            or any(c not in "0123456789abcdef" for c in source_sha256)
            or type(cases) not in (list, tuple)
            or len(cases) > MAX_CASES):
        raise EvaluationError("unbounded or unpinned evaluation input")
    seen = set()
    result = []
    for item in cases:
        if (type(item) is not dict or set(item) != FIELDS
                or type(item["case_id"]) is not str
                or not 1 <= len(item["case_id"]) <= MAX_ID
                or not item["case_id"].isascii()
                or not all(c.isalnum() or c in "_-:." for c in item["case_id"])
                or item["case_id"] in seen
                or item["source_sha256"] != source_sha256
                or item["origin"] != ORIGIN
                or any(item[k] not in LABELS or type(item[k]) is not str
                       for k in ("ground_truth", "baseline_prediction",
                                 "challenger_prediction"))):
            raise EvaluationError("invalid, duplicate or private evaluation row")
        seen.add(item["case_id"])
        result.append(dict(item))
    return sorted(result, key=lambda row: row["case_id"])


def _rates(rows: list[dict], method: str) -> dict:
    positive = sum(row["ground_truth"] == "RISK" for row in rows)
    negative = len(rows) - positive
    tp = sum(row["ground_truth"] == "RISK" and row[method] == "RISK"
             for row in rows)
    fp = sum(row["ground_truth"] == "SAFE" and row[method] == "RISK"
             for row in rows)
    fn = positive - tp
    tn = negative - fp
    return {
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "detection_rate": _ratio(tp, positive),
        "false_positive_rate": _ratio(fp, negative),
        "false_negative_rate": _ratio(fn, positive),
        "accuracy": _ratio(tp + tn, len(rows)),
    }


def evaluate_bounded_improvement(history: dict, registry: dict,
                                 rows: list[dict] | tuple[dict, ...],
                                 *, source_sha256: str) -> dict:
    """Source-pinned paired synthetic assessment with explicit failure metrics."""
    pinned = validate_review_history(history)
    review = validate_feedback_registry(pinned, registry)
    candidate = _validate_cases(rows, source_sha256=source_sha256)
    base = _rates(candidate, "baseline_prediction")
    next_ = _rates(candidate, "challenger_prediction")
    improved = sum((r["baseline_prediction"] != r["ground_truth"] and
                    r["challenger_prediction"] == r["ground_truth"]) for r in candidate)
    regressed = sum((r["baseline_prediction"] == r["ground_truth"] and
                     r["challenger_prediction"] != r["ground_truth"]) for r in candidate)
    changed = sum(r["baseline_prediction"] != r["challenger_prediction"]
                  for r in candidate)
    priority = prioritize_review_experiments(pinned, review)
    source_hold = any(row["blocked_by_upstream_change"]
                      for row in priority["priority_queue"])
    sufficient = bool(candidate) and all(x["denominator"] for x in (
        base["detection_rate"], base["false_positive_rate"],
        next_["detection_rate"], next_["false_positive_rate"]))
    # No statistical or causal proof follows from synthetic paired rows.
    status = ("HOLD_NO_SYNTHETIC_CASES" if not candidate else
              "HOLD_NO_POSITIVE_OR_NEGATIVE_CONTROL" if not sufficient else
              "HOLD_SOURCE_CHANGE" if source_hold else
              "REVIEW_REGRESSION_OBSERVED" if regressed else
              "REVIEW_SYNTHETIC_ONLY")
    payload = {
        "schema": SCHEMA, "status": status,
        "history_head_sha256": pinned["content_sha256"],
        "review_registry_sha256": review["content_sha256"],
        "fixture_source_sha256": source_sha256,
        "fixture_digest_sha256": digest(candidate),
        "sample_origin": ORIGIN, "paired_cases": len(candidate),
        "baseline": base, "challenger": next_,
        "paired_improved_cases": improved,
        "paired_regressed_cases": regressed,
        "paired_prediction_changed_cases": changed,
        "paired_regression_rate": _ratio(regressed, len(candidate)),
        "paired_improvement_rate": _ratio(improved, len(candidate)),
        "ranked_review_queue": priority["priority_queue"],
        "real_user_outcomes_collected": 0,
        "real_world_effectiveness_verified": False,
        "statistical_significance_claimed": False,
        "independent_qa_verified": False,
        "fixture_source_authentication_proven": False,
        "automatic_adoption": False, "automatic_training": False,
        "customer_release_authorized": False,
        "network_requests": 0, "operating_database_writes": 0,
    }
    return {**payload, "content_sha256": digest(payload)}
