# UCIE C40 ONLY. Alters principal level only on one existing Disabled task.
# Default is read-only Preview. No tunnel, task enable/start, other work, or DB.
[CmdletBinding()]
param([ValidateSet('Preview','Apply')] [string]$Mode='Preview',[switch]$OwnerOnlyConfirmed)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$name='UCIE-C40-Recover'
$script='D:\UCIE\scripts\ucie_c40_recover.ps1'
$exe=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
function Resolve-UCIESid([string]$account) {
    if ($account -match '^S-1-[0-9]+(?:-[0-9]+)+$') { return $account }
    return ([Security.Principal.NTAccount]::new($account)).Translate([Security.Principal.SecurityIdentifier]).Value
}
function Read-UCIEOnlyTask {
    $task=Get-ScheduledTask -TaskName $name -ErrorAction Stop
    if ([string]$task.State -ne 'Disabled') { throw 'UCIE_C40_TASK_MUST_REMAIN_DISABLED' }
    $actions=@($task.Actions)
    if ($actions.Count -ne 1) { throw 'UCIE_C40_ACTION_COUNT_MISMATCH' }
    $a=$actions[0]
    if (-not [string]::Equals([string]$a.Execute,$exe,[StringComparison]::OrdinalIgnoreCase) -or
        -not ([string]$a.Arguments).Contains($script) -or
        -not ([string]$a.Arguments).Contains('-Mode Supervise') -or
        -not ([string]$a.Arguments).Contains('-EnableAdminTools')) {
        throw 'UCIE_C40_TASK_ACTION_MISMATCH'
    }
    $sid=Resolve-UCIESid ([string]$task.Principal.UserId)
    $caller=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    if (-not [string]::Equals($sid,$caller,[StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_C40_TASK_OWNER_MISMATCH'
    }
    if ([string]$task.Principal.LogonType -ne 'Interactive') {
        throw 'UCIE_C40_LOGON_TYPE_MISMATCH'
    }
    return $task
}
$task=Read-UCIEOnlyTask
$previous=[string]$task.Principal.RunLevel
$candidate=New-ScheduledTaskPrincipal -UserId ([string]$task.Principal.UserId) -LogonType Interactive -RunLevel Highest
if ($Mode -eq 'Preview') {
    [pscustomobject]@{status='UCIE_C40_RUNLEVEL_PREVIEW_ONLY';task=$name;task_state='Disabled';
        current_runlevel=$previous;candidate_runlevel=[string]$candidate.RunLevel;
        will_enable_or_start_task=$false;will_stop_client=$false;other_tasks_changed=$false;operating_db_changed=$false} | ConvertTo-Json -Compress
    return
}
if (-not $OwnerOnlyConfirmed) { throw 'UCIE_C40_EXPLICIT_OWNER_SCOPE_REQUIRED' }
if ($previous -eq 'Highest') {
    [pscustomobject]@{status='UCIE_C40_RUNLEVEL_ALREADY_HIGHEST';task=$name;task_state='Disabled';changed=$false} | ConvertTo-Json -Compress
    return
}
if ($previous -ne 'Limited') { throw 'UCIE_C40_UNEXPECTED_ORIGINAL_RUNLEVEL' }
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'UCIE_C40_ELEVATED_OWNER_REQUIRED'
}
$decision=Read-Host 'Change ONLY Disabled UCIE-C40-Recover RunLevel to Highest: type APPROVE'
if ($decision -cne 'APPROVE') { throw 'UCIE_C40_OWNER_APPROVAL_DENIED' }
$backupPrincipal=$task.Principal
Set-ScheduledTask -TaskName $name -Principal $candidate -ErrorAction Stop | Out-Null
try {
    $after=Read-UCIEOnlyTask
    if ([string]$after.Principal.RunLevel -ne 'Highest') { throw 'UCIE_C40_RUNLEVEL_POSTCHECK_FAILED' }
}
catch {
    Set-ScheduledTask -TaskName $name -Principal $backupPrincipal -ErrorAction Stop | Out-Null
    throw 'UCIE_C40_RUNLEVEL_CHANGE_ROLLED_BACK'
}
[pscustomobject]@{status='UCIE_C40_RUNLEVEL_HIGHEST_REGISTERED_DISABLED';task=$name;
    previous_runlevel=$previous;current_runlevel=[string]$after.Principal.RunLevel;
    task_state=[string]$after.State;enabled_or_started_task=$false;stopped_client=$false;
    changed_other_tasks=$false;operating_db_modified=$false} | ConvertTo-Json -Compress
