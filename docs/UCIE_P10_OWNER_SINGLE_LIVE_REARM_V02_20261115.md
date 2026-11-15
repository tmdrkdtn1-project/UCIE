# UCIE P10 exact owner one-job rearm V02 — 2026-11-15

UCIE only; exact D:\UCIE existing P10 queue and Windows TaskScheduler
UCIE-Internal-Minute. No program runs an external GET or changes scheduler.

## Current independent owner Windows evidence

- PUBLIC_METADATA_REVIEW: existing P10 --execute subprocess exit 0 and
  HANDLER_READ_ONLY_SUCCESS.
- UCIE_REPORT_PREPARATION: same exit 0 and HANDLER_READ_ONLY_SUCCESS.
- P10 queue: 3 REVIEW_REQUIRED (both above plus P11 network kind), each
  attempts=5/5, reason=RETRYABLE_ERROR; 4 historical SUCCEEDED, zero
  PENDING and RUNNING at time of owner read-only observation.
- P11 network job is excluded from this capability without exception.
- Historical errors are NOT retroactively diagnosed by new handler success.

## Safety and actual implementation

- Default CLI is a read-only PREVIEW of exactly one allowed job.
- Live queue change requires the exact real owner Windows checkout,
  current Windows SID matching the minute-task principal, approved action
  and working directory, one PT1M trigger, IgnoreNew, Interactive/Limited,
  task state Ready, last result 0, and at least one bounded successful
  exact-task instance (Event IDs 100/200/201/102).
- Owner explicitly supplies an exact job ID, fresh SHA256 row fingerprint
  and exact one-job consent phrase. No Boolean-only OS attestation.
- One SQLite BEGIN IMMEDIATE transaction checks original held 5/5 row,
  all leases clear, zero RUNNING jobs, zero other ACTIVE owner rearm.
  It updates ONLY that job to PENDING with a fixed 10-minute delay,
  resets only its attempts, and stores original/post SHA and old due/reason
  in a new UCIE-only operation receipt (unique preimage).
- Automatic P10 one-minute supervisor will claim the row only after due;
  this CLI never invokes it or calls the public API.
- Optional ROLLBACK is allowed only before due and worker claim and must
  match exact post-rearm SHA, then restore the exact original row fingerprint.
- Explicit FINALIZE can close the active rearm only after first-party job
  status SUCCEEDED or matching completed history with finished_at >= due.
  TaskScheduler success alone is not an individual P10 job success.
- Synthetic tests write ONLY to exact disposable TempDirectory/UCIE with
  a special marker; internal transaction entrypoints also validate exact
  consent and synthetic marker or reattest the Windows owner before any
  actual write.
- No API/other project/private data, model, package, promotion or
  deployment is involved.

## Owner PREVIEW (safe read-only)

    D:\UCIE\.venv\Scripts\python.exe -B -m ucie_miner.p10_owner_single_live_rearm_v02 --ucie-root D:\UCIE --kind PUBLIC_METADATA_REVIEW

At owner observation this gave job_id=2 and exact_row_fingerprint_sha256:
b409b363490200412e972b41fab031aacef444f03ce7060923814c1e57d1b820

For UCIE_REPORT_PREPARATION, job_id=5, fingerprint:
3518c2977eeb1e03efc4aca2bcbff67d132181b6141a8d4222b2a1106e5f44d5

## Simplified one-command owner PowerShell wrapper

To avoid manually typing a SHA-256 fingerprint or job ID, an additional
exact UCIE-only wrapper computes and validates a FRESH read-only preview
first. It uses the reviewed fixed venv Python and exact module arguments.
Then, and ONLY if -Approve was explicitly supplied, it passes the fresh
SHA256 to the actual Python CLI. The Python CLI independently reattests
the Windows owner and task inside its process and atomically compares
the same row SHA. This prevents preview/apply TOCTOU drift.

Safe preview:

    cd D:\UCIE
    .\scripts\p10_owner_rearm_one_v02.ps1 -Kind PUBLIC_METADATA_REVIEW

Single approved mutation (MUST be done by owner after CI/source review):

    .\scripts\p10_owner_rearm_one_v02.ps1 -Kind PUBLIC_METADATA_REVIEW -Approve

The wrapper accepts only PUBLIC_METADATA_REVIEW and
UCIE_REPORT_PREPARATION. It refuses P11, unexpected job IDs, task/owner
drift, malformed fingerprint, or a non-eligible held row. It does NOT
run a worker or GET, start/stop/set a scheduler task, or rearm all jobs.

Actual owner Windows preview:
UCIE_P10_OWNER_ONE_JOB_PS_V02 / PREVIEW_ONLY_NO_QUEUE_CHANGE,
kind PUBLIC_METADATA_REVIEW, job_id 2, owner_task_verified=true,
public_gets=0, queue_modified=false. Windows one-file static/parser/
read-only wrapper tests 3/3 PASS. Live -Approve NOT called.

## Explicit owner APPLY (MUTATES ONLY ONE P10 ROW)

Do NOT use until code and CI reviewed. Run only against a new PREVIEW
whose job ID and row fingerprint still match, in the owner Windows session.

    D:\UCIE\.venv\Scripts\python.exe -B -m ucie_miner.p10_owner_single_live_rearm_v02 --ucie-root D:\UCIE --kind PUBLIC_METADATA_REVIEW --apply --job-id 2 --expected-sha256 b409b363490200412e972b41fab031aacef444f03ce7060923814c1e57d1b820 --owner-consent UCIE_OWNER_APPROVES_EXACT_ONE_NONNETWORK_JOB_REARM

Only a receipt with status EXACT_ONE_NONNETWORK_JOB_DELAYED_PENDING proves
that one row changed. Record its operation_sha256 and scheduled_due_at.
This does NOT mean a worker has run or that public evidence was verified.

Optional rollback BEFORE due and BEFORE claim (use returned operation SHA):

    D:\UCIE\.venv\Scripts\python.exe -B -m ucie_miner.p10_owner_single_live_rearm_v02 --ucie-root D:\UCIE --kind PUBLIC_METADATA_REVIEW --rollback --operation-sha256 <exact_operation_sha256> --owner-consent UCIE_OWNER_APPROVES_EXACT_ONE_NONNETWORK_JOB_ROLLBACK

After exact P10 SUCCEEDED and matching receipt/history observation:

    D:\UCIE\.venv\Scripts\python.exe -B -m ucie_miner.p10_owner_single_live_rearm_v02 --ucie-root D:\UCIE --kind PUBLIC_METADATA_REVIEW --finalize --operation-sha256 <exact_operation_sha256> --owner-consent UCIE_OWNER_APPROVES_EXACT_ONE_NONNETWORK_JOB_FINALIZE

A second held P10 job cannot be resumed until the first owner operation
is observed complete and explicitly finalized. Failed job is not
automatically retried beyond P10 queue bounds. P11 remains HOLD.

## Evidence and limits

Owner Windows new source/test results: 9/9 PASS on synthetically isolated
transactions plus exact owner task PREVIEW. Real P10 production queue was
never rearmed by these tests. Full GitHub Actions CI and review needed.
The UCIE bridge cannot invoke an arbitrary owner mutation command, so
actual live APPLY requires separately authorized owner Windows execution.

STATUS=P10_ONE_JOB_OWNER_LIVE_CODE_VALIDATED_IN_SYNTHETIC;
OPERATING_JOB_REARM_NOT_EXECUTED; P11_GET_NOT_REARMED;
AUTO_PROMOTION_OFF; CUSTOMER_RELEASE_HOLD.
