# UCIE public-only count report + independent Windows TaskScheduler evidence.
# Read-only on demand; no miner run, DB write, package promotion or Task mutation.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$module = Join-Path $root 'src\ucie_miner\public_collection_inventory_v01.py'
$taskScript = Join-Path $root 'scripts\task_status.ps1'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $module -PathType Leaf) -or
    -not (Test-Path -LiteralPath $taskScript -PathType Leaf)) {
    throw 'UCIE_COLLECTION_REPORT_PREREQUISITES_MISSING'
}
$original = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $raw = & $python -B -m ucie_miner.public_collection_inventory_v01 --format json
    $pythonExit = $LASTEXITCODE
    if ($null -eq $raw) { throw 'UCIE_INVENTORY_OUTPUT_MISSING' }
    $inventory = ($raw | Out-String) | ConvertFrom-Json -ErrorAction Stop
    if ($inventory.schema -cne 'UCIE_PUBLIC_COLLECTION_INVENTORY_READONLY_V01') {
        throw 'UCIE_INVENTORY_SCHEMA_UNEXPECTED'
    }
    $status = 'WINDOWS_TASK_EVENT_PROOF_UNAVAILABLE_NO_GO'
    $eventCount = 0
    $scheduledFinishedUtc = $null
    $schedulerVerified = $false
    try {
        $rawTask = & $taskScript -Evidence
        if ($null -ne $rawTask) {
            $task = ($rawTask | Out-String) | ConvertFrom-Json -ErrorAction Stop
            $allowed = @(
                'TWO_CYCLE_BASE_COLLECTOR_OBSERVED',
                'TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RESUMED',
                'TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RATE_PAUSED'
            )
            if ($task.schema -ceq 'UCIE_HOURLY_LOCAL_OPERATIONS_READONLY_V1') {
                $status = [string]$task.status
                $eventCount = [int]$task.scheduler_event_instance_receipts_verified
                $scheduledFinishedUtc = $task.last_cycle_finished_utc
                $schedulerVerified = (
                    $task.status -in $allowed -and
                    $task.scheduler_event_log_readable -ceq $true -and
                    $task.scheduler_event_instance_receipts_verified -ge 2 -and
                    $task.two_recent_hourly_successes -ceq $true -and
                    $task.last_task_result_zero -ceq $true -and
                    $task.last_scheduled_run_matches_receipt -ceq $true -and
                    $task.scheduler_changed -ceq $false -and
                    $task.database_modified -ceq $false
                )
            }
        }
    } catch {
        $status = 'WINDOWS_TASK_EVENT_PROOF_UNAVAILABLE_NO_GO'
        $schedulerVerified = $false
        $eventCount = 0
        $scheduledFinishedUtc = $null
    }
    $countValid = (
        $pythonExit -eq 0 -and
        $inventory.status -ceq 'COLLECTION_LEDGER_COUNTS_OBSERVED_SCHEDULER_UNATTESTED'
    )
    $verdict = if ($countValid -and $schedulerVerified) {
        'UCIE_COLLECTION_AND_WINDOWS_SCHEDULED_RUN_OBSERVED_NO_AUTO_APPROVAL'
    } elseif ($countValid) {
        'UCIE_COUNTS_OBSERVED_WINDOWS_SCHEDULER_NOT_PROVEN_NO_GO'
    } else {
        'UCIE_INVENTORY_INCOMPLETE_NO_GO'
    }
    [pscustomobject][ordered]@{
        schema = 'UCIE_PUBLIC_COLLECTION_OWNER_REPORT_V01'
        status = $verdict
        counts = $inventory
        task_scheduler = [ordered]@{
            status = $status
            exact_task_event_proof_verified = $schedulerVerified
            event_receipts_verified = $eventCount
            last_cycle_finished_utc = $scheduledFinishedUtc
        }
        report_files_written = 0
        operating_database_writes = 0
        scheduled_tasks_changed = $false
        other_project_access = $false
        public_network_requests = 0
        auto_approved_rules = 0
    } | ConvertTo-Json -Depth 12 -Compress
} finally {
    $env:PYTHONPATH = $original
}
