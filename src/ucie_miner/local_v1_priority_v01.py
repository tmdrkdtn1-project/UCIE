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
CURRENT_PHASE = "LOCAL_PRODUCT_IMPLEMENTATION"
LOCAL_V1_ACCEPTED_BY_OWNER = False
ONLINE_RELEASE_AUTHORIZED = False
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
        raise LocalPriorityError("WORK_DEFERRED_UNTIL_UCIE_LOCAL_V1_GO")
    if (LOCAL_V1_ACCEPTED_BY_OWNER is not False
            or ONLINE_RELEASE_AUTHORIZED is not False
            or PERIPHERAL_EXPANSION_AUTHORIZED is not False):
        raise LocalPriorityError("LOCAL_V1_OWNER_GATE_CHANGED_REVIEW_REQUIRED")
    return {
        "schema": SCHEMA,
        "owner_decision": OWNER_DECISION,
        "current_phase": CURRENT_PHASE,
        "task": task,
        "gate": LOCAL_WORK[task],
        "status": "LOCAL_PRODUCT_TASK_ALLOWED_UNDER_OWNER_PRIORITY",
        "local_v1_accepted": False,
        "online_release_authorized": False,
        "peripheral_expansion_authorized": False,
        "automatic_rule_promotion": False,
    }


def roadmap() -> dict:
    """The source-coded roadmap, not an implicit release approval."""
    require_local_work("LOCAL_APP")
    return {
        "schema": SCHEMA,
        "status": "UCIE_LOCAL_V1_NOT_YET_OWNER_ACCEPTED",
        "ordered_phases": [
            "1_LOCAL_V1_SINGLE_APP_FOUR_JOBS_OWNER_ACCEPTANCE",
            "2_ONLINE_AND_DESIGNATED_CUSTOMER_DELIVERY",
            "3_PERIPHERAL_DEVELOPMENT_AND_EXPANSION",
        ],
        "allowed_local_work": dict(LOCAL_WORK),
        "deferred_until_local_v1_go": list(DEFERRED_WORK),
        "local_acceptance_gates": list(LOCAL_ACCEPTANCE_GATES),
        "local_v1_accepted_by_owner": False,
        "online_release_authorized": False,
        "peripheral_expansion_authorized": False,
        "customer_distribution_authorized": False,
        "owner_acceptance_receipt_generated": False,
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
            "status": "WORK_DEFERRED_UNTIL_UCIE_LOCAL_V1_GO",
            "local_v1_accepted_by_owner": False,
            "customer_distribution_authorized": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
