# UCIE W28 — isolated one-shot transaction state/recovery model (SOURCE ONLY)

Date: 2026-11-19. UCIE first-party scope only. This model never contacts a Windows owner PC, other projects, connected apps, operating SQLite, Task Scheduler, C40/tunnel, private archives or Git remote. No full cutover is authorized.

## Owner Windows receipt basis

- W26 real owner Windows read-only tested patched W19 Same function on three real old Task Actions: PublicMiner Ready, Internal Minute Ready, LocalV1 Running; owner/action match 3/3. No writer pause, SQLite open, journal mutation or C40 action change. Historical W21 masked exception was NOT recovered.
- W27 real owner Windows read-only source metadata tested 10 existing .sqlite3 names, direct/non-reparse paths and bounded file sizes; total observed size 5,656,576 bytes; writers kept running. This does NOT establish DB hashes, integrity, freshness, locks or global snapshot consistency.
- W22/W24/W21 historic intent journals and owner emergency restoration receipts ALREADY EXIST. Do not delete, move, reset, reuse or overwrite them. W19/W13/W20 stage journals and newroot runtime were last owner-verified absent.

## W28 implementation

scripts/ucie_owner_w28_transaction_state_model_v01.py defaults to UCIE_W28_CONTRACT_ONLY_NO_HOST_ACCESS. A finite --scenario option selects only built-in synthetic cases; no user paths, process command lines, credentials or external code accepted. It imports no host APIs, file/network clients, SQLite or subprocess. Outputs only a JSON simulation verdict and never performs any recovery action.

Three NEW names are reserved for a future W28 one-shot transaction, NOT written by this model:
- UCIE_W28_OWNER_NEW_TRANSACTION_INTENT_V01.json
- UCIE_W28_OWNER_NEW_TRANSACTION_RECOVERY_INTENT_V01.json
- UCIE_W28_OWNER_NEW_TRANSACTION_RESTORED_V01.json

Every decision returns full_cutover_authorized=false, automatic_old_task_restart_allowed=false, task_scheduler_changed=false, journal_written=false, database_opened=false, c40_queried_or_modified=false, simulated_only=true.

## Failure matrix

1. Original old tasks Ready/Ready/Running and old LocalV1 healthy, no new W28 intent, no stage: W28_FRESH_PLAN_ELIGIBLE_NOT_AUTHORIZED. This is only a source-design readiness classification; no owner Apply authorization.
2. A fresh W28 intent exists, all three exact old actions are Disabled, port free, LocalV1 down, historical records secured, C40 and owner unchanged, AND ALL stage outputs absent: W28_OLD_TASKS_QUIESCED_PRE_REBIND_RECOVERY_CANDIDATE. This is ONLY a candidate for a separately journaled recovery flow: record recovery intent before restoring old LocalV1; verify exact loopback HTTP health; then enable two original writers. The state model does NOT do any of those actions.
3. W19 journal recorded: HOLD_W19_STAGE_REQUIRES_SEPARATE_ROLLBACK_REVIEW.
4. W13 rebind, W20 pilot, W19/W20 rollback receipts exist: HOLD_W13_W20_REBIND_REQUIRES_SEPARATE_ROLLBACK_REVIEW.
5. Private copied DB, owner marker or newroot runtime present without journal: HOLD_UNJOURNALED_OUTPUT_REQUIRES_MANUAL_REVIEW.
6. W28 recovery intent already exists: HOLD_INCOMPLETE_RECOVERY_ATTEMPT, no blind retry.
7. W28 restoration receipt exists: HOLD_RESTORATION_ALREADY_RECORDED, never reuse one-shot receipts.
8. Mixed/unknown OLD versus NEW Task Actions or missing/running unexpected old tasks: HOLD_OLD_TASK_ACTION_OR_STATE_DRIFT.
9. Port 18767 foreign/multiple/unknown listener or LocalV1 state inconsistent with exact old-phase expectation: HOLD_PORT_OWNER_UNVERIFIED. Never kill an unknown Python PID.
10. Same-owner SID, UAC, protected archive, historical receipts, source pin or C40 action hash not proven: respective HOLD. No task action/ACL change.

Every scenario is self-contained, synthetic and non-sensitive. Any external fixture filename or unrecognized scenario is denied.

## CI evidence gates

- tests/test_ucie_w28_new_transaction_state_model_v01.py: default no-host, three unique W28 names and disjoint old receipts, exact prejournal candidate, all eight residue variants, task-action/state drift permutations, SID/UAC/ACL/C40/source negatives, port collision, incomplete restoration attempt and no arbitrary fixture file input.
- tests/test_ucie_w28_source_anchored_transition_boundaries_v01.py: validates W19 journal precedes SQLite handoff and W13 rebind; W21's W27 pre-rebind no-stage guard; W22/W24 old owner journals and early task stop ordering. These are code-reading unit tests in disposable CI, NOT owner host acceptance.

## Next implementation milestone and operational restrictions

W28 state model is not a new owner command and does not make the previously used W22/W24/W21 journals reusable. A new owner one-shot maintenance and restore coordinator still must be implemented and independently tested with:
- NEW protected intent/recovery/restored receipts and explicit same-owner UAC approval, secured first-party source and old task/C40 exact action hashes, pre-stop old local health and port verification;
- W19 pre-journal failure safe restoration WITHOUT calling W19/W13/W20 rollback when they never staged, and without overwriting existing immutable receipts;
- partial restoration failure recovery accounting without blind re-Apply, foreign PID termination or user data loss;
- W19/W13/W20 post-journal lineage-specific recovery, never treating an existing stage journal as pre-rebind;
- fresh 10-SQLite lockstep capture only in an explicitly approved later maintenance window AFTER full old-root restoration paths pass independently;
- C40 real MCP roundtrip and two-writer newroot activation as separate later gates.

Existing D:\UCIE old-root LocalV1 and the two original writer schedules remain the accepted operating state. No live service interruption, data copy, deletion, clean/reset, scheduler change or tunnel intervention belongs in this W28 source-only milestone.
