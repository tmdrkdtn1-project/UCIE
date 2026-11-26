"""UCIE V2 B5: schema-bound comparison protocol and synthetic-only dry run.

NO free-form participant text, PII, recordings, files, customer code,
purchasing information or real-user inference. Synthetic input cannot
self-assert an owner-approved human observation. Comparison is NOT valid
until actual separately authorized, audited human studies are conducted.
"""
from __future__ import annotations

import re
import statistics

SCHEMA = "UCIE_V2_B5_COMPARISON_METHOD_V01"
STUDY_ID = "UCIE-B5-MCP-PROMPTS-FIRST-ACTION-001"
CASE_ID = "mcp-prompts"
METHODS = ("OFFICIAL_DOCS_ONLY", "GENERAL_TOOL", "UCIE_V2_REVIEW_ONLY")
COHORTS = ("FIRST_TIME_CODER", "TECHNICAL_REVIEWER")
SYNTHETIC_ORIGIN = "UCIE_AUTHORED_SYNTHETIC_DRY_RUN_ONLY"
MAX_SYNTHETIC_RECORDS = 48
TRIAL_FIELDS = frozenset({
    "study_id", "case_id", "anonymous_trial_token", "method", "cohort",
    "first_safe_action_time_ms", "correct_safe_action",
    "false_version_or_rights_claim", "evidence_detail_found", "origin",
})
TRIAL_TOKEN = re.compile(r"(?:F|T)[0-9]{2}\Z")


class B5StudyContractError(ValueError):
    """Protects study truth, no PII echo or fabricated customer claims."""


def build_comparison_protocol() -> dict:
    """Actual study instructions only; no claim that participants exist."""
    return {
        "schema": SCHEMA,
        "status": "METHOD_DEFINED_REAL_OBSERVATIONS_NOT_COLLECTED",
        "study_id": STUDY_ID,
        "task": {
            "case_id": CASE_ID,
            "scenario": "MCP_PROMPTS_GET_MISSING_REQUIRED_ARGUMENT",
            "required_safe_outcome": "RECOGNIZE_VERSION_UNKNOWN_HOLD_AND_ONE_SAFE_CHECK",
            "prohibited_outcome": "CLAIM_CUSTOMER_CODE_FIXED_OR_LICENSE_GRANTED",
            "source_fixture": "UCIE_FIRST_PARTY_SYNTHETIC_ONLY_UNTIL_AUTHORIZED",
        },
        "comparators": list(METHODS),
        "cohorts": list(COHORTS),
        "proposed_sample_ranges_not_actual": {
            "first_time_coders": "5..8",
            "technical_reviewers": "2..3",
            "distinct_prospective_buyers": "5..10",
        },
        "human_measures": [
            "TIME_TO_CORRECT_FIRST_SAFE_ACTION_MS",
            "CORRECT_SAFE_ACTION_FRACTION",
            "MATERIAL_FALSE_CONFIDENCE_COUNT",
            "WRONG_VERSION_OR_RIGHTS_CLAIM_COUNT",
            "EVIDENCE_DETAIL_FOUND_FRACTION",
            "RETEST_COST_AND_COST_OF_FAILURE",
            "REAL_DOCUMENT_COMPREHENSION",
            "REAL_BUYER_WILLINGNESS_RESEARCH_SEPARATE",
        ],
        "study_restrictions": [
            "OWNER_AUTHORIZED_RECRUITMENT_AND_CONSENT_REQUIRED",
            "NO_CUSTOMER_CODE_LOG_TOKEN_PATH_OR_PII",
            "OWNER_WINDOWS_EDGE_ACTUAL_BROWSER_ACCEPTANCE_SEPARATE",
            "NO_FALSE_PROMISE_OF_AUTOREPAIR_OR_APP_GENERATION",
            "UNSUPPORTED_OR_UNKNOWN_VERSION_MUST_HOLD",
            "PURCHASING_INTERVIEWS_NEVER_SUBSTITUTED_BY_SYNTHETIC_DATA",
        ],
        "real_novice_observed": 0,
        "real_technical_reviewer_observed": 0,
        "real_prospective_buyers_observed": 0,
        "first_action_under_10_seconds_target_fraction": 0.8,
        "material_overclaim_count_target": 0,
        "actual_human_study_completed": False,
        "baseline_comparison_completed": False,
        "actual_business_willingness_observed": False,
        "customer_export_authorized": False,
    }


def summarize_synthetic_comparison(records: tuple[dict, ...]) -> dict:
    """Dry-run parser only; even plausible outcome rows are NOT human facts."""
    if type(records) is not tuple or len(records) > MAX_SYNTHETIC_RECORDS:
        raise B5StudyContractError("bounded tuple of UCIE synthetic records only")
    counts: dict[str, dict] = {key: {
        "count": 0, "safe_action_count": 0, "false_claim_count": 0,
        "evidence_detail_count": 0, "time_ms": [],
    } for key in METHODS}
    unique = set()
    for row in records:
        if type(row) is not dict or set(row) != TRIAL_FIELDS:
            raise B5StudyContractError("unexpected study fields or private data")
        study_id = row["study_id"]
        case_id = row["case_id"]
        cohort = row["cohort"]
        method = row["method"]
        token = row["anonymous_trial_token"]
        ms = row["first_safe_action_time_ms"]
        if (type(study_id) is not str or study_id != STUDY_ID
                or type(case_id) is not str or case_id != CASE_ID
                or type(cohort) is not str or cohort not in COHORTS
                or type(method) is not str or method not in METHODS
                or type(token) is not str or TRIAL_TOKEN.fullmatch(token) is None
                or (token[0] == "F") != (cohort == "FIRST_TIME_CODER")
                or type(ms) is not int or not 0 <= ms <= 120_000
                or type(row["origin"]) is not str
                or row["origin"] != SYNTHETIC_ORIGIN
                or any(type(row[name]) is not bool for name in (
                    "correct_safe_action", "false_version_or_rights_claim",
                    "evidence_detail_found"))):
            raise B5StudyContractError("untrusted observation or synthetic scope")
        key = (method, token)
        if key in unique:
            raise B5StudyContractError("duplicate subject/method observation")
        unique.add(key)
        current = counts[method]
        current["count"] += 1
        current["time_ms"].append(ms)
        current["safe_action_count"] += int(row["correct_safe_action"])
        current["false_claim_count"] += int(row["false_version_or_rights_claim"])
        current["evidence_detail_count"] += int(row["evidence_detail_found"])
    result = {}
    for method in METHODS:
        values = counts[method]
        count = values["count"]
        result[method] = {
            "synthetic_count": count,
            "synthetic_correct_safe_action_count": values["safe_action_count"],
            "synthetic_false_claim_count": values["false_claim_count"],
            "synthetic_evidence_found_count": values["evidence_detail_count"],
            "synthetic_first_action_median_ms": (
                int(statistics.median(values["time_ms"])) if count else None
            ),
            "synthetic_safe_action_fraction": (
                round(values["safe_action_count"] / count, 6) if count else None
            ),
        }
    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_METRICS_AGGREGATED_NOT_HUMAN_STUDY",
        "study_id": STUDY_ID,
        "case_id": CASE_ID,
        "total_synthetic_records": len(records),
        "methods": result,
        "real_novice_observed": 0,
        "real_technical_reviewer_observed": 0,
        "real_prospective_buyers_observed": 0,
        "real_baseline_or_competitor_tested": False,
        "human_comparison_valid": False,
        "customer_willingness_measured": False,
        "first_party_synthetic_only": True,
        "automatic_approval_or_training": False,
        "network_requests": 0,
        "operating_database_writes": 0,
    }
