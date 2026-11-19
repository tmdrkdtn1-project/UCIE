# UCIE W27 — running-source SQLite metadata preflight + pre-rebind rollback safety

Date: 2026-11-19. Scope: first-party UCIE source and the user's existing `D:\UCIE` owner-owned operating environment. This does not authorize a live cutover, Task Scheduler change, Python process termination, private source code transmission, C40 restart, or alteration of any preserved W16–W26 evidence.

## Accepted owner Windows evidence prior to W27

- Isolated newroot `D:\UCIE_PROJECT\UCIE` pinned at `7e2442839fd4274940147ed7e5f14d4ee9d22b02` (W26).
- W26 owner `-CheckLocal` actual returned `UCIE_W26_REAL_HOST_W19_PATCHED_SAME_PASS__DISABLED_APPLY_NOT_REPLAYED`: all three original Task Scheduler Action objects match patched W19 pure Same function and exact owner SID, with PublicMiner=Ready, InternalMinute=Ready, LocalV1-Web=Running. No writer stop, SQLite open, journal write, C40 change.
- Original owner W22/W24/W21 intents, prior W22 restoration and W24 emergency restoration receipts remain private, immutable and one-shot. Old `D:\UCIE` LocalV1 and two writer schedules restored. W19/W13/W20 stage journals and newroot runtime were absent at last W25 owner read-only check.
- Original owner W21 nested exception was NOT captured; W25 simulated W19 `Same` false drift before fix, W26 actual current task-action check PASS. Historic actual root cause unproven, C40 MCP roundtrip unverified.

## W27 source-only improvement 1: no-outage metadata preflight

`scripts/ucie_owner_w27_source_metadata_readonly_v01.py`:
- Default returns `UCIE_W27_CONTRACT_ONLY_NO_HOST_ACCESS`; no host access, files, tasks, journal or DB opened.
- Exact owner-confirmed `--check-owner` requires interactive Windows Python 3.15, enabled local admin token and exact newroot venv. Pins Git remote, W26 source ancestor, unmodified W19 Python Git blob, clean staged checkout, canonical direct/non-reparse paths, and absence of newroot staged artifacts.
- Calls previously tested first-party W19 `_private_prerequisites()` solely to validate historical W14/W16/W18 private provenance and exact ten historical SQLite filenames (no operating DB opened).
- Uses only `Path.iterdir`, `lstat`/file metadata to confirm the live old-root runtime has exactly ten filenames, matching historical case-insensitive name set, and each is direct, non-reparse, allowed name, size between 512 bytes and 512 MiB. Does not inspect contents, compute hashes, take SQLite locks, run PRAGMA, call C40 or read task status. Normal writers remain active.
- Success `UCIE_W27_RUNNING_OLD_SOURCE_SQLITE_METADATA_MATCH__LOCKS_NOT_TESTED` means only metadata shape matches. It is NOT a fresh atomic snapshot, a verification of current DB integrity, DB SHA, lock availability, committed data freshness, or a live W19 handoff.
- Owner-reported metadata is private and is summarized by counts/total bytes; script does not output individual filename/path lists.
- CI synthetic coverage creates 10 small dummy files and proves correct-case accept, mismatched names/count and too small/large rejection, symlink/reparse rejection where available, no DB file content open, default no-host and approval denial.

## W27 source-only improvement 2: first-party pre-rebind rollback eligibility

`scripts/ucie_owner_w21_single_local_maintenance_v01.ps1`:
- Existing owner approval and one-shot private W21 intent checks stay unchanged. **This does not attempt a new W21 Apply.** Existing historical W21 journal from the failed W24 run must NOT be reused, deleted, copied or replaced.
- Previously the W21 `-RollbackLocal` stage threw `UCIE_W21_PRE_REBIND_PARTIAL_DATA_HOLD` whenever neither W20 pilot nor W13 rebind journal existed. That left already-Disabled original tasks unavailable to W22/W24 ResumeOld even if W19 had not written a journal or staged SQLite data.
- W27 adds `AssertPreRebindNoStage`, a conservative recovery gate for that exact early failure. It requires W19, W13, W20 and their rollback receipts, marker, private handoff output and newroot runtime to be **absent**, and exact original three task actions still **Disabled** with correct owner, plus identical C40 task action hash. Any residual staged file, action drift, wrong owner, unexpected task state or C40 drift -> HOLD before any new W21 rollback receipt. Existing W13/W20 rollback logic remains intact.
- On verified no-stage state, it records W21's **own** protected rollback receipt with `rollback_phase='W27_PRE_REBIND_ORIGINAL_DISABLED_NO_DATA_STAGE'`, `pre_rebind_no_w19_stage=true`, `new_private_sqlite_kept=false`. It does not edit tasks, open/copy SQLite, start LocalV1 or enable writers. A separately guarded enclosing W22/W24 `-ResumeOld` remains the only action that may start original old-root service, under its existing owner checks. Thus W21 can become a safe first step of a reviewed future maintenance recovery chain.
- This patch does NOT authorize calling legacy `W21 -RollbackLocal` or `W24 -ResumeOld` against the already-restored owner state. User is currently running old-root LocalV1 and collectors; the new guard would reject that state, and the old one-shot intents remain protected.
- W27 additionally avoids PowerShell's special variable `$args` when comparing exact W21 Action Arguments by using `$expectedArguments`.
- New native PowerShell CI tests extract production `AssertPreRebindNoStage` and `ActionEquals` AST functions to run ONLY on in-memory fake stage/tasks/C40. Positive empty stage passes; W19 partial stage, runtime residue, marker residue, original task mismatch or C40 drift rejects. Native parser and no-host/denied rollback approval also tested. CI NEVER executes owner `-RollbackLocal`, Task Scheduler mutations or the W19/W21 data handoff.

## Required future work before full cutover

1. Owner reads W27 no-outage SQLite metadata receipt; any mismatch is a blocker, not a request for destructive cleanup.
2. Future new one-shot migration design must use NEW transaction-specific protected journal names — existing W22/W24/W21 receipts are already occupied and MUST remain immutable.
3. Independently verify W21 pre-rebind rollback + enclosing old-root service recovery on synthetic end-to-end scenarios for interrupted W19 stages and host process-port collision, including owner SID/Task DACL and C40 source integrity.
4. Validate actual current SQLite lockstep snapshot under controlled user-approved maintenance only AFTER rollback design, and never treat W16 historical backups as current data.
5. C40 real MCP roundtrip, writer-task GO, full cutover and external deployment stay HOLD.

### Owner commands (only after PR CI 4/4 and merged pinned source)

```powershell
$root='D:\UCIE_PROJECT\UCIE'
$py=Join-Path $root '.venv\Scripts\python.exe'
$probe=Join-Path $root 'scripts\ucie_owner_w27_source_metadata_readonly_v01.py'

# No-host safe contract:
& $py -I -B $probe

# READ ONLY, same-owner elevated interactive PowerShell; no DB content open:
& $py -I -B $probe --check-owner --owner-approval 'AUTHORIZE_UCIE_W27_READONLY_RUNNING_SQLITE_SOURCE_METADATA'
```

**Do not run `-ApplyLocal`, `-RollbackLocal`, old W22/W24 maintenance modes, or any scheduler mutation.** This W27 scope is source-only plus future optional metadata inspection. No owner Windows W27 run was performed by the GitHub code PR.
