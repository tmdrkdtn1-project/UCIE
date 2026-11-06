# UCIE PublicMiner Hourly: scheduler termination triage and NO_GO gates
Date: 2026-11-05 (KST). Scope: UCIE only, approved public-source collector.

## Exact owner-PC observation (read only)

Original owner report at 2026-11-05T05:50:51Z:
- Legacy PR candidates = 359 (python/cpython=349, PowerShell/PowerShell=10).
- Legacy recorded runs = 491; Stage10 PR revisions = 126; Stage12 review proposals = 811.
- Latest cycle receipt finished 2026-11-05T05:37:19Z (14:37:19 KST).
- Two fresh local collection receipts were readable.
- TaskScheduler status = LAST_TASK_RESULT_NO_GO.
- Exact TaskScheduler event-to-receipt matches = 1 of required 2. NOT PASS.

A second UCIE Admin owner-only direct host probe read ONLY the exact
UCIE-PublicMiner-Hourly root scheduled task:
- State = Ready; LastTaskResult=267014 decimal / 0x00041306.
- Official Microsoft code SCHED_S_TASK_TERMINATED: last scheduled-task run terminated.
- Do not infer which human/process/OS policy caused termination.

A third UCIE Admin fixed-task-only Operational event probe observed:
- 2026-11-05T04:37:10Z -> 04:37:19Z: action 200->201, ResultCode=0.
- 2026-11-05T05:37:10Z -> 05:47:10Z: action 200->201,
  ResultCode=2147943691 / 0x8007050B (nonzero).
- The second task's collector completion receipt nevertheless finished at
  05:37:19Z, about 9 seconds after task start.
- Task Settings.ExecutionTimeLimit = PT10M (10 minutes).
- StopIfGoingOnBatteries=true, DisallowStartIfOnBatteries=true.
- TaskScheduler/Operational event history readable; latest IDs include
  102, 201, 200, 100, 107. Event 111 not seen in the bounded sample.

Interpretation: an observed problematic scheduled-action lifecycle, NOT a
failed public candidate inventory. The ~600 s action duration matches the
configured 10-minute execution limit exactly: timeout termination is a strong
HYPOTHESIS. The Python process remaining alive after the completion receipt,
and WHY (interpreter exit, child thread, process shutdown, OS termination or
something else), is NOT PROVEN. The nonzero 201 ResultCode is verbatim
evidence, not a unique TaskScheduler timeout code.

Official docs:
https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-error-and-success-constants
https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/get-scheduledtaskinfo
https://learn.microsoft.com/en-us/troubleshoot/windows-server/system-management-components/troubleshoot-scheduled-tasks-not-running

## Bundled implementation

1. src/ucie_miner/public_scheduler_diagnostic_v01.py: strict typed
   LastTaskResult and event-proof classifier. Maps 0x00041301 RUNNING,
   0x00041306 TERMINATED, but never returns GO without two task-bound events.
2. scripts/ucie_public_miner_scheduler_diagnostic_v01.ps1: exact owner task
   ScheduledTasks read-only query + existing task_status.ps1 -Evidence,
   returns sanitized machine-readable JSON with numeric result and blockers.
3. scripts/ucie_public_miner_task_event_triage_v01.ps1: bounded
   Get-WinEvent XPath for exact UCIE task only, recent event IDs, times,
   ResultCode, at most 64 retrieved / 24 returned. No raw messages,
   account identity, action command or events from other tasks.
4. scripts/ucie_public_collection_report_v01.ps1: now includes exact
   task_scheduler.last_task_result_decimal, _hex, _interpretation, task_state
   and blocker_codes, while keeping independent public DB candidate counts.
5. Synthetic regression and owner-only executable acceptance tests. CI
   checkouts outside exact D:/UCIE SKIP the owner-local execution tests.

Read-only commands on exact owner Windows PC:

    & 'D:\UCIE\scripts\ucie_public_collection_report_v01.ps1'
    & 'D:\UCIE\scripts\ucie_public_miner_scheduler_diagnostic_v01.ps1'
    & 'D:\UCIE\scripts\ucie_public_miner_task_event_triage_v01.ps1'

## Next owner-gated steps NOT done

- Verify if termination recurs for the exact UCIE task, using next naturally
  scheduled attempts without manually running or changing the collector.
- Determine if the Python process truly remains running after writing a
  completion receipt, with separately approved exit instrumentation.
- Review exact task execution time limit / battery policy / action settings
  before proposing any change, and retain failing incident evidence.
- Do not simply increase task limit, replace/enable task, kill processes,
  auto-reschedule, fetch extra API data or run production as a synthetic test.
- Require two NEW exact TaskScheduler instances with 100/200/201/102
  matching identifiers and zero 201 action return codes before scheduler GO.
- A later success does not erase this termination incident.

Safety: no public DB migration, operating DB write, TaskScheduler mutation,
new recurring task, autonomous learning/model update, source promotion,
other project access, production release or MCP server registration.
