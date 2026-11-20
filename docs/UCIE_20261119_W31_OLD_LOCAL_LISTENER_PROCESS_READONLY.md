# UCIE W31 - Read-only old LocalV1 listener PID evidence

Date: 2026-11-19. FIRST-PARTY UCIE ONLY. This is a READ ONLY source and synthetic-CI milestone. It does not authorize W29 old-root outage, W30 recovery, W28 data transfer, C40/tunnel modification or full cutover.

## Actual owner baseline and what remains unknown

- W26 actual Windows owner comparator: the three original UCIE Task Scheduler action/owner definitions PASS. PublicMiner and InternalMinute Ready, LocalV1-Web Running. No tasks/SQLite/C40 changed.
- W27 actual owner metadata scan: ten source SQLite file names, paths, size bounds PASS, observed sum 5,656,576 bytes while old writers continue running. Database bytes/sha, SQLite quickcheck, exclusive locks and current globally consistent image were NOT verified.
- W29 oldroot quiesce+immediate restoration and W30 bounded secondary recovery have merged with four-platform synthetic CI, but the actual healthy owner Windows environment has NEVER run W29 rehearsal, so W29 failed-restoration intents do not exist there. Occupied historical W22/W24/W21 and emergency recovery receipts remain protected.
- Actual listener-to-Task Scheduler launch linkage, C40 MCP/tunnel end-to-end, real Windows recovery acceptance and full production cutover remain UNVERIFIED.

## First-party W31 owner read-only gate

Source: scripts/ucie_owner_w31_local_listener_pid_readonly_v01.ps1

- Default contract-only mode accesses NO host files, port, Task Scheduler, process table, private archive, SQLite or C40.
- An explicit same-owner UAC-elevated -CheckLocal invocation checks exact newroot source path, clean pinned first-party Git remote, W30 ancestral SHA and immutable W29 PowerShell Git blob, owner-only protected archive, original six W22/W24/W21/emergency restoration private receipts, original three old exact task actions/states and C40 Action hash.
- Rejects any W19/W13/W20/W28 stage or W29/W30 one-shot intent/recovery/restored files; never removes or overwrites those files.
- Verifies original old LocalV1 HTTP health. Filters ONLY TCP listener port 18767 using Get-NetTCPConnection with LocalPort 18767 and Listen; requires exactly one listener bound to 127.0.0.1. Retrieves only the listener's OwningProcess PID and issues a PID-filtered Win32_Process CIM query; it does not enumerate unrelated processes.
- Compares actual process ExecutablePath and parsed CommandLine exactly against ORIGINAL old UCIE LocalV1 Task Action execute/arguments, and calls read-only CIM GetOwnerSid ONLY for that PID, requiring exact signed-in owner SID. Rechecks only port 18767 after the process inspection and refuses a changed or missing listener PID; this reduces a PID-rebinding race without claiming immutable process identity. Reconfirms C40 Action hash is unchanged.
- All mismatches fail CLOSED without process kill, Scheduler action, newroot runtime, journal writing, SQLite open or C40/tunnel activity.

### Accurate pass interpretation

Success status:
UCIE_W31_EXACT_LOOPBACK_PID_BINARY_CLI_OWNER_VERIFIED__TASK_LAUNCH_LINK_HOLD

This means that the sole loopback listener process PID, executable, exact arguments and owner SID are consistent with the current original UCIE LocalV1 ScheduledTask Action. THIS DOES NOT prove that Task Scheduler actually launched that process (a separate process launched manually by the same owner with the same executable and arguments could appear the same). The source deliberately outputs listener_pid_launched_by_task_scheduler_verified=false and listener_task_pid_identity_verified=false. It also explicitly states c40_mcp_round_trip_verified=false, full_cutover_authorized=false.

## Native synthetic failure-injection testing

tests/test_ucie_w31_listener_owner_pid_readonly_v01.py extracts the ACTUAL source PowerShell pure functions by AST. Disposable in-memory mocked TCP, Win32_Process and CIM GetOwnerSid replace host queries. Tests include:
- no-host default, missing owner approval denial, orphan approval denial;
- valid quoted and unquoted original Pythonw command line;
- wrong port, additional arguments, changed exe/script, altered quoting and executable masquerading denied;
- zero/multiple listeners, nonloopback bind, zero PID, missing/wrong CIM process, wrong process executable or owner SID denied;
- query only port 18767 and its observed PID, reject other CIM actions, no Schedule Task mutation, SQLite or journal writes;
- no misleading TaskScheduler-to-PID launch or C40 MCP claims.

Only CI disposable runners are used. Windows and Ubuntu x Python 3.13 and 3.15 offline CI 4/4 is required before any merge. A CI PASS is NOT a real Windows owner host PASS.

## Optional future owner action after exact pinned source merge

Sync the clean isolated D:\UCIE_PROJECT\UCIE checkout by fast-forward to the exact verified main SHA from W31 (do not touch operating D:\UCIE). In the same-owner UAC-elevated interactive PowerShell, the only relevant W31 commands are:

    $root = 'D:\UCIE_PROJECT\UCIE'
    $probe = "$root\scripts\ucie_owner_w31_local_listener_pid_readonly_v01.ps1"
    & $probe -ContractOnly
    & $probe -CheckLocal -OwnerApproval 'AUTHORIZE_UCIE_W31_READONLY_OLD_LOCAL_LISTENER_PID_INSPECTION'

W32 usability correction: when the owner runs the explicitly approved W31 -CheckLocal mode in a normal, non-elevated Windows PowerShell, W31 now requests Windows UAC elevation using the fixed system Windows PowerShell executable and an encoded literal read-only child command. The child verifies that its Windows SID matches the original non-admin caller SID before accessing the UCIE host. The original shell reports UCIE_W32_ELEVATED_READONLY_WINDOW_STARTED__RESULT_PENDING and does NOT report a host PASS. The elevated PowerShell window remains visible (-NoExit) and prints the actual W31 pass/HOLD receipt. If UAC is denied/cancelled or invokes a different Windows account, W31 fails CLOSED without skipping any owner/archive or C40 checks. This convenience does not automate Git fetch/merge and must be run only after source is clean, verified and fast-forward synced.

These are strictly read-only W31 checks. A HOLD is reason for review, NEVER to kill the unknown 18767 PID, change C40/tunnel, clear protected journals, or retry already-used W21/W24. Do not run W29 -RehearseOld or W30 -RecoverPartial/-ResumePartial on the current healthy owner PC.

## Future gates (all remain HOLD)

Actual Task Scheduler to listener PID launch trace; oldroot interruption/recovery full Windows acceptance; C40 MCP/tunnel real roundtrip; current writer-barrier ten-SQLite consistent image; separately approved W28 newroot data/task transaction; two newroot writers; full cutover.
