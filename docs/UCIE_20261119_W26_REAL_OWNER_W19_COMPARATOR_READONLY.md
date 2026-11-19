# UCIE W26 — verified old-root restore and W19 real-owner task comparator (READ ONLY)

Date: 2026-11-19. Scope: first-party UCIE Windows owner three known old tasks and existing pinned `D:\UCIE_PROJECT\UCIE` checkout only. No private source transfer, unrelated projects, C40/tunnel changes, Windows scheduled-task mutation, SQLite open/copy, data migration or service stop.

## Source-backed recovery status

The owner physically fast-forwarded new-root source to W25 main `b5f3d05db9c2dd13e23a066c96a5c73dda5a2920`. Owner-reported W25 receipt:

- `UCIE_W25_CONTRACT_ONLY_NO_HOST_ACCESS` — no host queries or writes.
- `UCIE_W25_RUNNING_OLD_ROOT_PREREQUISITES_VERIFIED__W19_DISABLED_PREJOURNAL_NOT_REPLAYED` — protected archive and prior W22/W24/W21 recovery journals PASS, original three task owner/action checks PASS, W19 source and ancestry PASS, old LocalV1 health PASS, absent W19/W13/W20 pilot/SQLite stage and newroot runtime PASS. Source reports `root_cause_verified=false`, `operating_sqlite_opened=false`, `task_or_c40_modified=false`, `journal_written=false`, `c40_mcp_round_trip_verified=false`, `full_cutover_authorized=false`.
- Prior emergency restore `UCIE_W24_PRE_REBIND_ORIGINAL_SERVICE_RESTORED` confirms original LocalV1 HTTP healthy, both old collector schedules re-enabled, original SQLite not overwritten by recovery, C40 action unchanged. Normal subsequent old-root collector writes can occur.

The original Windows W24/W21 internal error was masked. Disposable CI W25 reproduced an exact-match false `UCIE_W19_TASK_ACTION_DRIFT_HOLD` via PowerShell `Same`/`ConfirmThree` functions and fixed automatic `$args` binding and indexed Action forwarding. This is not proof that the hidden owner exception was precisely that bug.

## W26: test REAL host Task action against actual patched W19 pure function, no outage

Script `scripts/ucie_owner_w26_real_task_action_check_v01.ps1`:

- Default `-ContractOnly`: no filesystem, Task Scheduler, C40, HTTP, port, journal or DB access.
- Explicit `-CheckLocal` requires SAME owner Windows SID, UAC-elevated enabled Admin token, owner-protected UCIE archive and direct non-reparse first-party source paths.
- Verifies first-party canonical GitHub remote and W25 ancestral commit, **exact pinned W19 Git blob** `17e1620659c15a570313c4d87fa425227f076839`, and clean local new-root checkout. Never mutates Git history or worktree.
- Uses PowerShell language parser to extract **only** the `function Same` AST from pinned W19 file, verifies one function and exact expected signature/body marker, then invokes that pure function on the THREE actual owner `Get-ScheduledTask` Action objects while tasks continue running, verifying exact original execute path, arguments and working directory plus owner identity. Does not dot-source the W19 main owner maintenance script.
- Accepts expected original states `Ready/Ready/Running`, permitting a writer task to temporarily report `Running`. Does not require or cause `Disabled` state and does not attempt W19 Apply.
- Emits `UCIE_W26_REAL_HOST_W19_PATCHED_SAME_PASS__DISABLED_APPLY_NOT_REPLAYED` only if all three actual task action comparisons return true. If any drift, FAIL CLOSED before any mutation.
- It **does not** prove full W19 disabled-state prejournal success or historical owner W21 inner exception; it keeps both false. No protected journal write or rollback.

### Owner commands, only AFTER PR CI/merge and exact pinned clean checkout update

```powershell
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w26_real_task_action_check_v01.ps1' -ContractOnly

# Explicitly approved read-only owner action in same-user elevated PowerShell:
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w26_real_task_action_check_v01.ps1' -CheckLocal -OwnerApproval 'AUTHORIZE_UCIE_W26_READONLY_PATCHED_W19_HOST_ACTION_COMPARISON'
```

No user action has been executed by ChatGPT; CI verifies only disposable PowerShell parser/default denial/native W19 AST and in-memory Action fixture.

## Critical owner operational hold

Do **NOT** invoke existing `W21 -ApplyLocal` or `W24 -RecoveredAttempt -ApplyLocal`: original one-shot private W22/W24/W21 journals remain and cannot be reused/deleted. A future local migration requires a new independently reviewed maintenance+rollback transaction with:
1. Observable bounded W19 pre-journal checks before stopping current LocalV1 or disabling writers;
2. No change to C40/tunnel, and exact owner task action/ACL guarantees;
3. A fresh full SQLite handoff after known writers quiesce;
4. A proven automatic old-root pre-rebind restoration path when no W13/W20 journal exists;
5. Complete separate private receipts / immutable prior journal retention;
6. Actual C40 MCP roundtrip and new-root writer activation acceptance later, never inferred from CI.

Current decision: original D:\UCIE service continues. LIVE_CUTOVER=HOLD.
