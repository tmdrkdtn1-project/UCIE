# UCIE C40 owner loss-drill V1 — independent recovery safety note

Scope: UCIE ONLY. This is a deliberately disruptive controlled test of the
**existing** UCIE C40 client, never a normal maintenance operation. PR #175
remains DRAFT, no automatic rule promotion.

## Independent recovery paths

1. The Windows Scheduled Task \UCIE-C40-Recover runs the existing supervisor
   under the interactive owner / Highest context and checks every 300 seconds.
   That task and supervisor are independent of the ChatGPT C40 connection.
2. If the task is still Running and the UCIE client is missing, the owner can
   use elevated Windows PowerShell locally (not through ChatGPT MCP):
   \`& 'D:\UCIE\scripts\ucie_c40_recover.ps1' -Mode Once -EnableAdminTools\`
   This is conditional manual recovery: registered task identity and owner
   authority must pass, and duplicate-client checks can stop execution.
3. If the supervisor is not Running, or the owner session has logged off,
   this Once mode is not an unconditional recovery mechanism. Get the exact
   task state/owner/trigger and repair only with separately reviewed,
   authorized local procedures. DO NOT blindly run the activation Apply
   script against a Running task.

## Safe preflight

The new \`scripts/ucie_c40_owner_loss_drill_once.ps1\` defaults to read-only
\`-Mode Preview\`. The preview checks exact root task Running/Highest/
Interactive, owner SID/elevated context, action and logon trigger, pinned
source SHA, existing UCIE-only process identity, and fresh CYCLE_OK health.
It does not stop/start a process, change a task, or touch databases.

## One-time real fault test (NOT executed by ChatGPT)

Only from a local elevated owner PowerShell session in which the operator can
keep the window open after the UCIE tunnel disconnects:

\`& 'D:\UCIE\scripts\ucie_c40_owner_loss_drill_once.ps1' -Mode Preview\`

After independently reviewing the printed preflight and ensuring continued
local console access, the owner can decide whether to run:

\`& 'D:\UCIE\scripts\ucie_c40_owner_loss_drill_once.ps1' -Mode Apply -OwnerOnlyConfirmed\`

Enter \`UCIE_C40_LOSS_ONE_TIME\` at the local consent prompt. The tool checks
the owner, exact task/source/client again after consent, creates a single-use
journal, terminates only its verified matching UCIE client, and *does not*
spawn a replacement itself. It observes the independent Windows supervisor
for a new identity and a fresh \`CYCLE_OK/UCIE_C40_CHILD_STARTED\` receipt,
then records result in:
\`D:\UCIE\.ucie_bridge_state\c40_owner_loss_drill_v1.json\`

Any duplicate client, stale receipt, changed PID/start time or unexpected
process causes FAIL-CLOSED. If recovery is absent/unproven, the owner must
review the task state before attempting the separate Once manual recovery.
ChatGPT cannot guarantee an automatic fallback because the C40 tunnel itself
is the remote control path. Do not close the owner PowerShell window during
the test. Do not run Apply more than once.

## Status vocabulary

- \`SIMULATED_5_PASS\`: synthetic unit tests only.
- \`PREVIEW_HOST_PASS\`: no disruption, checks initial local prerequisites.
- \`AUTO_RESTART_OBSERVED\`: owner-local test observed new process and child
  receipt. *Not* independent proof ChatGPT plugin is reachable.
- \`MCP_RECONNECTED_VERIFIED\`: independently re-query UCIE tools after restart.
- \`OWNER_LOGON_ACCEPTANCE\`: separate real logoff/logon test, never inferred
  from an AtLogOn trigger.
- \`FULL_AUTORECOVERY_GO\`: prohibited until both real outage and real logon
  acceptance pass. No production change merely from CI PASS.

No other project, UCIE task or operating database should be modified.
