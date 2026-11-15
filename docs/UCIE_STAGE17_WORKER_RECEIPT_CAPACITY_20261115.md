# UCIE Stage17 worker receipt capacity contract recovery (2026-11-15)

UCIE-only; source-pinned diagnosis and bounded fix. No forced miner cycle,
external GET, queue rearm, scheduler registration, P11 action, model or release.

## Actual failure attribution

- Owner D:/UCIE on 2026-11-15 15:37:24 KST: actual normal hourly
  Stage17 quality snapshot advanced to 1313 source-linked groups
  (the previous snapshot from 11/09 contained 992). PR #278 raised
  library_audit_v07.MAX_ROWS from 1000 to 2000 and this audit now completes
  without AuditError. These are still unverified public candidates.
- Yet the same hourly worker's runtime/last_run.json returned
  status=COLLECTION_FAILED, error_phase=COLLECTOR_RESULT_VALIDATION,
  error_type=ValueError, while stage10_status was
  STAGE10_UNVERIFIED_STAGED_NO_GO. Owner read-only one-file test obtained
  the exact bounded receipt; task/DB remained unchanged by inspection.
- Root cause confirmed by source + isolated reproduction:
  worker.run_cycle Stage17 receipt gate still checked
  0 <= source-linked-count <= 1000 and -1000 <= delta <= +1000.
  The Stage17 producer and auditor could produce 1313 valid candidates,
  so the worker rejected a valid, unapproved-but-bounded result.
- Before applying the change, the new UCIE synthetic test produced the
  expected red result: counts 1313 and 2000, plus delta -2000, rejected
  as COLLECTION_FAILED / ValueError in COLLECTOR_RESULT_VALIDATION.
  This is independent confirmation of the missing validation update.

## Narrow fix

- Only worker.py's Stage17 receipt counter/delta validation now imports
  the SAME first-party named library_audit_v07.MAX_ROWS bound. Both the
  counter and signed delta allow values within [-2000,+2000] but 2001
  and -2001 still fail closed. Other receipt checks and provenance gates
  have not been relaxed.
- Preserve the local D:/UCIE original worker.py by exact before SHA lease
  and automatic backup. It has owner-local changes that differ from
  GitHub main; the GitHub branch changes ONLY the common three-line
  Stage17 bounds, never copies the entire owner-local worker.
- New tests/test_ucie_worker_stage17_receipt_cap_v14.py:
  isolated synthetic 1313 and exact 2000 accepted; 2001 rejected;
  +2001/-2001 delta rejected, -2000 accepted; actual owner-host
  receipt observed read-only. Windows owner 6/6 after patch.
- Existing test_ucie_worker.py: Windows owner 12/12 after patch.
  Existing test_ucie_owner_public_automation_observation_v01.py:
  read-only Windows 1/1, quality snapshot 1313, P10/P11 unchanged.
  The latest actual operating receipt is still the PRE-PATCH failure
  until the next natural scheduled invocation; do not claim runtime GO.

## Separate hard gates

- Next NORMAL hourly collection (not a forced run) must independently
  produce COLLECTED_UNVERIFIED or an explicitly classified PARTIAL result,
  matching Stage17 quality 1313+ with bounded delta, with fresh
  run_history/task-event identity. Any different error remains a blocker.
- P10 installed minute TaskScheduler is Ready, task action/principal
  matches and it recently produced successful task instances, but three
  exact P10 queue jobs remain REVIEW_REQUIRED 5/5. The minute task result
  is not the same as P10 job completion. No queue reset authorized.
- P11 source collector remains held since 2026-11-01; 450 historical
  public GETs, 91 first-party synthetic experiences and zero production
  algorithm improvements. No public collection restart without root-cause,
  quota and independent owner gates.
- No Qwen/model work before owner GPU upgrade and separate approval.
  Rule auto-promotion, client distribution and billing remain OFF/HOLD.

STATUS=STAGE17_WORKER_RECEIPT_BOUND_CODE_FIXED__OWNER_REGRESSION_19_PASS__
NEXT_REAL_HOURLY_RUNTIME_RECEIPT_PENDING__P10_P11_REARM_NO_GO
