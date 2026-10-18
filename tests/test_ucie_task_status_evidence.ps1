# Windows PowerShell 5.1 synthetic task-evidence acceptance.
# Only UCIE-authored source block, mocked Task Scheduler and temp receipts.
# No actual scheduled task enumeration, registration or user DB access.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$path = Join-Path $repo 'scripts\task_status.ps1'
$tokens = $null
$errorsFound = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $path, [ref]$tokens, [ref]$errorsFound)
if ($errorsFound.Count -ne 0) { throw 'UCIE_STATUS_SYNTAX_NO_GO' }
$blocks = @($ast.FindAll({
    param($node)
    if ($node -isnot [System.Management.Automation.Language.IfStatementAst]) {
        return $false
    }
    return ($node.Clauses.Count -gt 0 -and
        $node.Clauses[0].Item1.Extent.Text.Trim() -ceq '$Evidence')
}, $true))
if ($blocks.Count -ne 1) { throw 'UCIE_EVIDENCE_AST_BRANCH_NO_GO' }
$extent = $blocks[0].Clauses[0].Item2.Extent.Text
if (-not ($extent.StartsWith('{') -and $extent.EndsWith('}'))) {
    throw 'UCIE_EVIDENCE_BODY_NO_GO'
}
$evaluator = [ScriptBlock]::Create($extent.Substring(1, $extent.Length - 2))
$root = Join-Path ([System.IO.Path]::GetTempPath()) ('UCIE_HOURLY_SYNTH_' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path (Join-Path $root 'runtime') -Force
$script:mockBadAction = $false
$script:mockBadOwner = $false
$script:mockExit = 0
$script:mockLastRunMinutesAgo = 5
function Get-ScheduledTask {
    param($TaskPath, $TaskName, $ErrorAction)
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if ($script:mockBadAction) { $python = Join-Path $root 'unknown.exe' }
    $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    if ($script:mockBadOwner) { $user = 'unrecognized-ucie-principal' }
    return [pscustomobject]@{
        Actions = @([pscustomobject]@{
            Execute = $python
            Arguments = ('"' + (Join-Path $root 'scripts\public_miner_cycle.py') + '"')
            WorkingDirectory = $root
        })
        Principal = [pscustomobject]@{
            UserId = $user; LogonType = 'Interactive'; RunLevel = 'Limited'
        }
        Triggers = @([pscustomobject]@{
            Repetition = [pscustomobject]@{Interval = 'PT1H'}
        })
        Settings = [pscustomobject]@{ MultipleInstances = 'IgnoreNew' }
        State = 'Ready'
    }
}
function Get-ScheduledTaskInfo {
    param($TaskPath, $TaskName)
    return [pscustomobject]@{
        LastTaskResult = $script:mockExit
        LastRunTime = [datetime]::Now.AddMinutes(-$script:mockLastRunMinutesAgo)
        NextRunTime = [datetime]::Now.AddMinutes(55)
    }
}
function Write-SyntheticReceipts {
    param([string]$LastStage, [string]$LastStatus = 'COLLECTED_UNVERIFIED',
          [int]$GapMinutes = 60,
          [string]$PreviousStage = 'EXTERNAL_HISTORY_BACKFILL_OK_NO_GO')
    $base = [DateTimeOffset]::UtcNow.AddMinutes(-65)
    $two = @()
    foreach ($i in 0,1) {
        $start = $base.AddMinutes($i * $GapMinutes)
        $two += @{
            schema = 'UCIE_MINER_CYCLE_V1'
            status = if ($i -eq 1) { $LastStatus } else { 'COLLECTED_UNVERIFIED' }
            started_utc = $start.ToString('o')
            finished_utc = $start.AddSeconds(8).ToString('o')
            sources_checked = 2
            consecutive_failures = 0
            verification_pass = 0
            production_approved = $false
            stage13_history_status = if ($i -eq 1) { $LastStage }
                else { $PreviousStage }
            stage12_review_status = 'STAGE12_UNVERIFIED_REVIEW_UPDATED_NO_GO'
        }
    }
    $lines = @($two | ForEach-Object { ConvertTo-Json -InputObject $_ -Compress -Depth 4 })
    [System.IO.File]::WriteAllLines(
        (Join-Path $root 'runtime\run_history.jsonl'),
        $lines, (New-Object System.Text.UTF8Encoding($false)))
}
try {
    Write-SyntheticReceipts -LastStage 'EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO'
    $report = (& $evaluator | ConvertFrom-Json)
    if ($report.status -cne 'TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RATE_PAUSED' -or
        -not $report.two_recent_hourly_successes -or
        -not $report.stage13_rate_pause_protected -or
        -not $report.action_matches_ucie_only -or
        -not $report.owner_least_privilege_verified -or
        -not $report.hourly_no_overlap_configured -or
        -not $report.last_scheduled_run_matches_receipt -or
        $report.candidates_auto_approved -ne 0 -or
        $report.database_modified -ne $false) {
        throw 'UCIE_HOURLY_RATE_BUDGET_STATE_NO_GO'
    }
    Write-SyntheticReceipts -LastStage 'EXTERNAL_HISTORY_BACKFILL_OK_NO_GO'
    $normal = (& $evaluator | ConvertFrom-Json)
    if ($normal.status -cne 'TWO_CYCLE_BASE_COLLECTOR_OBSERVED') {
        throw 'UCIE_HOURLY_TWO_CYCLE_STATE_NO_GO'
    }
    Write-SyntheticReceipts -LastStage 'EXTERNAL_HISTORY_BACKFILL_OK_NO_GO' -PreviousStage 'EXTERNAL_HISTORY_RATE_BUDGET_PAUSED_NO_GO'
    $resumed = (& $evaluator | ConvertFrom-Json)
    if ($resumed.status -cne 'TWO_CYCLE_BASE_COLLECTOR_OBSERVED_STAGE13_RESUMED' -or
        -not $resumed.stage13_pause_then_success_observed -or
        $resumed.stage13_resumed_after_quota_reset -ne $false) {
        throw 'UCIE_HOURLY_RESUME_EVIDENCE_NO_GO'
    }
    Write-SyntheticReceipts -LastStage 'EXTERNAL_HISTORY_BACKFILL_OK_NO_GO'
    $script:mockLastRunMinutesAgo = 25
    $stale = (& $evaluator | ConvertFrom-Json)
    if ($stale.status -cne 'LAST_SCHEDULED_RUN_RECEIPT_MISMATCH_NO_GO' -or
        $stale.two_recent_hourly_successes -ne $false) {
        throw 'UCIE_HOURLY_STALE_SCHEDULER_RESULT_ACCEPTED'
    }
    $script:mockLastRunMinutesAgo = 5
    Write-SyntheticReceipts -LastStage 'EXTERNAL_HISTORY_BACKFILL_OK_NO_GO' -LastStatus 'COLLECTION_FAILED'
    $failed = (& $evaluator | ConvertFrom-Json)
    if ($failed.status -cne 'TWO_RECENT_HOURLY_CYCLES_NOT_PROVEN_NO_GO') {
        throw 'UCIE_HOURLY_FAILED_CYCLE_NO_GO'
    }
    Write-SyntheticReceipts -LastStage 'EXTERNAL_HISTORY_BACKFILL_OK_NO_GO' -GapMinutes 5
    $wrongGap = (& $evaluator | ConvertFrom-Json)
    if ($wrongGap.two_recent_hourly_successes -ne $false) {
        throw 'UCIE_HOURLY_BAD_CADENCE_ACCEPTED'
    }
    Write-SyntheticReceipts -LastStage 'EXTERNAL_HISTORY_BACKFILL_OK_NO_GO'
    $script:mockBadAction = $true
    if ((& $evaluator | ConvertFrom-Json).status -cne 'TASK_IDENTITY_OR_CADENCE_NO_GO') {
        throw 'UCIE_HOURLY_BAD_ACTION_ACCEPTED'
    }
    $script:mockBadAction = $false
    $script:mockBadOwner = $true
    if ((& $evaluator | ConvertFrom-Json).status -cne 'TASK_IDENTITY_OR_CADENCE_NO_GO') {
        throw 'UCIE_HOURLY_BAD_OWNER_ACCEPTED'
    }
    $script:mockBadOwner = $false
    $script:mockExit = 1
    if ((& $evaluator | ConvertFrom-Json).status -cne 'LAST_TASK_RESULT_NO_GO') {
        throw 'UCIE_HOURLY_NONZERO_EXIT_ACCEPTED'
    }
    $script:mockExit = 0
    Write-Output 'UCIE_HOURLY_SYNTHETIC_EVIDENCE=PASS; TASK_MUTATED=FALSE; OWNER_FILES_SCANNED=FALSE'
}
finally {
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue
}
