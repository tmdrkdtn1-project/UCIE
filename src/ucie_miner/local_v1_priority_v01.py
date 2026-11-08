"""UCIE owner-mandated execution priority: LOCAL PRODUCT FIRST.

This hardcoded contract is executable and fail-closed. No caller-supplied
"approved" boolean, timestamp, or synthetic CI receipt can promote phases.
Only a separately evidenced owner acceptance and reviewed source change can
lift the local release hold. This is not a host-wide Git permission layer:
local product entrypoints MUST call require_local_work.
"""
from __future__ import annotations

import argparse
import json

SCHEMA = "UCIE_LOCAL_V1_OWNER_PRIORITY_CONTRACT_V01"
OWNER_DECISION = "2026-11-08_LOCAL_PRODUCT_BEFORE_ONLINE_AND_PERIPHERAL"
CURRENT_PHASE = "LOCAL_V1_CONTINUOUS_USE_AND_DATA_MATURITY_PUBLIC_LAUNCH_HOLD"
LOCAL_V1_ACCEPTED_BY_OWNER = True
LOCAL_V1_OWNER_ACCEPTANCE_RECEIPT = "docs/UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md"
ONLINE_RELEASE_AUTHORIZED = False
PAID_HOSTING_SPEND_AUTHORIZED = False
PUBLIC_CLOUDFLARE_ROUTE_AUTHORIZED = False
DATA_MATURITY_BEFORE_PUBLIC_RELEASE = True
PERIPHERAL_EXPANSION_AUTHORIZED = False

LOCAL_WORK = {
    "LOCAL_APP": "LG1_SINGLE_WINDOWS_LAUNCH_AND_BROWSER",
    "ERROR_PREVENTION": "LG2_PUBLIC_ERROR_EVIDENCE_AND_SAFE_GUIDANCE",
    "DEV_ENGINE_SKILL": "LG2_REAL_FIRST_PARTY_ENGINE_INVOCATION",
    "VIRTUAL_LIBRARY": "LG2_SOURCE_BOUND_SKILLBOOK_READING",
    "EVIDENCE_EVOLUTION": "LG2_REAL_PUBLIC_CHANGE_REVIEW",
    "LOCAL_ACCEPTANCE": "LG3_TO_LG6_OWNER_REAL_WALKTHROUGH",
    "BLOCKING_LOCAL_DEFECT": "OBSERVED_LOCAL_PRODUCT_BLOCKER_ONLY",
}
DEFERRED_WORK = (
    "ONLINE_DEPLOYMENT",
    "CUSTOMER_SIGNING",
    "CUSTOMER_LICENSING",
    "COMMERCIAL_INSTALLER",
    "NEW_MINER",
    "SCHEDULER_REFACTOR",
    "PERFORMANCE_TUNING",
    "EXTRA_DASHBOARD",
    "ADDITIONAL_SKILLS",
    "OTHER_PLATFORM_EXPANSION",
    "EXTRA_PROOF_SCAFFOLD",
)
LOCAL_ACCEPTANCE_GATES = (
    "LG1_ONE_REAL_LOCAL_APP_LAUNCHED",
    "LG2_FOUR_USER_JOBS_COMPLETED",
    "LG3_SOURCE_VERSION_DRAFT_STATE_HONEST",
    "LG4_LOCAL_RESTART_AND_FAIL_CLOSED",
    "LG5_UCIE_ONLY_NO_AUTO_PROMOTION",
    "LG6_OWNER_HOST_SIGNOFF_RECEIPT",
)


class LocalPriorityError(ValueError):
    """Requested work would bypass the local-first execution order."""


def require_local_work(task: str) -> dict:
    """Apply to every new UCIE Local V1 product entrypoint and work dispatch.

    No externally supplied "owner approval" or boolean overrides the source
    pinned hold. Local owner acceptance is deliberately not self-attested.
    """
    if type(task) is not str or task not in LOCAL_WORK:
        raise LocalPriorityError("WORK_REQUIRES_SEPARATE_ONLINE_OR_EXPANSION_APPROVAL")
    if (LOCAL_V1_ACCEPTED_BY_OWNER is not True
            or ONLINE_RELEASE_AUTHORIZED is not False
            or PERIPHERAL_EXPANSION_AUTHORIZED is not False):
        raise LocalPriorityError("LOCAL_V1_OWNER_GATE_CHANGED_REVIEW_REQUIRED")
    return {
        "schema": SCHEMA,
        "owner_decision": OWNER_DECISION,
        "current_phase": CURRENT_PHASE,
        "task": task,
        "gate": LOCAL_WORK[task],
        "status": "LOCAL_PRODUCT_TASK_ALLOWED_AFTER_OWNER_ACCEPTANCE",
        "local_v1_accepted": True,
        "online_release_authorized": False,
        "paid_hosting_spend_authorized": False,
        "public_cloudflare_route_authorized": False,
        "data_maturity_before_public_release": True,
        "peripheral_expansion_authorized": False,
        "automatic_rule_promotion": False,
    }


def roadmap() -> dict:
    """The source-coded roadmap, not an implicit release approval."""
    require_local_work("LOCAL_APP")
    return {
        "schema": SCHEMA,
        "status": "UCIE_LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO",
        "ordered_phases": [
            "1_LOCAL_V1_OWNER_ACCEPTED_GO",
            "2_EXISTING_PUBLIC_EVIDENCE_DATA_MATURITY_AND_LOCAL_STABILITY",
            "3_ONLINE_AND_CUSTOMER_RELEASE_ONLY_AFTER_SEPARATE_OWNER_GO",
            "4_PERIPHERAL_DEVELOPMENT_AND_EXPANSION_LAST",
        ],
        "allowed_local_work": dict(LOCAL_WORK),
        "deferred_until_separate_commercial_or_expansion_approval": list(DEFERRED_WORK),
        "local_acceptance_gates": list(LOCAL_ACCEPTANCE_GATES),
        "local_v1_accepted_by_owner": True,
        "online_release_authorized": False,
        "peripheral_expansion_authorized": False,
        "customer_distribution_authorized": False,
        "owner_acceptance_receipt_generated": True,
        "owner_acceptance_receipt_path": LOCAL_V1_OWNER_ACCEPTANCE_RECEIPT,
        "daily_0900_report_paused": True,
        "no_other_project_access": True,
        "no_public_collector_or_scheduler_mutation": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="UCIE executable local-product-first priority lock")
    parser.add_argument("--work", default="LOCAL_APP")
    args = parser.parse_args(argv)
    try:
        require_local_work(args.work)
        report = roadmap()
    except LocalPriorityError:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "WORK_REQUIRES_SEPARATE_ONLINE_OR_EXPANSION_APPROVAL",
            "local_v1_accepted_by_owner": False,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
