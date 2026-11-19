# UCIE W29 — owner-only old-root maintenance and immediate restoration rehearsal core

Date: 2026-11-19. Scope first-party UCIE only. This phase implements an actual owner-gated core but validates it ONLY with disposable mock functions in CI. No operator Windows execution, current SQLite handoff, C40 MCP tunnel acceptance, or production cutover.

## Accepted real owner baseline

- W26 owner Windows read-only: patched W19 pure Same comparator PASS on all 3 real OLD original ScheduledTask Actions and same owner; old PublicMiner Ready, InternalMinute Ready, old LocalV1 Running.
- W27 owner Windows read-only: ten current .sqlite3 names/path types/sizes agree with historic W16/W18, total observed 5,656,576 bytes; two old writers stayed operational; no content, SHA, quickcheck or global lockstep snapshot evidence.
- Historic W22/W24/W21 private intents, W22 restored receipt and W24 pre-rebind emergency restore intent/receipt are already occupied and immutable. No reuse or deletion. No W19/W13/W20 stage/newroot runtime last verified. Original W21 child exception unrecoverable, historical actual root cause UNVERIFIED.

## W29 coordinator (new UCIE-only source)

File: scripts/ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1

Modes:
1. Default -ContractOnly emits UCIE_W29_CONTRACT_ONLY_NO_HOST_ACCESS, accesses no host object.
2. -OwnerPreflightReadOnly is a separately approved same SID UAC-elevated inspection of historical owner receipts, protected archive, clean pinned first-party Git, original three task actions/states, C40 action hash and old LocalV1 loopback/health. Does not modify task, private journal or operating DB.
3. -RehearseOld requires a DIFFERENT explicit approval and is **NOT authorized for current owner execution**. If separately approved later, it writes a NEW private W29 intent before disabling any task, disables exactly the three original task schedules, stops ONLY the original LocalV1 Scheduled Task, expects free 18767 port and exact old Disabled actions, then immediately attempts a separately journaled restore whether the quiesce stage passed or failed. It does not copy SQLite, invoke legacy W19/W21/W22/W24 or rebind C40.
4. -RecoverOld requires a third explicit approval and an existing W29 intent. It may attempt one bounded restore if no W29 recovery intent or restored receipt already exists, no staged W19/W13/W20 outputs, original task action/owner and C40 unchanged. It never repeats an incomplete restore blindly.

New private one-shot filenames, distinct from old occupied W22/W24/W21 and future W28 reserved migration names:
- UCIE_W29_OWNER_OLDROOT_REHEARSAL_INTENT_V01.json
- UCIE_W29_OWNER_OLDROOT_RECOVERY_INTENT_V01.json
- UCIE_W29_OWNER_OLDROOT_RESTORED_V01.json

The recovery intent is persisted before any restoration task changes. LocalV1 must return Task Running and ONE 127.0.0.1 listener with exact UCIE owner-local HTTP health before two ORIGINAL writers are merely enabled, never force-started. C40 task action hash must match. Restored receipt is written ONLY after all verification. On failure, all intents remain for manual review; no claim of full self-healing. Unknown 18767 listener or modified Task/C40 denies recovery; no foreign Python PID kill.

## CI negative cases

tests/test_ucie_w29_oldroot_restore_core_injected_v01.py parses actual first-party W29 PowerShell function definitions but executes only isolated core functions with disposable mock ScheduledTask objects and in-memory fake receipts. Tests check:
- no-host/default and unauthenticated mutating mode rejection;
- exact local-before-writers restoration order;
- partial task disable + already-healthy local recovery;
- foreign listener/C40 drift/stage residue fail-closed;
- recovery intent preceding first task mutation;
- restored receipt only after all tasks/HTTP accepted and duplicate call denied;
- failed second writer enable creates no restored receipt, preserves intent, rejects blind retry;
- only three original tasks quiesced and only old LocalV1 stopped.

Windows/Ubuntu Python3.13+3.15 CI executes no owner Task Scheduler/SQLite/C40 mutations. CI success does NOT prove the owner host task DACL can always enable tasks or that an unknown process can be safely stopped. Real owner -RehearseOld is not requested, and if such a future test fails, old service may still need manual repair.

## Explicit remaining gates

- W29 is a bounded old-root service-availability rehearsal, **not** W28 actual current ten-SQLite migration, a global snapshot, newroot cutover or C40 MPC end-to-end proof.
- A separate reviewed recovery plan for a partial recovery-intent failure must be accepted before a real owner outage, otherwise a single fail-closed recovery attempt may leave original tasks disabled.
- A new W28/W30 data-handoff owner transaction must not call legacy occupied W19/W21/W24 Apply/Resume/Rollback and must preserve historical logs; fresh 10-SQLite lockstep handoff and task action lineage are separately tested.
- C40/tunnel unchanged and unverified. No automation scheduling, production deployment, cleanup or data-rule promotion authorized.
