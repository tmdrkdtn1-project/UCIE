# UCIE ACG 05:00 daily local snapshot — source-only rollout
Date: 2026-11-26 KST. PROJECT=UCIE. Repository=tmdrkdtn1-project/UCIE.

Goal: take a committed-HEAD Git recovery reference daily at 05:00 local Windows time, when the owner generally is not developing. The absence of live development does NOT guarantee a clean working tree. Uncommitted or untracked files always HOLD; never silently claim to back them up.

New scripts:
- scripts/ucie_acg_daily_snapshot_v01.py: imports the preexisting ACG snapshot guard, checks exact UCIE repository identity and clean HEAD, creates refs/acg/snapshots/UCIE/daily_YYYYMMDD with explicit --run. Preview default. Existing same SHA is idempotent, existing different SHA is HOLD. Offset-aware KST date. No CI or remote push.
- scripts/install_ucie_acg_daily_snapshot_task_v01.ps1: read-only preview default; -Install creates only UCIE-ACG-DailySnapshot daily at 05:00 in Windows Task Scheduler. Current interactive user, least privilege, StartWhenAvailable catch-up, IgnoreNew and 5-minute limit. Existing task name blocks replacement. No immediate task launch. Existing public miner and all other Windows tasks unchanged.
- tests/test_ucie_acg_daily_snapshot_v01.py: disposable Git negative controls and timing/source checks.

IMPORTANT current owner Windows D:\UCIE was observed DIRTY through UCIE bridge. If it remains dirty at scheduled time, it records HOLD and captures NO daily Git ref. Committed SHA snapshot is NOT full worktree/SQLite/host backup. No automated commit, stash, reset, clean, checkout, secret copies, service restarts, scheduler activation or source uploads.

Source-only development does not itself install a task. The current UCIE Admin Bridge exposes scoped file writes but no unrestricted PowerShell or task registration API. Real host preflight, preview, -Install invocation and read-only Get-ScheduledTask verification are separate acceptance gates. An interactive logon token means missed work can be attempted after the task scheduler resumes only while the user is logged on; it does not power on a shut-down PC.

In an owner Windows PowerShell session after these files exist locally, execute:
  cd D:\UCIE
  .\scripts\install_ucie_acg_daily_snapshot_task_v01.ps1
  .\scripts\install_ucie_acg_daily_snapshot_task_v01.ps1 -Install
  Get-ScheduledTask -TaskName UCIE-ACG-DailySnapshot
  Get-ScheduledTaskInfo -TaskName UCIE-ACG-DailySnapshot

Do not claim Windows TASK_REGISTERED or 05:00 first execution until native receipt evidence exists. No local owner worktree modification from this GitHub Draft PR; no CI product acceptance, signing or release.
