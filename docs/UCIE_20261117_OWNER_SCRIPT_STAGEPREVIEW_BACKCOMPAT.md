# UCIE 2026-11-17 — owner script backward-compatible staged path preview

UCIE-only. This changes NO active Windows tasks, C40 MCP plugin/tunnel, operating DB or owner files. The owner D:\UCIE checkout still has 20 modified and 210 untracked records, so **no git pull/reset/clean/checkout** on that live tree.

## Real user-facing script delta

Three existing first-party Windows scripts have a new optional `-StagePreview` switch:

- `scripts/bootstrap_local.ps1`: normal `-Setup` behavior and strict `D:\UCIE` requirement are unchanged.
- `scripts/install_hourly_task.ps1`: old scheduled task registration remains opt-in `-Install` and exact `D:\UCIE` only; no existing task is overwritten.
- `scripts/install_internal_minute_task.ps1`: old P10 minute dispatcher registration remains opt-in `-Install` and exact `D:\UCIE` only.

Each script now supports a **read-only code-stage check** when its own path is structurally nested under `UCIE_PROJECT\UCIE\scripts`, with direct, non-reparse `UCIE_PROJECT`, `UCIE`, `scripts` and script-file checks. For isolated runner tests the parent may be a temporary path; on owner Windows the intended location is `D:\UCIE_PROJECT\UCIE\scripts`. No global D: enumeration, operating database open, Git checkout, venv import, scheduler query/start/registration, C40 profile access or browser/service launch is needed in this code-stage preview.

Example after an owner-approved code-only stage exists (NOT yet created in D:\ drive):

```powershell
powershell.exe -NoProfile -NonInteractive -File 'D:\UCIE_PROJECT\UCIE\scripts\bootstrap_local.ps1' -StagePreview
powershell.exe -NoProfile -NonInteractive -File 'D:\UCIE_PROJECT\UCIE\scripts\install_hourly_task.ps1' -StagePreview
powershell.exe -NoProfile -NonInteractive -File 'D:\UCIE_PROJECT\UCIE\scripts\install_internal_minute_task.ps1' -StagePreview
```

All three print `UCIE_STAGE_PREVIEW_ONLY_NO_SETUP_OR_TASK_MUTATION`, the staged code path, and `LIVE_ROOT_CUTOVER_AUTHORIZED=FALSE`. Invoking `-StagePreview -Setup`, `-StagePreview -Install`, or calling the scripts from an unrelated parent fails closed. **Calling the relocated script without `-StagePreview` still rejects nonlegacy roots.** This is deliberate: an approved path cutover and a working live scheduler/tunnel binding are separate future events.

## Actual Windows runner QA

New `tests/test_ucie_owner_stagepreview_backcompat_v01.py` copies precisely these three scripts to a disposable `<runner temp>/UCIE_PROJECT/UCIE/scripts` with no `.git`, `runtime`, `.venv` or bridge state; Windows Python3.13/3.15 actually invokes `powershell.exe -NoProfile -NonInteractive -File ... -StagePreview` three times, tests mutation flag denial, wrong parent, strict legacy behavior without the flag, and native PowerShell parser. Ubuntu runs all static contracts and skips only Windows-specific actual PowerShell execution. Test harness checks script SHA256 and a sentinel for no mutation. PR exact-head 4/4 CI and named test logs, not static review alone, determine acceptance.

## Remaining real host dependencies / rollback

Existing C40 tunnel profile/client and owner-admin registration live outside source and may have old absolute paths; LocalV1 auto-start scripts have additional old-root paths. These scripts have **not** been changed by this PR. The exact four UCIE Task actions and current C40 one-client PID/SID, private profile/ACLs, operating DB backups and **230 owner dirty files** have NOT been independently validated or migrated on the owner PC.

Next: owner-approved empty `D:\UCIE_PROJECT` staging with explicit ACL/path checks, pin/backup owner dirty files and known runtime receipts, apply isolated code copy (not live Git clone), run PR #304 source search smoke plus these PowerShell previews, and only then draft a separate controlled cutover with rollback. No symlink/junction deception. Do not migrate live .venv/runtime or attempt automatic cleanup/`git gc`. PublicMiner HTTP403 and P11 job6 REVIEW_REQUIRED5/5 remain hold; customer V1 release NO-GO.

STATUS=UCIE_STAGE_PATH_PREVIEW_BACKCOMPAT_DEVELOPMENT_ONLY__LIVE_TASK_MCP_UNCHANGED__OWNER_D_DRIVE_NOT_MIGRATED__V1_NO_GO