# UCIE PublicMiner 60 -> 10 minute change (2026-11-15, KST)

Scope: isolated D:\UCIE, fixed task name \UCIE-PublicMiner-Hourly,
base official/approved public-only candidate miner. Task name stays
historically stable; its cadence changes to 10 minutes.

## Owner evidence and implementation state

- Actual owner Windows PREVIEW ONLY of
  scripts/set_public_miner_10min.ps1 returned:
  status=PREVIEW_ONLY_NO_TASK_CHANGES,
  existing_interval=PT1H,
  requested_interval=PT10M,
  exact_task_action_and_owner_verified=true,
  scheduler_changed=false,
  collection_run_requested=false,
  existing_last_task_result=2.
- DO NOT claim the Windows task has changed until owner-only APPLY returns
  status=EXACT_TASK_SET_TO_10_MINUTES and a subsequent independent read-only
  task query confirms an exact PT10M repetition interval.
- src/ucie_miner/schedule_policy.py uses INTERVAL=timedelta(minutes=10).
  Existing completed cycles have 30s bounded trigger jitter.
  Consecutive failures preserve a growing retry/backoff up to 60 minutes:
  a 10-minute scheduled trigger does NOT guarantee a new collection during
  a rate-limit, failing source, live worker or other safety gate.
- Existing source-only installer scripts/install_hourly_task.ps1 has a
  10-minute trigger for a FRESH install; because the owner task ALREADY
  EXISTS it refuses to overwrite it. Do NOT invoke that installer to
  migrate a live owner task.
- scripts/task_status.ps1 -Evidence expects PT10M and 8-12 minute
  completed-cycle separation. It preserves the historical task name and
  backward-compatible hourly_no_overlap_configured output key, but adds
  cadence_minutes=10 and ten_minute_no_overlap_configured. The output's
  historical "hourly" schema name is not proof of a 60-minute cadence.
- tests/test_ucie_schedule_policy.py and
  tests/test_ucie_public_miner_10min_cadence_v01.py execute offline and
  owner preview checks. UCIE Windows owner 14/14 + 3/3 PASS, existing
  worker tests 12/12 PASS. All operating records remain unmodified
  by those checks.

## Exact one-owner task update (not automatically invoked)

In the owner's Windows PowerShell session, from the already approved
D:\UCIE checkout:

    cd D:\UCIE
    .\scripts\set_public_miner_10min.ps1
    .\scripts\set_public_miner_10min.ps1 -Apply
    .\scripts\task_status.ps1 -Evidence

- First command is read-only and must show the exact preflight status,
  one approved task owner and action, and PT1H or PT10M. The second
  command changes ONLY the existing TaskScheduler trigger for the
  fixed UCIE-PublicMiner-Hourly task when -Apply is explicitly provided.
  It refuses task identity drift, wrong user SID, state != Ready,
  unapproved cadence and missing Python/policy. Attempts trigger
  rollback if post-update verification fails.
- First new scheduled activation is about 10 minutes after APPLY.
  It does not call Start-ScheduledTask, does not call a collector
  and does not modify the queue or operating SQLite itself.
- Verify Get-ScheduledTask for the exact UCIE task: PT10M, matching
  action/principal/IgnoreNew and NextRunTime. An operating PASS still
  requires actual scheduled run and source-linked receipt/event binding.
- If Windows TaskScheduler permissions deny Set-ScheduledTask, this
  change stays NO_GO and the owner must diagnose that scoped privilege
  error; do not elevate indiscriminately or delete/re-register a task.
- Existing 60-minute receipt history is intentionally preserved.
  Two new 10-minute completed-cycle receipts are needed for future
  event-to-receipt operational acceptance.

## Update failure and independent owner reconciliation (2026-11-15)

An owner invocation of -Apply returned
UCIE_TEN_MINUTE_APPLY_FAILED_ROLLBACK_UNCONFIRMED at the old catch block.
That string is NOT evidence that the task was actually changed, because
the former catch swallowed the original Set-ScheduledTask exception,
then attempted a second Set of the original trigger even when no first
write had occurred.

Read-only owner Windows rechecks AFTER the failure:
- Exact task still found, Ready, single trigger, actual interval PT1H,
  last task result decimal 2. Principal SID matches current owner;
  installed Python action and task settings match approved UCIE path.
- Current diagnostic subprocess uses an elevated administrator token,
  can read the task file ACL and exact Task Scheduler DACL, and can
  successfully construct the intended PT10M trigger IN MEMORY with the
  existing 3,650-day duration. None of these checks PROVES the specific
  owner interactive PowerShell session has task modify permission, nor
  whether Windows rejected Set for another reason.
