# UCIE only: one exact owner-attested non-network P10 job.
# Default PREVIEW ONLY; -Approve explicitly permits one delayed queue update.
# No network GET, task start/stop/edit, P11 rearm, broad retry or model training.
[CmdletBinding()]
param(
    [ValidateSet('PUBLIC_METADATA_REVIEW','UCIE_REPORT_PREPARATION')]
    [string]$Kind = 'PUBLIC_METADATA_REVIEW',
    [switch]$Approve
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root,'D:\UCIE',[StringComparison]::OrdinalIgnoreCase) -or
    ((Get-Item -LiteralPath $root).Attributes -band [IO.FileAttributes]::ReparsePoint) -or
    -not (Test-Path -LiteralPath (Join-Path $root '.git') -PathType Container)) {
    throw 'UCIE_EXACT_OWNER_REARM_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$source = Join-Path $root 'src\ucie_miner\p10_owner_single_live_rearm_v02.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $source -PathType Leaf) -or
    ((Get-Item -LiteralPath $source).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'UCIE_APPROVED_OWNER_V02_SOURCE_MISSING'
}
$env:PYTHONPATH = Join-Path $root 'src'
$module = 'ucie_miner.p10_owner_single_live_rearm_v02'
$previewArgs = @('-B','-m',$module,'--ucie-root',$root,'--kind',$Kind)
$previewText = & $python @previewArgs 2>$null
if ($LASTEXITCODE -ne 0 -or @($previewText).Count -ne 1) {
    throw 'UCIE_EXACT_OWNER_P10_READONLY_PREFLIGHT_FAILED'
}
$preview = [string]$previewText | ConvertFrom-Json
$expectedId = if ($Kind -eq 'PUBLIC_METADATA_REVIEW') { 2 } else { 5 }
if ($preview.schema -cne 'UCIE_P10_OWNER_ONE_NONNETWORK_LIVE_REARM_V02' -or
    $preview.status -cne 'EXACT_OWNER_P10_SINGLE_JOB_PREVIEW_ONLY' -or
    $preview.kind -cne $Kind -or [int]$preview.job_id -ne $expectedId -or
    $preview.held -ne $true -or
    $preview.eligible_for_explicit_single_owner_action -ne $true -or
    $preview.task_verified -ne $true -or
    $preview.public_gets -ne 0 -or
    $preview.queue_modified -ne $false -or
    $preview.scheduler_modified -ne $false -or
    [string]$preview.exact_row_fingerprint_sha256 -cnotmatch '^[0-9a-f]{64}$') {
    throw 'UCIE_P10_EXACT_PREVIEW_IDENTITY_OR_STATE_NO_GO'
}
if (-not $Approve) {
    [pscustomobject]@{
        schema = 'UCIE_P10_OWNER_ONE_JOB_PS_V02'
        status = 'PREVIEW_ONLY_NO_QUEUE_CHANGE'
        kind = $Kind
        job_id = $expectedId
        exact_row_fingerprint_sha256 = [string]$preview.exact_row_fingerprint_sha256
        owner_task_verified = $true
        scheduler_changed = $false
        queue_modified = $false
        public_gets = 0
        auto_promoted = $false
    } | ConvertTo-Json -Compress
    return
}
# Owner chose one kind and -Approve. The separate Python process repeats
# owner/task attestation and atomically verifies exact row SHA at commit.
$applyArgs = @(
    '-B','-m',$module,'--ucie-root',$root,'--kind',$Kind,
    '--apply','--job-id',[string]$expectedId,
    '--expected-sha256',[string]$preview.exact_row_fingerprint_sha256,
    '--owner-consent','UCIE_OWNER_APPROVES_EXACT_ONE_NONNETWORK_JOB_REARM'
)
$receiptText = & $python @applyArgs 2>$null
if ($LASTEXITCODE -ne 0 -or @($receiptText).Count -ne 1) {
    throw 'UCIE_P10_ONE_OWNER_QUEUE_REARM_REJECTED'
}
$receipt = [string]$receiptText | ConvertFrom-Json
if ($receipt.schema -cne 'UCIE_P10_OWNER_ONE_NONNETWORK_LIVE_REARM_V02' -or
    $receipt.status -cne 'EXACT_ONE_NONNETWORK_JOB_DELAYED_PENDING' -or
    $receipt.kind -cne $Kind -or
    [int]$receipt.job_id -ne $expectedId -or
    [string]$receipt.operation_sha256 -cnotmatch '^[0-9a-f]{64}$' -or
    $receipt.worker_started -ne $false -or
    $receipt.public_gets -ne 0 -or
    $receipt.scheduler_modified -ne $false -or
    $receipt.auto_promoted -ne $false) {
    throw 'UCIE_P10_OWNER_MUTATION_RECEIPT_REQUIRES_INDEPENDENT_REVIEW'
}
[pscustomobject]@{
    schema = 'UCIE_P10_OWNER_ONE_JOB_PS_V02'
    status = 'ONE_DELAYED_OWNER_REARM_COMMITTED'
    kind = $Kind
    job_id = $expectedId
    operation_sha256 = [string]$receipt.operation_sha256
    scheduled_due_at = [string]$receipt.scheduled_due_at
    worker_started = $false
    public_gets = 0
    scheduler_modified = $false
    auto_promoted = $false
} | ConvertTo-Json -Compress
