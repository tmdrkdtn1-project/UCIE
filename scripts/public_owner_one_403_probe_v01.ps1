# UCIE only. A single diagnostic GET after observed python/cpython HTTP403.
# Default READ-ONLY. Both -Approve and -AcceptUnknownSharedQuota required.
# NEVER changes P10/P11 queues or task scheduler and NEVER auto resumes.
[CmdletBinding()]
param(
    [switch]$Approve,
    [switch]$AcceptUnknownSharedQuota
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root,'D:\UCIE',
        [StringComparison]::OrdinalIgnoreCase) -or
    ((Get-Item -LiteralPath $root).Attributes -band
        [IO.FileAttributes]::ReparsePoint) -or
    -not (Test-Path -LiteralPath (Join-Path $root '.git') -PathType Container)) {
    throw 'UCIE_PUBLIC403_EXACT_OWNER_ROOT_DENIED'
}
$python=Join-Path $root '.venv\Scripts\python.exe'
$source=Join-Path $root 'src\ucie_miner\public_owner_one_403_probe_v01.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $source -PathType Leaf) -or
    ((Get-Item -LiteralPath $source).Attributes -band
        [IO.FileAttributes]::ReparsePoint)) {
    throw 'UCIE_PUBLIC403_ONE_GET_APPROVED_SOURCE_MISSING'
}
$env:PYTHONPATH=Join-Path $root 'src'
$module='ucie_miner.public_owner_one_403_probe_v01'
$preArgs=@('-B','-m',$module,'--ucie-root',$root)
$line=& $python @preArgs 2>$null
if ($LASTEXITCODE -ne 0 -or @($line).Count -ne 1) {
    throw 'UCIE_PUBLIC403_OWNER_DIAGNOSTIC_PREFLIGHT_NO_GO'
}
$pre=[string]$line | ConvertFrom-Json
if ($pre.schema -cne 'UCIE_PUBLIC_MINER_ONE_HTTP403_OWNER_PROBE_V01' -or
    $pre.status -cne 'EXACT_ONE_403_OWNER_DIAGNOSTIC_PREVIEW_ONLY' -or
    $pre.approved_source -cne 'python/cpython' -or
    $pre.approved_operation -cne 'FETCH_PR_LIST' -or
    $pre.unknown_shared_rate_budget -ne $true -or
    [int]$pre.maximum_approved_gets -ne 1 -or
    [int]$pre.public_gets_requested -ne 0 -or
    $pre.operating_miner_receipt_modified -ne $false -or
    $pre.p10_queue_modified -ne $false -or
    $pre.task_modified -ne $false -or
    [string]$pre.original_receipt_sha256 -cnotmatch '^[0-9a-f]{64}$') {
    throw 'UCIE_PUBLIC403_EXACT_OWNER_PREVIEW_SOURCE_DRIFT'
}
if (-not $Approve) {
    if ($AcceptUnknownSharedQuota) {
        throw 'UCIE_PUBLIC403_QUOTA_CONSENT_REQUIRES_EXPLICIT_APPROVE'
    }
    [pscustomobject]@{
        schema='UCIE_PUBLIC403_OWNER_ONESHOT_PS_V01'
        status='OWNER_PREVIEW_NO_GET'
        approved_source='python/cpython'
        approved_operation='FETCH_PR_LIST'
        original_receipt_sha256=[string]$pre.original_receipt_sha256
        public_gets_requested=0
        task_modified=$false
        p10_queue_modified=$false
        p11_rearmed=$false
    } | ConvertTo-Json -Compress
    return
}
if (-not $AcceptUnknownSharedQuota) {
    throw 'UCIE_PUBLIC403_UNKNOWN_SHARED_QUOTA_EXPLICIT_ACK_REQUIRED'
}
# Python rechecks the owner Windows task and the original SHA while
# holding the SAME first-party PublicMiner lock, and persists a single
# nonreplayable receipt before making at most ONE approved GitHub GET.
$applyArgs=@(
    '-B','-m',$module,'--ucie-root',$root,'--apply',
    '--expected-sha256',[string]$pre.original_receipt_sha256,
    '--owner-consent',
    'UCIE_OWNER_ACCEPTS_ONE_GET_AFTER_HTTP403_WITH_UNKNOWN_SHARED_BUDGET'
)
$outLine=& $python @applyArgs 2>$null
$childExit=$LASTEXITCODE
if (@($outLine).Count -ne 1) {
    throw 'UCIE_PUBLIC403_RESULT_UNAVAILABLE_REVIEW_FIRST_PARTY_RECEIPT'
}
$out=[string]$outLine | ConvertFrom-Json
if ($out.schema -cne 'UCIE_PUBLIC_MINER_ONE_HTTP403_OWNER_PROBE_V01' -or
    [string]$out.status -cnotin @(
        'EXACT_ONE_403_DIAGNOSTIC_SUCCEEDED_UNVERIFIED',
        'EXACT_ONE_403_DIAGNOSTIC_FAILED_NO_RETRY'
    ) -or
    [int]$out.public_gets_requested -ne 1 -or
    $out.source_id -cne 'repo:python/cpython' -or
    $out.base_miner_original_last_run_modified -ne $false -or
    $out.p10_queue_modified -ne $false -or
    $out.p11_rearmed -ne $false -or
    $out.task_modified -ne $false -or
    $out.auto_promoted -ne $false) {
    throw 'UCIE_PUBLIC403_UNEXPECTED_OPERATOR_RECEIPT_REQUIRE_REVIEW'
}
[pscustomobject]@{
    schema='UCIE_PUBLIC403_OWNER_ONESHOT_PS_V01'
    status=[string]$out.status
    source_id='repo:python/cpython'
    public_gets_requested=[int]$out.public_gets_requested
    sanitized_error_category=$out.sanitized_error_category
    rate_hold_reason=$out.rate_hold_reason
    rate_remaining=$out.rate_remaining
    rate_reset_epoch=$out.rate_reset_epoch
    task_modified=$false
    p10_queue_modified=$false
    p11_rearmed=$false
    auto_promoted=$false
} | ConvertTo-Json -Compress
if ($childExit -ne 0) {
    exit 3
}
