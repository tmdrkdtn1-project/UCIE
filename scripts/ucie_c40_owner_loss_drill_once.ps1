# UCIE C40 only: one-time owner-controlled real loss drill.
# Preview does not modify task, client, source or database.
# Apply MUST be launched locally in elevated owner PowerShell, independently of MCP.
[CmdletBinding()]
param(
    [ValidateSet('Preview','Apply')] [string]$Mode = 'Preview',
    [switch]$OwnerOnlyConfirmed
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$taskName = 'UCIE-C40-Recover'
$source = 'D:\UCIE\scripts\ucie_c40_recover.ps1'
$sourceSha = '23dcb08524b32c611b43c1136a444286d7dc776598a739a7152a651a5244e66f'
$clientExe = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$profileMarker = 'ucie-private-c40.yaml'
$profilePath = 'D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml'
$healthPath = 'D:\UCIE\.ucie_bridge_state\c40_supervisor_health_v1.json'
$receiptPath = 'D:\UCIE\.ucie_bridge_state\c40_owner_loss_drill_v1.json'
$psExe = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'

function Assert-ExactTask {
    $matches = @(Get-ScheduledTask -TaskName $taskName -ErrorAction Stop |
        Where-Object { [string]$_.TaskPath -eq [string][char]92 })
    if ($matches.Count -ne 1) { throw 'UCIE_C40_DRILL_ROOT_TASK_NOT_UNIQUE' }
    $task = $matches[0]
    if ([string]$task.State -ne 'Running' -or
        [string]$task.Principal.RunLevel -ne 'Highest' -or
        [string]$task.Principal.LogonType -ne 'Interactive') {
        throw 'UCIE_C40_DRILL_TASK_NOT_RUNNING_HIGHEST_INTERACTIVE'
    }
    $a = @($task.Actions)
    if ($a.Count -ne 1 -or
        -not [string]::Equals([string]$a[0].Execute,$psExe,[StringComparison]::OrdinalIgnoreCase) -or
        ([string]$a[0].Arguments).IndexOf($source,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or
        -not ([string]$a[0].Arguments).Contains('-Mode Supervise') -or
        -not ([string]$a[0].Arguments).Contains('-EnableAdminTools')) {
        throw 'UCIE_C40_DRILL_TASK_ACTION_MISMATCH'
    }
    $triggers = @($task.Triggers | Where-Object {
        $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger'
    })
    if ($triggers.Count -lt 1) { throw 'UCIE_C40_DRILL_LOGON_TRIGGER_MISSING' }
    $principalId = [string]$task.Principal.UserId
    $taskSid = if ($principalId -match '^S-1-[0-9]+(?:-[0-9]+)+$') {
        $principalId
    } else {
        ([Security.Principal.NTAccount]::new($principalId)).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    }
    $owner = [Security.Principal.WindowsIdentity]::GetCurrent()
    $admin = New-Object Security.Principal.WindowsPrincipal($owner)
    if (-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) -or
        -not [string]::Equals($taskSid,$owner.User.Value,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_C40_DRILL_ELEVATED_OWNER_REQUIRED'
    }
    return $task
}

function Assert-PinnedSource {
    if (-not (Test-Path -LiteralPath $source -PathType Leaf) -or
        -not (Test-Path -LiteralPath $clientExe -PathType Leaf) -or
        -not (Test-Path -LiteralPath $profilePath -PathType Leaf)) {
        throw 'UCIE_C40_DRILL_INPUT_MISSING'
    }
    $item = Get-Item -LiteralPath $source -ErrorAction Stop
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sourceSha) {
        throw 'UCIE_C40_DRILL_SOURCE_SHA_OR_LINK_MISMATCH'
    }
}

function Get-ExactC40 {
    $rows = @(Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
        Where-Object {
            [string]::Equals([string]$_.ExecutablePath,$clientExe,[StringComparison]::OrdinalIgnoreCase)
        })
    if ($rows.Count -gt 1) { throw 'UCIE_C40_DRILL_DUPLICATE_CLIENT' }
    foreach ($c in $rows) {
        $line = [string]$c.CommandLine
        if ($line.IndexOf($profileMarker,[StringComparison]::OrdinalIgnoreCase) -lt 0 -or
            -not $line.Contains('--profile-file')) {
            throw 'UCIE_C40_DRILL_UNRECOGNIZED_CLIENT'
        }
        $native = Get-Process -Id ([int]$c.ProcessId) -ErrorAction Stop
        if (-not [string]::Equals([string]$native.Path,$clientExe,[StringComparison]::OrdinalIgnoreCase)) {
            throw 'UCIE_C40_DRILL_NATIVE_PROCESS_MISMATCH'
        }
        $nativeStarted = ([datetime]$native.StartTime).ToUniversalTime()
        $cimStarted = ([datetime]$c.CreationDate).ToUniversalTime()
        if ([math]::Abs(($nativeStarted - $cimStarted).TotalSeconds) -gt 2) {
            throw 'UCIE_C40_DRILL_PROCESS_START_MISMATCH'
        }
    }
    return @($rows)
}

function Read-C40Health {
    if (-not (Test-Path -LiteralPath $healthPath -PathType Leaf)) {
        throw 'UCIE_C40_DRILL_HEALTH_MISSING'
    }
    $file = Get-Item -LiteralPath $healthPath -ErrorAction Stop
    if ($file.Length -gt 2048 -or
        ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'UCIE_C40_DRILL_HEALTH_UNTRUSTED'
    }
    $h = Get-Content -LiteralPath $healthPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$h.schema -ne 'UCIE_C40_SUPERVISOR_HEALTH_V1') {
        throw 'UCIE_C40_DRILL_HEALTH_SCHEMA_MISMATCH'
    }
    return $h
}

