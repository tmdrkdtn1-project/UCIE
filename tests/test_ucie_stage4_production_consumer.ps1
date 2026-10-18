# Synthetic Stage4 dual-key end-to-end test on disposable GitHub Windows runner.
# IMPORTANT: synthetic QA claims are never independently approved real claims.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $root 'scripts/ucie_signed_production_scan.ps1'
$python = (Get-Command python -ErrorAction Stop).Source
$old = $env:PYTHONPATH
$scratch = Join-Path ([IO.Path]::GetTempPath()) ('ucie_prod_gate_' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scratch -ErrorAction Stop | Out-Null
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $setup = @'
from pathlib import Path
import sys
from datetime import datetime, timezone
from ucie_public.rulepack import generate_keys, _private_key, canonical_json, key_id
from ucie_public.production_release import EXPECTED_QA, OWNER_CONFIRM, publish_production
root=Path(sys.argv[1])
(root/"build").mkdir()
qa, qapub=generate_keys(root/"qa",purpose="qa")
owner, ownpub=generate_keys(root/"owner",purpose="production")
qa_private=_private_key(qa)
claim=dict(EXPECTED_QA)
claim["qa_key_id"]=key_id(qa_private.public_key())
claim["reviewed_utc"]=datetime.now(timezone.utc).replace(
    microsecond=0).isoformat().replace("+00:00","Z")
data=canonical_json(claim)
(root/"claim.json").write_bytes(data)
(root/"claim.sig").write_bytes(qa_private.sign(data))
publish_production(root,owner,root/"claim.json",root/"claim.sig",
                   qapub,root/"build"/"public.zip",serial=7,
                   confirmation=OWNER_CONFIRM)
print("SYNTHETIC_DUAL_KEY_FIXTURE_ONLY")
'@
    $seen = $setup | & $python -B - $scratch
    if ($LASTEXITCODE -ne 0 -or $seen -cne 'SYNTHETIC_DUAL_KEY_FIXTURE_ONLY') {
        throw 'STAGE4_SYNTHETIC_FIXTURE_FAILED'
    }
    $params = @{
        PackPath = Join-Path $scratch 'build/public.zip'
        OwnerTrustPath = Join-Path $scratch 'owner/public_production.pem'
        QaTrustPath = Join-Path $scratch 'qa/public_qa.pem'
        PythonPath = $python
        MinSerial = 7
    }
    $badSource = @'
throw 'DO_NOT_EXECUTE'
python -I -X disable_remote_debug -c 'DO_NOT_EXECUTE'
'@
    $bad = & $runner @params -SourceText $badSource | ConvertFrom-Json
    if ($bad.status -cne 'PUBLIC_PREVENTION_RULE_MATCH' -or
        $bad.finding_count -ne 1 -or
        $bad.qa_signature -cne 'VALID' -or
        $bad.owner_signature -cne 'VALID' -or
        $bad.scope -cne 'PUBLIC_ONLY_MANUAL_STATIC_SCAN' -or
        $bad.production_approved -ne $true -or
        $bad.auto_apply -ne $false -or
        $bad.supplied_source_executed -ne $false) {
        throw 'STAGE4_SIGNED_PUBLIC_DETECTION_INTEGRATION_FAILED'
    }
    $good = & $runner @params -SourceText 'python -X disable-remote-debug -' | ConvertFrom-Json
    if ($good.status -cne 'PUBLIC_PREVENTION_RULE_NO_MATCH' -or
        $good.finding_count -ne 0) { throw 'STAGE4_CORRECT_FLAG_FALSE_POSITIVE' }
    $unrelated = & $runner @params -SourceText 'Get-Command foo -UseFuzzyMatching' | ConvertFrom-Json
    if ($unrelated.finding_count -ne 0) { throw 'STAGE4_RULE_SCOPE_LEAK' }

    $rollback = $false
    try {
        $params.MinSerial = 8
        $null = & $runner @params -SourceText $badSource
    }
    catch {
        if ($_.Exception.Message -match 'UCIE_DUAL_SIGNATURE_VERIFICATION_FAILED') {
            $rollback = $true
        } else { throw }
    }
    if (-not $rollback) { throw 'STAGE4_ROLLBACK_NOT_DENIED' }
    Write-Output 'UCIE_STAGE4_PRODUCTION_CONSUMER=PASS_SYNTHETIC_ONLY'
}
finally {
    $env:PYTHONPATH = $old
    Remove-Item -LiteralPath $scratch -Recurse -Force -ErrorAction Stop
}
exit 0
