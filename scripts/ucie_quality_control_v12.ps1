# UCIE V1.2: explicit opt-in/opt-out for *quality audit only* inside existing hourly cycle.
[CmdletBinding(DefaultParameterSetName='Inspect')]
param(
    [Parameter(ParameterSetName='Enable')][switch]$Enable,
    [Parameter(ParameterSetName='Disable')][switch]$Disable
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_D_DRIVE_REQUIRED'
}
$runtime = Join-Path $root 'runtime'
if (-not (Test-Path -LiteralPath $runtime -PathType Container)) {
    throw 'UCIE_RUNTIME_NOT_FOUND'
}
foreach ($directory in @($root, $runtime)) {
    $entry = Get-Item -LiteralPath $directory -Force -ErrorAction Stop
    if (-not $entry.PSIsContainer -or
        ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'UCIE_OWNER_DIRECTORY_REPARSE_POINT_NOT_ALLOWED'
    }
}
$marker = Join-Path $runtime 'stage17_quality_opt_in.txt'
$token = 'UCIE_STAGE17_HOURLY_LIBRARY_QUALITY_OPT_IN_V1'
$stage10 = Join-Path $runtime 'stage10_hourly_opt_in.txt'
$stage12 = Join-Path $runtime 'stage12_review_opt_in.txt'

function ValidateSafeFile([string]$Path) {
    $entry = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($entry.PSIsContainer -or
        ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'UCIE_UNSAFE_OPTIN_FILE_NO_GO'
    }
    return $entry
}

if ($Enable) {
    if (-not (Test-Path -LiteralPath (Join-Path $root 'src\ucie_miner\library_quality_loop_v12.py') -PathType Leaf)) {
        throw 'STAGE17_QUALITY_CODE_NOT_INSTALLED'
    }
    foreach ($check in @(
        @{path=$stage10; token='UCIE_STAGE10_HOURLY_OPT_IN_V1'},
        @{path=$stage12; token='UCIE_STAGE12_REVIEW_OPT_IN_V1'}
    )) {
        [void](ValidateSafeFile $check.path)
        if ((Get-Content -LiteralPath $check.path -Raw -Encoding UTF8).Trim() -cne $check.token) {
            throw 'UCIE_PREREQUISITE_OPT_IN_INVALID_NO_GO'
        }
    }
    if (Test-Path -LiteralPath $marker) { throw 'QUALITY_OPT_IN_ALREADY_EXISTS' }
    $stream = [IO.File]::Open($marker, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write,
                              [IO.FileShare]::None)
    try {
        $raw = [Text.Encoding]::UTF8.GetBytes($token + [Environment]::NewLine)
        $stream.Write($raw, 0, $raw.Length)
        $stream.Flush($true)
    } finally { $stream.Dispose() }
    [pscustomobject]@{
        schema = 'UCIE_STAGE17_OWNER_CONTROL_V12'
        status = 'STAGE17_QUALITY_EXPLICITLY_ENABLED_NEXT_EXISTING_HOURLY_RUN'
        existing_task_changed = $false
        collector_manually_run = $false
        rules_approved = 0
    } | ConvertTo-Json -Compress
    return
}
if ($Disable) {
    [void](ValidateSafeFile $marker)
    if ((Get-Content -LiteralPath $marker -Raw -Encoding UTF8).Trim() -cne $token) {
        throw 'UNEXPECTED_STAGE17_MARKER_NO_DELETE'
    }
    Remove-Item -LiteralPath $marker -ErrorAction Stop
    [pscustomobject]@{
        schema = 'UCIE_STAGE17_OWNER_CONTROL_V12'
        status = 'STAGE17_QUALITY_OPTED_OUT'
        existing_task_changed = $false
        rules_approved = 0
    } | ConvertTo-Json -Compress
    return
}
$status = 'STAGE17_DISABLED'
if (Test-Path -LiteralPath $marker) {
    [void](ValidateSafeFile $marker)
    $status = if ((Get-Content -LiteralPath $marker -Raw -Encoding UTF8).Trim() -ceq $token) {
        'STAGE17_OWNER_OPT_IN_PRESENT_NOT_PROOF_OF_RUN'
    } else { 'STAGE17_MARKER_INVALID_NO_GO' }
}
[pscustomobject]@{
    schema='UCIE_STAGE17_OWNER_CONTROL_V12'
    status=$status
    existing_task_changed=$false
    auto_rule_approvals=0
} | ConvertTo-Json -Compress
