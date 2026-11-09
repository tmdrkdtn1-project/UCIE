# UCIE owner-only console -> windowless migration. Preview unless -Apply.
# Change ONLY the exact current-user UCIE-LocalV1-Web scheduled task action.
# Preserve triggers, identity, recovery settings, public miner and Cloudflare.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch] $Apply,
    [ValidateRange(1024, 65535)]
    [int] $Port = 18767
)
$ErrorActionPreference = 'Stop'
if ($Port -eq 8767) { throw 'UCIE_WINDOWLESS_LEGACY_PORT_REJECTED' }

$root = 'D:\UCIE'
$pythonConsole = 'D:\UCIE\.venv\Scripts\python.exe'
$pythonWindowless = 'D:\UCIE\.venv\Scripts\pythonw.exe'
$launcher = 'D:\UCIE\scripts\run_ucie_local_v1_autostart.py'
$taskName = 'UCIE-LocalV1-Web'
$taskPath = '\'
$expectedArgs = '-B "' + $launcher + '" --port ' + $Port

foreach ($path in @($pythonConsole, $pythonWindowless, $launcher,
        (Join-Path $root '.git'),
        (Join-Path $root 'runtime'),
        (Join-Path $root 'docs\UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md'))) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw ('UCIE_WINDOWLESS_OWNER_PATH_MISSING: ' + $path)
    }
}
if (-not [Environment]::UserInteractive) {
    throw 'UCIE_WINDOWLESS_INTERACTIVE_OWNER_REQUIRED'
}
Import-Module ScheduledTasks -ErrorAction Stop
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$task = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
$actions = @($task.Actions)
$actionCountMatches = ($actions.Count -eq 1)
$argumentsMatch = ($actionCountMatches -and $actions[0].Arguments -eq $expectedArgs)
$workingDirectoryMatches = ($actionCountMatches -and [string]::Equals(
    $actions[0].WorkingDirectory, $root, [System.StringComparison]::OrdinalIgnoreCase))
