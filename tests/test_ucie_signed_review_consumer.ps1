# UCIE synthetic signed-pack consumer regression on disposable Windows CI only.
# Generates ephemeral TEST signing keys, never accesses owner-host keys.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = Split-Path -Parent $PSScriptRoot
$consumer = Join-Path $root 'scripts/ucie_signed_review_scan.ps1'
$python = (Get-Command python -ErrorAction Stop).Source
$oldPath = $env:PYTHONPATH
$scratch = Join-Path ([IO.Path]::GetTempPath()) ('ucie_review_test_' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scratch -ErrorAction Stop | Out-Null

try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $setup = @'
from pathlib import Path
import sys
from ucie_public.rulepack import generate_keys
from ucie_public.prevention_rulepack import CONFIRM, publish_prevention_review
root = Path(sys.argv[1])
(root / "build").mkdir()
key, _ = generate_keys(root / "keys", purpose="prevention")
publish_prevention_review(
    root, key, root / "build" / "review.zip",
    serial=7, confirmation=CONFIRM)
print("EPHEMERAL_SIGNED_REVIEW_FIXTURE_CREATED")
'@
    $created = $setup | & $python -B - $scratch
    if ($LASTEXITCODE -ne 0 -or $created -cne 'EPHEMERAL_SIGNED_REVIEW_FIXTURE_CREATED') {
        throw 'EPHEMERAL_FIXTURE_FAILED'
    }
    $pack = Join-Path $scratch 'build/review.zip'
    $trust = Join-Path $scratch 'keys/public_prevention.pem'
    $bad = @'
throw "DO_NOT_EXECUTE"
python -I -X disable_remote_debug -c "DO_NOT_EXECUTE"
'@
    $first = & $consumer -SourceText $bad -PackPath $pack -TrustPath $trust -PythonPath $python -MinSerial 7 | ConvertFrom-Json
    if ($first.status -cne 'SIGNED_REVIEW_RULE_MATCH_UNVERIFIED' -or
        $first.finding_count -ne 1 -or
        $first.signature -cne 'VALID' -or
        $first.findings[0].pattern_code -cne 'PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO' -or
        $first.production_approved -ne $false -or
        $first.deploy_allowed -ne $false -or
        $first.supplied_source_executed -ne $false -or
        $first.persistent_writes -ne 0) {
        throw 'SIGNED_REVIEW_DETECTOR_CONNECTION_FAILED'
    }
    $fixed = & $consumer -SourceText 'python -I -X disable-remote-debug -' -PackPath $pack -TrustPath $trust -PythonPath $python -MinSerial 7 | ConvertFrom-Json
    if ($fixed.status -cne 'SIGNED_REVIEW_RULE_NO_MATCH' -or $fixed.finding_count -ne 0) {
        throw 'CORRECTED_PYTHON_OPTION_FALSE_POSITIVE'
    }
    $other = & $consumer -SourceText 'Get-Command Foo -UseFuzzyMatching' -PackPath $pack -TrustPath $trust -PythonPath $python -MinSerial 7 | ConvertFrom-Json
    if ($other.finding_count -ne 0) {
        throw 'UNSIGNED_DIFFERENT_RULE_LEAKED_INTO_CONSUMER'
    }

    $rollbackRejected = $false
    try {
        $null = & $consumer -SourceText $bad -PackPath $pack -TrustPath $trust -PythonPath $python -MinSerial 8
    }
    catch {
        if ($_.Exception.Message -match 'UCIE_SIGNED_REVIEW_PACK_VERIFICATION_FAILED') {
            $rollbackRejected = $true
        } else {
            throw
        }
    }
    if (-not $rollbackRejected) {
        throw 'ROLLBACK_PACK_NOT_REJECTED_BEFORE_SOURCE_SCAN'
    }
    $missingRejected = $false
    try {
        $null = & $consumer -SourceText $bad -PackPath (Join-Path $scratch 'missing.zip') -TrustPath $trust -PythonPath $python
    }
    catch {
        if ($_.Exception.Message -match 'UCIE_SIGNED_REVIEW_PACK_VERIFICATION_FAILED') {
            $missingRejected = $true
        } else {
            throw
        }
    }
    if (-not $missingRejected) {
        throw 'MISSING_PACK_NOT_REJECTED'
    }
    Write-Output 'UCIE_SIGNED_REVIEW_CONSUMER=PASS_EPHEMERAL_SYNTHETIC_ONLY'
}
finally {
    $env:PYTHONPATH = $oldPath
    Remove-Item -LiteralPath $scratch -Force -Recurse -ErrorAction Stop
}
# The fail-closed negative tests intentionally leave Python LASTEXITCODE=2.
# Explicit success is reachable only after every assertion and cleanup pass.
exit 0
