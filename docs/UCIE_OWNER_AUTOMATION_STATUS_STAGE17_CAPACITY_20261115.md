# UCIE owner-only hourly + P10/P11 automation diagnosis and bounded Stage17 repair (2026-11-15)

## Grounded owner-local observations (read-only, not a release acceptance)

Source: the existing UCIE-only Windows host D:/UCIE, native UCIE read-only bridge,
and new source-pinned test_ucie_owner_public_automation_observation_v01.py.
Observed state may change after a new hourly run.

- Legacy public miner last receipt observed 2026-11-15T05:37:18+00:00:
  COLLECTED_UNVERIFIED with STAGE10_HOURLY_FAILED_NO_GO,
  phase STAGE17_QUALITY, type AuditError. A legacy collected receipt does
  NOT mean the multi-stage hourly pipeline succeeded.
- Runtime/reports/2026-11-15.md: total historical *legacy* public PRs 497
  (2026-11-14.md: 488). Stage10 candidate table contains 156 PR rows,
  Stage12 review queue 1318 unverified rows. After validated Stage12 source
  handoff, **1310 grouped source-linked candidates** require Stage17 audit.
- Previous quality_v12/latest.json, 2026-11-09T00:37:19+00:00, was at 992
  source-linked candidates. Original library_audit_v07.MAX_ROWS=1000
  caused exact AuditError("public candidate count exceeds bound") at 1310.
  Source-linked validation completed, so this was a bounded audit capacity
  issue, not permission to disregard untrusted source or claim a real fix.
- Owner Windows P10 queue: SUCCEEDED 4, REVIEW_REQUIRED 3, PENDING 0,
  RUNNING 0. Held kinds PUBLIC_METADATA_REVIEW, UCIE_REPORT_PREPARATION
  and PUBLIC_INCREMENTAL_MINING each reached attempts=5/max_attempts=5,
  with generic last_reason=RETRYABLE_ERROR. That is not proof of the
  underlying OS task's current registered/Running/Ready status.
- P11 status: 91 unverified leads, 91 first-party synthetic experience
  records, 26 improvement-review records, 450 historical successful public
  GETs; last public attempt 2026-11-01T09:03:02Z failed. No new P11
  public attempts proven since Nov 1, production improvements applied=0,
  rule auto-promotion=false. Existing 3 P10 REVIEW_REQUIRED rows must be
  handled under separate owner-approved recovery gates; an immediate
  blind retry/queue reset is NOT authorized here.
- Existing owner-specific TaskScheduler event-to-hourly receipt test:
  event log accessible but matched recent instance receipts=0,
  last scheduled run not matched, two recent successful scheduled cycles
  NOT PROVEN. We do not assert task registered or healthy on that basis.

## Fix implemented without changing any scheduler or operating data

- Raise the **finite** first-party source-linked audit bound from 1,000 to
  **2,000** groups. Stage10's own established raw-ledger capacity is higher,
  but this does not remove the separate audit cap.
- Use the SAME named audit bound in the optional Stage17 quality snapshot
  count, signed snapshot validation and candidate delta guards.
- No source allowlist, URLs, accepted claims, provenance/receipt checks,
  licenses, version/signature evidence, independent QA or approval checks
  changed. No extra public API requests or external source additions.
- Do NOT silently truncate to top 2,000: counts over 2,000 still fail closed.
  This is a bounded incident repair, not a future-proof infinite ledger.
- Operator real source-linked read-only audit after code change returned
  1310 candidates and AUDIT_REVIEW_REQUIRED_NO_GO with no AuditError.
  This means "unverified candidates pending human review," NOT a successful
  verified upstream fix or rule promotion.
- Synthetic first-party tests prove 1310 and exact cap 2000 accepted,
  cap+1=2001 denied, forged approval denied, prior 992 -> 1310 quality
  snapshot delta=318 with intact previous hash/zero approvals.
  Synthetic snapshot writes only an isolated TemporaryDirectory.
- The actual quality_v12/latest.json has NOT been manually rewritten.
  Check its next normal hourly receipt, exact scheduler events and status
  before declaring the full pipeline healthy.

## Repeatable owner checks (read-only, never installation or repair)

Use a normal non-elevated owner PowerShell session on D:/UCIE, after
reviewing source scripts and confirming local environment:

    $env:PYTHONPATH = 'D:\UCIE\src'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.pending_queue --ucie-root 'D:\UCIE'
    & 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.p11_closed_loop --ucie-root 'D:\UCIE' --status
    powershell.exe -NoProfile -NonInteractive -File 'D:\UCIE\scripts\task_status.ps1' -Evidence

The above are the project-owned explicit read-only status modes. They
must not be replaced with install/activate/collect/learn/start arguments
without separate owner review. Test pass alone is not an OS event receipt.

## Outstanding blockers and future gates

1. Stage17: next real opt-in hourly invocation must produce a current
   linked quality snapshot (above 1000, no AuditError), and an exact
   TaskScheduler instance-to-receipt chain must be independently matched.
2. P10: independently verify the exact task action, least-privilege owner,
   LastTaskResult and recent event+completed job evidence. Inspect each
   REVIEW_REQUIRED cause before planning an authorized bounded retry.
3. P11: identify why the last public attempt failed and worker attempts
   exhausted; keep API quota and source boundaries, rearm only after
   explicit owner approval and verifiable no-overlap safeguards.
4. Beyond 2000 source groups, design a revision-pinned, bounded
   pagination/checkpointed audit without losing source-linked receipt
   verification; do not increase arbitrary caps repeatedly.
5. Hardware GPU upgrade must precede any local Qwen/model installation or
   training. AI remains deferred until the user's separate approval.
6. No customer distribution, billing, automated rule activation or
   production release authority is implied by this maintenance PR.
