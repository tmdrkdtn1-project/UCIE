# UCIE P10 owner-gated single-job recovery preparation (2026-11-15)

Scope: UCIE ONLY. This document records code-only preparation and a bounded
read-only owner-host preflight. It does not authorize or perform recovery.

## Why P10 is held

- Read-only D:/UCIE queue: four historical SUCCEEDED, three REVIEW_REQUIRED,
  zero PENDING, zero RUNNING. Three failed at attempts=5/max=5 with generic
  RETRYABLE_ERROR. This does NOT disclose the old child/worker exception.
- P11 PUBLIC_INCREMENTAL_MINING remains REVIEW_REQUIRED and was NOT selected
  for recovery. The most recent real public attempt in the P11 ledger was
  2026-11-01 09:03:02 UTC and failed; 450 historical successful GETs and
  91 first-party synthetic experiences are not ongoing success evidence.
- 2026-11-15 exact Windows read-only dependency test:
  PUBLIC_METADATA_REVIEW current search completed with 1,310 grouped /
  1,318 source-linked revision records. UCIE_REPORT_PREPARATION current
  integrated read-only preview also completed with the expected NO_GO output.
  No network calls or queue changes. These findings do NOT prove why five
  earlier attempts failed.

## New code and guardrails

- src/ucie_miner/p10_owner_rearm_v01.py
  - CLI is PREVIEW ONLY for PUBLIC_METADATA_REVIEW and
    UCIE_REPORT_PREPARATION, with no apply/rollback command.
  - Uses mode=ro, query_only SQLite preview, exact job kind/dedupe key and
    pre-transaction row SHA256.
  - Internal owner apply/rollback core exists for future integration, but
    is NOT hooked into MCP, scheduler, web app or live owner launcher.
  - Internal apply, when independently authorized by a later owner launcher,
    admits only one REVIEW_REQUIRED row at 5/5, zero RUNNING jobs, zero
    active recovery receipts. It writes only the isolated P10 queue and a
    one-operation receipt in the same transaction. It schedules PENDING
    after a 10-minute grace period; no immediate worker, API call, new task
    or auto-promotion.
  - Internal rollback checks exact after-state fingerprint, no RUNNING
    workers, exact active operation and time before due. After a claim or
    deadline, rollback explicitly refuses; rollback is NOT a process kill.
  - Once-rearmed historical snapshot SHA cannot be replayed after rollback.
  - P11 public GET, experience learning, other P10 kinds, OS tasks and
    operating PublicMiner SQLite are excluded.
- tests/test_ucie_p10_owner_rearm_v01.py:
  14 disposable synthetic cases plus one real owner-Windows read-only
  preview. Actual owner-host runner 15/15 PASS.
- tests/test_ucie_p10_p11_readonly_live_probes_v01.py:
  one actual owner-Windows read-only dependency test, 1/1 PASS.

## Operational barriers remain mandatory

The flags accepted by the INTERNAL apply/rollback functions are NOT
cryptographic identity proofs and are NOT a trusted TaskScheduler
attestation. They must never be treated as sufficient live permission.

A future, separately reviewed owner-only launcher must, **before exposing
any apply or rollback interface**:

1. Independently inspect the current exact UCIE-Internal-Minute Windows
   task, configured action, owner SID, run level, LastTaskResult and
   exact recent TaskScheduler events, not a caller-supplied Boolean.
2. Independently attest zero active / overlapping workers and current
   source SHA against the reviewed owner checkout. Do not reset other
   jobs or touch the separate P11 collector.
3. Require a fresh preview fingerprint and specific explicit owner
   authorization for ONE kind, without an API GET.
4. Capture before/after operation receipts and safely verify that
   only the one P10 row transitioned to delayed PENDING.
5. Offer rollback only while the original row is unclaimed and before
   its due time. Later failures require investigation, not blind rollback
   or retry.
6. Reverify the real scheduled P10 transition and independent P11
   freshness only with separate P11 authorization and quota review.

## Separate Stage17 gate

PR #278 revised the bounded source-linked audit cap 1000 to 2000, and
local source-linked audit of 1310 groups now returns review-required
without AuditError. The legacy 2026-11-15 14:37 KST hourly receipt still
reports Stage17 failure; the latest quality snapshot is from 2026-11-09.
A new NORMAL hourly run and two exact scheduler event-to-receipt matches
are required before claiming operating recovery. Do not run a forced miner.

## Independent Windows minute-task evidence (read-only)

- New `tests/test_ucie_p10_task_owner_readonly_v01.py`: static bounded
  scope and real exact Windows TaskScheduler query, owner 2/2 PASS.
- Exact root task `\\UCIE-Internal-Minute` exists, State=Ready,
  LastTaskResult=0, current owner SID matches, action path + arguments +
  working directory match installed first-party entrypoint, Interactive/
  Limited principal matches, PT1M repetition and IgnoreNew match.
- Bounded exact-task events: 64 returned (limit reached), 16 grouped
  successful scheduler action instances observed; last run
  2026-11-15T06:20:20Z and next run 2026-11-15T06:21:21Z at observation.
  The bounded result is not the full task history.
- This proves that the TaskScheduler dispatcher itself is currently
  operating, **not** that the three exhausted jobs resumed or that P11
  public evidence collection recovered. Event-to-queue-job completion
  receipt binding remains NOT_VERIFIED, and owner APPLY remains disabled.

## Status

OWNER_ONLY_PREVIEW_AND_SYNTHETIC_REARM_CORE_READY;
NO_TRUSTED_LIVE_APPLY_INTERFACE;
NO_PRODUCTION_REARM;
P11_HOLD;
STAGE17_RUNTIME_HOLD;
RULE_PROMOTION_OFF;
CUSTOMER_RELEASE_NO_GO.

Owner hardware/GPU upgrade and separate explicit approval remain a
precondition for any UCIE-specific Qwen/model work. No other project
sources, code, user/private files, credentials or models were accessed.