- The original Set-ScheduledTask exception category and HRESULT were
  not captured in the old script. Do NOT call a permission/error root cause
  proven or retry blindly.

Safe updater repair:
- Separate first Set from post-update verification; on exception, query
  ONLY the exact task read-only. If the original trigger including interval,
  start boundary, duration, approved action and owner is still unchanged,
  emit status SET_FAILED_ORIGINAL_PT1H_INTACT_NO_ROLLBACK_NEEDED and a
  bounded error class/category/HRESULT, with no second Set attempt.
- If the first Set reports failure but the task is modified or unreadable,
  STOP with STATE_UNCERTAIN and do not blindly rollback.
- If Set returns success but post-verification fails, attempt one
  tightly scoped rollback and then verify the original interval/boundary;
  no rollback PASS if re-read does not confirm it.
- One owner read-only source parser/preflight and an injected PowerShell
  Set-ScheduledTask function (which deliberately throws without calling
  the actual cmdlet) verified that the repaired failure branch performs
  one mocked Set attempt and zero real task writes. Owner revised test
  5/5 PASS plus independent diagnostic 2/2 PASS.
- The live Windows task remains PT1H, NOT yet 10 minutes.

Next owner action: from the SAME original interactive PowerShell window
after the failure, inspect only the error object types, numeric HRESULTs
and error categories stored in $Error. Do not disclose raw messages,
task XML, account identities or source text. Have the actual first Set
failure category reviewed before another authorized -Apply attempt.
No manual unregister/re-register, forced collection, broad ACL change
or task enable/disable as an improvised workaround.

## Actual Set-ScheduledTask failure category (2026-11-15)

The owner provided the original PowerShell $Error summary from the SAME
window as the failing operation:

    Command=Set-ScheduledTask; Type=CimException;
    HResult=0x80131500; Category=PermissionDenied
    Command=Set-ScheduledTask; Type=CimException;
    HResult=0x80131500; Category=PermissionDenied

The leading RuntimeException/0x80131501 is the script's own rollback
error wrapper. The two CIM PermissionDenied responses prove both the
initial Set and the unnecessary rollback Set were denied; the general
.NET/CIM HRESULT alone does NOT identify the Windows native cause.
Do not label this a Python collector or 10m trigger validation bug.

Dedicated **read-only** ACL probe
tests/test_ucie_owner_exact_task_acl_readonly_v02.py, owner 2/2 PASS:
- exact UCIE-PublicMiner-Hourly is Ready, still PT1H
- diagnostic subprocess has elevated admin token, task file is present,
  task file DACL and Task Scheduler COM DACL readable
- task file owner SID differs from diagnostic process user SID
- current token SIDs matched 2 file write allow ACEs, 0 explicit write
  deny ACEs; 2 WriteDAC allow and 0 explicit deny; task COM DACL
  exposes 3 matching allow ACEs, 0 matching deny ACEs
- matching ACEs are not a definitive effective-access authorization.
  Diagnostic subprocess and the user's original interactive session
  may have **different** elevated tokens. Also, run-as task principal
  matching a user is not proof of task-file ownership.
- No ACL, Windows task, task file, or database was modified.

**Next mandatory read-only same-window check:** evaluate only
[Security.Principal.WindowsPrincipal]::new(
[Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
[Security.Principal.WindowsBuiltInRole]::Administrator)
in the original PowerShell session. If False, close that non-elevated
context and perform an exact-task preflight using an approved elevated
PowerShell window in the same account; do not blindly run -Apply.
If True, stop and independently inspect exact task permission and
Windows Task Scheduler event category before any additional write.
Never delete/re-register the task, grant broad ACL rights, or change
another project's task as a workaround.

## Quotas, safety and exclusions

Ten-minute cadence permits up to 6 scheduled cycles/hour rather than 1,
so public GitHub requests may increase. Keep allowlist, source caps,
HTTP quota guard, backoff, 0 automatic promotions and no customer release.
A 403/429/network failure must not trigger a tight retry loop. If API
limits are reached, report the actual status and allow safety backoff.

No change to UCIE-Internal-Minute/P10, P11 network job, C40, other
projects, customer UI, AI/Qwen, memory, personal data or private code.

STATUS=TEN_MINUTE_CODE_AND_OWNER_APPLY_SCRIPT_READY;
OWNER_WINDOWS_SCHEDULE_LAST_OBSERVED_PT1H;
REAL_TASK_APPLY_NOT_EXECUTED_BY_BRIDGE;
OPERATING_ACCEPTANCE_PENDING.
