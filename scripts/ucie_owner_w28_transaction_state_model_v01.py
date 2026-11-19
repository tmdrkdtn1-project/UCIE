"""UCIE W28: deterministic no-host migration/rollback decision model.

Scope: source-only simulation for a FRESH, isolated W28 one-shot transaction.
This module does NOT examine any real source, owner Windows host, SQLite,
Task Scheduler, C40/tunnel, Git checkout or archives. It CANNOT authorize a
live cutover or recover the historical W22/W24/W21 private journals.

All scenarios are built-in fixtures; caller input never supplies a path,
command, host, secret, task data or external code to execute.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import json
from typing import Literal


SCHEMA = "UCIE_W28_FRESH_OWNER_TRANSACTION_STATE_MODEL_V01"
BASELINE_SHA = "dd503ef37c908dccd7216fe8ecf1bcf061cc97ed"
NEW_INTENT = "UCIE_W28_OWNER_NEW_TRANSACTION_INTENT_V01.json"
NEW_RECOVERY = "UCIE_W28_OWNER_NEW_TRANSACTION_RECOVERY_INTENT_V01.json"
NEW_RESTORED = "UCIE_W28_OWNER_NEW_TRANSACTION_RESTORED_V01.json"

OLD_TASK_NAMES = (
    "UCIE-PublicMiner-Hourly",
    "UCIE-Internal-Minute",
    "UCIE-LocalV1-Web",
)
HISTORICAL_INTENTS = (
    "UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json",
    "UCIE_W22_ORIGINAL_AVAILABILITY_RESTORED_V01.json",
    "UCIE_W24_OWNER_RECOVERED_RETRY_INTENT_V01.json",
    "UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01.json",
    "UCIE_W24_PRE_REBIND_OWNER_RECOVERY_INTENT_V01.json",
    "UCIE_W24_PRE_REBIND_OWNER_RECOVERY_RECEIPT_V01.json",
)
STAGE_ITEMS = (
    "w19_journal",
    "w13_rebind_journal",
    "w20_pilot_journal",
    "w19_rollback_receipt",
    "w20_rollback_receipt",
    "opt_in_marker",
    "private_data",
    "new_runtime",
)
STATUSES = (
    "NO_TRANSACTION_NEEDED_OLD_ROOT_RUNNING",
    "W28_FRESH_PLAN_ELIGIBLE_NOT_AUTHORIZED",
    "W28_OLD_TASKS_QUIESCED_PRE_REBIND_RECOVERY_CANDIDATE",
    "HOLD_C40_OR_OWNER_DRIFT",
    "HOLD_OLD_TASK_ACTION_OR_STATE_DRIFT",
    "HOLD_PORT_OWNER_UNVERIFIED",
    "HOLD_LEGACY_RECEIPTS_NOT_VERIFIED",
    "HOLD_W28_TRANSACTION_NOT_PROVEN",
    "HOLD_RESTORATION_ALREADY_RECORDED",
    "HOLD_INCOMPLETE_RECOVERY_ATTEMPT",
    "HOLD_W19_STAGE_REQUIRES_SEPARATE_ROLLBACK_REVIEW",
    "HOLD_W13_W20_REBIND_REQUIRES_SEPARATE_ROLLBACK_REVIEW",
    "HOLD_UNJOURNALED_OUTPUT_REQUIRES_MANUAL_REVIEW",
)

TaskAction = Literal["OLD_EXACT", "NEW_EXACT", "UNKNOWN"]
TaskState = Literal["Ready", "Running", "Disabled", "Missing"]
Port = Literal["ONE_LOOPBACK_HEALTHY_OLD", "FREE", "OTHER_OR_MULTIPLE"]


@dataclass(frozen=True)
class OwnerSnapshot:
    """Synthetic fixture; no real host information is ever loaded."""
    actions: tuple[TaskAction, TaskAction, TaskAction] = (
        "OLD_EXACT", "OLD_EXACT", "OLD_EXACT"
    )
    states: tuple[TaskState, TaskState, TaskState] = (
        "Ready", "Ready", "Running"
    )
    same_owner_sid: bool = True
    owner_uac_elevated: bool = True
    archive_acl_protected: bool = True
    c40_task_running: bool = True
    c40_action_hash_unchanged: bool = True
    old_http_healthy: bool = True
    port_state: Port = "ONE_LOOPBACK_HEALTHY_OLD"
    history_preserved_and_recovered: bool = True
    pinned_first_party_source: bool = True
    w28_intent_exists: bool = False
    w28_recovery_intent_exists: bool = False
    w28_restored_receipt_exists: bool = False
    w19_journal: bool = False
    w13_rebind_journal: bool = False
    w20_pilot_journal: bool = False
    w19_rollback_receipt: bool = False
    w20_rollback_receipt: bool = False
    opt_in_marker: bool = False
    private_data: bool = False
    new_runtime: bool = False

    def stage_residue(self) -> bool:
        return any(getattr(self, field) for field in STAGE_ITEMS)

    def old_actions_exact(self) -> bool:
        return self.actions == ("OLD_EXACT",) * 3

    def old_running_states(self) -> bool:
        return (self.states[:2] in (("Ready", "Ready"), ("Running", "Ready"),
                                    ("Ready", "Running"), ("Running", "Running"))
                and self.states[2] == "Running")

    def old_disabled_states(self) -> bool:
        return self.states == ("Disabled",) * 3


@dataclass(frozen=True)
class Decision:
    status: str
    recommended_workflow: str
    automatic_old_task_restart_allowed: bool = False
    task_scheduler_changed: bool = False
    database_opened: bool = False
    c40_queried_or_modified: bool = False
    journal_written: bool = False
    original_owner_failure_explained: bool = False
    full_cutover_authorized: bool = False
    simulated_only: bool = True

    def as_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "status": self.status,
            "recommended_workflow": self.recommended_workflow,
            "automatic_old_task_restart_allowed":
                self.automatic_old_task_restart_allowed,
            "task_scheduler_changed": self.task_scheduler_changed,
            "database_opened": self.database_opened,
            "c40_queried_or_modified": self.c40_queried_or_modified,
            "journal_written": self.journal_written,
            "original_owner_failure_explained": self.original_owner_failure_explained,
            "full_cutover_authorized": self.full_cutover_authorized,
            "simulated_only": self.simulated_only,
        }


def classify(state: OwnerSnapshot) -> Decision:
    """Strict ordering: never trust stale, partial or mixed state as recoverable."""
    if not isinstance(state, OwnerSnapshot):
        raise TypeError("Synthetic OwnerSnapshot required")
    if (not state.same_owner_sid or not state.owner_uac_elevated
            or not state.archive_acl_protected
            or not state.c40_task_running
            or not state.c40_action_hash_unchanged):
        return Decision(
            "HOLD_C40_OR_OWNER_DRIFT", "STOP__READONLY_OWNER_REVIEW"
        )
    if not state.history_preserved_and_recovered:
        return Decision(
            "HOLD_LEGACY_RECEIPTS_NOT_VERIFIED", "STOP__PRESERVE_HISTORICAL_RECEIPTS"
        )
    if not state.pinned_first_party_source:
        return Decision(
            "HOLD_W28_TRANSACTION_NOT_PROVEN", "STOP__VERIFY_EXACT_SOURCE_SHA"
        )
    if not state.old_actions_exact():
        if state.w13_rebind_journal or state.w20_pilot_journal:
            return Decision(
                "HOLD_W13_W20_REBIND_REQUIRES_SEPARATE_ROLLBACK_REVIEW",
                "STOP__REVIEW_PINNED_W13_W20_OWNER_ROLLBACK_PROVENANCE"
            )
        return Decision(
            "HOLD_OLD_TASK_ACTION_OR_STATE_DRIFT", "STOP__READONLY_TASK_ACTION_REVIEW"
        )
    if state.w28_restored_receipt_exists:
        return Decision(
            "HOLD_RESTORATION_ALREADY_RECORDED", "STOP__NEVER_RETRY_SAME_W28_INTENT"
        )
    if state.w28_recovery_intent_exists:
        return Decision(
            "HOLD_INCOMPLETE_RECOVERY_ATTEMPT", "STOP__INSPECT_W28_RECOVERY_RECEIPT"
        )
    if (state.w13_rebind_journal or state.w20_pilot_journal
            or state.w19_rollback_receipt or state.w20_rollback_receipt):
        return Decision(
            "HOLD_W13_W20_REBIND_REQUIRES_SEPARATE_ROLLBACK_REVIEW",
            "STOP__REVIEW_PINNED_W13_W20_OWNER_ROLLBACK_PROVENANCE"
        )
    if state.w19_journal:
        return Decision(
            "HOLD_W19_STAGE_REQUIRES_SEPARATE_ROLLBACK_REVIEW",
            "STOP__DO_NOT_REMOVE_W19_JOURNAL_OR_DB_COPIES"
        )
    if any((state.opt_in_marker, state.private_data, state.new_runtime)):
        return Decision(
            "HOLD_UNJOURNALED_OUTPUT_REQUIRES_MANUAL_REVIEW",
            "STOP__PRESERVE_PARTIAL_OUTPUTS"
        )
    if state.w28_intent_exists:
        # The only recovery-eligible state is exactly OLD_EXACT+DISABLED
        # on all three tasks, no outputs, and free port. Even then this
        # plan NEVER invokes Task Scheduler or restarts anything.
        if not state.old_disabled_states():
            return Decision(
                "HOLD_OLD_TASK_ACTION_OR_STATE_DRIFT",
                "STOP__VERIFY_ORIGINAL_THREE_DISABLED_BEFORE_RECOVERY"
            )
        if state.port_state != "FREE" or state.old_http_healthy:
            return Decision(
                "HOLD_PORT_OWNER_UNVERIFIED",
                "STOP__REVIEW_PORT_18767_NO_FOREIGN_PROCESS_KILL"
            )
        return Decision(
            "W28_OLD_TASKS_QUIESCED_PRE_REBIND_RECOVERY_CANDIDATE",
            "OWNER_SEPARATE_JOURNALED_RECOVERY__LOCALV1_THEN_WRITERS"
        )
    # No W28 intent exists: no operation can be retried.
    if not state.old_actions_exact() or not state.old_running_states():
        return Decision(
            "HOLD_OLD_TASK_ACTION_OR_STATE_DRIFT", "STOP__REVIEW_ORIGINAL_TASKS"
        )
    if state.port_state != "ONE_LOOPBACK_HEALTHY_OLD" or not state.old_http_healthy:
        return Decision(
            "HOLD_PORT_OWNER_UNVERIFIED", "STOP__REVIEW_OLD_LOCAL_HTTP"
        )
    return Decision(
        "W28_FRESH_PLAN_ELIGIBLE_NOT_AUTHORIZED",
        "SOURCE_DESIGN_ONLY__FRESH_OWNER_APPROVAL_REQUIRED"
    )


def fixtures() -> dict[str, OwnerSnapshot]:
    """Small, fixed, non-sensitive scenarios: no file-based fixtures."""
    pristine = OwnerSnapshot()
    disabled = replace(
        pristine,
        w28_intent_exists=True,
        states=("Disabled",) * 3,
        old_http_healthy=False,
        port_state="FREE",
    )
    return {
        "old-running": pristine,
        "prejournal-recovery": disabled,
        "prejournal-c40-drift": replace(disabled, c40_action_hash_unchanged=False),
        "prejournal-port-occupied": replace(
            disabled, port_state="OTHER_OR_MULTIPLE"),
        "prejournal-w19-journal": replace(disabled, w19_journal=True),
        "prejournal-orphan-db": replace(disabled, private_data=True),
        "prejournal-mixed-action": replace(
            disabled, actions=("OLD_EXACT", "NEW_EXACT", "OLD_EXACT")),
        "recovery-intent-incomplete": replace(
            disabled, w28_recovery_intent_exists=True),
        "restoration-recorded": replace(
            disabled, w28_restored_receipt_exists=True),
        "missing-legacy-receipts": replace(
            pristine, history_preserved_and_recovered=False),
        "wrong-owner": replace(disabled, same_owner_sid=False),
        "w13-rebound": replace(
            disabled, w13_rebind_journal=True,
            actions=("NEW_EXACT", "NEW_EXACT", "NEW_EXACT")),
        "w20-pilot": replace(disabled, w20_pilot_journal=True),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UCIE W28 no-host plan simulation")
    parser.add_argument("--scenario", choices=tuple(fixtures()))
    args = parser.parse_args(argv)
    if args.scenario is None:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "UCIE_W28_CONTRACT_ONLY_NO_HOST_ACCESS",
            "expected_w27_main": BASELINE_SHA,
            "fresh_private_receipts": (NEW_INTENT, NEW_RECOVERY, NEW_RESTORED),
            "legacy_receipts_reused": False,
            "real_owner_host_accessed": False,
            "task_or_c40_modified": False,
            "sqlite_opened": False,
            "journal_written": False,
            "full_cutover_authorized": False,
        }, sort_keys=True))
        return 0
    result = classify(fixtures()[args.scenario]).as_dict()
    result["scenario"] = args.scenario
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
