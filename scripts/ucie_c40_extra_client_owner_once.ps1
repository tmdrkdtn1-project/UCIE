# UCIE-only, one-time owner-mediated cleanup of the extra C40 process.
# Read-only by default; never creates a tunnel or edits tasks.
[CmdletBinding()]
param([ValidateSet('Preview','Apply')][string]$Mode='Preview',[switch]$OwnerOnlyConfirmed)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$taskName='UCIE-C40-Recover'
$expectedExe='D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$originalPid=57016
$extraPid=53556
$originalStart=[DateTime]::Parse('2026-11-02T06:31:20.9199320Z').ToUniversalTime()
$extraStart=[DateTime]::Parse('2026-11-02T07:45:35.3567200Z').ToUniversalTime()
function Assert-C40Identity([int]$expectedPid,[datetime]$expectedStart) {
    $rows=@(Get-CimInstance Win32_Process -Filter "ProcessId = $expectedPid" -ErrorAction Stop)
    if ($rows.Count -ne 1) { throw 'UCIE_C40_EXACT_PID_NOT_PRESENT' }
    $p=$rows[0]
    if (-not [string]::Equals([string]$p.ExecutablePath,$expectedExe,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_C40_EXACT_EXECUTABLE_MISMATCH'
    }
    $cmd=[string]$p.CommandLine
    if (-not $cmd.Contains('ucie-private-c40.yaml') -or
        -not $cmd.Contains('--profile-file')) {
        throw 'UCIE_C40_PROFILE_MISMATCH'
    }
    $created=([datetime]$p.CreationDate).ToUniversalTime()
    if ([math]::Abs(($created-$expectedStart).TotalSeconds) -gt 1) {
        throw 'UCIE_C40_PROCESS_START_TIME_MISMATCH'
    }
    return $p
}
$owner=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=New-Object Security.Principal.WindowsPrincipal($owner)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'UCIE_C40_ELEVATED_OWNER_REQUIRED'
}
$task=Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction Stop
if ([string]$task.State -ne 'Disabled' -or
    [string]$task.Principal.RunLevel -ne 'Highest') {
    throw 'UCIE_C40_RECOVERY_TASK_NOT_DISABLED_HIGHEST'
}
$currentOwner=[string]$task.Principal.UserId
if ($currentOwner -match '^S-1-[0-9]+(?:-[0-9]+)+$') { $taskSid=$currentOwner }
else { $taskSid=([Security.Principal.NTAccount]::new($currentOwner)).Translate(
    [Security.Principal.SecurityIdentifier]).Value }
if (-not [string]::Equals($owner.User.Value,$taskSid,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_C40_OWNER_SID_MISMATCH'
}
$original=Assert-C40Identity $originalPid $originalStart
$extra=Assert-C40Identity $extraPid $extraStart
# With an elevated token, the pinned UCIE-only client census must be complete.
$all=@(Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
    Where-Object { [string]::Equals([string]$_.ExecutablePath,$expectedExe,[StringComparison]::OrdinalIgnoreCase) })
if ($all.Count -ne 2 -or
    (@($all | Where-Object { @($originalPid,$extraPid) -contains [int]$_.ProcessId }).Count -ne 2)) {
    throw 'UCIE_C40_CLIENT_CENSUS_NOT_EXACTLY_TWO'
}
if ($Mode -eq 'Preview') {
    [pscustomobject]@{status='UCIE_C40_DUPLICATE_OWNER_PREVIEW_ONLY';
        original_pid=$originalPid;extra_pid=$extraPid;original_verified=$true;
        extra_verified=$true;task_state='Disabled';task_runlevel='Highest';
        stopped_process=$false;other_tasks_changed=$false;operating_db_changed=$false} |
        ConvertTo-Json -Compress
    return
}
if (-not $OwnerOnlyConfirmed) { throw 'UCIE_C40_EXPLICIT_OWNER_SCOPE_REQUIRED' }
$consent=Read-Host 'Stop only verified newer UCIE C40 PID 53556: type STOP_UCIE_53556'
if ($consent -cne 'STOP_UCIE_53556') { throw 'UCIE_C40_OWNER_CLEANUP_NOT_APPROVED' }
# Recheck both identities immediately before any termination to reject PID reuse.
$null=Assert-C40Identity $originalPid $originalStart
$null=Assert-C40Identity $extraPid $extraStart
$finalTask=Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction Stop
if ([string]$finalTask.State -ne 'Disabled' -or
    [string]$finalTask.Principal.RunLevel -ne 'Highest') {
    throw 'UCIE_C40_TASK_CHANGED_AFTER_OWNER_CONSENT'
}
$finalClients=@(Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
    Where-Object { [string]::Equals([string]$_.ExecutablePath,$expectedExe,[StringComparison]::OrdinalIgnoreCase) })
if ($finalClients.Count -ne 2 -or
    (@($finalClients | Where-Object { @($originalPid,$extraPid) -contains [int]$_.ProcessId }).Count -ne 2)) {
    throw 'UCIE_C40_CLIENT_CENSUS_CHANGED_AFTER_OWNER_CONSENT'
}
Stop-Process -Id $extraPid -ErrorAction Stop
Start-Sleep -Seconds 2
$still=@(Get-CimInstance Win32_Process -Filter "ProcessId = $extraPid" -ErrorAction Stop)
$null=Assert-C40Identity $originalPid $originalStart
if ($still.Count -gt 0) { throw 'UCIE_C40_EXTRA_CLIENT_STILL_PRESENT' }
[pscustomobject]@{status='UCIE_C40_EXTRA_CLIENT_STOPPED_ORIGINAL_PRESERVED';
    stopped_pid=$extraPid;original_pid=$originalPid;task_state='Disabled';
    task_enabled=$false;other_tasks_changed=$false;operating_db_changed=$false} |
    ConvertTo-Json -Compress
