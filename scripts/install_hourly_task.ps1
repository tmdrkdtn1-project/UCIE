# UCIE-owned Windows Task Scheduler installer.
# Runs one small public-source collection cycle hourly; current-user / least privilege.
# Never registers any task for another project and never modifies another task.
[CmdletBinding()]
param([switch]$Install, [switch]$QuietExisting)

$ErrorActionPreference = 'Stop'
$taskName = 'UCIE-PublicMiner-Hourly'
$taskPath = '\'
$scriptRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
$root = $scriptRoot
# Preview PR78 may manage ONLY the exact preexisting D:\UCIE task, never
# install one in the preview tree or modify any other scheduled task.
if ($QuietExisting -and [string]::Equals(
        $scriptRoot, 'D:\UCIE_PREVIEW\UCIE_ADMIN',
        [StringComparison]::OrdinalIgnoreCase)) {
    $root = 'D:\UCIE'
}
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'EXPECTED_UCIE_ROOT_D_DRIVE'
}
if ((Get-Item -LiteralPath $root).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
    throw 'SYMLINKED_UCIE_ROOT_NOT_ALLOWED'
}
if (-not (Test-Path -LiteralPath (Join-Path $root '.git') -PathType Container)) {
    throw 'UCIE_GIT_CHECKOUT_NOT_FOUND'
}

$python = Join-Path $root '.venv\Scripts\python.exe'
$worker = Join-Path $root 'scripts\public_miner_cycle.py'
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_VENV_PYTHON_MISSING'
}
if (-not (Test-Path -LiteralPath $pythonw -PathType Leaf)) {
    throw 'UCIE_VENV_PYTHONW_MISSING_NO_TASK_CHANGE'
}
if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) {
    throw 'UCIE_WORKER_MISSING'
}
$version = (& $python --version 2>&1 | Out-String).Trim()
if (-not $version.StartsWith('Python 3.15')) {
    throw "UCIE_REQUIRES_PYTHON_315_IN_VENV (installed: $version)"
}
$existing = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
if ($QuietExisting -and $Install) {
    throw 'UCIE_QUIET_EXISTING_AND_INSTALL_ARE_MUTUALLY_EXCLUSIVE'
}
if ($QuietExisting) {
    # Only this already-installed UCIE task may be converted, preserving
    # user principal, hourly trigger, limits and every other setting.
    if ($null -eq $existing) {
        throw 'UCIE_HOURLY_TASK_NOT_REGISTERED_NO_CHANGE'
    }
    $actions = @($existing.Actions)
    $expectedArgs = '"' + $worker + '"'
    if ($actions.Count -ne 1 -or
        -not [string]::Equals([string]$actions[0].Arguments, $expectedArgs,
            [StringComparison]::Ordinal) -or
        -not [string]::Equals(([string]$actions[0].WorkingDirectory).TrimEnd('\'),
            $root, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_HOURLY_TASK_ACTION_NOT_EXACT_NO_CHANGE'
    }
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $userId = [string]$existing.Principal.UserId
    if ([string]::IsNullOrWhiteSpace($userId)) {
        throw 'UCIE_HOURLY_TASK_OWNER_MISSING_NO_CHANGE'
    }
    try {
        $taskSid = if ($userId -match '^S-[0-9]+-[0-9]+(-[0-9]+)+$') {
            [System.Security.Principal.SecurityIdentifier]::new($userId)
        } else {
            ([System.Security.Principal.NTAccount]::new($userId)).Translate(
                [System.Security.Principal.SecurityIdentifier])
        }
    } catch {
        throw 'UCIE_HOURLY_TASK_OWNER_UNRESOLVED_NO_CHANGE'
    }
    if (-not $taskSid.Equals($sid) -or
        [string]$existing.Principal.LogonType -ne 'Interactive' -or
        [string]$existing.Principal.RunLevel -ne 'Limited' -or
        [string]$existing.Settings.MultipleInstances -ne 'IgnoreNew') {
        throw 'UCIE_HOURLY_TASK_PRINCIPAL_OR_POLICY_MISMATCH_NO_CHANGE'
    }
    $intervals = @($existing.Triggers | ForEach-Object { [string]$_.Repetition.Interval })
    if ($intervals.Count -ne 1 -or $intervals[0] -ne 'PT1H') {
        throw 'UCIE_HOURLY_TASK_CADENCE_MISMATCH_NO_CHANGE'
    }
    $oldExe = [string]$actions[0].Execute
    if ([string]::Equals($oldExe, $pythonw, [StringComparison]::OrdinalIgnoreCase)) {
        Write-Output 'UCIE_HOURLY_TASK_WINDOWLESS_ALREADY_CONFIGURED'
        return
    }
    if (-not [string]::Equals($oldExe, $python,
        [StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_HOURLY_TASK_FOREIGN_EXECUTABLE_NO_CHANGE'
    }
    if ([string]$existing.State -eq 'Running') {
        throw 'UCIE_HOURLY_TASK_ACTIVE_NO_CHANGE_RETRY_AFTER_CYCLE'
    }
    # Re-read action before making a single update, no scheduling changes.
    $fresh = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
    if (@($fresh.Actions).Count -ne 1 -or
        -not [string]::Equals([string]$fresh.Actions[0].Execute,
            $python, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_HOURLY_TASK_CHANGED_BEFORE_UPDATE_NO_CHANGE'
    }
    $quietAction = New-ScheduledTaskAction -Execute $pythonw -Argument $expectedArgs -WorkingDirectory $root
    Set-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Action $quietAction -ErrorAction Stop | Out-Null
    $verify = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
    if (-not [string]::Equals(
        [string]@($verify.Actions)[0].Execute, $pythonw,
        [StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_HOURLY_TASK_QUIET_UPDATE_NOT_VERIFIED'
    }
    Write-Output 'UCIE_HOURLY_TASK_WINDOWLESS_ACTION_UPDATED'
    Write-Output 'TASK_RESTARTED=FALSE'
    Write-Output 'TRIGGER_OR_PRINCIPAL_CHANGED=FALSE'
    return
}
if ($null -ne $existing) {
    throw 'UCIE_SCHEDULE_ALREADY_EXISTS_REFUSE_OVERWRITE'
}
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Output "UCIE_ROOT=$root"
Write-Output "PYTHON=$version"
Write-Output "TASK_NAME=$taskName"
Write-Output "TASK_USER=$identity"
Write-Output 'SCHEDULE=HOURLY_CURRENT_USER_ONLY'
Write-Output 'MINING_STATUS=UNVERIFIED_CANDIDATES_ONLY'
Write-Output 'NO_PROJECT_ACCESS=ENFORCED_BY_PUBLIC_SOURCE_ALLOWLIST'
if (-not $Install) {
    Write-Output 'PREVIEW_ONLY: run .\scripts\install_hourly_task.ps1 -Install to register this UCIE-only task.'
    return
}

$action = New-ScheduledTaskAction -Execute $pythonw -Argument ('"' + $worker + '"') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
# Interactive + limited means no stored password, no SYSTEM or elevation.
# Runs only while this user has an interactive session; sleeping/logged-out PCs do not mine.
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'UCIE public third-party PR candidate miner; stores only unverified local metadata' -ErrorAction Stop | Out-Null
Write-Output 'TASK_REGISTERED=TRUE'
Start-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
Write-Output 'IMMEDIATE_RUN_REQUESTED=TRUE'
Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName |
    Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskPath $taskPath -TaskName $taskName |
    Select-Object LastRunTime, NextRunTime, LastTaskResult
