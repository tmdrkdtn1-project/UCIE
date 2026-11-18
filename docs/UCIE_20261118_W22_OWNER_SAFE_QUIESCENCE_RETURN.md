# W22: owner-only quiescence and return-to-original-availability (2026-11-18)

**GATE = CODE / CI ONLY. No one has executed W22 against the owner's Windows PC. Full operating cutover remains HOLD.**

## Why this step exists

The owner supplied the following non-mutating observations:

- `UCIE-PublicMiner-Hourly` = Ready, exact original (`D:\UCIE`) task action and matching owner SID.
- `UCIE-Internal-Minute` = Ready, exact original task action and matching owner SID.
- `UCIE-LocalV1-Web` = Running, exact original task action and matching owner SID.
- `UCIE-C40-Recover` = Running, matching owner SID; C40 profile/tunnel binding and MCP roundtrip **not proven**.
- One loopback TCP listener on port 18767; `/local/health` returned `UCIE_LOCAL_V1_HEALTHY`.
- Port-owner process executable classified `OTHER_PYTHON_PATH_HOLD`, not exact old/new venv python executable. Its UCIE launcher command line was deliberately not read, so do NOT infer it is a known malicious process, a separate service, or the registered UCIE task.
- Owner-reported Git fast-forward from W17 staged checkout to W21 `44ae75fdcdcbdd4940076e0e58c3b6ea7bed729f`; W21 contract-only returned `UCIE_W21_CONTRACT_ONLY_NO_HOST_ACCESS`.
- W19/W20/W21 private maintenance journals absent and new-root `runtime` absent.

W21 `-ApplyLocal` **cannot be executed directly** in this state because it requires three already Disabled old tasks plus an unoccupied port. W21 `-RollbackLocal` restores old task ACTIONS but leaves all three DISABLED, so it cannot on its own resume the exact original Ready/Ready/Running availability. W22 is a first-party, bounded source-level remedy to that lifecycle gap, NOT a workaround for missing C40 proof.

## W22 implementation

`scripts/ucie_owner_w22_quiesce_resume_local_v01.ps1`

Default with no flags = `UCIE_W22_CONTRACT_ONLY_NO_HOST_ACCESS`. GitHub CI checks it and denies both mutating modes without their **different explicit owner approval phrase**, before any host access.

### Owner-only ApplyLocal (DO NOT RUN without a separate maintenance window)

The script requires:
1. Interactive Windows owner, protected ARCHIVE ACL, exact direct existing `D:\UCIE` and `D:\UCIE_PROJECT\UCIE` checkout paths, verified W21 Git ancestry and no indirect paths.
2. C40 exact task owner + one action + *Running* state; C40 action hash captured as a baseline, never modified.
3. Exact OLD action on each of the three Python tasks, owner SID, and exact reported starting states `Ready/Ready/Running`. Only one loopback listener at 18767 and expected UCIE LocalV1 HTTP schema/owner-local/no-online-release. HTTP PASS does NOT assert socket PID belongs to the task.
4. Existing W19/W20/W21 journals, marker, W19 final data/target `runtime` and rollback receipts all ABSENT. W19 historical W14/W16/W18 private receipt lineage validated in a READ-ONLY Python check **before any scheduled task stop**. No old DB open.
5. W22 private intent with initial state, owner SID hash and C40 action hash written atomically BEFORE any task mutation.

