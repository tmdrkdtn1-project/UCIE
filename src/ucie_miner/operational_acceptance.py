"""Stage 8 no-side-effect acceptance evaluator, never a scheduler installer."""
from __future__ import annotations

REQUIRED = ("stage4_ci_matrix_passed", "knowledge_db_restore_test_passed",
            "stage5_pattern_tests_passed", "stage6_regression_tests_passed",
            "stage7_independent_approval", "stage7_rulepack_signature_verified",
            "source_scope_reviewed", "operator_authorized")


def operational_acceptance(evidence: object) -> dict:
    """Consume explicit documented observations; do not inspect local projects."""
    if not isinstance(evidence, dict) or set(evidence) != set(REQUIRED):
        raise ValueError("missing or unexpected acceptance evidence")
    if any(type(v) is not bool for v in evidence.values()):
        raise ValueError("nonboolean evidence denied")
    missing = [name for name in REQUIRED if evidence[name] is False]
    return {"schema": "UCIE_OPERATIONAL_ACCEPTANCE_PREVIEW_V1",
            "status": "READY_FOR_MANUAL_REVIEW" if not missing else "NO_GO",
            "pending": missing,
            "checks_claimed_by_caller_not_reverified": True,
            "scheduler_registered": False, "database_migrated": False,
            "package_published": False, "rulepack_signed": False,
            "production_approved": False}