function Assert-Ready {
    $null = Assert-ExactTask
    Assert-PinnedSource
    $client = @(Get-ExactC40)
    if ($client.Count -ne 1) { throw 'UCIE_C40_DRILL_EXISTING_CLIENT_REQUIRED' }
    $health = Read-C40Health
    $utc = ([datetime]::Parse([string]$health.utc)).ToUniversalTime()
    $age = ([DateTime]::UtcNow - $utc).TotalSeconds
    if ([string]$health.stage -ne 'CYCLE_OK' -or
        [string]$health.code -ne 'UCIE_C40_ALREADY_RUNNING' -or
        [int]$health.client_count -ne 1 -or $age -lt -10 -or $age -gt 420) {
        throw 'UCIE_C40_DRILL_ACTIVE_SUPERVISOR_NOT_PROVEN'
    }
    return $client[0]
}

function Save-DrillReceipt {
    param([string]$Status,[datetime]$FaultUtc,[int]$OldProcess,[int]$NewProcess=0)
    $data = [pscustomobject]@{
        schema = 'UCIE_C40_OWNER_LOSS_DRILL_V1'
        status = $Status
        fault_utc = $FaultUtc.ToString('o')
        updated_utc = [DateTime]::UtcNow.ToString('o')
        original_pid = $OldProcess
        recovered_pid = $NewProcess
        other_tasks_modified = $false
        operating_database_modified = $false
        requires_chatgpt_bridge_recheck = $true
    }
    [IO.File]::WriteAllText($receiptPath,($data | ConvertTo-Json -Compress),
        [Text.Encoding]::UTF8)
}

$observed = Assert-Ready
if ($Mode -eq 'Preview') {
    [pscustomobject]@{
        status = 'UCIE_C40_LOSS_DRILL_PREVIEW_ONLY'
        task = $taskName
        task_state = 'Running'
        owner_and_source_verified = $true
        client_count = 1
        client_pid = [int]$observed.ProcessId
        standby_path = 'WINDOWS_OWNER_RUNNING_SUPERVISOR'
        independent_manual_once_available = $true
        task_modified = $false
        client_modified = $false
        operating_database_modified = $false
    } | ConvertTo-Json -Compress
    return
}
if (-not $OwnerOnlyConfirmed) { throw 'UCIE_C40_DRILL_OWNER_SCOPE_REQUIRED' }
if (Test-Path -LiteralPath $receiptPath) { throw 'UCIE_C40_DRILL_ONCE_ALREADY_ATTEMPTED' }
$confirm = Read-Host 'One-time controlled loss of the exact UCIE C40 client; type UCIE_C40_LOSS_ONE_TIME'
if ($confirm -cne 'UCIE_C40_LOSS_ONE_TIME') { throw 'UCIE_C40_DRILL_NOT_APPROVED' }