# TaskScheduler may return the same owner as a SID or an account name.
# Compare security identifiers, never merely the final username segment.
$principalMatches = $false
try {
    $taskPrincipalId = [string]$task.Principal.UserId
    if ($taskPrincipalId -match '^S-1-[0-9-]+
if (-not ($actionCountMatches -and $argumentsMatch -and
          $workingDirectoryMatches -and $principalMatches)) {
    throw ('UCIE_WINDOWLESS_TASK_IDENTITY_OR_ACTION_MISMATCH;' +
        ' action_count_ok=' + $actionCountMatches +
        ' arguments_ok=' + $argumentsMatch +
        ' working_directory_ok=' + $workingDirectoryMatches +
        ' principal_ok=' + $principalMatches)
}
$isConsole = [string]::Equals(
    $actions[0].Execute, $pythonConsole,
    [System.StringComparison]::OrdinalIgnoreCase)
$isWindowless = [string]::Equals(
    $actions[0].Execute, $pythonWindowless,
    [System.StringComparison]::OrdinalIgnoreCase)
if (-not $isConsole -and -not $isWindowless) {
    throw 'UCIE_WINDOWLESS_FOREIGN_EXECUTABLE_BLOCKED'
}
if ($isWindowless) {
    Write-Output 'UCIE_LOCAL_V1_ALREADY_WINDOWLESS_NO_CHANGES'
    Write-Output ('Local URL: http://127.0.0.1:' + $Port + '/local')
    return
}
if (-not $Apply) {
    Write-Output 'UCIE_WINDOWLESS_PREVIEW_ONLY_NO_CHANGES'
    Write-Output ('Verified task: ' + $taskName)
    Write-Output ('Current action: ' + $pythonConsole)
    Write-Output ('Proposed action: ' + $pythonWindowless)
    Write-Output 'Only this task action would change; existing triggers are preserved.'
    return
}
if (-not $PSCmdlet.ShouldProcess($taskName, 'switch exact UCIE task to pythonw.exe')) {
    return
}

$oldAction = $actions[0]
$wasRunning = ($task.State -eq 'Running')
$modified = $false
try {
    if ($wasRunning) {
        Stop-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
    }
    # Do not replace or kill a listener belonging to an unrelated process.
    $portReleased = $false
    for ($i = 0; $i -lt 20; $i++) {
        $listening = @([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
            Where-Object { $_.Port -eq $Port })
        if ($listening.Count -eq 0) {
            $portReleased = $true
            break
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $portReleased) {
        throw 'UCIE_WINDOWLESS_PORT_STILL_BUSY_ABORT_AND_RESTORE'
    }
    $newAction = New-ScheduledTaskAction -Execute $pythonWindowless -Argument $expectedArgs -WorkingDirectory $root
    Set-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Action $newAction -ErrorAction Stop | Out-Null
    $modified = $true
    $changed = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
    if (@($changed.Actions).Count -ne 1 -or
        -not [string]::Equals($changed.Actions[0].Execute, $pythonWindowless,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_WINDOWLESS_ACTION_POSTCHECK_FAILED'
    }

    Start-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
    $healthy = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $Port + '/local/health') -Method Get -TimeoutSec 2 -ErrorAction Stop
            $current = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath
            if ($current.State -eq 'Running' -and
                $health.schema -eq 'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01' -and
                $health.bound_host -eq '127.0.0.1' -and
                [int]$health.bound_port -eq $Port -and
                $health.owner_acceptance_verified -eq $true -and
                $health.online_release_authorized -eq $false) {
                $healthy = $true
                break
            }
        }
        catch {
            # Bounded retry of the specific owner's local health endpoint only.
        }
    }
    if (-not $healthy) {
        throw 'UCIE_WINDOWLESS_HEALTH_FAILED_ROLLBACK_REQUIRED'
    }
    Write-Output 'UCIE_LOCAL_V1_WINDOWLESS_APPLIED_AND_HEALTHY'
    Write-Output ('Local URL: http://127.0.0.1:' + $Port + '/local')
    Write-Output 'Windowless startup log: D:\UCIE\runtime\ucie_local_v1_windowless.log'
}
catch {
    $originalFailure = $_.Exception.Message
    $rollbackResult = 'NOT_NEEDED'
    try {
        if ($modified) {
            $currentTask = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath
            if ($currentTask.State -eq 'Running') {
                Stop-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
            }
            Set-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Action $oldAction -ErrorAction Stop | Out-Null
            $rollbackResult = 'ORIGINAL_ACTION_RESTORED'
        }
        if ($wasRunning) {
            Start-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
            $rollbackResult += '_RESTART_REQUESTED'
        }
    }
    catch {
        $rollbackResult = 'ROLLBACK_FAILED_REQUIRES_OWNER_REVIEW'
    }
    throw ('UCIE_WINDOWLESS_APPLY_FAILED: ' + $originalFailure + '; ' + $rollbackResult)
}
) {
        $principalSid = ([System.Security.Principal.SecurityIdentifier]::new(
            $taskPrincipalId)).Value
    }
    else {
        $principalSid = ([System.Security.Principal.NTAccount]::new(
            $taskPrincipalId)).Translate(
            [System.Security.Principal.SecurityIdentifier]).Value
    }
    $ownerSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $principalMatches = [string]::Equals(
        $principalSid, $ownerSid, [System.StringComparison]::OrdinalIgnoreCase)
}
catch {
    $principalMatches = $false
}
if (-not ($actionCountMatches -and $argumentsMatch -and
          $workingDirectoryMatches -and $principalMatches)) {
    throw ('UCIE_WINDOWLESS_TASK_IDENTITY_OR_ACTION_MISMATCH;' +
        ' action_count_ok=' + $actionCountMatches +
        ' arguments_ok=' + $argumentsMatch +
        ' working_directory_ok=' + $workingDirectoryMatches +
        ' principal_ok=' + $principalMatches)
}
$isConsole = [string]::Equals(
    $actions[0].Execute, $pythonConsole,
    [System.StringComparison]::OrdinalIgnoreCase)
