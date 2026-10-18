# UCIE first-rule PUBLIC_ONLY manual production scanner (never auto-fix).
# Does not scan files, user projects, codebases or arbitrary paths. Caller must
# provide an approved public/synthetic inert snippet explicitly in SourceText.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourceText,
    [Parameter(Mandatory)][string]$PackPath,
    [Parameter(Mandatory)][string]$OwnerTrustPath,
    [Parameter(Mandatory)][string]$QaTrustPath,
    [Parameter(Mandatory)][string]$PythonPath,
    [ValidateRange(1,10000000)][int]$MinSerial = 1
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$previous = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $verifyArgs = @('-B', '-m', 'ucie_public.cli', 'verify-production',
                    '--pack', $PackPath,
                    '--owner-trust', $OwnerTrustPath,
                    '--qa-trust', $QaTrustPath,
                    '--min-serial', [string]$MinSerial)
    $raw = @(& $PythonPath @verifyArgs 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw 'UCIE_DUAL_SIGNATURE_VERIFICATION_FAILED'
    }
    try {
        $valid = ($raw -join [Environment]::NewLine) | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw 'UCIE_PRODUCTION_VERIFICATION_RESPONSE_INVALID'
    }
    if ($valid.result -cne 'DUAL_SIGNED_PUBLIC_PRODUCTION_RULEPACK_VERIFIED' -or
        $valid.rule_id -cne 'PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO' -or
        $valid.scope -cne 'PUBLIC_ONLY_MANUAL_STATIC_SCAN' -or
        $valid.owner_signature -cne 'VALID' -or
        $valid.independent_qa_signature -cne 'VALID' -or
        $valid.production_approved -cne $true -or
        $valid.deploy_allowed -cne $true -or
        $valid.auto_apply -cne $false -or
        $valid.serial -lt $MinSerial) {
        throw 'UCIE_PRODUCTION_GATE_NOT_APPROVED'
    }
    . (Join-Path $PSScriptRoot 'ucie_powershell_static_candidates.ps1')
    $receipt = Find-UCIEPowerShellCandidate -SourceText $SourceText
    $matched = @($receipt.findings | Where-Object {
        $_.pattern_code -ceq $valid.rule_id
    })
    foreach ($item in $matched) {
        if ($item.public_evidence -cne 'https://github.com/python/cpython/pull/159014') {
            throw 'UCIE_PRODUCTION_RULE_SOURCE_MISMATCH'
        }
    }
    [pscustomobject]@{
        schema = 'UCIE_STAGE4_PUBLIC_PRODUCTION_CONSUMER_V1'
        status = if ($matched.Count) { 'PUBLIC_PREVENTION_RULE_MATCH' } else { 'PUBLIC_PREVENTION_RULE_NO_MATCH' }
        rule_id = $valid.rule_id
        pack_serial = $valid.serial
        qa_signature = $valid.independent_qa_signature
        owner_signature = $valid.owner_signature
        scope = $valid.scope
        source_sha256 = $receipt.source_sha256
        finding_count = $matched.Count
        findings = @($matched)
        safe_guidance = $valid.safe_guidance
        source_files_read = 0
        supplied_source_executed = $false
        auto_fix_applied = $false
        persistent_writes = 0
        production_approved = $true
        deploy_allowed = $true
        auto_apply = $false
    } | ConvertTo-Json -Depth 8 -Compress
}
finally {
    $env:PYTHONPATH = $previous
}
