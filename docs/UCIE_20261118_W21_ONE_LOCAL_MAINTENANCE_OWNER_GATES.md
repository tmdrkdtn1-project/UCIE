# UCIE W21: one owner-only local maintenance wrapper (2026-11-18)

**STATUS: SOURCE/CHECKOUT PREPARATION ONLY. Owner D-drive execution and live cutover NOT authorized or observed.**

## Why W21 exists

W19 already supplies exact final-ten-SQLite handoff and three Disabled scheduled task action rebinding. W20 already supplies preactivation ten-DB drift rejection plus a LocalV1-only start/health/rollback pilot. The owner requested a bounded, non-repetitive operational step instead of more W15-W18 backup rehearsals.

W21 **orchestrates W19 and W20 exactly once under one explicit owner-only Windows action** while preserving their independent fail-closed gates and private journals. It does not independently authenticate the C40 tunnel/MCP plugin roundtrip and does not switch the two writer tasks on.

File: `scripts/ucie_owner_w21_single_local_maintenance_v01.ps1`.

## Non-mutating default

Invoking without mutation parameters yields `UCIE_W21_CONTRACT_ONLY_NO_HOST_ACCESS`. CI verifies this mode and rejects `-ApplyLocal` or `-RollbackLocal` without their **different exact** owner approval phrases, before reading Windows Tasks, C40 or SQLite.

## Exact owner Windows prerequisites, NOT checked by GitHub CI

- Fresh first-party UCIE checkout at exact direct `D:\UCIE_PROJECT\UCIE` must contain W19, W20 and W21 scripts from the reviewed Git ancestor at or above W20 `5a996565b828e88dfd3dffa78662bb6182e6c5ec`. No forced `git pull`, reset, clean, or overwrite of owner-modified files. W17 owner venv prepared receipt and W18 private restore remain as previously reported, not repeated.
- `D:\UCIE_PROJECT\ARCHIVE` has owner SID and protected ACL; all existing paths are direct (no junction/symlink/reparse). No existing W19/W20/W21 journal, marker, staged runtime or private W19 final data directory. If an existing output or partial state is found, STOP; **never repeat or delete**.
- The three exact original UCIE Python scheduled tasks must have been separately **quiesced and Disabled** by the verified owner maintenance process; prior `Running` or `Ready` on GitHub or in old screenshots is not proof they are now stopped. W21 intentionally does not forcibly stop old writer tasks or unrelated processes. Their exact original action/owner SID is checked again before any data access.
- C40 task action and owner SID are hash-checked, but this is **not** proof of its active connection, one-client invariant or authenticated plugin roundtrip. No C40 profile contents are read and no tunnel restart is made.
- Confirm old-root non-SQLite writers and other UCIE services are quiesced by the owner maintenance gate. The W19 SQLite writer-barrier alone does not prove a permanently consistent cutoff across all artifacts. Unknown owners, extra DBs, changed DBs, busy writer locks or stale manifests force HOLD.
- This local-only stage affects the machine and should run only after a specifically approved maintenance window, **not automatically based on passing CI**. Source availability and permission do not imply live GO.

## Stage logic (owner-approved later)

1. Fail-closed checks owner Windows identity, paths, protected archive, W20 Git ancestor, three Disabled *old* task actions and unchanged C40 task-action SHA-256.
2. Persists a unique private W21 intent before any SQLite access or task changes.
3. Delegates existing W19 `-Apply`: verified W16/W18 lineage, ten-database SQLite writer-lock handoff, private copy and new-root runtime, W13 reversible rebind of the three Python actions while **Disabled**.
4. Delegates existing W20 `-PilotLocal`: recheck source-vs-staged SQLite drift, enable/start **only** `UCIE-LocalV1-Web` on fixed loopback `127.0.0.1:18767`, validate exact owner LocalV1 health response. Checks C40 task action SHA again. PublicMiner and Internal-Minute remain **Disabled**.
5. Reports `UCIE_W21_LOCAL_ONLY_HEALTHY__WRITERS_AND_C40_HOLD` only after these local checks. It never reports customer GO, complete cutover, active C40 tunnel or independent MCP proof.
6. On error: preserve original DB and private partial state, do not automatically retry/re-copy/rollback. A *separately approved* `-RollbackLocal` delegates W20 rollback (if its intent exists), otherwise W19 task-action rollback (if W13 journal exists), and restores original **Disabled** actions. If W19 had only partially copied data before W13 journal, manual owner review is mandatory. Old DB is never overwritten with an old backup.

## Commands — reference only, **NOT a current instruction to run**

**No-host source contract** (can be CI-tested):

```powershell
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w21_single_local_maintenance_v01.ps1'
```

The following modes are deliberately withheld from automatic execution. Use only after exact SHA/code review, original-root writer quiescence, source/owner ACL checks and a separate explicit owner maintenance approval:

- `-ApplyLocal -OwnerApproval AUTHORIZE_UCIE_W21_SINGLE_FINAL_DATA_AND_LOCALV1_MAINTENANCE`
- `-RollbackLocal -OwnerApproval AUTHORIZE_UCIE_W21_SINGLE_LOCAL_MAINTENANCE_ROLLBACK`

**Not yet implemented or accepted:** two writer-task activation, authenticated UCIE C40/MCP roundtrip proof, live tunnel client count and binding, full Windows host maintenance / rollback acceptance, customer release. The connected UCIE bridge returning `UCIE_LOCAL_ADMIN_BRIDGE_READY` proves only a bounded API reachability observation at a time, never the C40 endpoint or tunnel identity.

## Source and CI acceptance

The CI checks native PowerShell parsing, contract-only behavior, explicit approval denial, ordering (owner intent → W19 data/Disabled actions → W20 local pilot), C40 action hash checks, two writer tasks disabled, restricted rollback delegate and forbidden automation/cleanup operations. The CI cannot execute real Windows Task Scheduler operations or prove owner-host runtime/MCP health. A source/CI PASS must not be reported as owner apply, full cutover or acceptance.

**NEXT GATE**: owner maintenance window, quiesced original UCIE writers, staged new checkout update and owner W21 apply receipt; independent C40/plugin roundtrip plus the two writer-task activation with a separately proven source/target data-consistency window, not another W15-W18 rehearsal.
