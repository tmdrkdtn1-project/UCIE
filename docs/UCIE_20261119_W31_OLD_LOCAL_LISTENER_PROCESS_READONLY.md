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

W33 (2026-11-20): Owner observed `UCIE_W32_SYSTEM_WINDOWS_PATH_UNAVAILABLE` after a successful contract-only receipt. The machine-scoped `SystemRoot` registry environment entry can be absent even on a functioning Windows system. W33 resolves `[Environment]::SystemDirectory` through the OS, then requires the fixed `WindowsPowerShell\\v1.0\\powershell.exe` beneath it. Neither machine/process `SystemRoot`, PATH nor an arbitrary executable is trusted. Existing same-owner SID and explicit UAC gates remain; native Windows test overrides only its own process environment to verify the trusted path remains OS-backed. CI is synthetic and does not establish an actual UAC or owner W31 result. No task/SQLite/C40/host/cutover change is authorized.

## W34 actual owner diagnostic / W35 Python venv redirector compatibility (2026-11-20)

After W33 was clean fast-forward synced, owner same-account UAC W31 reached the real localhost listener process inspection and returned `UCIE_W31_LISTENER_EXE_PATH_MISMATCH_HOLD`. A separately owner-run, bounded W34 **read-only** probe reported: pinned Task Action executable equals the original virtual-environment `D:\UCIE\.venv\Scripts\pythonw.exe`, observed listener command line equals that Task Action, same owner SID, stable exactly-one 127.0.0.1:18767 PID; **actual OS executable is the base Python 3.15 `pythonw.exe`**, not the virtual-environment redirector. No user-profile path, SID, command line or other private host detail is saved in this public document. This remains evidence of command-line and owner consistency, NOT Task-Scheduler-to-PID launch lineage, and is NOT a permission for W29/W30 outage or cutover.

**Approved public implementation evidence (not proof of this user's particular process):**
- https://docs.python.org/3.15/library/venv.html explains that Windows venv uses redirectors for `python[w].exe`.
- https://github.com/python/cpython/blob/main/PC/venvlauncher.c shows the redirector reads the nearby `pyvenv.cfg` `home`, resolves the base Python executable and uses `CreateProcessW` with the original command line.

**W35 source-only compatible read-only gate:** On an otherwise exact owner/argv match, if `Win32_Process.ExecutablePath` differs from the original Task Action's venv launcher, read only the ORIGINAL `D:\UCIE\.venv\pyvenv.cfg`, its directory/launcher file and the `home/pythonw.exe` metadata. Require a single canonical absolute `home`, bounded config bytes, existing non-reparse regular executable and direct local paths, and exact case-insensitive equality between `home/pythonw.exe` and that specific TCP-owning PID's OS image. Unexpected executable, duplicate/absent/relative/oversized config, reparse, wrong SID/argv/PID or filename mismatches HOLD. No execution of the venv Python, no process restart, change of Task/DB/C40 or archive journal.

The output distinguishes `listener_binary_matches_original_task=false` and `listener_venv_base_pythonw_config_consistent=true` when the OS-reported image is the checked base executable. W35's precise status is `UCIE_W35_VENV_BASE_PYTHONW_CLI_OWNER_CONFIG_CONSISTENT__TASK_LAUNCH_LINK_HOLD`: consistency with Python's documented redirector model, NOT cryptographic binary attestation, genuine launch origin, C40 MCP roundtrip, database snapshot, or production cutover authorization. Existing direct-image case retains its original W31 status. Synthetic Windows and Ubuntu native tests use disposable first-party files and mocks only; actual owner W35 must be separately observed after final merged-source sync.

These are strictly read-only W31 checks. A HOLD is reason for review, NEVER to kill the unknown 18767 PID, change C40/tunnel, clear protected journals, or retry already-used W21/W24. Do not run W29 -RehearseOld or W30 -RecoverPartial/-ResumePartial on the current healthy owner PC.

## Future gates (all remain HOLD)

Actual Task Scheduler to listener PID launch trace; oldroot interruption/recovery full Windows acceptance; C40 MCP/tunnel real roundtrip; current writer-barrier ten-SQLite consistent image; separately approved W28 newroot data/task transaction; two newroot writers; full cutover.
