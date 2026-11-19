# W24 — owner restoration verified; UAC gate before maintenance journaling; isolated second attempt

Scope: UCIE-only Windows owner `D:\UCIE` and staged `D:\UCIE_PROJECT\UCIE`, protected `D:\UCIE_PROJECT\ARCHIVE`. NO C40 tunnel changes, no private project crossover, no old SQLite overwrites, no process kill, no release.

## Actual owner evidence received

- W22 first owner Apply failed at `Disable-ScheduledTask` with Windows `0x80070005` **after** writing W22 private intent. W21/W19 current data handoff was not reached.
- A non-elevated owner PowerShell then hit `UCIE_RECOVERY_ELEVATED_SAME_OWNER_REQUIRED` before any recovery mutation.
- Owner subsequently ran W22 `-ResumeOld` from appropriately elevated **same-owner** Windows account and returned:
  `UCIE_W22_ORIGINAL_SCHEDULES_RESTORED__HTTP_HEALTHY_PID_AND_C40_HOLD`.
  Receipt reported `original_writer_schedules_enabled=2`, `old_local_http_healthy=true`, `c40_action_unchanged=true`, `old_sqlite_unchanged_by_w22=true`, `full_cutover_authorized=false`. The LocalV1 listener PID/Task identity and C40 MCP end-to-end still unverified.
- W16/W18 original owner archive 10-DB / 5,656,576-byte historical snapshot/restore images were physically verified by user-provided read-only SHA256 and SQLite quick_check PASS, but are **NOT** a fresh, multi-DB global cutover snapshot.

## W24 source repair

Existing entrypoint remains `scripts/ucie_owner_w22_quiesce_resume_local_v01.ps1` (no duplicated 400-line wrapper). W24 introduces new optional `-RecoveredAttempt` switch, with **two new private W24 journal filenames and explicit owner approval strings**, plus a high-priority UAC guard.

1. For EVERY mutating W22/W24 mode, assert `WindowsPrincipal.IsInRole(Administrator)` after user-interactive/approval checks, and **before** archive access, Task Scheduler query, intent file creation or task disable. UAC admin rights do not guarantee individual task DACL permissions; any unexpected access denial still stops, preserves journal and requires recovery review.
2. The original W22 apply/rollback mode is unchanged in terms of journal filename, owner-only service scope and C40/DB boundary, except that a non-elevated token is now rejected before any mutation. **Never reuse** an old completed W22 intent by deleting it.
3. With `-RecoveredAttempt`, first read/validate existing W22 original intent + restoration receipts (both direct paths, original recorded owner SID hash, original three task names/states, original C40 action SHA against current C40 task action, previous LocalV1 HTTP health, both original writers re-enabled, W22 original DB not overwritten and full live cutover still false).
4. Use fresh one-shot protected private W24 intent `UCIE_W24_OWNER_RECOVERED_RETRY_INTENT_V01.json` and independent W24 restore receipt `UCIE_W24_OWNER_RECOVERED_RETRY_RESTORED_V01.json`. W22 original intent and restoration receipts **stay in place byte-for-byte**.
5. W24 Apply still verifies the *current* original three task actions and Ready/Ready/Running states, C40 Task Running, LocalV1 loopback HTTP health, W14/W16/W18 provenance W23 Python file, canonical clean repository and absence of W19/W20/W21 outputs BEFORE writing W24 intent, then disables only exact original three UCIE tasks and stops only UCIE LocalV1 Scheduled Task. It does not inspect/kill unknown port owner. If 18767 stays listening, HOLD, no fresh data handoff and **three tasks may remain Disabled**.
6. Only a free 18767 listener allows delegating W21's latest ten-SQLite W19 locked copy and new LocalV1-only W20 pilot. Two writer tasks remain Disabled and C40/MCP/online GO remain HOLD. No non-SQLite global snapshot guarantee.
7. W24 Resume via the new mode validates its distinct W24 protected intent, delegates W21/W20/W19 exact action rollback if necessary, attempts restoring old LocalV1 only when safe, re-enables original two writers and stores W24-specific private restoration receipt. A foreign/unknown still-listening Python process, partial W21 state or security ACL may leave tasks Disabled and demand owner review.

**Important:** W24 does not guarantee zero downtime or automatic recovery. CI cannot exercise Windows owner Task Scheduler DACL, real database writer quiescence, unknown listener PID ownership, or C40 end-to-end.

## Owner safety contract (reference only; not run by CI)

```powershell
# Safe no-host contract: reads no task, archive or SQLite.
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w22_quiesce_resume_local_v01.ps1' -RecoveredAttempt -ContractOnly

# Future explicit owner maintenance only. Do NOT run without pinned SHA,
# same-owner UAC-elevated PowerShell, maintained current states, recovery access.
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w22_quiesce_resume_local_v01.ps1' -RecoveredAttempt -ApplyLocal -OwnerApproval 'AUTHORIZE_UCIE_W24_OWNER_RECOVERED_RETRY_LOCAL_ONLY'

# Only if W24 private intent exists and host incident status was assessed.
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w22_quiesce_resume_local_v01.ps1' -RecoveredAttempt -ResumeOld -OwnerApproval 'AUTHORIZE_UCIE_W24_OWNER_RECOVERED_RETRY_RESUME_OLD'
```

No owner PC operation was performed through GitHub. Never run old W22 `-ApplyLocal` after W22 recovery journal exists. Existing evidence is not a global production cutover.
