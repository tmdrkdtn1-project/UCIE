# UCIE-only daily 05:00 task. Preview default; -Install only creates a distinct task.
[CmdletBinding()]
param([switch]$Install)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskName = 'UCIE-ACG-DailySnapshot'
$taskPath = '\'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) { throw 'UCIE_ROOT_MISMATCH' }
if ((Get-Item -LiteralPath $root).Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'UCIE_ROOT_REPARSE_POINT_DENIED' }
if (-not (Test-Path -LiteralPath (Join-Path $root '.git') -PathType Container)) { throw 'UCIE_GIT_CHECKOUT_REQUIRED' }
$python = Join-Path $root '.venv\Scripts\python.exe'
$worker = Join-Path $root 'scripts\ucie_acg_daily_snapshot_v01.py'
$guard = Join-Path $root 'scripts\ucie_acg_snapshot_guard_v01.py'
foreach ($path in @($python, $worker, $guard)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'REQUIRED_UCIE_FILE_MISSING' }
}
$installedVersion = (& $python --version 2>&1 | Out-String).Trim()
if (-not $installedVersion.StartsWith('Python 3.15')) { throw 'UCIE_PYTHON_315_REQUIRED' }
$existing = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue
if ($null -ne $existing) { throw 'EXISTING_UCIE_ACG_TASK_REFUSE_OVERWRITE' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Output "TASK_NAME=$taskName"
Write-Output 'SCHEDULE=DAILY_05_00_LOCAL_WINDOWS_TIME'
Write-Output 'MISSED_RUN=START_WHEN_AVAILABLE_IF_USER_LOGGED_ON'
Write-Output 'SCOPE=COMMITTED_CLEAN_HEAD_ONLY_NO_AUTO_COMMIT'
Write-Output 'TASKS_AND_DATABASES_UNTOUCHED=TRUE'
if (-not $Install) { Write-Output 'PREVIEW_ONLY_NO_TASK_CREATED'; return }
$action = New-ScheduledTaskAction -Execute $python -Argument ('-m scripts.ucie_acg_daily_snapshot_v01 --repo-root "' + $root + '" --run') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At '05:00'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'UCIE ACG committed-HEAD snapshot at 05:00 local; dirty worktree held' -ErrorAction Stop | Out-Null
$task = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
$info = Get-ScheduledTaskInfo -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
if ($task.Triggers.Count -ne 1 -or $task.Triggers[0].StartBoundary -notmatch 'T05:00:00') { throw 'TASK_REGISTERED_BUT_TRIGGER_VERIFY_FAILED_NO_SUCCESS_CLAIM' }
Write-Output 'TASK_REGISTERED_AND_TRIGGER_VERIFIED=TRUE'
Write-Output "TASK_STATE=$($task.State)"
Write-Output "NEXT_RUN_TIME=$($info.NextRunTime.ToString('o'))"
# No immediate Start-ScheduledTask, no task overwrite or scheduler adjustment.
