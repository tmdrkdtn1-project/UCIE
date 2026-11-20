# UCIE W36 — TaskScheduler event 129 / LocalV1 redirector parent PID (READ ONLY)

Date: 2026-11-20. UCIE FIRST PARTY ONLY. Source-only synthetic-CI milestone.
**NOT a production transition, Task launch attestation, C40 MCP proof, or outage/recovery authorization.**

## Prior owner Windows evidence (separate W35)
After the user synced merged main `846fbcb0e69efdb76115d83773f7e4af28193f54`,
the actual same-owner W35 read-only output was:

`UCIE_W35_VENV_BASE_PYTHONW_CLI_OWNER_CONFIG_CONSISTENT__TASK_LAUNCH_LINK_HOLD`

Actual W35 booleans true: exact old three Task Action/state checks,
historical protected receipts preserved/validated, old LocalV1 HTTP health,
sole 127.0.0.1:18767 listener with stable PID, same owner SID, exact old
Task Action command line, old virtualenv pyvenv.cfg matches actual base
Python 3.15 image, C40 *task action hash* unchanged.

Actual W35 booleans false: listener direct image equals Task executable
(expected CPython Windows venv redirector difference), TaskScheduler-to-
listener actual launch linkage, independent Task-to-PID proof, C40 MCP
roundtrip, full cutover authorization. W35 did not open operating SQLite,
start/stop processes, change tasks/C40 or write journals. This evidence
does not prove the current PID is unchanged at a later W36 probe.

## Official source anchors
- Microsoft Win32_Process ParentProcessId and CreationDate:
  https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process
  — parent PIDs can outlive or be reused, therefore parent PID alone cannot prove lineage.
- Microsoft official Task Scheduler Operational log troubleshooting:
  https://learn.microsoft.com/en-us/troubleshoot/windows-server/system-management-components/troubleshoot-scheduled-tasks-not-running
- Microsoft PowerShell Get-WinEvent FilterHashtable / MaxEvents:
  https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent
- Microsoft Q&A Task Scheduler event 129 process-ID metadata:
  https://learn.microsoft.com/en-us/answers/questions/1637770/how-to-fix-shorter-run-in-task-scheduler-in-window
- Approved python/cpython v3.15.0 `PC/venvlauncher.c` blob
  `b6bb0218236ae9ddf725fe7f74370e21c59534a8`.
  The venv redirector launches a base interpreter via CreateProcessW,
  preserving the original command line.

## W36 owner-approved read-only probe
First-party script:
`scripts/ucie_owner_w36_task129_parent_event_readonly_v01.ps1`

- Default `-ContractOnly` accesses NO host files, services, events, TaskScheduler,
  SQLite, private archives or C40.
- `-InspectLocal` requires exact explicit owner approval, interactive Windows
  and the canonical first-party checkout. It checks clean Git and the
  **exact W35 script Git blob** `b6420a1b00336d62907440078947a50ffbc3af51`.
- Imports only two reviewed W35 pure helper functions (PowerShell AST),
  not the side-effectful W31/W35 script body. Reads the exact original
  LocalV1 task definition/state, owner SID, one loopback 18767 listener,
  its one filtered CIM process PID, exact task CLI, owner SID, W35 base-image
  path and Windows process CreationDate and ParentProcessId.
- Queries **only** the existing Microsoft-Windows-TaskScheduler/Operational
  channel, event ID 129, within a four-minute window around that
  listener's creation time, maximum 128 events. Event XML must have
  the exact provider/channel/event ID and unambiguous TaskName/Path/ProcessID.
  A match needs the original task name, original venv pythonw.exe
  executable, a PID equal to the listener's reported parent PID,
  and event time from two seconds *after* to 60 seconds *before* listener creation.
- Requires one and only one match. Re-reads that same port/PID, CreationDate
  and ParentProcessId to catch simple rebinding. Never enables event history
  or security process creation auditing; missing/rotated log, unsupported
  XML, ambiguity or changed process -> HOLD with no changes or retries.
- Does not read unrelated service state or task history, scan other process
  PIDs, open SQLite, connect to C40, send user data externally or write
  a journal. No scheduler modification, service restart, recovery, rollback
  or change to original `D:\UCIE`.

If correlated, the result is only:
`UCIE_W36_TASK129_PARENT_PID_TIME_CORRELATED__LAUNCH_NOT_ATTESTED`.
Even this result says
`listener_pid_launched_by_task_scheduler_verified=false`,
`parent_process_creation_independently_attested=false`, and
`c40_mcp_round_trip_verified=false`. Task event 129 plus a current
parent PID and close timestamp are bounded **correlation**, NOT immutable
parent/child process creation evidence. Windows Security 4688 or an
equivalent preexisting trustworthy process-creation record would require
a different independently approved gate. Never enable missing logs merely
to make this check pass.

## Acceptance
Only after final PR head Windows/Ubuntu × Python 3.13/3.15 CI 4/4 PASS
may the W36 source merge. Synthetic testing does not grant an actual
owner-host receipt. Only a separately executed exact pinned owner
`-InspectLocal` read-only result can be recorded as W36 host evidence.
All W29/W30 mutations, writer barrier/data transfer, C40 MCP roundtrip,
customer release and complete production cutover remain HOLD.
