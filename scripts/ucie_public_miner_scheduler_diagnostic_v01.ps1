# UCIE fixed public miner scheduled-task diagnosis, strictly READ-ONLY.
# Reads only \UCIE-PublicMiner-Hourly and the existing UCIE-only event proof.
# No repair, no task start/stop/register, no other task enumeration.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$module = Join-Path $root 'src\ucie_miner\public_scheduler_diagnostic_v01.py'
$existing = Join-Path $root 'scripts\task_status.ps1'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $module -PathType Leaf) -or
    -not (Test-Path -LiteralPath $existing -PathType Leaf)) {
    throw 'UCIE_EXACT_SCHEDULER_DIAGNOSTIC_PREREQUISITES_MISSING'
}
# Exact task name and exact root TaskPath only. No wildcard or task listing.
$task = Get-ScheduledTask -TaskPath '\' -TaskName 'UCIE-PublicMiner-Hourly' -ErrorAction SilentlyContinue
$info = if ($null -eq $task) { $null } else {
    Get-ScheduledTaskInfo -TaskPath '\' -TaskName 'UCIE-PublicMiner-Hourly' -ErrorAction Stop
}
$found = ($null -ne $task)
$state = if ($found) { [string]$task.State } else { 'Absent' }
if ($state -notin @('Ready','Running','Disabled','Queued','Unknown','Absent')) {
    $state = 'Unknown'
}
$lastResult = $null
if ($null -ne $info) {
    # LastTaskResult can arrive as signed Int32 HRESULT, normalize as UInt32.
    $number = [int64]$info.LastTaskResult
    if ($number -lt 0) { $number += 4294967296L }
    if ($number -lt 0 -or $number -gt 4294967295L) {
        throw 'UCIE_LAST_TASK_RESULT_OUTSIDE_UINT32'
    }
    $lastResult = $number
}
$rawProof = & $existing -Evidence
if ($null -eq $rawProof) { throw 'UCIE_EXISTING_SCHEDULER_PROOF_UNAVAILABLE' }
$proof = ($rawProof | Out-String) | ConvertFrom-Json -ErrorAction Stop
if ($proof.schema -cne 'UCIE_HOURLY_LOCAL_OPERATIONS_READONLY_V1') {
    throw 'UCIE_ORIGINAL_SCHEDULER_EVIDENCE_SCHEMA_MISMATCH'
}
# Never forward owner principal ID, executable path, account name, event XML.
# Only whitelisted booleans/status and the matched event count are forwarded.
$boundedProof = [ordered]@{
    schema = 'UCIE_HOURLY_LOCAL_OPERATIONS_READONLY_V1'
    status = [string]$proof.status
    scheduled_task_registered = $proof.scheduled_task_registered
    action_matches_ucie_only = $proof.action_matches_ucie_only
    owner_least_privilege_verified = $proof.owner_least_privilege_verified
    hourly_no_overlap_configured = $proof.hourly_no_overlap_configured
    last_task_result_zero = $proof.last_task_result_zero
    scheduler_event_log_readable = $proof.scheduler_event_log_readable
    scheduler_event_instance_receipts_verified = $proof.scheduler_event_instance_receipts_verified
    last_scheduled_run_matches_receipt = $proof.last_scheduled_run_matches_receipt
    two_recent_hourly_successes = $proof.two_recent_hourly_successes
    scheduler_changed = $proof.scheduler_changed
    database_modified = $proof.database_modified
}
$payload = [ordered]@{
    schema = 'UCIE_PUBLIC_MINER_SCHEDULER_SOURCE_FIXED_V01'
    task_found = $found
    task_state = $state
    last_task_result = $lastResult
    evidence = $boundedProof
} | ConvertTo-Json -Depth 6 -Compress
$previous = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $output = $payload | & $python -B -m ucie_miner.public_scheduler_diagnostic_v01
    $resultCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $previous
}
if ($null -eq $output) { throw 'UCIE_SCHEDULER_DIAGNOSTIC_NO_OUTPUT' }
$data = ($output | Out-String) | ConvertFrom-Json -ErrorAction Stop
if ($data.schema -cne 'UCIE_PUBLIC_MINER_SCHEDULER_DIAGNOSTIC_V01' -or
    $resultCode -ne 0) {
    throw 'UCIE_EXACT_SCHEDULER_PROOF_INVALID_NO_GO'
}
# This is still a read-only observation, not an attempt to fix the task.
$output
