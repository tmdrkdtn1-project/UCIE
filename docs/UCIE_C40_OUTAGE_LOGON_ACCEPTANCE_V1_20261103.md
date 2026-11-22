# UCIE C40 recovery — outage and owner logon acceptance V1 (2026-11-03)

## Purpose and current evidence

This UCIE-only plan separates normal supervision from the still-unverified
loss-of-client and Windows logon recovery guarantees.

- Owner Windows observed the original C40 client (historically PID 57016) alone,
  the exact UCIE-C40-Recover task Running / Highest / Interactive, owner SID and
  action matching, with LastTaskResult 267009 meaning running, not exit success.
- Health receipts recorded four CYCLE_OK / UCIE_C40_ALREADY_RUNNING / clients=1
  events at 14:58:55, 15:03:55, 15:08:55 and 15:13:56 KST on November 3.
- Normal multi-cycle supervision PASS is not the same as recovery after a process
  disappears or owner logoff/logon. The two latter tests are **NOT RUN** here.
- No observed PID is authorization for future process termination; PID reuse is
  possible. Never use a saved PID as a kill instruction.

## Read-only acceptance, safe to repeat

1. Confirm the exact root task name and path, owner SID, expected Action,
   Highest/Interactive, Running state, exact approved UCIE client executable
   and profile, and **exactly one** client (cross-check process identity).
2. Read the bounded local supervisor receipt schema, stage, code and UTC time.
   Require a fresh CYCLE_OK with client_count=1, not merely an old success.
3. If the task is Running, do NOT rerun the disabled-only activation Preview
   or the one-time Apply. These are only applicable before initial activation.
4. Fail closed on unknown process identity, duplicate clients, absent or
   unreadable command line, stale receipt, PID mismatch, unexpected task owner,
   stopped/disabled task, or changes to the checked UCIE source SHA.
5. Inspect the GitHub PR's exact head and Windows/Ubuntu CI separately from
   Windows host evidence. No synthetic test is production PASS.

## Synthetic outage cases (no real process or task operations)

The test file tests/test_ucie_c40_loss_recovery_synthetic_v1.py extracts only
One-C40Check through the PowerShell AST and replaces process, task, timing,
authority and input functions with synthetic stubs. It covers:

- A missing client with owner authority, two independent empty censuses,
  one synthetic child start, confirmation after start, and environment restore.
- No owner authority -> no child, inputs untouched.
- Client appears at the second census -> abort before process start.
- Synthetic Start-Process failure -> exact exception and environment restore.
- Existing healthy client -> no redundant start.

These are **SYNTHETIC ONLY**, not real process-loss, reboot or logon tests.

## Controlled real outage acceptance — owner-gated, NOT executed

Prerequisites: deliberate one-time owner approval; current UCIE host backup
and rollback plan; verified exact client executable/profile/start time and
owner task identity; functioning alternate manual management access; an
uninterrupted maintenance window. Absence of any prerequisite is NO_GO.

At the approved maintenance time, the owner must use an independently
reviewed exact-scope procedure that does not target other projects or
unrelated tunnel clients. Do not construct process-kill instructions from
this document. Before any controlled fault, capture running supervisor
state and current UTC receipt. The fault is unsafe to inject if doing so
would sever the only recovery/control channel.

Expected evidence after an approved real client-loss test:
- One new C40 process with the exact executable/profile/owner, no duplicate.
- A new supervisor receipt CYCLE_OK / UCIE_C40_CHILD_STARTED and client_count=1,
  not an old CYCLE_OK / ALREADY_RUNNING receipt.
- A subsequent CYCLE_OK / ALREADY_RUNNING with client_count=1 after 5 minutes.
- Exact task still Running/Highest and bridge connectivity restored.
- Bounded failure codes and task/client counts if recovery does not occur.
A success receipt alone never substitutes for the real process census.

For logon recovery, use a naturally occurring owner interactive logon and
compare pre/post event time, exact task trigger, task state, new live client,
and fresh bounded receipt. Do not log off or reboot automatically and do
not infer logon PASS from the mere presence of an AtLogOn trigger.

Stop criteria: any unexpected/duplicate UCIE instance, stale or untrusted
receipt, wrong identity/SHA, unrelated process exposure or inadequate
rollback path. Preserve evidence, do not blindly retry or upgrade rules.

## Release decisions

STEADY_STATE: PASS only while contemporaneous host evidence supports it.
SYNTHETIC_LOSS_RECOVERY: PENDING_CI until exact-head CI succeeds.
REAL_LOSS_RECOVERY: NOT_RUN.
OWNER_LOGON_RECOVERY: NOT_RUN.
FULL_AUTORECOVERY_GO: NO_GO.
PR remains DRAFT. No automated rule promotion or additional MCP deployment.
