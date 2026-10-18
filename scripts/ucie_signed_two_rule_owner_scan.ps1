# Explicit PUBLIC_ONLY manual static scan of two owner-signed rules.
# SourceText is caller-selected text; this never scans files/projects, executes
# supplied text, mutates code, schedules a job, or auto-fixes anything.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourceText,
    [Parameter(Mandatory)][string]$PackPath,
    [Parameter(Mandatory)][string]$OwnerTrustPath,
    [Parameter(Mandatory)][string]$PythonPath,
    [ValidateRange(1,10000000)][int]$MinSerial = 1
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$old = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    . (Join-Path $PSScriptRoot 'ucie_powershell_static_candidates.ps1')
    $receipt = Find-UCIEPowerShellCandidate -SourceText $SourceText
    $payload = $receipt | ConvertTo-Json -Depth 8 -Compress
    $argsForVerifier = @('-B', '-m', 'ucie_public.cli', 'scan-two-rule-owner-receipt-stdin',
                         '--pack', $PackPath, '--owner-trust', $OwnerTrustPath,
                         '--min-serial', [string]$MinSerial)
    $raw = @($payload | & $PythonPath @argsForVerifier 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw 'UCIE_TWO_RULE_OWNER_RECEIVER_FAIL_CLOSED'
    }
    try {
        $response = ($raw -join [Environment]::NewLine) |
            ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw 'UCIE_TWO_RULE_RECEIVER_JSON_INVALID'
    }
    $expectedIds = @(
        'PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO',
        'PS_RESOLVE_PATH_DOT_PREFIX'
    )
    $ids = @($response.rule_ids)
    if ($response.schema -cne 'UCIE_TWO_RULE_OWNER_PUBLIC_MANUAL_SCAN_V1' -or
        $response.owner_signature -cne 'VALID' -or
        $response.scope -cne 'PUBLIC_ONLY_MANUAL_STATIC_SCAN' -or
        $response.approval_mode -cne 'AUTOMATED_QA_OWNER_RISK_ACCEPTED' -or
        $response.rule_count -ne 2 -or $ids.Count -ne 2 -or
        $ids[0] -cne $expectedIds[0] -or $ids[1] -cne $expectedIds[1] -or
        $response.source_sha256 -cne $receipt.source_sha256 -or
        $response.pack_serial -lt $MinSerial -or
        $response.source_authentication_verified -cne $false -or
        $response.source_executed -cne $false -or
        $response.source_files_read -ne 0 -or
        $response.auto_fix_applied -cne $false -or
        $response.auto_apply -cne $false -or
        $response.independent_human_qa_approved -cne $false -or
        $response.legal_license_signoff -cne $false -or
        $response.release_version_coverage_proven -cne $false -or
        $response.production_approved -cne $true -or
        $response.finding_count -ne @($response.findings).Count) {
        throw 'UCIE_TWO_RULE_OWNER_RECEIVER_OUTSIDE_SCOPE'
    }
    Write-Output (($response | ConvertTo-Json -Depth 8 -Compress))
}
finally {
    $env:PYTHONPATH = $old
}
