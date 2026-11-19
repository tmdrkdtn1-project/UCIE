# UCIE C40 owner logon acceptance; never signs out, restarts or alters a task.
# Preview is read-only. Prepare writes a single UCIE-only marker.
# Verify is read-only and requires explicit owner attestation of signout/logon.
[CmdletBinding()]
param(
  [ValidateSet('Preview','Prepare','Verify')]
  [string]$Mode='Preview',
  [switch]$OwnerOnlyConfirmed,
  [switch]$OwnerSignedOutAndBackInConfirmed
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$source='D:\UCIE\scripts\ucie_c40_recover.ps1'
$sourceSha='23dcb08524b32c611b43c1136a444286d7dc776598a739a7152a651a5244e66f'
$folder='D:\UCIE\.ucie_bridge_state'
$marker=Join-Path $folder 'c40_owner_logon_acceptance_v1.json'
$healthReceiptPath=Join-Path $folder 'c40_supervisor_health_v1.json'
$clientExe='D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$taskName='UCIE-C40-Recover'

function Convert-ExactUtc {
  param([string]$Value)
  $dt=[datetime]::MinValue
  if(-not [datetime]::TryParse($Value,[ref]$dt)) {
    throw 'UCIE_C40_LOGON_TIMESTAMP_UNPARSABLE'
  }
  return $dt.ToUniversalTime()
}
function Get-GuardedReceipt {
  param([string]$Path,[int]$MaxBytes)
  if(-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw 'UCIE_C40_LOGON_RECEIPT_MISSING'
  }
  $item=Get-Item -LiteralPath $Path -ErrorAction Stop
  if($item.Length -gt $MaxBytes -or
     ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'UCIE_C40_LOGON_RECEIPT_UNTRUSTED'
  }
  return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8 |
    ConvertFrom-Json -ErrorAction Stop)
}
function Get-C40OwnerSnapshot {
  $item=Get-Item -LiteralPath $source -ErrorAction Stop
  if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
     (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sourceSha) {
    throw 'UCIE_C40_LOGON_SOURCE_SHA_MISMATCH'
  }
  # The sourced script executes its read-only Status path, not Once/Supervise/Install.
  . $source -Mode Status -EnableAdminTools | Out-Null
  $task=Assert-ApprovedRecoveryTask
  if([string]$task.State -ne 'Running' -or
     [string]$task.Principal.RunLevel -ne 'Highest' -or
     [string]$task.Principal.LogonType -ne 'Interactive') {
    throw 'UCIE_C40_LOGON_TASK_NOT_RUNNING_HIGHEST'
  }
  $triggers=@($task.Triggers | Where-Object {
    $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger'
  })
  if($triggers.Count -lt 1){throw 'UCIE_C40_LOGON_TRIGGER_MISSING'}
  $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
  $principal=New-Object Security.Principal.WindowsPrincipal($identity)
  if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    throw 'UCIE_C40_LOGON_ELEVATED_OWNER_REQUIRED'
  }
  $clients=@(Find-C40)
  if($clients.Count -ne 1){throw 'UCIE_C40_LOGON_NOT_EXACTLY_ONE_CLIENT'}
  $c=$clients[0]
  $native=Get-Process -Id ([int]$c.ProcessId) -ErrorAction Stop
  if(-not [string]::Equals([string]$native.Path,$clientExe,
    [StringComparison]::OrdinalIgnoreCase) -or
    ([string]$c.CommandLine).IndexOf('ucie-private-c40',
    [StringComparison]::OrdinalIgnoreCase) -lt 0 -or
    [math]::Abs((([datetime]$native.StartTime).ToUniversalTime() -
      ([datetime]$c.CreationDate).ToUniversalTime()).TotalSeconds) -gt 2) {
    throw 'UCIE_C40_LOGON_CLIENT_IDENTITY_MISMATCH'
  }
  $h=Get-GuardedReceipt -Path $healthReceiptPath -MaxBytes 2048
  $now=[DateTime]::UtcNow
  $hUtc=Convert-ExactUtc -Value ([string]$h.utc)
  $age=($now-$hUtc).TotalSeconds
  if([string]$h.schema -ne 'UCIE_C40_SUPERVISOR_HEALTH_V1' -or
    [string]$h.stage -ne 'CYCLE_OK' -or
    [string]$h.code -notin @('UCIE_C40_CHILD_STARTED','UCIE_C40_ALREADY_RUNNING') -or
    [int]$h.client_count -ne 1 -or $age -lt -10 -or $age -gt 420) {
    throw 'UCIE_C40_LOGON_SUPERVISOR_HEALTH_NOT_FRESH'
  }
  $info=Get-ScheduledTaskInfo -TaskName $taskName -ErrorAction Stop
  if([int]$info.LastTaskResult -ne 267009){
    throw 'UCIE_C40_LOGON_TASK_NOT_STILL_RUNNING'
  }
  return [pscustomobject]@{
    schema='UCIE_C40_OWNER_LOGON_SNAPSHOT_V1'
    observed_utc=$now.ToString('o')
    task_last_run_utc=$info.LastRunTime.ToUniversalTime().ToString('o')
    client_pid=[int]$c.ProcessId
    client_created_utc=([datetime]$c.CreationDate).ToUniversalTime().ToString('o')
    supervisor_utc=$hUtc.ToString('o')
    supervisor_code=[string]$h.code
    task_running_highest_owner=$true
    task_logon_trigger_present=$true
    exact_client_count=1
    task_or_process_modified=$false
  }
}
$snapshot=Get-C40OwnerSnapshot
if($Mode -eq 'Preview') {
  [pscustomobject]@{
    status='UCIE_C40_OWNER_LOGON_PREVIEW_ONLY'
    observed_utc=$snapshot.observed_utc
    task_last_run_utc=$snapshot.task_last_run_utc
    current_client_pid=$snapshot.client_pid
    current_client_created_utc=$snapshot.client_created_utc
    task_running_highest_owner=$true
    task_logon_trigger_present=$true
    exact_client_count=1
    marker_already_present=(Test-Path -LiteralPath $marker)
    task_or_process_modified=$false
  } | ConvertTo-Json -Compress
  return
}
if($Mode -eq 'Prepare') {
  if(-not $OwnerOnlyConfirmed){throw 'UCIE_C40_LOGON_OWNER_PREPARE_REQUIRED'}
  if(Test-Path -LiteralPath $marker){throw 'UCIE_C40_LOGON_ALREADY_PREPARED'}
  $entry=[pscustomobject]@{
    schema='UCIE_C40_OWNER_LOGON_ACCEPTANCE_V1'
    status='PREPARED'
    prepared_utc=[DateTime]::UtcNow.ToString('o')
    before_task_last_run_utc=$snapshot.task_last_run_utc
    before_client_pid=$snapshot.client_pid
    before_client_created_utc=$snapshot.client_created_utc
    source_sha=$sourceSha
    other_tasks_modified=$false
    operating_database_modified=$false
  }
  $json=$entry | ConvertTo-Json -Compress -Depth 4
  if(-not (Test-Path -LiteralPath $folder -PathType Container)){
    throw 'UCIE_C40_LOGON_JOURNAL_FOLDER_MISSING'
  }
  $stream=[IO.File]::Open($marker,[IO.FileMode]::CreateNew,
     [IO.FileAccess]::Write,[IO.FileShare]::None)
  try {
    $bytes=[Text.Encoding]::UTF8.GetBytes($json)
    $stream.Write($bytes,0,$bytes.Length)
  } finally {
    $stream.Dispose()
  }
  [pscustomobject]@{
    status='UCIE_C40_OWNER_LOGON_PREPARED'
    marker=$marker
    baseline_task_last_run_utc=$snapshot.task_last_run_utc
    baseline_client_pid=$snapshot.client_pid
    requires_real_owner_signout_signin=$true
    process_or_task_modified=$false
  } | ConvertTo-Json -Compress
  return
}
if($Mode -eq 'Verify') {
  if(-not $OwnerOnlyConfirmed -or -not $OwnerSignedOutAndBackInConfirmed) {
    throw 'UCIE_C40_LOGON_OWNER_ATTESTATION_REQUIRED'
  }
  $baseline=Get-GuardedReceipt -Path $marker -MaxBytes 4096
  if([string]$baseline.schema -ne 'UCIE_C40_OWNER_LOGON_ACCEPTANCE_V1' -or
     [string]$baseline.status -ne 'PREPARED' -or
     [string]$baseline.source_sha -ne $sourceSha) {
    throw 'UCIE_C40_LOGON_BASELINE_UNTRUSTED'
  }
  $prepared=Convert-ExactUtc -Value ([string]$baseline.prepared_utc)
  $oldTask=Convert-ExactUtc -Value ([string]$baseline.before_task_last_run_utc)
  $currentTask=Convert-ExactUtc -Value $snapshot.task_last_run_utc
  $newCreated=Convert-ExactUtc -Value $snapshot.client_created_utc
  $oldCreated=Convert-ExactUtc -Value ([string]$baseline.before_client_created_utc)
  $healthUtc=Convert-ExactUtc -Value $snapshot.supervisor_utc
  if($prepared -le $oldTask -or
     $currentTask -le $prepared -or
     $currentTask -le $oldTask -or
     $newCreated -le $prepared -or
     $newCreated -le $oldCreated -or
     [int]$snapshot.client_pid -eq [int]$baseline.before_client_pid -or
     $healthUtc -lt $prepared) {
    throw 'UCIE_C40_LOGON_FRESH_TASK_AND_CLIENT_NOT_PROVEN'
  }
  [pscustomobject]@{
    status='UCIE_C40_OWNER_LOGON_RESTART_HOST_VERIFIED'
    owner_attests_real_signout_and_signin=$true
    task_rerun_after_prepare=$true
    old_client_pid=[int]$baseline.before_client_pid
    new_client_pid=[int]$snapshot.client_pid
    fresh_supervisor_code=$snapshot.supervisor_code
    new_task_last_run_utc=$snapshot.task_last_run_utc
    new_client_created_utc=$snapshot.client_created_utc
    exact_client_count=1
    task_or_process_modified=$false
    mcp_reconnect_requires_independent_check=$true
  } | ConvertTo-Json -Compress
  return
}
throw 'UCIE_C40_LOGON_INVALID_MODE'