# Repeat all preconditions after consent. Never trust a historical PID.
$current = Assert-Ready
if ([int]$current.ProcessId -ne [int]$observed.ProcessId -or
    ([datetime]$current.CreationDate).ToUniversalTime() -ne
    ([datetime]$observed.CreationDate).ToUniversalTime()) {
    throw 'UCIE_C40_DRILL_PROCESS_CHANGED_AFTER_APPROVAL'
}
$process = Get-Process -Id ([int]$current.ProcessId) -ErrorAction Stop
if (-not [string]::Equals([string]$process.Path,$clientExe,[StringComparison]::OrdinalIgnoreCase) -or
    [math]::Abs((([datetime]$process.StartTime).ToUniversalTime() -
      ([datetime]$current.CreationDate).ToUniversalTime()).TotalSeconds) -gt 2) {
    throw 'UCIE_C40_DRILL_TARGET_HANDLE_MISMATCH'
}
# Atomic create-new journal: a prior attempt or concurrent operator is rejected.
$stream = [IO.File]::Open($receiptPath,[IO.FileMode]::CreateNew,
    [IO.FileAccess]::Write,[IO.FileShare]::None)
$stream.Dispose()
$faultUtc = [DateTime]::UtcNow
Save-DrillReceipt -Status 'FAULT_REQUESTED' -FaultUtc $faultUtc -OldProcess ([int]$current.ProcessId)
$process.Kill()
if (-not $process.WaitForExit(5000)) {
    Save-DrillReceipt -Status 'FAULT_TERMINATION_UNCONFIRMED' -FaultUtc $faultUtc -OldProcess ([int]$current.ProcessId)
    throw 'UCIE_C40_DRILL_TERMINATION_NOT_CONFIRMED'
}
Save-DrillReceipt -Status 'CLIENT_STOPPED_WAITING_FOR_SUPERVISOR' -FaultUtc $faultUtc -OldProcess ([int]$current.ProcessId)

# The local PowerShell process remains independent of the tunnel connection.
# Do not start a second client here: this avoids racing the existing supervisor.
for ($step=0; $step -lt 90; $step++) {
    Start-Sleep -Seconds 5
    $clients = @(Get-ExactC40)
    if ($clients.Count -eq 0) { continue }
    $new = $clients[0]
    if ([int]$new.ProcessId -eq [int]$current.ProcessId -or
        ([datetime]$new.CreationDate).ToUniversalTime() -lt $faultUtc.AddSeconds(-3)) {
        Save-DrillReceipt -Status 'UNEXPECTED_PROCESS_IDENTITY' -FaultUtc $faultUtc -OldProcess ([int]$current.ProcessId)
        throw 'UCIE_C40_DRILL_UNEXPECTED_RECOVERED_IDENTITY'
    }
    $h = Read-C40Health
    $hTime = ([datetime]::Parse([string]$h.utc)).ToUniversalTime()
    if ([string]$h.stage -eq 'CYCLE_OK' -and
        [string]$h.code -eq 'UCIE_C40_CHILD_STARTED' -and
        [int]$h.client_count -eq 1 -and $hTime -ge $faultUtc.AddSeconds(-3)) {
        Save-DrillReceipt -Status 'SINGLE_CLIENT_RESTART_RECEIPT_OBSERVED' -FaultUtc $faultUtc -OldProcess ([int]$current.ProcessId) -NewProcess ([int]$new.ProcessId)
        [pscustomobject]@{
            status = 'UCIE_C40_DRILL_AUTO_RESTART_OBSERVED'
            new_client_count = 1
            new_client_pid = [int]$new.ProcessId
            bridge_reconnect_still_requires_independent_check = $true
            owner_logon_recovery_not_tested = $true
            operating_database_modified = $false
        } | ConvertTo-Json -Compress
        return
    }
    Save-DrillReceipt -Status 'CLIENT_RETURNED_WITHOUT_ATTRIBUTED_RESTART_RECEIPT' -FaultUtc $faultUtc -OldProcess ([int]$current.ProcessId) -NewProcess ([int]$new.ProcessId)
    throw 'UCIE_C40_DRILL_AUTO_RESTART_ATTRIBUTION_NOT_PROVEN'
}
Save-DrillReceipt -Status 'AUTO_RESTART_NOT_OBSERVED_OWNER_MANUAL_REVIEW' -FaultUtc $faultUtc -OldProcess ([int]$current.ProcessId)
throw 'UCIE_C40_DRILL_AUTO_RESTART_NOT_PROVEN_USE_OWNER_MANUAL_RECOVERY'
