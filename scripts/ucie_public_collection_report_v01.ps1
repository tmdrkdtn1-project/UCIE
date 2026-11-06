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
$taskScript = Join-Path $root 'scripts\ucie_public_miner_scheduler_diagnostic_v01.ps1'
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
    $scheduledFinishedUtc = $inventory.recent_hourly_activity.last_finished_utc
    $schedulerVerified = $false
    $diagnosis = $null
    try {
        # Exact UCIE task only; see separate fail-closed diagnostic. The
        # script never starts/stops/registers a task or executes the miner.
        $rawTask = & $taskScript
        if ($null -ne $rawTask) {
            $task = ($rawTask | Out-String) | ConvertFrom-Json -ErrorAction Stop
            if ($task.schema -ceq 'UCIE_PUBLIC_MINER_SCHEDULER_DIAGNOSTIC_V01' -and
                $task.status -in @(
                    'PUBLIC_MINER_TWO_CYCLE_SCHEDULED_EVIDENCE_OBSERVED',
                    'PUBLIC_MINER_SCHEDULER_NOT_ATTESTED_NO_GO'
                )) {
                $diagnosis = $task
                $status = [string]$task.task_evidence_status
                $eventCount = [int]$task.matched_event_instances
                $schedulerVerified = (
                    $task.status -ceq 'PUBLIC_MINER_TWO_CYCLE_SCHEDULED_EVIDENCE_OBSERVED' -and
                    $task.last_task_result_decimal -eq 0 -and
                    $task.last_task_result_interpretation -ceq 'LAST_TASK_RESULT_ZERO' -and
                    $task.matched_event_instances -eq 2 -and
                    @($task.blocker_codes).Count -eq 0 -and
                    $task.actual_task_mutation -ceq $false -and
                    $task.operating_database_writes -eq 0
                )
            }
        }
    } catch {
        # A failed diagnostic never overrides valid independent DB counts
        # and cannot be reinterpreted as successful TaskScheduler execution.
        $status = 'WINDOWS_TASK_EVENT_PROOF_UNAVAILABLE_NO_GO'
        $schedulerVerified = $false
        $eventCount = 0
        $diagnosis = $null
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
            task_state = if ($null -eq $diagnosis) { $null } else { $diagnosis.task_state }
            last_task_result_decimal = if ($null -eq $diagnosis) { $null } else { $diagnosis.last_task_result_decimal }
            last_task_result_hex = if ($null -eq $diagnosis) { $null } else { $diagnosis.last_task_result_hex }
            last_task_result_interpretation = if ($null -eq $diagnosis) { 'NOT_OBSERVED_NO_GO' } else { $diagnosis.last_task_result_interpretation }
            blocker_codes = if ($null -eq $diagnosis) { @('TASK_DIAGNOSTIC_UNAVAILABLE') } else { @($diagnosis.blocker_codes) }
            diagnostic_validated = ($null -ne $diagnosis)
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
