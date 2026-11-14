# UCIE C40 recovery: verified access-level mismatch (2026-11-03)

**Scope:** UCIE owner-only C40, Draft PR #175, Issue #176. No other
project, tunnel, scheduler, source repo or operating DB is in scope.

## Current owner-host disposition

- Existing task `UCIE-C40-Recover` is **Disabled** (owner receipt and
  independent UCIE host test). Do not enable or start it yet.
- Existing UCIE-only ChatGPT admin MCP remains READY.
- Two same-profile tunnel clients were observed: PID 57016 (manual
  2026-11-02 06:31:20Z) and PID 53556 (task-spawned
  2026-11-02 07:45:35Z). These are historical observations; PID reuse
  and process exit MUST be checked before any owner-host action.

## Root cause backed by host evidence

The original UCIE-only manual tunnel client was launched with an elevated
Windows token. The auto-recovery task was registered with
`-LogonType Interactive -RunLevel Limited`.

Read-only UCIE-only `tests/test_ucie_c40_exact_pid_visibility_readonly.py`
compared **the same two preverified UCIE PIDs** in separate tool calls:

| Caller token | PID 53556 | PID 57016 |
|---|---|---|
| Non-elevated | ExecutablePath, CommandLine and native Process.Path readable | Process exists by exact PID, BUT those path/command-line properties are unavailable |
| Elevated | All same-file/profile properties readable | All same-file/profile properties readable |

Original `Find-C40` in `scripts/ucie_c40_recover.ps1` first issues the
WQL query `Win32_Process WHERE Name='tunnel-client.exe' AND ExecutablePath
LIKE '%UCIE_DATA%'`, then compares exact UCIE executable/profile.
The Limited task cannot reliably find the *already-running elevated C40*
through this property filter, so a false "absent" result can create a
second C40 client. The owner-host task's actual receipt records
`CYCLE_OK / UCIE_C40_CHILD_STARTED`; independent process inspection
then confirmed both UCIE PIDs.

A repeated WQL query alone **does not resolve an access-control mismatch**.
In additional ten-sample comparisons, one caller could see both UCIE
clients throughout, while another could see only PID 53556 throughout.
This is consistent with privilege-dependent property availability.
It is more precise than the earlier provisional "intermittent CIM query"
hypothesis; do not promote the earlier patch proposal.

Official reference:
- https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process
  (ExecutablePath privilege qualifier)
- https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights

## Required remediation before re-enabling

1. Keep the existing `UCIE-C40-Recover` task Disabled. No second
   plugin, tunnel ID, listener or startup task.
2. Choose and verify **one consistently observable UCIE owner integrity
   level**, not a mixture of elevated manual C40 and Limited supervisor.
   Candidate: owner-approved Highest-run-level version of the *existing*
   task, but only after explicit Windows owner approval and confirmation
   its principal actually has that elevation. The alternative is
   consistently non-elevated C40 startup with verified single-client
   ownership. Merely changing a Task Scheduler flag is not sufficient.
3. Preserve working ChatGPT connectivity and do an **exact UCIE-only**
   identity+creation-time+profile check before resolving the duplicate.
   Never blindly kill a PID by memory, process name or wildcard.
4. Fail closed on unreadable executable/profile properties, WMI access
   denial, unknown identity, inconsistent enumeration or multiple C40
   instances. No new C40 child may launch from an inconclusive snapshot.
5. Add synthetic regression for the *actual privilege split*: elevated
   existing UCIE client, Limited observer, process exists but its
   `ExecutablePath` and `CommandLine` are unreadable. Expected outcome
   is **NO START / OWNER REVIEW**, not "no client". Include a parallel
   owner-logon race test and exact one-client invariant.
6. Only after the owner host is down to one verified UCIE C40 and the
   launch gate has passed a real two-cycle Windows test may the owner
   re-enable `UCIE-C40-Recover`.
7. Keep scoped source-apply consent handlers out of the live C40 MCP
   until independent authentication, ACL and rollback host acceptance.

This document records evidence and an acceptance gate only. It does not
modify the scheduler, terminate any process, activate source application,
or claim automatic recovery PASS. The process-control source modification
previously attempted was blocked by tool safety screening and **was not
committed or installed**.

**Current status:** C40_CHATGPT_READY / RECOVERY_TASK_DISABLED /
DUPLICATE_CLIENT_EVIDENCED / PRIVILEGE_BOUNDARY_ROOT_CAUSE_SUPPORTED /
AUTO_RECOVERY_NO_GO.