$isWindowless = [string]::Equals(
    $actions[0].Execute, $pythonWindowless,
    [System.StringComparison]::OrdinalIgnoreCase)
if (-not $isConsole -and -not $isWindowless) {
    throw 'UCIE_WINDOWLESS_FOREIGN_EXECUTABLE_BLOCKED'
}
if ($isWindowless) {
    Write-Output 'UCIE_LOCAL_V1_ALREADY_WINDOWLESS_NO_CHANGES'
    Write-Output ('Local URL: http://127.0.0.1:' + $Port + '/local')
    return
}
if (-not $Apply) {
    Write-Output 'UCIE_WINDOWLESS_PREVIEW_ONLY_NO_CHANGES'
    Write-Output ('Verified task: ' + $taskName)
    Write-Output ('Current action: ' + $pythonConsole)
    Write-Output ('Proposed action: ' + $pythonWindowless)
    Write-Output 'Only this task action would change; existing triggers are preserved.'
    return
}
if (-not $PSCmdlet.ShouldProcess($taskName, 'switch exact UCIE task to pythonw.exe')) {
    return
}

$oldAction = $actions[0]
$wasRunning = ($task.State -eq 'Running')
$modified = $false
try {
    if ($wasRunning) {
        Stop-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
    }
    # Do not replace or kill a listener belonging to an unrelated process.
    $portReleased = $false
    for ($i = 0; $i -lt 20; $i++) {
        $listening = @([Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
            Where-Object { $_.Port -eq $Port })
        if ($listening.Count -eq 0) {
            $portReleased = $true
            break
        }
        Start-Sleep -Milliseconds 200
    }
    if (-not $portReleased) {
        throw 'UCIE_WINDOWLESS_PORT_STILL_BUSY_ABORT_AND_RESTORE'
    }
    $newAction = New-ScheduledTaskAction -Execute $pythonWindowless -Argument $expectedArgs -WorkingDirectory $root
    Set-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Action $newAction -ErrorAction Stop | Out-Null
    $modified = $true
    $changed = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
    if (@($changed.Actions).Count -ne 1 -or
        -not [string]::Equals($changed.Actions[0].Execute, $pythonWindowless,
            [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_WINDOWLESS_ACTION_POSTCHECK_FAILED'
    }

    Start-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
    $healthy = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $Port + '/local/health') -Method Get -TimeoutSec 2 -ErrorAction Stop
            $current = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath
            if ($current.State -eq 'Running' -and
                $health.schema -eq 'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01' -and
                $health.bound_host -eq '127.0.0.1' -and
                [int]$health.bound_port -eq $Port -and
                $health.owner_acceptance_verified -eq $true -and
                $health.online_release_authorized -eq $false) {
                $healthy = $true
                break
            }
        }
        catch {
            # Bounded retry of the specific owner's local health endpoint only.
        }
    }
    if (-not $healthy) {
        throw 'UCIE_WINDOWLESS_HEALTH_FAILED_ROLLBACK_REQUIRED'
    }
    Write-Output 'UCIE_LOCAL_V1_WINDOWLESS_APPLIED_AND_HEALTHY'
    Write-Output ('Local URL: http://127.0.0.1:' + $Port + '/local')
    Write-Output 'Windowless startup log: D:\UCIE\runtime\ucie_local_v1_windowless.log'
}
catch {
    $originalFailure = $_.Exception.Message
    $rollbackResult = 'NOT_NEEDED'
    try {
        if ($modified) {
            $currentTask = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath
            if ($currentTask.State -eq 'Running') {
                Stop-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
            }
            Set-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Action $oldAction -ErrorAction Stop | Out-Null
            $rollbackResult = 'ORIGINAL_ACTION_RESTORED'
        }
        if ($wasRunning) {
            Start-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
            $rollbackResult += '_RESTART_REQUESTED'
        }
    }
    catch {
        $rollbackResult = 'ROLLBACK_FAILED_REQUIRES_OWNER_REVIEW'
    }
    throw ('UCIE_WINDOWLESS_APPLY_FAILED: ' + $originalFailure + '; ' + $rollbackResult)
}
