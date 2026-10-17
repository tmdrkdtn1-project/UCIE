# UCIE signed REVIEW_ONLY prevention Rulepack -> inert PowerShell AST scan.
# Explicit approved PUBLIC/synthetic text input only. No file reads, source
# execution, auto-fixes, persisted findings, tasks or production deployment.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourceText,
    [Parameter(Mandatory)][string]$PackPath,
    [Parameter(Mandatory)][string]$TrustPath,
    [Parameter(Mandatory)][string]$PythonPath,
    [ValidateRange(1, 10000000)][int]$MinSerial = 1
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root 'src'
$previous = $env:PYTHONPATH

try {
    # Signature, source identity and review-only restrictions are checked
    # before source analysis. SourceText is NEVER supplied to Python.
    $env:PYTHONPATH = $src
    $pythonArgs = @('-B','-m','ucie_public.cli','verify-prevention-review',
                    '--pack', $PackPath, '--trust', $TrustPath,
                    '--min-serial', [string]$MinSerial)
    $raw = @(& $PythonPath @pythonArgs 2>&1)
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw 'UCIE_SIGNED_REVIEW_PACK_VERIFICATION_FAILED'
    }
    try {
        $verification = ($raw -join [Environment]::NewLine) | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw 'UCIE_VERIFICATION_RESPONSE_INVALID'
    }
    if ($verification.result -cne 'SIGNED_PUBLIC_PREVENTION_REVIEW_PACK_VERIFIED' -or
        $verification.signature -cne 'VALID' -or
        $verification.rule_id -cne 'PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO' -or
        $verification.production_approved -cne $false -or
        $verification.deploy_allowed -cne $false -or
        $verification.auto_promoted -cne $false -or
        $verification.serial -lt $MinSerial) {
        throw 'UCIE_SIGNED_REVIEW_PACK_NOT_SAFE'
    }

    # UCIE first-party PowerShell scanner only parses an inert source string.
    . (Join-Path $PSScriptRoot 'ucie_powershell_static_candidates.ps1')
    $receipt = Find-UCIEPowerShellCandidate -SourceText $SourceText
    $matched = @($receipt.findings | Where-Object {
        $_.pattern_code -ceq $verification.rule_id
    })
    foreach ($item in $matched) {
        if ($item.public_evidence -cne 'https://github.com/python/cpython/pull/159014') {
            throw 'UCIE_RULE_EVIDENCE_SOURCE_CHANGED'
        }
    }
    $status = if ($matched.Count -gt 0) {
        'SIGNED_REVIEW_RULE_MATCH_UNVERIFIED'
    } else {
        'SIGNED_REVIEW_RULE_NO_MATCH'
    }
    [pscustomobject]@{
        schema = 'UCIE_SIGNED_REVIEW_CONSUMER_SCAN_V1'
        status = $status
        rule_id = $verification.rule_id
        pack_serial = $verification.serial
        signing_key_id = $verification.trust_key_id
        signature = 'VALID'
        source_sha256 = $receipt.source_sha256
        finding_count = $matched.Count
        findings = @($matched)
        safe_guidance = $verification.safe_guidance
        source_files_read = 0
        supplied_source_executed = $false
        persistent_writes = 0
        auto_fix_applied = $false
        approved_rules = 0
        production_approved = $false
        deploy_allowed = $false
    } | ConvertTo-Json -Depth 8 -Compress
}
finally {
    $env:PYTHONPATH = $previous
}
