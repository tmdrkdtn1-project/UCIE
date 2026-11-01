# UCIE V1.2: independent Windows TaskScheduler event proof + local receipt proof.
# Read-only: no scheduler changes, no collector runs, no DB or repo writes.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_D_DRIVE_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$source = Join-Path $root 'src'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'UCIE_OWNER_PYTHON_NOT_FOUND' }
if (-not (Test-Path -LiteralPath (Join-Path $source 'ucie_miner\library_hourly_proof_v12.py') -PathType Leaf)) {
    throw 'UCIE_V12_HOURLY_PROOF_NOT_INSTALLED'
}
$original = $env:PYTHONPATH
try {
    $taskRaw = & (Join-Path $root 'scripts\task_status.ps1') -Evidence
    if ($null -eq $taskRaw) { throw 'UCIE_TASK_EVIDENCE_ABSENT' }
    $task = $taskRaw | ConvertFrom-Json -ErrorAction Stop
    $env:PYTHONPATH = $source
    $raw = & $python -B -m ucie_miner.library_hourly_proof_v12
    $pythonExit = $LASTEXITCODE
    if ($null -eq $raw) { throw 'UCIE_HOURLY_PROOF_ABSENT' }
    $cycles = $raw | ConvertFrom-Json -ErrorAction Stop
    $schedulerProven = (
        $task.schema -ceq 'UCIE_HOURLY_LOCAL_OPERATIONS_READONLY_V1' -and
        $task.status -in @(
            'TWO_CYCLE_BASE_COLLECTOR_OBSERVED',
            'TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RESUMED',
            'TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RATE_PAUSED'
        ) -and
        $task.scheduler_event_instance_receipts_verified -ge 2 -and
        $task.scheduler_event_log_readable -ceq $true -and
        $task.two_recent_hourly_successes -ceq $true -and
        $task.last_task_result_zero -ceq $true
    )
    $recent = (
        $pythonExit -eq 0 -and
        $cycles.schema -ceq 'UCIE_HOURLY_PUBLIC_LIBRARY_PROOF_V12' -and
        $cycles.status -ceq 'TWO_FRESH_CYCLE_RECEIPTS_OBSERVED_SCHEDULER_NOT_ATTESTED'
    )
    $stage12 = (
        $recent -and
        $cycles.stage_statuses.stage12_unverified_review_learning -ceq
        'STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO'
    )
    $quality = (
        $recent -and
        $cycles.stage_statuses.stage17_hourly_quality_audit -in @(
            'STAGE17_QUALITY_OBSERVED_UNVERIFIED_NO_GO',
            'STAGE17_QUALITY_REVIEW_REQUIRED_NO_GO'
        )
    )
    $result = [ordered]@{
        schema = 'UCIE_HOURLY_LIBRARY_COMBINED_ACCEPTANCE_V12'
        status = if ($schedulerProven -and $recent) {
            'HOURLY_COLLECTOR_CURRENTLY_EVIDENCED_NO_AUTO_APPROVAL'
        } else {
            'HOURLY_CURRENT_SCHEDULER_NOT_PROVEN_NO_GO'
        }
        real_scheduler_event_proof = $schedulerProven
        two_fresh_local_receipts = $recent
        last_finished_utc = $cycles.latest_finished_utc
        scheduled_task_status = $task.status
        stage10_status = $cycles.stage_statuses.stage10_public_candidate_collection
        stage12_unverified_review_automatic_pass = $stage12
        stage16_safe_qa_status = $cycles.stage_statuses.stage16_safe_candidate_qa
        stage17_automatic_quality_snapshot_observed = $quality
        stage17_quality_status = $cycles.stage_statuses.stage17_hourly_quality_audit
        stage17_owner_marker = $cycles.operator_marker_presence.stage17
        inferred_machine_learning = $false
        independent_fix_verifications = 0
        auto_promoted_rules = 0
        scheduler_changed = $false
        operating_db_changed = $false
    }
    [pscustomobject]$result | ConvertTo-Json -Depth 4 -Compress
    if (-not ($schedulerProven -and $recent)) {
        throw 'CURRENT_HOURLY_SCHEDULER_NOT_VERIFIED'
    }
} finally {
    $env:PYTHONPATH = $original
}
