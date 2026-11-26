"""UCIE first-party B5 paired-control readiness; synthetic-only, no customer data.

Reject partial, unpaired, mixed-cohort, overclaimed or untrusted reports.
Original comparison contract is authoritative for per-row validation.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import median

from .ucie_v2_b5_comparison_contract_v01 import (
    B5StudyContractError, METHODS, SYNTHETIC_ORIGIN,
    summarize_synthetic_comparison,
)

SCHEMA = "UCIE_V2_B5_PAIRED_SYNTHETIC_READINESS_V01"


def assess_synthetic_pairs(records: tuple[dict, ...]) -> dict:
    """Assess comparability, not actual competitive advantage or human UX."""
    # Existing B5 validation rejects PII, duplicates, fake human origin and scope drift.
    summary = summarize_synthetic_comparison(records)
    by_subject: dict[str, dict[str, dict]] = defaultdict(dict)
    cohort_by_subject = {}
    for row in records:
        token = row["anonymous_trial_token"]
        cohort = row["cohort"]
        if token in cohort_by_subject and cohort_by_subject[token] != cohort:
            raise B5StudyContractError("paired cohort mismatch")
        cohort_by_subject[token] = cohort
        by_subject[token][row["method"]] = row
    if not by_subject:
        return {
            "schema": SCHEMA,
            "status": "SYNTHETIC_COMPARISON_EMPTY_HOLD",
            "paired_synthetic_subjects": 0,
            "missing_method_subjects": {},
            "unpaired_observation_count": 0,
            "comparison": None,
            "synthetic_summary": summary,
            "real_human_observations": 0,
            "human_evidence_valid": False,
            "competitor_advantage_verified": False,
            "automatic_rule_adoption": False,
            "customer_release_authorized": False,
        }
    missing = {
        token: sorted(set(METHODS) - set(variants))
        for token, variants in sorted(by_subject.items())
        if set(variants) != set(METHODS)
    }
    if missing:
        return {
            "schema": SCHEMA,
            "status": "SYNTHETIC_COMPARISON_INCOMPLETE_HOLD",
            "paired_synthetic_subjects": 0,
            "missing_method_subjects": missing,
            "unpaired_observation_count": len(records),
            "comparison": None,
            "synthetic_summary": summary,
            "real_human_observations": 0,
            "human_evidence_valid": False,
            "competitor_advantage_verified": False,
            "automatic_rule_adoption": False,
            "customer_release_authorized": False,
        }
    deltas: dict[str, list[int]] = {name: [] for name in METHODS if name != "UCIE_V2_REVIEW_ONLY"}
    safety_regressions = []
    for token, variants in sorted(by_subject.items()):
        target = variants["UCIE_V2_REVIEW_ONLY"]
        for comparator, times in deltas.items():
            baseline = variants[comparator]
            times.append(baseline["first_safe_action_time_ms"] - target["first_safe_action_time_ms"])
            if target["correct_safe_action"] is False and baseline["correct_safe_action"] is True:
                safety_regressions.append({"token": token, "against": comparator})
            if (target["false_version_or_rights_claim"] is True
                    and baseline["false_version_or_rights_claim"] is False):
                safety_regressions.append({"token": token, "against": comparator, "kind": "FALSE_CONFIDENCE"})
    report = {
        name: {"paired_synthetic_count": len(times),
               "synthetic_median_baseline_minus_ucie_ms": median(times) if times else None}
        for name, times in deltas.items()
    }
    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_PAIRED_CONTROL_CONTRACT_ONLY",
        "paired_synthetic_subjects": len(by_subject),
        "missing_method_subjects": {},
        "unpaired_observation_count": 0,
        "comparison": report,
        "synthetic_safety_regressions": safety_regressions,
        "synthetic_summary": summary,
        "real_human_observations": 0,
        "human_evidence_valid": False,
        "competitor_advantage_verified": False,
        "automatic_rule_adoption": False,
        "customer_release_authorized": False,
        "origin": SYNTHETIC_ORIGIN,
    }
