# UCIE only. Default is PREVIEW; -Apply updates ONE exact current-user task trigger.
# No collector invocation, API call, new registration, disable, stop or deletion.
[CmdletBinding()]
param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$taskName = 'UCIE-PublicMiner-Hourly'
$taskPath = '\'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase) -or
    ((Get-Item -LiteralPath $root).Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
    -not (Test-Path -LiteralPath (Join-Path $root '.git') -PathType Container)) {
    throw 'UCIE_EXACT_OWNER_ROOT_REQUIRED'
}
$policyPath = Join-Path $root 'src\ucie_miner\schedule_policy.py'
$evidencePath = Join-Path $root 'scripts\task_status.ps1'
if (-not (Test-Path -LiteralPath $policyPath -PathType Leaf) -or
    -not (Test-Path -LiteralPath $evidencePath -PathType Leaf) -or
    ((Get-Item -LiteralPath $policyPath).Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
    ((Get-Item -LiteralPath $evidencePath).Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
    throw 'UCIE_LOCAL_POLICY_OR_EVIDENCE_MISSING'
}
$policyText = Get-Content -LiteralPath $policyPath -Raw -Encoding UTF8
$evidenceText = Get-Content -LiteralPath $evidencePath -Raw -Encoding UTF8
if (-not $policyText.Contains('INTERVAL = timedelta(minutes=10)') -or
    -not $evidenceText.Contains("$" + "intervals[0] -eq 'PT10M'")) {
    throw 'UCIE_TEN_MINUTE_SOURCE_CONTRACT_NOT_INSTALLED'
}

$task = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) { throw 'EXACT_UCIE_TASK_MISSING_NO_GO' }
$actions = @($task.Actions)
$triggers = @($task.Triggers)
$expectedPy = Join-Path $root '.venv\Scripts\python.exe'
$expectedWorker = Join-Path $root 'scripts\public_miner_cycle.py'
$expectedArg = '"' + $expectedWorker + '"'
if ($actions.Count -ne 1 -or $triggers.Count -ne 1 -or
    -not [string]::Equals([string]$actions[0].Execute, $expectedPy,
                         [StringComparison]::OrdinalIgnoreCase) -or
    -not [string]::Equals([string]$actions[0].Arguments, $expectedArg,
                         [StringComparison]::Ordinal) -or
    -not [string]::Equals([string]$actions[0].WorkingDirectory.TrimEnd('\'), $root,
                         [StringComparison]::OrdinalIgnoreCase) -or
    -not (Test-Path -LiteralPath $expectedPy -PathType Leaf) -or
    -not [string]::Equals([string]$task.Principal.LogonType, 'Interactive',
                         [StringComparison]::OrdinalIgnoreCase) -or
    -not [string]::Equals([string]$task.Principal.RunLevel, 'Limited',
                         [StringComparison]::OrdinalIgnoreCase) -or
    -not [string]::Equals([string]$task.Settings.MultipleInstances, 'IgnoreNew',
                         [StringComparison]::OrdinalIgnoreCase)) {
    throw 'EXACT_UCIE_TASK_ACTION_PRINCIPAL_SETTINGS_MISMATCH_NO_GO'
}
try {
    $identity = [string]$task.Principal.UserId
    $ownerSid = if ($identity -match '^S-[0-9]+-[0-9]+(-[0-9]+)+$') {
        [System.Security.Principal.SecurityIdentifier]::new($identity)
    } else {
        ([System.Security.Principal.NTAccount]::new($identity)).Translate(
            [System.Security.Principal.SecurityIdentifier])
    }
    $currentSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    if (-not $ownerSid.Equals($currentSid)) {
        throw 'WRONG_OWNER_SID'
    }
} catch { throw 'EXACT_UCIE_CURRENT_OWNER_SID_REQUIRED' }
$oldInterval = [string]$triggers[0].Repetition.Interval
if ($oldInterval -notin @('PT1H', 'PT10M')) {
    throw 'EXISTING_CADENCE_NOT_THE_APPROVED_60M_OR_10M_NO_GO'
}
if ([string]$task.State -ne 'Ready') { throw 'UCIE_TASK_MUST_BE_READY' }
try {
    $oldDuration = [System.Xml.XmlConvert]::ToTimeSpan(
        [string]$triggers[0].Repetition.Duration)
    if ($oldDuration.TotalDays -lt 1 -or $oldDuration.TotalDays -gt 3650) {
        throw 'UNEXPECTED_REPEAT_DURATION'
    }
} catch { throw 'UNEXPECTED_REPEAT_DURATION_NO_GO' }

$info = Get-ScheduledTaskInfo -TaskPath $taskPath -TaskName $taskName
if (-not $Apply) {
    [pscustomobject]@{
        schema = 'UCIE_PUBLIC_MINER_10MIN_OWNER_CADENCE_V1'
        status = 'PREVIEW_ONLY_NO_TASK_CHANGES'
        existing_interval = $oldInterval
        requested_interval = 'PT10M'
        exact_task_action_and_owner_verified = $true
        existing_last_task_result = [int64]$info.LastTaskResult
        collection_run_requested = $false
        scheduler_changed = $false
        queue_or_database_modified = $false
        production_approved = $false
    } | ConvertTo-Json -Compress
    return
}
if ($oldInterval -eq 'PT10M') {
    [pscustomobject]@{
        schema = 'UCIE_PUBLIC_MINER_10MIN_OWNER_CADENCE_V1'
        status = 'ALREADY_AT_10_MINUTES_NO_CHANGE'
        existing_interval = 'PT10M'
        collection_run_requested = $false
        scheduler_changed = $false
        queue_or_database_modified = $false
        production_approved = $false
    } | ConvertTo-Json -Compress
    return
}

# First new trigger in 10 minutes. Preserve the existing repetition duration
# and all other task properties; do NOT Start-ScheduledTask.
$newTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(10) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration $oldDuration
$updateReturnedSuccess = $false
try {
    Set-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Trigger $newTrigger -ErrorAction Stop | Out-Null
    $updateReturnedSuccess = $true
    $after = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
    $a = @($after.Actions)
    $t = @($after.Triggers)
    if ($a.Count -ne 1 -or $t.Count -ne 1 -or
        [string]$t[0].Repetition.Interval -ne 'PT10M' -or
        -not [string]::Equals([string]$a[0].Execute, $expectedPy,
                             [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals([string]$a[0].Arguments, $expectedArg,
                             [StringComparison]::Ordinal) -or
        -not [string]::Equals([string]$a[0].WorkingDirectory.TrimEnd('\'), $root,
                             [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals([string]$after.Principal.UserId, $identity,
                             [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals([string]$after.Settings.MultipleInstances,
                             'IgnoreNew', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'POST_UPDATE_IDENTITY_OR_INTERVAL_DRIFT'
    }
} catch {
    # Do NOT print exception messages: they may contain local paths or secrets.
    # Preserve only a bounded exception class, numeric HRESULT, and enum category.
    $errorClass = [string]$_.Exception.GetType().Name
    if ($errorClass -notmatch '^[A-Za-z0-9_]{1,64}$') { $errorClass = 'UNKNOWN' }
    $hresult = ('{0:X8}' -f ([long]$_.Exception.HResult -band 4294967295))
    $errorCategory = [string]$_.CategoryInfo.Category
    if ($errorCategory -notmatch '^[A-Za-z]{1,36}$') { $errorCategory = 'OTHER' }
    $seen = $null
    try {
        $seen = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
    } catch {
        $seen = $null
    }
    $sameOriginal = $false
    $seenInterval = 'UNREADABLE'
    if ($null -ne $seen) {
        $seenActions = @($seen.Actions)
        $seenTriggers = @($seen.Triggers)
        if ($seenTriggers.Count -eq 1) {
            $seenInterval = [string]$seenTriggers[0].Repetition.Interval
        }
        $sameOriginal = (
            $seenActions.Count -eq 1 -and $seenTriggers.Count -eq 1 -and
            [string]$seenTriggers[0].Repetition.Interval -ceq $oldInterval -and
            [string]$seenTriggers[0].Repetition.Duration -ceq [string]$triggers[0].Repetition.Duration -and
            [string]$seenTriggers[0].StartBoundary -ceq [string]$triggers[0].StartBoundary -and
            [string]::Equals([string]$seenActions[0].Execute, $expectedPy,
                             [StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals([string]$seenActions[0].Arguments, $expectedArg,
                             [StringComparison]::Ordinal) -and
            [string]::Equals([string]$seen.Principal.UserId, $identity,
                             [StringComparison]::OrdinalIgnoreCase)
        )
    }
    if ($sameOriginal) {
        # The first Set failed without changing the task. A second Set cannot
        # help and can mask the original error; do NOT attempt rollback.
        [pscustomobject]@{
            schema = 'UCIE_PUBLIC_MINER_10MIN_OWNER_CADENCE_V1'
            status = 'SET_FAILED_ORIGINAL_PT1H_INTACT_NO_ROLLBACK_NEEDED'
            original_interval = $oldInterval
            observed_interval = $seenInterval
            set_error_type = $errorClass
            set_error_hresult = $hresult
            set_error_category = $errorCategory
            scheduler_changed = $false
            collection_run_requested = $false
            queue_or_database_modified = $false
            production_approved = $false
        } | ConvertTo-Json -Compress
        throw 'UCIE_SET_TASK_REJECTED_ORIGINAL_CONFIGURATION_VERIFIED'
    }
    if (-not $updateReturnedSuccess) {
        # An error before Set returned success, yet task is no longer exactly
        # original (or cannot be read). Do not perform a blind second write.
        throw ('UCIE_SET_TASK_ERROR_STATE_UNCERTAIN_NO_BLIND_ROLLBACK_' +
               $errorClass + '_0x' + $hresult)
    }
    # The Set returned success, but post-verification detected drift.
    # Attempt ONE rollback, and verify it rather than assuming success.
    try {
        Set-ScheduledTask -TaskPath $taskPath -TaskName $taskName -Trigger $triggers[0] -ErrorAction Stop | Out-Null
        $restored = Get-ScheduledTask -TaskPath $taskPath -TaskName $taskName -ErrorAction Stop
        $rt = @($restored.Triggers)
        if ($rt.Count -ne 1 -or
            [string]$rt[0].Repetition.Interval -cne $oldInterval -or
            [string]$rt[0].StartBoundary -cne [string]$triggers[0].StartBoundary) {
            throw 'ROLLBACK_NOT_VERIFIED'
        }
    } catch {
        throw ('UCIE_POST_VERIFY_FAILED_ROLLBACK_UNCONFIRMED_' +
               $errorClass + '_0x' + $hresult)
    }
    throw ('UCIE_POST_VERIFY_FAILED_ROLLBACK_VERIFIED_' +
           $errorClass + '_0x' + $hresult)
}
$next = Get-ScheduledTaskInfo -TaskPath $taskPath -TaskName $taskName
[pscustomobject]@{
    schema = 'UCIE_PUBLIC_MINER_10MIN_OWNER_CADENCE_V1'
    status = 'EXACT_TASK_SET_TO_10_MINUTES'
    previous_interval = $oldInterval
    current_interval = 'PT10M'
    next_scheduled_utc = $next.NextRunTime.ToUniversalTime().ToString('o')
    scheduler_changed = $true
    collection_run_requested = $false
    queue_or_database_modified = $false
    production_approved = $false
} | ConvertTo-Json -Compress
