# UCIE-only C40 reconnect at Windows owner logon, checked every five minutes.
# One existing tunnel only. Other projects, jobs, databases and tasks untouched.
[CmdletBinding()]
param(
    [ValidateSet('Status','Install','Supervise','Once','Remove')]
    [string]$Mode = 'Status',
    [switch]$OwnerOnlyConfirmed,
    [switch]$EnableAdminTools
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$taskName = 'UCIE-C40-Recover'
$scriptPath = 'D:\UCIE\scripts\ucie_c40_recover.ps1'
$clientExe = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$profile = 'D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml'
$health = 'D:\UCIE_DATA\mcp_tunnel_profiles\c40_health.url'
$serverFile = 'D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py'
$expectedServerSha = '83b58b68ad0c15a32991e03e82b3c309a5e045da1d4c9a4c8ca3101d8b010d8e'
$mcpPython = 'D:\UCIE_DATA\.venv_mcp\Scripts\python.exe'
$librarySrc = 'D:\UCIE_PREVIEW\UCIE\src'
$adminSrc = 'D:\UCIE_PREVIEW\UCIE_ADMIN\src'
$libraryApp = 'D:\UCIE_DATA\library_app'
$ownerMarker = 'UCIE_PRIVATE_READONLY_APPROVED'
$psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'

function Find-C40 {
    # No other project's process command line is inspected.
    $found = @(Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
        Where-Object { [string]::Equals([string]$_.ExecutablePath, $clientExe, [StringComparison]::OrdinalIgnoreCase) })
    if ($found.Count -gt 1) { throw 'UCIE_C40_DUPLICATE_CLIENT_STOP' }
    foreach ($p in $found) {
        if (([string]$p.CommandLine).IndexOf('ucie-private-c40',[StringComparison]::OrdinalIgnoreCase) -lt 0) {
            throw 'UCIE_C40_UNRECOGNIZED_CLIENT_STOP'
        }
    }
    return @($found)
}
function Verify-C40Inputs {
    foreach ($path in @($scriptPath,$clientExe,$profile,$serverFile,$mcpPython,$librarySrc,$adminSrc,$libraryApp)) {
        if (-not (Test-Path -LiteralPath $path)) { throw 'UCIE_C40_REQUIRED_INPUT_MISSING' }
    }
    if ((Get-FileHash -LiteralPath $serverFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedServerSha) {
        throw 'UCIE_C40_SERVER_SHA_CHANGED_STOP'
    }
    if ((Get-Item -LiteralPath $serverFile).Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw 'UCIE_C40_SERVER_LINK_STOP'
    }
    $raw = [IO.File]::ReadAllText($profile)
    if ($raw.Length -gt 150000 -or -not $raw.Contains('mcp_stdio_server')) {
        throw 'UCIE_C40_PROFILE_UNEXPECTED_STOP'
    }
    $ids = @([regex]::Matches($raw, 'tunnel_[0-9a-fA-F]{32}') |
        ForEach-Object { $_.Value.ToLowerInvariant() } | Select-Object -Unique)
    $raw = $null
    if ($ids.Count -ne 1) { throw 'UCIE_C40_PROFILE_ID_NOT_UNIQUE_STOP' }
    return $ids[0]
}
function One-C40Check {
    # PowerShell bare -StartMissing is valid only for [switch], not [bool].
    param([switch]$StartMissing)
    $items = @(Find-C40)
    if ($items.Count -eq 1) {
        return [pscustomobject]@{status='UCIE_C40_ALREADY_RUNNING';started=$false;tunnel_clients=1}
    }
    if (-not $StartMissing) {
        return [pscustomobject]@{status='UCIE_C40_NOT_RUNNING';started=$false;tunnel_clients=0}
    }
    # Fail closed when a non-elevated caller cannot inspect an elevated C40.
    # The only launch authority is the original owner's Running Highest task.
    Assert-C40LaunchAuthority
    $id = Verify-C40Inputs
    # Reject a C40 appearing after the first process census, before launch.
    if (@(Find-C40).Count -ne 0) { throw 'UCIE_C40_CLIENT_APPEARED_ABORT_LAUNCH' }
    $oldApproval = $env:UCIE_MCP_OWNER_APPROVAL
    $oldId = $env:UCIE_MCP_TUNNEL_ID
    $oldFlag = $env:UCIE_ADMIN_TOOLS_ENABLED
    $oldPath = $env:PYTHONPATH
    try {
        $env:UCIE_MCP_OWNER_APPROVAL = $ownerMarker
        $env:UCIE_MCP_TUNNEL_ID = $id
        $env:UCIE_ADMIN_TOOLS_ENABLED = if ($EnableAdminTools) { '1' } else { '0' }
        $env:PYTHONPATH = @($librarySrc,$adminSrc,$libraryApp) -join ';'
        $args = @('run','--profile-file',('"' + $profile + '"'),
            '--control-plane.tunnel-id',$id,'--health.url-file',('"' + $health + '"'))
        $child = Start-Process -FilePath $clientExe -ArgumentList $args -WorkingDirectory 'D:\UCIE' -WindowStyle Hidden -PassThru -ErrorAction Stop
        if ($null -eq $child -or $child.Id -lt 1) { throw 'UCIE_C40_CLIENT_START_FAILED' }
    }
    finally {
        $env:UCIE_MCP_OWNER_APPROVAL = $oldApproval
        $env:UCIE_MCP_TUNNEL_ID = $oldId
        $env:UCIE_ADMIN_TOOLS_ENABLED = $oldFlag
        $env:PYTHONPATH = $oldPath
    }
    Start-Sleep -Seconds 2
    $observed = @(Find-C40)
    if ($observed.Count -ne 1 -or $observed[0].ProcessId -ne $child.Id) {
        throw 'UCIE_C40_START_NOT_OBSERVED'
    }
    return [pscustomobject]@{status='UCIE_C40_CHILD_STARTED';started=$true;tunnel_clients=1}
}
function Get-C40Task {
    return (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue)
}
function Assert-ApprovedRecoveryTask {
    $task = Get-C40Task
    if ($null -eq $task -or @($task.Actions).Count -ne 1) {
        throw 'UCIE_C40_REGISTERED_TASK_REQUIRED'
    }
    $action = $task.Actions[0]
    # Compare canonical SIDs, not a Task Scheduler SID with a DOMAIN\\user name.
    $identitySid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $principalId = [string]$task.Principal.UserId
    try {
        if ($principalId -match '^S-1-[0-9]+(?:-[0-9]+)+$') {
            $taskSid = $principalId
        }
        else {
            $taskSid = ([Security.Principal.NTAccount]::new($principalId)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
    }
    catch {
        throw 'UCIE_C40_TASK_PRINCIPAL_UNRESOLVED'
    }
    if (-not [string]::Equals($taskSid,$identitySid,[StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals([string]$action.Execute,$psExe,[StringComparison]::OrdinalIgnoreCase) -or
        ([string]$action.Arguments).IndexOf($scriptPath,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or
        ([string]$action.Arguments).IndexOf('-Mode Supervise',[StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw 'UCIE_C40_TASK_OWNER_OR_ACTION_MISMATCH'
    }
    $registeredAdmin = ([string]$action.Arguments).Contains('-EnableAdminTools')
    if ([bool]$EnableAdminTools -ne $registeredAdmin) {
        throw 'UCIE_C40_ADMIN_MODE_MISMATCH'
    }
    return $task
}
# Limited callers cannot reliably inspect the elevated original tunnel.
function Assert-C40LaunchAuthority {
    $task = Assert-ApprovedRecoveryTask
    if ([string]$task.State -ne 'Running' -or
        [string]$task.Principal.RunLevel -ne 'Highest' -or
        [string]$task.Principal.LogonType -ne 'Interactive') {
        throw 'UCIE_C40_LAUNCH_REQUIRES_RUNNING_HIGHEST_TASK'
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'UCIE_C40_ELEVATED_OWNER_REQUIRED_FOR_LAUNCH'
    }
}
# Bounded UCIE-only supervisor heartbeat. No raw error messages, tokens or IDs.
function Save-C40SupervisorReceipt {
    param([string]$Stage,[string]$Code='NONE',[int]$Count=-1)
    $folder = 'D:\UCIE\.ucie_bridge_state'
    if (-not (Test-Path -LiteralPath $folder -PathType Container)) { return }
    $output = Join-Path $folder 'c40_supervisor_health_v1.json'
    $entry = [pscustomobject]@{
        schema='UCIE_C40_SUPERVISOR_HEALTH_V1'
        stage=$Stage
        code=$Code
        client_count=$Count
        utc=[DateTime]::UtcNow.ToString('o')
        another_task_modified=$false
        operating_db_modified=$false
    }
    try {
        $json = $entry | ConvertTo-Json -Compress -Depth 3
        [IO.File]::WriteAllText($output,$json,[Text.Encoding]::UTF8)
    } catch { }
}
if ($Mode -eq 'Status') {
    $task = Get-C40Task
    $items = @(Find-C40)
    [pscustomobject]@{
        status='UCIE_C40_RECOVERY_STATUS_READONLY'
        task_registered=($null -ne $task)
        task_state=$(if($null -ne $task){[string]$task.State}else{'ABSENT'})
        c40_client_count=$items.Count
        admin_mode_not_inferred=$true
        db_changed=$false
    } | ConvertTo-Json -Compress
    return
}
if ($Mode -eq 'Install') {
    if (-not $OwnerOnlyConfirmed) { throw 'UCIE_OWNER_ONLY_SCOPE_REQUIRED' }
    if ($null -ne (Get-C40Task)) { throw 'UCIE_C40_TASK_EXISTS_NO_OVERWRITE' }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'UCIE_C40_ELEVATED_OWNER_REQUIRED_FOR_INSTALL'
    }
    $id = Verify-C40Inputs
    $id = $null
    $active = @(Find-C40)
    $decision = Read-Host 'UCIE C40 logon recovery registration: type APPROVE'
    if ($decision -cne 'APPROVE') { throw 'UCIE_C40_INSTALL_NOT_APPROVED' }
    $self = Get-Item -LiteralPath $scriptPath
    if (($self.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'UCIE_C40_RECOVERY_SCRIPT_LINK_DENIED'
    }
    $args = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy RemoteSigned -File "' +
        $scriptPath + '" -Mode Supervise'
    if ($EnableAdminTools) { $args += ' -EnableAdminTools' }
    $action = New-ScheduledTaskAction -Execute $psExe -Argument $args -WorkingDirectory 'D:\UCIE'
    $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Highest
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $principal.UserId
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Trigger $trigger -Settings $settings -Description 'UCIE-only existing C40 at owner logon and every five minutes' -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
    [pscustomobject]@{status='UCIE_C40_RECOVERY_TASK_REGISTERED';task=$taskName;
        trigger='OWNER_LOGON';check_interval_seconds=300;admin_enabled=[bool]$EnableAdminTools;
        existing_c40_count=$active.Count;other_tasks_modified=$false;operating_db_modified=$false} | ConvertTo-Json -Compress
    return
}
if ($Mode -eq 'Remove') {
    if (-not $OwnerOnlyConfirmed) { throw 'UCIE_OWNER_ONLY_SCOPE_REQUIRED' }
    $decision = Read-Host 'Remove ONLY UCIE-C40-Recover task: type REMOVE'
    if ($decision -cne 'REMOVE') { throw 'UCIE_C40_REMOVAL_NOT_APPROVED' }
    if ($null -eq (Get-C40Task)) { throw 'UCIE_C40_TASK_NOT_PRESENT' }
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction Stop
    [pscustomobject]@{status='UCIE_C40_RECOVERY_TASK_REMOVED';
        running_c40_not_terminated=$true;other_tasks_modified=$false} | ConvertTo-Json -Compress
    return
}
if ($Mode -eq 'Once') {
    $task = Assert-ApprovedRecoveryTask
    $r = One-C40Check -StartMissing
    $r | ConvertTo-Json -Compress
    return
}
if ($Mode -eq 'Supervise') {
    Save-C40SupervisorReceipt -Stage 'PROCESS_STARTED'
    try {
        $task = Assert-ApprovedRecoveryTask
        Save-C40SupervisorReceipt -Stage 'TASK_IDENTITY_OK'
    }
    catch {
        $reason = [string]$_.Exception.Message
        if ($reason -notmatch '^UCIE_C40_[A-Z0-9_]+$') { $reason = 'NON_UCIE_EXCEPTION' }
        Save-C40SupervisorReceipt -Stage 'TASK_IDENTITY_FAILED' -Code $reason
        throw 'UCIE_C40_SUPERVISOR_TASK_IDENTITY_FAILED'
    }
    while ($true) {
        try {
            $r = One-C40Check -StartMissing
            Save-C40SupervisorReceipt -Stage 'CYCLE_OK' -Code ([string]$r.status) -Count ([int]$r.tunnel_clients)
            $r | ConvertTo-Json -Compress
        }
        catch {
            $reason = [string]$_.Exception.Message
            if ($reason -notmatch '^UCIE_C40_[A-Z0-9_]+$') { $reason = 'NON_UCIE_EXCEPTION' }
            Save-C40SupervisorReceipt -Stage 'CYCLE_FAILED' -Code $reason
            throw 'UCIE_C40_SUPERVISOR_NEEDS_OWNER_REVIEW'
        }
        Start-Sleep -Seconds 300
    }
}
throw 'UCIE_C40_INVALID_MODE'
