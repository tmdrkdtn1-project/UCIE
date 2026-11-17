# UCIE-owned Windows Task Scheduler installer.
# Runs one small public-source collection cycle every 10 minutes; current-user / least privilege.
# Never registers any task for another project and never modifies another task.
[CmdletBinding()]
param([switch]$Install, [switch]$StagePreview)

$ErrorActionPreference = 'Stop'
$taskName = 'UCIE-PublicMiner-Hourly'
$taskPath = '\'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
# Optional source portability preview ONLY. Never permits a new owner runtime
# task, Python environment, Git checkout, database or C40 tunnel cutover.
# The current D:\UCIE default/Install/Setup behavior below is unchanged.
if ($StagePreview) {
    if ($Install) { throw 'UCIE_STAGE_PREVIEW_MUTATING_ACTION_DENIED' }
    $parent = Split-Path -Path $root -Parent
    if (-not [string]::Equals((Split-Path -Path $root -Leaf), 'UCIE',
        [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals((Split-Path -Path $parent -Leaf), 'UCIE_PROJECT',
        [StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_STAGE_PREVIEW_EXACT_HIERARCHY_REQUIRED'
    }
    foreach ($path in @($parent, $root)) {
        $entry = Get-Item -LiteralPath $path -Force -ErrorAction Stop
        if (-not $entry.PSIsContainer -or
            (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw 'UCIE_STAGE_PREVIEW_INDIRECT_PATH_DENIED'
        }
    }
    Write-Output 'UCIE_STAGE_PREVIEW_ONLY_NO_SETUP_OR_TASK_MUTATION'
    Write-Output ('STAGED_CODE_ROOT=' + $root)
    Write-Output 'GIT_VENV_RUNTIME_MCP_TUNNEL_NOT_INSPECTED_OR_MODIFIED'
    Write-Output 'LIVE_ROOT_CUTOVER_AUTHORIZED=FALSE'
    return
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
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_VENV_PYTHON_MISSING'
}
if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) {
    throw 'UCIE_WORKER_MISSING'
}
$version = (& $python --version 2>&1 | Out-String).Trim()
if (-not $version.StartsWith('Python 3.15')) {
    throw "UCIE_REQUIRES_PYTHON_315_IN_VENV (installed: $version)"
}
$existing = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    throw 'UCIE_SCHEDULE_ALREADY_EXISTS_REFUSE_OVERWRITE'
}
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Output "UCIE_ROOT=$root"
Write-Output "PYTHON=$version"
Write-Output "TASK_NAME=$taskName"
Write-Output "TASK_USER=$identity"
Write-Output 'SCHEDULE=EVERY_10_MINUTES_CURRENT_USER_ONLY'
Write-Output 'MINING_STATUS=UNVERIFIED_CANDIDATES_ONLY'
Write-Output 'NO_PROJECT_ACCESS=ENFORCED_BY_PUBLIC_SOURCE_ALLOWLIST'
if (-not $Install) {
    Write-Output 'PREVIEW_ONLY: run .\scripts\install_hourly_task.ps1 -Install to register this UCIE-only task.'
    return
}

$action = New-ScheduledTaskAction -Execute $python -Argument ('"' + $worker + '"') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(3) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650)
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
