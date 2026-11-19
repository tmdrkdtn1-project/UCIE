# UCIE-only owner activation of the EXISTING disabled C40 recovery task.
# Preview is read-only. Apply never starts/stops a tunnel-client.exe directly.
[CmdletBinding()]
param(
    [ValidateSet('Preview','Apply')] [string]$Mode='Preview',
    [switch]$OwnerOnlyConfirmed
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$name='UCIE-C40-Recover'
$path='\'
$source='D:\UCIE\scripts\ucie_c40_recover.ps1'
$expectedSourceSha='23dcb08524b32c611b43c1136a444286d7dc776598a739a7152a651a5244e66f'
$exe='D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$ownerPid=57016
$ownerStartedUtc=[DateTime]::Parse('2026-11-02T06:31:20.9199320Z').ToUniversalTime()
$receiptPath='D:\UCIE\.ucie_bridge_state\c40_supervisor_health_v1.json'
$psExe=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'

function Get-ExactUCIERecoveryTask {
    $task=Get-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop
    if ([string]$task.State -ne 'Disabled') { throw 'UCIE_C40_ACTIVATION_TASK_NOT_DISABLED' }
    if ([string]$task.Principal.RunLevel -ne 'Highest' -or
        [string]$task.Principal.LogonType -ne 'Interactive') {
        throw 'UCIE_C40_ACTIVATION_OWNER_TASK_NOT_HIGHEST_INTERACTIVE'
    }
    $a=@($task.Actions)
    if ($a.Count -ne 1 -or
        -not [string]::Equals([string]$a[0].Execute,$psExe,[StringComparison]::OrdinalIgnoreCase) -or
        -not ([string]$a[0].Arguments).Contains($source) -or
        -not ([string]$a[0].Arguments).Contains('-Mode Supervise') -or
        -not ([string]$a[0].Arguments).Contains('-EnableAdminTools')) {
        throw 'UCIE_C40_ACTIVATION_ACTION_MISMATCH'
    }
    $sid=[string]$task.Principal.UserId
    if ($sid -notmatch '^S-1-[0-9]+(?:-[0-9]+)+$') {
        $sid=([Security.Principal.NTAccount]::new($sid)).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    }
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    if (-not [string]::Equals($sid,$identity.User.Value,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_C40_ACTIVATION_OWNER_SID_MISMATCH'
    }
    return $task
}
function Assert-C40OwnerClientOne {
    $clients=@(Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
        Where-Object {
            [string]::Equals([string]$_.ExecutablePath,$exe,[StringComparison]::OrdinalIgnoreCase)
        })
    if ($clients.Count -ne 1) { throw 'UCIE_C40_ACTIVATION_CLIENT_COUNT_NOT_ONE' }
    $c=$clients[0]
    if ([int]$c.ProcessId -ne $ownerPid -or
        ([string]$c.CommandLine).IndexOf('ucie-private-c40',[StringComparison]::OrdinalIgnoreCase) -lt 0 -or
        -not ([string]$c.CommandLine).Contains('--profile-file')) {
        throw 'UCIE_C40_ACTIVATION_CLIENT_IDENTITY_MISMATCH'
    }
    $when=([datetime]$c.CreationDate).ToUniversalTime()
    if ([Math]::Abs(($when-$ownerStartedUtc).TotalSeconds) -gt 1) {
        throw 'UCIE_C40_ACTIVATION_CLIENT_START_TIME_MISMATCH'
    }
    return $true
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'UCIE_C40_ACTIVATION_ELEVATED_OWNER_REQUIRED'
}
$null=Get-ExactUCIERecoveryTask
if (-not (Test-Path -LiteralPath $source -PathType Leaf) -or
    (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedSourceSha) {
    throw 'UCIE_C40_ACTIVATION_SOURCE_SHA_MISMATCH'
}
$null=Assert-C40OwnerClientOne
if ($Mode -eq 'Preview') {
    [pscustomobject]@{
        status='UCIE_C40_ACTIVATION_PREVIEW_ONLY'
        task=$name;task_state='Disabled';task_runlevel='Highest'
        guarded_script_sha_matches=$true;original_client_count=1
        original_client_pid=$ownerPid;task_modified=$false;client_modified=$false
        other_tasks_modified=$false;operating_db_modified=$false
    } | ConvertTo-Json -Compress
    return
}
if (-not $OwnerOnlyConfirmed) { throw 'UCIE_C40_ACTIVATION_EXPLICIT_OWNER_SCOPE_REQUIRED' }
$approval=Read-Host 'Enable and start ONLY existing UCIE-C40-Recover for guarded one-cycle acceptance: type APPROVE'
if ($approval -cne 'APPROVE') { throw 'UCIE_C40_ACTIVATION_NOT_APPROVED' }
# Reject changed task/client/source between preview and owner approval.
$null=Get-ExactUCIERecoveryTask
$null=Assert-C40OwnerClientOne
if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedSourceSha) {
    throw 'UCIE_C40_ACTIVATION_SOURCE_CHANGED_AFTER_CONSENT'
}
$started=[DateTime]::UtcNow
try {
    Enable-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop | Out-Null
    Start-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop
    Start-Sleep -Seconds 8
    $running=Get-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop
    if ([string]$running.State -ne 'Running') { throw 'UCIE_C40_ACTIVATION_TASK_NOT_RUNNING' }
    $null=Assert-C40OwnerClientOne
    if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) {
        throw 'UCIE_C40_ACTIVATION_FRESH_RECEIPT_MISSING'
    }
    $health=Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $healthyUtc=[DateTime]::Parse([string]$health.utc).ToUniversalTime()
    if ([string]$health.schema -ne 'UCIE_C40_SUPERVISOR_HEALTH_V1' -or
        [string]$health.stage -ne 'CYCLE_OK' -or
        [string]$health.code -ne 'UCIE_C40_ALREADY_RUNNING' -or
        [int]$health.client_count -ne 1 -or
        $healthyUtc -lt $started.AddSeconds(-2)) {
        throw 'UCIE_C40_ACTIVATION_FIRST_CYCLE_NOT_CONFIRMED'
    }
}
catch {
    try {
        Stop-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction SilentlyContinue
        Disable-ScheduledTask -TaskPath $path -TaskName $name -ErrorAction Stop | Out-Null
    }
    catch { throw 'UCIE_C40_ACTIVATION_ROLLBACK_FAILED_OWNER_REVIEW' }
    throw 'UCIE_C40_ACTIVATION_FAILED_TASK_DISABLED'
}
[pscustomobject]@{
    status='UCIE_C40_FIRST_CYCLE_RUNNING_ONE_CLIENT'
    task=$name;task_state='Running';task_runlevel='Highest'
    original_client_pid=$ownerPid;original_client_count=1
    first_supervisor_cycle_verified=$true
    next_cycle_and_logon_validation_pending=$true
    other_tasks_modified=$false;operating_db_modified=$false
} | ConvertTo-Json -Compress
