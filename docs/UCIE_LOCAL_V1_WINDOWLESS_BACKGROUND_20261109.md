# UCIE Local V1 — Windowless Automatic Startup
**2026-11-09 KST. Owner Windows only. No public release.**

## Goal

The owner confirmed Microsoft Edge displays the local page. The remaining UX issue is the visible black Python console launched by the Windows UCIE-LocalV1-Web scheduled task.

This changes only the action of that exact task from the UCIE virtualenv python.exe to pythonw.exe, which runs without a Windows console. The task's existing user, at-logon and recovery triggers, startup retry settings, low-privilege execution and localhost address stay unchanged.

This guide does NOT mean the currently running scheduled task has been migrated yet. A separate one-time owner operation is necessary.

## Owner's one-time commands

Use a regular non-administrator PowerShell under the same account that registered the UCIE task.

1. Show the action migration plan (NO CHANGES):

       & D:\UCIE\scripts\set_ucie_local_v1_windowless.ps1

   Expected: UCIE_WINDOWLESS_PREVIEW_ONLY_NO_CHANGES. If a task principal, path, arguments or working-directory check fails, stop and review instead of overriding it.

2. Explicit one-time apply:

       & D:\UCIE\scripts\set_ucie_local_v1_windowless.ps1 -Apply

   The script verifies the same Windows owner SID and exact action, stops only the UCIE-LocalV1-Web task, checks the fixed private port was released, changes only the task's launch action, starts it using pythonw, then validates the real local health response. If the change fails, it attempts to restore the original action and relaunch it. This rollback attempt is NOT proof of successful recovery; inspect status on any error.

   Successful output: UCIE_LOCAL_V1_WINDOWLESS_APPLIED_AND_HEALTHY

3. Confirm real task and app status without making changes:

       & D:\UCIE\scripts\status_ucie_local_v1_autostart.ps1

   Expected: task_state=Running; task_action_matches_exact_ucie=true; windowless_background_mode=true; console_mode=false; health=UCIE_LOCAL_V1_HEALTHY; app_schema=UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01. A running task can show last_task_result=267009 (normal).

The browser URL stays:

    http://127.0.0.1:18767/local

## Private log and troubleshooting

The windowless process has no visible console. Its UCIE-only standard output and errors are redirected to:

    D:\UCIE\runtime\ucie_local_v1_windowless.log

This log is created only after the exact owner venv and UCIE root checks pass. If the private page does not respond, inspect the read-only status and that UCIE-only log before attempting any restart. Do not terminate unknown processes or reset the operating SQLite database.

The original autostart installer uses pythonw for NEW installations, but deliberately does not auto-convert an already registered python.exe action. The exact old task is converted only with the separate explicit migration script. The original remove-task script recognizes both valid versions for safe opt-out.

## Limits and separate work

An interactive task stays available only while the owner has an active Windows session and the PC is powered and awake. It does not run while the PC is off, does not expose a mobile endpoint, and is not an online commercial release.

Actual owner Windows tests exercise the real pythonw on a temporary separate private localhost port and then terminate the test server, leaving the real 18767 process untouched. Source tests and GitHub CI alone do not prove the visible console has already disappeared. A true operator apply and read-only health check are needed.

Separately observed invalid UCIE public candidate review-ledger integrity errors remain unresolved. Do not auto-repair provenance, approve rules or change the public miner to fix console window behavior.

No paid hosting, public Cloudflare tunnel, data export, operating DB writes, other-project access or customer deployment is authorized.

Official docs:
- https://docs.python.org/3/using/windows.html
- https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/set-scheduledtask

UCIE roadmap and separate release hold: https://github.com/tmdrkdtn1-project/UCIE/issues/199
