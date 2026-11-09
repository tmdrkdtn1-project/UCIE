# UCIE Local V1 owner-only auto-start installer: PREVIEW by default.
# Explicit -Apply installs one per-user logon Scheduled Task and requests start.
# Existing public miner, cloudflared, firewall and other projects are untouched.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch] $Apply,
    [ValidateRange(1024, 65535)]
    [int] $Port = 18767
)
$ErrorActionPreference = 'Stop'
$root = 'D:\UCIE'
$python = 'D:\UCIE\.venv\Scripts\pythonw.exe'
$consolePython = 'D:\UCIE\.venv\Scripts\python.exe'
$launcher = 'D:\UCIE\scripts\run_ucie_local_v1_autostart.py'
$taskName = 'UCIE-LocalV1-Web'
$taskPath = '\'
$arguments = '-B "' + $launcher + '" --port ' + $Port

if ($Port -eq 8767) { throw 'UCIE_AUTOSTART_LEGACY_8767_PORT_REJECTED' }
foreach ($path in @($python, $consolePython, $launcher, (Join-Path $root '.git'),
                    (Join-Path $root 'src'),
                    (Join-Path $root 'docs\UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md'))) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw ('UCIE_OWNER_ENVIRONMENT_MISSING: ' + $path)
    }
}
if (-not [Environment]::UserInteractive) {
    throw 'UCIE_INSTALL_REQUIRES_OWNER_INTERACTIVE_SESSION'
}
Import-Module ScheduledTasks -ErrorAction Stop
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
if ([string]::IsNullOrWhiteSpace($identity)) { throw 'UCIE_OWNER_IDENTITY_UNKNOWN' }

$existing = Get-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    $actions = @($existing.Actions)
    $isWindowless = [string]::Equals($actions[0].Execute, $python,
        [System.StringComparison]::OrdinalIgnoreCase)
    $isLegacyConsole = [string]::Equals($actions[0].Execute, $consolePython,
        [System.StringComparison]::OrdinalIgnoreCase)
    if ($actions.Count -ne 1 -or
        (-not $isWindowless -and -not $isLegacyConsole) -or
        $actions[0].Arguments -ne $arguments -or
        -not [string]::Equals($actions[0].WorkingDirectory, $root,
            [System.StringComparison]::OrdinalIgnoreCase) -or
        $existing.Principal.UserId -ne $identity) {
        throw 'UCIE_AUTOSTART_TASK_NAME_CONFLICT_NO_OVERWRITE'
    }
    if (-not $Apply) {
        if ($isLegacyConsole) {
            Write-Output 'UCIE_LOCAL_V1_CONSOLE_TASK_PREVIEW_USE_WINDOWLESS_MIGRATION'
        }
        else {
            Write-Output 'UCIE_LOCAL_V1_AUTOSTART_ALREADY_REGISTERED_PREVIEW_ONLY'
        }
        return
    }
    if ($isLegacyConsole) {
        throw 'UCIE_CONSOLE_TASK_USE_SET_UCIE_LOCAL_V1_WINDOWLESS_PS1'
    }
    if ($PSCmdlet.ShouldProcess($taskName, 'start existing verified UCIE task')) {
        if ($existing.State -ne 'Running') {
            Start-ScheduledTask -TaskName $taskName -TaskPath $taskPath
        }
        Write-Output 'UCIE_LOCAL_V1_AUTOSTART_ALREADY_REGISTERED_START_REQUESTED'
    }
    return
}

# Do not take over any process bound to the proposed stable localhost port.
$listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
if (@($listeners | Where-Object { $_.Port -eq $Port }).Count -gt 0) {
    throw ('UCIE_AUTOSTART_PORT_ALREADY_IN_USE_NO_CHANGES: ' + $Port)
}
if (-not $Apply) {
    Write-Output 'UCIE_LOCAL_V1_AUTOSTART_PREVIEW_ONLY_NO_CHANGES'
    Write-Output ('Proposed task: ' + $taskName)
    Write-Output ('Local URL: http://127.0.0.1:' + $Port + '/local')
    Write-Output ('Run with -Apply to register + start for current logged-on user: ' + $identity)
    return
}

$actionParams = @{
    Execute = $python
    Argument = $arguments
    WorkingDirectory = $root
}
$action = New-ScheduledTaskAction @actionParams
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
# A second trigger recovers after abnormal termination/restart-budget exhaustion.
# IgnoreNew prevents overlapping processes while the localhost app is running.
$recoveryTrigger = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(2)) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settingsParams = @{
    AllowStartIfOnBatteries = $true
    DontStopIfGoingOnBatteries = $true
    StartWhenAvailable = $true
    ExecutionTimeLimit = [TimeSpan]::Zero
    MultipleInstances = 'IgnoreNew'
    RestartCount = 3
    RestartInterval = (New-TimeSpan -Minutes 1)
}
$settings = New-ScheduledTaskSettingsSet @settingsParams
if ($PSCmdlet.ShouldProcess($taskName, 'register UCIE-only at-logon task and request start')) {
    $register = @{
        TaskName = $taskName
        TaskPath = $taskPath
        Action = $action
        Trigger = @($logonTrigger, $recoveryTrigger)
        Principal = $principal
        Settings = $settings
        Description = 'UCIE Local V1 only. Logon auto-start; private 127.0.0.1. No cloud/customer release.'
        ErrorAction = 'Stop'
    }
    Register-ScheduledTask @register | Out-Null
    Start-ScheduledTask -TaskName $taskName -TaskPath $taskPath -ErrorAction Stop
    Write-Output 'UCIE_LOCAL_V1_AUTOSTART_REGISTERED_START_REQUESTED_VERIFY_HEALTH_SEPARATELY'
    Write-Output ('Local URL: http://127.0.0.1:' + $Port + '/local')
}
