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
    $windowlessAction = $false
    $principalOk = $false
    $principalUserMatches = $false
    $principalIdentityResolution = 'UNOBSERVED_NO_GO'
    $principalLogonType = 'UNOBSERVED'
    $principalRunLevel = 'UNOBSERVED'
    $cadenceConfigured = $false
    $lastResultOk = $false
    $scheduleNextUtc = $null
    $lastTaskUtc = $null
    if ($null -ne $task -and $null -ne $info) {
        $actions = @($task.Actions)
        if ($actions.Count -eq 1) {
            $a = $actions[0]
            $expectedPython = Join-Path $root '.venv\Scripts\python.exe'
            $expectedPythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
            $expectedWorker = Join-Path $root 'scripts\public_miner_cycle.py'
            $expectedArgs = '"' + $expectedWorker + '"'
            $windowlessAction = [string]::Equals(
                [string]$a.Execute, $expectedPythonw, [StringComparison]::OrdinalIgnoreCase)
            $knownLegacyAction = [string]::Equals(
                [string]$a.Execute, $expectedPython, [StringComparison]::OrdinalIgnoreCase)
            $actionOk = (
                ($windowlessAction -or $knownLegacyAction) -and
                [string]::Equals($a.Arguments, $expectedArgs, [StringComparison]::Ordinal) -and
                [string]::Equals($a.WorkingDirectory.TrimEnd('\'), $root, [StringComparison]::OrdinalIgnoreCase)
            )
        }
        # Compare security identities, not account display-name spelling.
        # No account name or SID is printed to the evidence report.
        $processSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
        $taskUserId = [string]$task.Principal.UserId
        $principalIdentityResolution = 'UNRESOLVED_NO_GO'
        if (-not [string]::IsNullOrWhiteSpace($taskUserId)) {
            try {
                $taskSid = if ($taskUserId -match '^S-[0-9]+-[0-9]+(-[0-9]+)+$') {
                    [System.Security.Principal.SecurityIdentifier]::new($taskUserId)
                } else {
                    ([System.Security.Principal.NTAccount]::new($taskUserId)).Translate(
                        [System.Security.Principal.SecurityIdentifier])
                }
                $principalUserMatches = $taskSid.Equals($processSid)
                $principalIdentityResolution = if ($principalUserMatches) {
                    'SAME_USER_SID'
                } else {
                    'DIFFERENT_USER_SID_NO_GO'
                }
            } catch {
                $principalIdentityResolution = 'UNRESOLVED_NO_GO'
            }
        }
        $principalLogonType = [string]$task.Principal.LogonType
        $principalRunLevel = [string]$task.Principal.RunLevel
        $principalOk = (
            $principalUserMatches -and
            [string]::Equals($principalLogonType, 'Interactive', [StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals($principalRunLevel, 'Limited', [StringComparison]::OrdinalIgnoreCase)
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
    $eventLogReadable = $false
    $eventProofCount = 0
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
                # LastRunTime is informational only: on the owner host it can
                # differ from the actual start by 27 seconds. Never relax
                # receipt chronology or grant a PASS solely from that field.
                # Filter at the Windows event service for this ONE UCIE task;
                # do not enumerate or inspect other projects' task events.
                $eventInstances = @{}
                try {
                    $eventXPath = "*[System[(EventID=100 or EventID=102 or EventID=200 or EventID=201) and TimeCreated[timediff(@SystemTime) <= 10800000]] and EventData[Data[@Name='TaskName']='\UCIE-PublicMiner-Hourly']]"
                    $events = @(Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -FilterXPath $eventXPath -MaxEvents 64 -ErrorAction Stop)
                    $eventLogReadable = $true
                    foreach ($event in $events) {
                        if ($event.Id -notin @(100, 102, 200, 201)) { continue }
                        [xml]$xml = $event.ToXml()
                        $eventData = $xml.SelectSingleNode("/*[local-name()='Event']/*[local-name()='EventData']")
                        if ($null -eq $eventData) { continue }
                        $taskNode = $eventData.SelectSingleNode("./*[local-name()='Data' and @Name='TaskName']")
                        if ($null -eq $taskNode -or $taskNode.InnerText -cne '\UCIE-PublicMiner-Hourly') { continue }
                        $idField = if ($event.Id -in @(100, 102)) { 'InstanceId' } else { 'TaskInstanceId' }
                        $instanceNode = $eventData.SelectSingleNode("./*[local-name()='Data' and @Name='$idField']")
                        $guid = [guid]::Empty
                        if ($null -eq $instanceNode -or
                            -not [guid]::TryParse([string]$instanceNode.InnerText, [ref]$guid)) { continue }
                        $key = $guid.ToString('D')
                        if (-not $eventInstances.ContainsKey($key)) { $eventInstances[$key] = @{} }
                        $instance = $eventInstances[$key]
                        $eventKind = [string]$event.Id
                        # Duplicate records for one event type are ambiguous.
                        if ($instance.ContainsKey($eventKind)) { $instance['duplicate'] = $true; continue }
                        $actionNode = $eventData.SelectSingleNode("./*[local-name()='Data' and @Name='ActionName']")
                        $codeNode = $eventData.SelectSingleNode("./*[local-name()='Data' and @Name='ResultCode']")
                        $instance[$eventKind] = [pscustomobject]@{
                            utc = ([DateTimeOffset]$event.TimeCreated).ToUniversalTime()
                            action = if ($null -eq $actionNode) { '' } else { [string]$actionNode.InnerText }
                            result = if ($null -eq $codeNode) { '' } else { [string]$codeNode.InnerText }
                        }
                    }
                } catch {
                    # No event history / access denied / malformed evidence:
                    # fail closed; never fall back to LastRunTime heuristics.
                    $eventLogReadable = $false
                    $eventInstances = @{}
                }
                if ($eventLogReadable) {
                    $expectedAction = Join-Path $root '.venv\Scripts\python.exe'
                    $pairs = @(
                        [pscustomobject]@{ start = $pStart; finish = $pEnd },
                        [pscustomobject]@{ start = $cStart; finish = $cEnd }
                    )
                    foreach ($pair in $pairs) {
                        $matched = 0
                        foreach ($instance in $eventInstances.Values) {
                            if ($instance.Count -ne 4 -or
                                -not ($instance.ContainsKey('100') -and $instance.ContainsKey('102') -and
                                      $instance.ContainsKey('200') -and $instance.ContainsKey('201'))) { continue }
                            $t100 = $instance['100'].utc
                            $t200 = $instance['200'].utc
                            $t201 = $instance['201'].utc
                            $t102 = $instance['102'].utc
                            if (-not ([string]::Equals($instance['200'].action, $expectedAction, [StringComparison]::OrdinalIgnoreCase) -and
                                      [string]::Equals($instance['201'].action, $expectedAction, [StringComparison]::OrdinalIgnoreCase) -and
                                      $instance['201'].result -ceq '0')) { continue }
                            if ($t100 -gt $t200 -or $t200 -gt $t201 -or $t201 -gt $t102 -or
                                ($t200 - $t100).TotalSeconds -gt 10 -or
                                ($t102 - $t201).TotalSeconds -gt 10 -or
                                ($t102 - $t100).TotalMinutes -gt 10) { continue }
                            # Actual worker receipt must start with this action
                            # and finish before its successful completion.
                            # Only two seconds of timestamp-rounding slack.
                            if ($pair.start -ge $t100.AddSeconds(-2) -and
                                $pair.start -le $t200.AddSeconds(10) -and
                                $pair.finish -ge $t201.AddSeconds(-10) -and
                                $pair.finish -le $t102.AddSeconds(2)) { $matched++ }
                        }
                        if ($matched -eq 1) { $eventProofCount++ }
                    }
                    $taskReceiptBound = ($eventProofCount -eq 2)
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
                  elseif (-not $eventLogReadable) { 'TASK_SCHEDULER_EVENT_LOG_UNAVAILABLE_NO_GO' }
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
        task_uses_pythonw_without_main_console = $windowlessAction
        owner_least_privilege_verified = $principalOk
        principal_user_matches_current_process = $principalUserMatches
        principal_identity_resolution = $principalIdentityResolution
        principal_logon_type = $principalLogonType
        principal_run_level = $principalRunLevel
        hourly_no_overlap_configured = $cadenceConfigured
        last_task_result_zero = $lastResultOk
        last_scheduled_run_utc = if ($null -eq $lastTaskUtc) { $null } else { $lastTaskUtc.ToString('o') }
        last_scheduled_run_matches_receipt = $taskReceiptBound
        scheduler_event_log_readable = $eventLogReadable
        scheduler_event_instance_receipts_verified = $eventProofCount
        scheduler_binding_method = 'INSTANCE_GUID_EVENTS_100_200_201_102'
        task_info_last_run_time_used_for_binding = $false
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
