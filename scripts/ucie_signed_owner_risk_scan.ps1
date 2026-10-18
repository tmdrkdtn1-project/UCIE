# UCIE owner-risk-accepted PUBLIC_ONLY manual static scan.
# SourceText is supplied explicitly: no project/file scan, code execution,
# auto-fix or unattended deployment. No independent human QA claimed.
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
$previous = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $argsForVerifier = @('-B', '-m', 'ucie_public.cli',
                         'verify-owner-risk-release',
                         '--pack', $PackPath,
                         '--owner-trust', $OwnerTrustPath,
                         '--min-serial', [string]$MinSerial)
    $raw = @(& $PythonPath @argsForVerifier 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw 'UCIE_OWNER_RISK_RELEASE_VERIFICATION_FAILED'
    }
    try {
        $valid = ($raw -join [Environment]::NewLine) | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw 'UCIE_OWNER_RISK_VERIFICATION_RESPONSE_INVALID'
    }
    if ($valid.result -cne 'OWNER_RISK_ACCEPTED_PUBLIC_RULEPACK_VERIFIED' -or
        $valid.rule_id -cne 'PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO' -or
        $valid.scope -cne 'PUBLIC_ONLY_MANUAL_STATIC_SCAN' -or
        $valid.owner_signature -cne 'VALID' -or
        $valid.approval_mode -cne 'AUTOMATED_QA_OWNER_RISK_ACCEPTED' -or
        $valid.owner_risk_accepted -cne $true -or
        $valid.independent_human_qa_approved -cne $false -or
        $valid.legal_license_signoff -cne $false -or
        $valid.production_approved -cne $true -or
        $valid.deploy_allowed -cne $true -or
        $valid.auto_apply -cne $false -or
        $valid.serial -lt $MinSerial) {
        throw 'UCIE_OWNER_RISK_RELEASE_OUTSIDE_APPROVED_SCOPE'
    }
    . (Join-Path $PSScriptRoot 'ucie_powershell_static_candidates.ps1')
    $receipt = Find-UCIEPowerShellCandidate -SourceText $SourceText
    $matched = @($receipt.findings | Where-Object {
        $_.pattern_code -ceq $valid.rule_id
    })
    foreach ($item in $matched) {
        if ($item.public_evidence -cne 'https://github.com/python/cpython/pull/159014') {
            throw 'UCIE_OWNER_RISK_RULE_PROVENANCE_MISMATCH'
        }
    }
    [pscustomobject]@{
        schema = 'UCIE_OWNER_RISK_PUBLIC_MANUAL_SCAN_V1'
        status = if ($matched.Count) { 'PUBLIC_PREVENTION_RULE_MATCH' } else { 'PUBLIC_PREVENTION_RULE_NO_MATCH' }
        rule_id = $valid.rule_id
        pack_serial = $valid.serial
        source_commit_sha = $valid.source_commit_sha
        owner_signature = 'VALID'
        independent_human_qa_approved = $false
        owner_risk_accepted = $true
        scope = $valid.scope
        source_sha256 = $receipt.source_sha256
        finding_count = $matched.Count
        findings = @($matched)
        safe_guidance = $valid.safe_guidance
        supplied_source_executed = $false
        source_files_read = 0
        persistent_writes = 0
        auto_fix_applied = $false
        auto_apply = $false
        production_approved = $true
        deploy_allowed = $true
    } | ConvertTo-Json -Depth 8 -Compress
}
finally {
    $env:PYTHONPATH = $previous
}
