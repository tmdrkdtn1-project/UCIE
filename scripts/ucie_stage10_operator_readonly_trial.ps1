# UCIE Stage 10 operator-initiated, read-only Windows host trial.
# Never installs a task, writes SQLite, stores source, or executes PR code.
[CmdletBinding()]
param([switch]$AllowPublicReads)
$ErrorActionPreference = 'Stop'
$root = 'D:\UCIE'
$py = Join-Path $root '.venv\Scripts\python.exe'
$miner = Join-Path $root 'runtime\public_miner.sqlite3'
$knowledge = Join-Path $root 'runtime\knowledge.sqlite3'
$stage = Join-Path $root 'runtime\stage10_unverified_public_candidates.sqlite3'
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    throw 'Dedicated UCIE root unavailable; no other project is inspected.'
}
if (-not (Test-Path -LiteralPath $py -PathType Leaf)) {
    throw 'Dedicated UCIE Python interpreter unavailable.'
}
$allowed = @($miner, $knowledge, $stage)
function Get-UCIEReadOnlyHashes {
    $result = @{}
    foreach ($path in $allowed) {
        $name = [IO.Path]::GetFileName($path)
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            $result[$name] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        } else {
            $result[$name] = 'ABSENT'
        }
    }
    return $result
}
$prior = Get-UCIEReadOnlyHashes
Push-Location -LiteralPath $root
try {
    $environment = & $py -B -m ucie_miner preflight-public-batch-host
    if ($LASTEXITCODE -ne 0) { throw 'UCIE host preflight failed' }
    $inventory = & $py -B -m ucie_miner inspect-public-candidate-ledger
    if ($LASTEXITCODE -ne 0) { throw 'UCIE read-only ledger inspection failed' }
    $preflight = $environment | ConvertFrom-Json -ErrorAction Stop
    $ledger = $inventory | ConvertFrom-Json -ErrorAction Stop
    $batchSummary = $null
    if ($AllowPublicReads) {
        # One approved source, one page, up to one enrichment; no DB writes.
        $public = & $py -B -m ucie_miner batch-public-evidence --live --source modelcontextprotocol/python-sdk --limit 1 --skip-advisory
        if ($LASTEXITCODE -ne 0) {
            throw 'Approved public batch failed; do not report a PASS'
        }
        $batch = $public | ConvertFrom-Json -ErrorAction Stop
        $batchSummary = [ordered]@{
            status = $batch.status
            selected_candidates = $batch.enriched_count
            metadata_candidates = $batch.public_metadata_candidate_count
            public_api_requests_upper_bound = $batch.overall_gets_upper_bound
            production_approved = $false
        }
    }
} finally {
    Pop-Location
}
$after = Get-UCIEReadOnlyHashes
foreach ($name in $prior.Keys) {
    if ($prior[$name] -ne $after[$name]) {
        throw "UCIE read-only invariant changed for $name; investigate"
    }
}
[ordered]@{
    schema = 'UCIE_STAGE10_OPERATOR_READONLY_TRIAL_V1'
    status = 'READ_ONLY_OPERATOR_TRIAL_NO_GO'
    host_preflight = $preflight.status
    ledger_status = $ledger.status
    ledger_unverified_revisions = $ledger.candidate_revisions
    public_batch = $batchSummary
    operating_and_staging_db_unchanged = $true
    actual_public_batch_run_observed = [bool]$AllowPublicReads
    independent_upstream_fix_proven = $false
    permanent_learning_applied = $false
    scheduler_changed = $false
    rulepack_signed = $false
    production_approved = $false
} | ConvertTo-Json -Depth 5 -Compress