Then:
- Disable the three exact owner UCIE tasks, stop ONLY `UCIE-LocalV1-Web` task (never `Stop-Process`, no other PID / Python command line inspection).
- Require exact original actions now Disabled; wait a bounded time for **all** 18767 listeners to disappear, confirming only the observed port-release consequence (not permanent OS/process identity proof). If the unknown Python remains listening, STOP with `UCIE_W22_LISTENER_NOT_RELEASED_BY_OLD_TASK_EXPLICIT_RESUME` and preserve the intent. **Never kill the unknown process.**
- If the port is free and C40 action unchanged, call existing W21 one-shot `-ApplyLocal`, which calls W19 final 10-SQLite lockstep handoff and W13 Disabled rebind then W20 LocalV1-only pilot with drift gate. Writer tasks stay Disabled; C40 untouched. If failure or partial stage, no blind re-run, no DB rollback.
- Successful W22 source status is a **LocalV1-only pilot**, not operating GO, and **not** proof of C40/MCP plugin roundtrip, global non-SQLite snapshot consistency, or safe enablement of PublicMiner/InternalMinute.

### Owner-only ResumeOld (separately approved)

- Validate original W22 private intent SID/C40 action and exact original task names/states.
- If W21 journal exists, call W21 `-RollbackLocal`, which delegates existing W20/W19/W13 exact action rollback and keeps both SQLite copies. A W19 partial data copy before W13 journal is a manual-review HOLD, not an automatic retry.
- If no W21 journal exists, accept only exact OLD actions. Also accept a partially quiesced subset (writer states Ready or Disabled or Running, LocalV1 Running/Ready/Disabled) rather than requiring all three fully disabled.
- If old LocalV1 is already Running and HTTP healthy, leave it running; otherwise require **port 18767 completely FREE** before enabling/starting only the exact old UCIE LocalV1 task. Never kill or adopt a foreign listener. Verify its Running task state and local HTTP schema before re-enabling the two original writer schedules.
- Re-enable only original two UCIE writer schedules as needed, verify their Ready/Running state and C40 action hash, then record a protected W22 restore receipt.
- A matching local HTTP schema does **not** cryptographically bind the listener PID to the scheduled task. Explicitly record `listener_task_pid_identity_verified=false`; no customer release or C40/MCP live claim.

**Recovery failure may require owner intervention.** In particular, when port 18767 remains owned by an unknown Python process, W22 intentionally refuses to start a second old/new LocalV1 and may leave the three owner tasks Disabled pending review. Do not claim automatic availability restoration in that case.

## Safety / acceptance restrictions

- This source stages a **planned temporary interruption to LocalV1** and pauses the two UCIE data collection schedules when owner explicitly approves; it must not execute merely because CI passes or because the user sent a receipt.
- There is no automatic scheduling, Service/PID kill, tunnel/C40 restart or C40 profile touch. No modification to Git collisions, old operating files, SQLite data, other projects or unrelated processes.
- The local SQLite barrier is a temporary write lock, not proof of all non-SQLite processes having drained. Require a maintenance window and owner review of old running writers/side effects before any live GO.
- Preserve original `D:\UCIE`, `D:\UCIE_DATA`, `D:\UCIE_PREVIEW`, archive, 92 owner-collision holds and all journals.
- An independently authenticated C40/MCP plugin roundtrip and carefully gated activation of PublicMiner/InternalMinute remain **future steps**. Do not report W22 as complete migration or user-facing release.

### Explicitly withheld owner operations (reference only)

`-ApplyLocal -OwnerApproval AUTHORIZE_UCIE_W22_EXACT_OLD_TASK_QUIESCE_AND_W21_LOCAL_ONLY`

`-ResumeOld -OwnerApproval AUTHORIZE_UCIE_W22_RESTORE_ORIGINAL_SCHEDULES_AND_LOCALV1`

Do NOT ask the owner to run these until source/CI and native host maintenance design are independently reviewed, the exact Git SHA is pinned in new checkout, current task states are revalidated, and a short maintenance window is explicitly approved.

## Source testing

Tests: `tests/test_ucie_w22_owner_quiesce_resume_local_v01.py`.

CI runs PowerShell parser, no-host default, denied owner actions, static safety/lifecycle checks in Windows and available Ubuntu PowerShell contexts; it cannot simulate the real Task Scheduler operating state, C40/MCP connector identity or actual PID-to-task attribution. **CI PASS must not be called owner acceptance.**
