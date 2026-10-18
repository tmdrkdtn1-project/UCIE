# UCIE task status, no writes and no project access.
[CmdletBinding()]
param([switch]$Evidence)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'EXPECTED_UCIE_ROOT_D_DRIVE'
}

if ($Evidence) {
    # Additional read-only operational acceptance: do not change task,
    # run miner, consume quota, sign releases or inspect user project files.
    $now = [DateTimeOffset]::UtcNow
    $task = Get-ScheduledTask -TaskPath '\' -TaskName 'UCIE-PublicMiner-Hourly' -ErrorAction SilentlyContinue
    $info = if ($null -ne $task) {
        Get-ScheduledTaskInfo -TaskPath '\' -TaskName 'UCIE-PublicMiner-Hourly'
    } else { $null }
    $actionOk = $false
    $principalOk = $false
    $cadenceConfigured = $false
    $lastResultOk = $false
    $scheduleNextUtc = $null
    $lastTaskUtc = $null
    if ($null -ne $task -and $null -ne $info) {
        $actions = @($task.Actions)
        if ($actions.Count -eq 1) {
            $a = $actions[0]
            $expectedPython = Join-Path $root '.venv\Scripts\python.exe'
            $expectedWorker = Join-Path $root 'scripts\public_miner_cycle.py'
            $expectedArgs = '"' + $expectedWorker + '"'
            $actionOk = (
                [string]::Equals($a.Execute, $expectedPython, [StringComparison]::OrdinalIgnoreCase) -and
                [string]::Equals($a.Arguments, $expectedArgs, [StringComparison]::Ordinal) -and
                [string]::Equals($a.WorkingDirectory.TrimEnd('\'), $root, [StringComparison]::OrdinalIgnoreCase)
            )
        }
        $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $principalOk = (
            [string]::Equals($task.Principal.UserId, $me, [StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals([string]$task.Principal.LogonType, 'Interactive', [StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals([string]$task.Principal.RunLevel, 'Limited', [StringComparison]::OrdinalIgnoreCase)
        )
        $intervals = @($task.Triggers | ForEach-Object { [string]$_.Repetition.Interval })
        $cadenceConfigured = (
            $intervals.Count -eq 1 -and $intervals[0] -eq 'PT1H' -and
            [string]::Equals([string]$task.Settings.MultipleInstances, 'IgnoreNew', [StringComparison]::OrdinalIgnoreCase)
        )
        $lastResultOk = ($info.LastTaskResult -eq 0)
        if ($info.LastRunTime -gt [datetime]::MinValue) {
            $lastTaskUtc = ([DateTimeOffset]$info.LastRunTime).ToUniversalTime()
        }
        if ($info.NextRunTime -gt [datetime]::MinValue) {
            $scheduleNextUtc = $info.NextRunTime.ToUniversalTime().ToString('o')
        }
    }
    $receipts = @()
    $history = Join-Path $root 'runtime\run_history.jsonl'
    $historyReadable = $false
    if ((Test-Path -LiteralPath $history -PathType Leaf) -and
        -not ((Get-Item -LiteralPath $history).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        try {
            $lines = @(Get-Content -LiteralPath $history -Tail 2 -Encoding UTF8 -ErrorAction Stop)
            foreach ($line in $lines) {
                if ([System.Text.Encoding]::UTF8.GetByteCount($line) -gt 4096) {
                    throw 'OVERSIZED_OPERATING_RECEIPT'
                }
                $receipts += ($line | ConvertFrom-Json -ErrorAction Stop)
            }
            $historyReadable = $true
        } catch {
            # Fail closed without printing potentially untrusted exception content.
            $receipts = @()
            $historyReadable = $false
        }
    }
    $twoCyclesOk = $false
    $taskReceiptBound = $false
    $priorStage13 = 'UNOBSERVED'
    $lastFinishedUtc = $null
    $stage13 = 'UNOBSERVED'
    $stage12 = 'UNOBSERVED'
    $lastStatus = 'UNOBSERVED'
    $gapMinutes = $null
    if ($receipts.Count -gt 0) {
        $latest = $receipts[-1]
        $lastStatus = [string]$latest.status
        $stage13 = [string]$latest.stage13_history_status
        $stage12 = [string]$latest.stage12_review_status
        try {
            if ($receipts.Count -eq 2) {
                $previous = $receipts[0]
                $priorStage13 = [string]$previous.stage13_history_status
                $pStart = [DateTimeOffset]::Parse([string]$previous.started_utc)
                $pEnd = [DateTimeOffset]::Parse([string]$previous.finished_utc)
                $cStart = [DateTimeOffset]::Parse([string]$latest.started_utc)
                $cEnd = [DateTimeOffset]::Parse([string]$latest.finished_utc)
                $lastFinishedUtc = $cEnd.ToUniversalTime().ToString('o')
                $gapMinutes = [Math]::Round(($cStart - $pStart).TotalMinutes, 2)
                if ($null -ne $lastTaskUtc) {
                    # A successful scheduler exit alone may be stale or belong
                    # to a skipped run. Bind it to the newest persisted cycle.
                    $taskReceiptBound = (
                        [Math]::Abs(($cStart.ToUniversalTime() - $lastTaskUtc).TotalMinutes) -le 10 -and
                        $lastTaskUtc -ge $now.AddMinutes(-90) -and
                        $lastTaskUtc -le $now.AddMinutes(5)
                    )
                }
                $twoCyclesOk = (
                    $previous.schema -ceq 'UCIE_MINER_CYCLE_V1' -and
                    $latest.schema -ceq 'UCIE_MINER_CYCLE_V1' -and
                    $previous.status -ceq 'COLLECTED_UNVERIFIED' -and
                    $latest.status -ceq 'COLLECTED_UNVERIFIED' -and
                    $previous.production_approved -ceq $false -and
                    $latest.production_approved -ceq $false -and
                    $previous.verification_pass -eq 0 -and
                    $latest.verification_pass -eq 0 -and
                    $previous.consecutive_failures -eq 0 -and
                    $latest.consecutive_failures -eq 0 -and
                    $pStart -le $pEnd -and $pEnd -le $cStart -and
                    $cStart -le $cEnd -and $cEnd -le $now.AddMinutes(5) -and
                    $cEnd -ge $now.AddMinutes(-90) -and
                    $gapMinutes -ge 45 -and $gapMinutes -le 75
                )
            }
        } catch {
            $twoCyclesOk = $false
            $taskReceiptBound = $false
        }
    }
    $pauseThenResumed = ($twoCyclesOk -and $taskReceiptBound -and
        $priorStage13 -ceq 'EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO' -and
        $stage13 -ceq 'EXTERNAL_HISTORY_BACKFILL_OK_NO_GO')
    $taskStatus = if ($null -eq $task) { 'NOT_REGISTERED_NO_GO' }
                  elseif (-not $actionOk -or -not $principalOk -or -not $cadenceConfigured) { 'TASK_IDENTITY_OR_CADENCE_NO_GO' }
                  elseif (-not $lastResultOk) { 'LAST_TASK_RESULT_NO_GO' }
                  elseif (-not $historyReadable -or -not $twoCyclesOk) { 'TWO_RECENT_HOURLY_CYCLES_NOT_PROVEN_NO_GO' }
                  elseif (-not $taskReceiptBound) { 'LAST_SCHEDULED_RUN_RECEIPT_MISMATCH_NO_GO' }
                  elseif ($pauseThenResumed) { 'TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RESUMED' }
                  elseif ($stage13 -ceq 'EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO') { 'TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RATE_PAUSED' }
                  else { 'TWO_CYCLE_BASE_COLLECTOR_OBSERVED' }
    [pscustomobject]@{
        schema = 'UCIE_HOURLY_LOCAL_OPERATIONS_READONLY_V1'
        status = $taskStatus
        observed_utc = $now.ToString('o')
        scheduled_task_registered = ($null -ne $task)
        task_state = if ($null -eq $task) { 'ABSENT' } else { [string]$task.State }
        action_matches_ucie_only = $actionOk
        owner_least_privilege_verified = $principalOk
        hourly_no_overlap_configured = $cadenceConfigured
        last_task_result_zero = $lastResultOk
        last_scheduled_run_utc = if ($null -eq $lastTaskUtc) { $null } else { $lastTaskUtc.ToString('o') }
        last_scheduled_run_matches_receipt = $taskReceiptBound
        next_scheduled_utc = $scheduleNextUtc
        last_cycle_finished_utc = $lastFinishedUtc
        last_cycle_status = $lastStatus
        two_recent_hourly_successes = ($twoCyclesOk -and $taskReceiptBound)
        observed_start_gap_minutes = $gapMinutes
        stage12_review_status = $stage12
        stage13_history_status = $stage13
        stage13_rate_pause_protected = ($stage13 -ceq 'EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO')
        stage13_pause_then_success_observed = $pauseThenResumed
        # A successful next page alone does not prove the GitHub reset timestamp.
        stage13_resumed_after_quota_reset = $false
        scheduler_changed = $false
        database_modified = $false
        private_projects_accessed = $false
        candidates_auto_approved = 0
        production_approved = $false
    } | ConvertTo-Json -Depth 4 -Compress
    return
}

$taskName = 'UCIE-PublicMiner-Hourly'
$task = Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Output 'TASK_STATUS=NOT_REGISTERED'
} else {
    $task | Select-Object TaskName, State
    Get-ScheduledTaskInfo -TaskPath '\' -TaskName $taskName |
        Select-Object LastRunTime, NextRunTime, LastTaskResult
}
$last = Join-Path $root 'runtime\last_run.json'
if (Test-Path -LiteralPath $last -PathType Leaf) {
    Write-Output 'LAST_UCIE_RUN_RECEIPT:'
    Get-Content -LiteralPath $last -Raw -Encoding UTF8
} else {
    Write-Output 'LAST_UCIE_RUN_RECEIPT=NOT_FOUND'
}
