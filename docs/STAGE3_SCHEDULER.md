# UCIE Stage 3 — local hourly collection scheduler

## What this implementation does

- Runs the existing tiny **anonymous, allowlisted public-GitHub PR sampler** once every hour.
- Stores deduplicated UNVERIFIED_CANDIDATE_ONLY metadata in local SQLite, not Git.
- Generates a local daily Markdown candidate-count report and atomically writes \`runtime/last_run.json\`.
- Appends limited per-run receipts to \`runtime/run_history.jsonl\`.
- Blocks simultaneous runs using both Windows Task Scheduler's IgnoreNew policy and an OS-held file lock.
- Uses only the signed-in Windows user's limited process token, never SYSTEM or admin privileges.
- Records no upstream raw code or exception messages in receipts.
- Does **not** train LLM weights, prove bug fixes, promote Rulepacks, share project data, or publish private files.

**Important:** The scripts do not create or read any user-project folder, connector or account. A local-only installation on a PC shared with other projects is not equivalent to independently tested OS-level sandbox isolation. Run the worker with restricted account/ACLs for stronger guarantees.

## Installation on the validated Windows PC

From PowerShell:

~~~powershell
git -C D:\UCIE pull --ff-only
Set-Location D:\UCIE
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\scripts\install_hourly_task.ps1
.\scripts\install_hourly_task.ps1 -Install
.\scripts\task_status.ps1
~~~

- Run from the D:\UCIE checkout created for UCIE only.
- Default installer is **preview-only**; it registers only with \`-Install\`.
- Refuses to overwrite an existing task or change a non-UCIE task.
- Requires the current UCIE virtual environment to be Python 3.15.
- The task repeats hourly for ten years from installation and does not require scheduled-task admin privileges in the typical current-user configuration.
- The first run is requested on registration; the next one is scheduled approximately one hour after the initial scheduled trigger.
- It runs only while the user is logged on, the PC is on/awake, and network access is available. No hidden password is saved.
- The action has a 10-minute time limit and Task Scheduler ignores overlapping invocations.

If PowerShell script execution is blocked by local policy, do not disable system-wide protection merely for UCIE; inspect and use an approved, signed script execution policy.

## Stored data

~~~text
D:\UCIE\runtime\
  public_miner.sqlite3  # original local DB, not git tracked
  last_run.json         # latest safe run receipt
  run_history.jsonl     # append-only safe result receipts
  public_miner.lock     # transient OS-held lock
  reports\YYYY-MM-DD.md # candidate counts; no project data
~~~

\`runtime/\` is excluded from Git via .gitignore. Back up this directory to a separate permitted location if permanent durability is required; GitHub does not back it up.

## Read-only status and removal

~~~powershell
Set-Location D:\UCIE
.\scripts\task_status.ps1
Get-Content .\runtime\reports\2026-10-13.md
.\scripts\remove_hourly_task.ps1
# To uninstall the exact UCIE scheduler only:
.\scripts\remove_hourly_task.ps1 -Remove
~~~

Uninstalling the task **does not** delete the local database, reports, or source checkout.

## What remains before production status

- Python 3.15 tests on the user's updated checkout and actual scheduled run receipts.
- Privilege/network boundary review for a shared host.
- Corpus licensing / deletion / opt-out process and wider publicly owned source approval.
- Measured quota/rate limit/backoff and full restore/restart behavior.
- Independent real-code test verification, rule promotion gate, read-only reporting connector.
- GitHub synchronization of safe, approved summaries only; raw DB must remain local.

An installed *collection* scheduler is not a validated independent *learning* engine yet.
