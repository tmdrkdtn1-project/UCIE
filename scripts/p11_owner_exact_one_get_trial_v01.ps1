# UCIE owner P11 one anonymous GitHub metadata GET diagnostic.
# Default READ-ONLY. -Approve AND -AcceptUnknownSharedQuota both required
# before exactly ONE approved GitHub GET may occur. Never rearm P10/P11.
[CmdletBinding()]
param(
    [switch]$Approve,
    [switch]$AcceptUnknownSharedQuota
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root,'D:\UCIE',
        [StringComparison]::OrdinalIgnoreCase) -or
    ((Get-Item -LiteralPath $root).Attributes -band
        [IO.FileAttributes]::ReparsePoint) -or
    -not (Test-Path -LiteralPath (Join-Path $root '.git') -PathType Container)) {
    throw 'UCIE_P11_EXACT_OWNER_ROOT_DENIED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$moduleSource = Join-Path $root 'src\ucie_miner\p11_owner_one_get_trial_v01.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $moduleSource -PathType Leaf) -or
    ((Get-Item -LiteralPath $moduleSource).Attributes -band
        [IO.FileAttributes]::ReparsePoint)) {
    throw 'UCIE_P11_ONE_GET_APPROVED_SOURCE_MISSING'
}
$env:PYTHONPATH = Join-Path $root 'src'
$module = 'ucie_miner.p11_owner_one_get_trial_v01'
$previewArgs = @('-B','-m',$module,'--ucie-root',$root)
$previewText = & $python @previewArgs 2>$null
if ($LASTEXITCODE -ne 0 -or @($previewText).Count -ne 1) {
    throw 'UCIE_P11_OWNER_READONLY_PREFLIGHT_DENIED'
}
$preview = [string]$previewText | ConvertFrom-Json
if ($preview.schema -cne 'UCIE_P11_OWNER_EXACT_ONE_GET_TRIAL_V01' -or
    $preview.status -cne 'ONE_GET_OWNER_PREVIEW_ONLY_SHARED_QUOTA_UNKNOWN' -or
    $preview.kind -cne 'PUBLIC_INCREMENTAL_MINING' -or
    [int]$preview.job_id -ne 6 -or
    $preview.source_id -cne 'repo:python/cpython' -or
    $preview.shared_rate_remaining_verified -ne $false -or
    $preview.shared_public_miner_last_run_healthy -ne $true -or
    $preview.max_additional_approved_public_gets -ne 1 -or
    $preview.requested_public_gets -ne 0 -or
    $preview.p10_queue_modified -ne $false -or
    $preview.scheduler_modified -ne $false -or
    [string]$preview.exact_held_row_sha256 -cnotmatch '^[0-9a-f]{64}$') {
    throw 'UCIE_P11_OWNER_EXACT_ONE_GET_PREVIEW_DRIFT'
}
if (-not $Approve) {
    if ($AcceptUnknownSharedQuota) {
        throw 'UCIE_P11_QUOTA_CONSENT_REQUIRES_APPROVE'
    }
    [pscustomobject]@{
        schema = 'UCIE_P11_OWNER_ONE_GET_PS_V01'
        status = 'READONLY_PREVIEW_ONE_GET_NOT_EXECUTED'
        kind = 'PUBLIC_INCREMENTAL_MINING'
        job_id = 6
        source_id = 'repo:python/cpython'
        exact_held_row_sha256 = [string]$preview.exact_held_row_sha256
        shared_rate_remaining_verified = $false
        public_gets_requested = 0
        queue_modified = $false
        scheduler_modified = $false
        auto_promoted = $false
    } | ConvertTo-Json -Compress
    return
}
if (-not $AcceptUnknownSharedQuota) {
    throw 'UCIE_P11_EXPLICIT_UNKNOWN_SHARED_QUOTA_CONSENT_REQUIRED'
}
# The caller explicitly accepts unknown shared quota exposure (one GET max).
# Python repeats the owner/task and live queue/ledger source checks inside
# the guarded first-party process, then records a non-replayable receipt
# BEFORE the approved single public API request.
$argsOne = @(
    '-B','-m',$module,'--ucie-root',$root,
    '--apply',
    '--expected-sha256',[string]$preview.exact_held_row_sha256,
    '--owner-consent','UCIE_OWNER_APPROVES_ONE_PUBLIC_GET_ACCEPTING_UNKNOWN_SHARED_QUOTA'
)
$textOne = & $python @argsOne 2>$null
$exitOne = $LASTEXITCODE
if (@($textOne).Count -ne 1) {
    throw 'UCIE_P11_ONE_GET_RESULT_MISSING_REQUIRE_OWNER_REVIEW'
}
$receipt = [string]$textOne | ConvertFrom-Json
if ($receipt.schema -cne 'UCIE_P11_OWNER_EXACT_ONE_GET_TRIAL_V01' -or
    [string]$receipt.status -cnotin @(
        'ONE_APPROVED_PUBLIC_GET_SUCCEEDED_UNVERIFIED',
        'ONE_APPROVED_PUBLIC_GET_FAILED_NO_RETRY',
        'ONE_APPROVED_PUBLIC_GET_SKIPPED_NO_NETWORK'
    ) -or
    [int]$receipt.public_gets_requested -gt 1 -or
    $receipt.kind -cne 'PUBLIC_INCREMENTAL_MINING' -or
    [int]$receipt.job_id -ne 6 -or
    $receipt.source_id -cne 'repo:python/cpython' -or
    $receipt.p10_job_rearmed -ne $false -or
    $receipt.p10_queue_modified -ne $false -or
    $receipt.scheduler_modified -ne $false -or
    $receipt.auto_promoted -ne $false) {
    throw 'UCIE_P11_UNEXPECTED_RESULT_REQUIRE_OWNER_REVIEW'
}
[pscustomobject]@{
    schema = 'UCIE_P11_OWNER_ONE_GET_PS_V01'
    status = [string]$receipt.status
    source_id = 'repo:python/cpython'
    public_gets_requested = [int]$receipt.public_gets_requested
    rate_remaining_observed = $receipt.rate_remaining_observed
    sanitized_error_category = $receipt.sanitized_error_category
    p10_queue_modified = $false
    scheduler_modified = $false
    auto_promoted = $false
} | ConvertTo-Json -Compress
if ($exitOne -ne 0) {
    exit 3
}
