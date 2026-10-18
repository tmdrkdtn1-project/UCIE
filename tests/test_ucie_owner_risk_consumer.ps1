# End-to-end owner-risk Rulepack consumer on disposable Windows CI.
# Uses test-only temporary owner keys + MOCKED GitHub run (not actual approval).
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$consumer = Join-Path $root 'scripts/ucie_signed_owner_risk_scan.ps1'
$python = (Get-Command python -ErrorAction Stop).Source
$previous = $env:PYTHONPATH
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('ucie_owner_risk_' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -ErrorAction Stop | Out-Null
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $source = @'
from pathlib import Path
import sys
from unittest.mock import patch
from ucie_public.owner_release import (
    JOBS, CONFIRM, RISK, publish_owner_risk_release
)
from ucie_public.rulepack import generate_keys
root=Path(sys.argv[1])
(root/"build").mkdir()
private,_=generate_keys(root/"keys",purpose="production")
commit="a"*40
names=sorted(JOBS)
ev={
  "schema":"UCIE_OWNER_RELEASE_AUTOMATED_QA_EVIDENCE_V1",
  "repository":"tmdrkdtn1-project/UCIE",
  "workflow":".github/workflows/stage1-offline-tests.yml",
  "run_id":777777,
  "run_url":"https://github.com/tmdrkdtn1-project/UCIE/actions/runs/777777",
  "head_sha":commit,"event":"push","branch":"main",
  "conclusion":"success","job_names":names,
  "runtime_platforms":["ubuntu-latest","windows-latest"],
  "windows_ps51_verified":True,"stage4_synthetic_verified":True,
  "independent_human_qa":False,"legal_license_signoff":False,
  "evidence_kind":"LIVE_PUBLIC_GITHUB_ACTIONS_CHECKED_AT_SIGNING",
}
with patch("ucie_public.owner_release._local_clean_sha",return_value=commit), \
     patch("ucie_public.owner_release.validate_live_automated_qa",return_value=ev):
    publish_owner_risk_release(
        root,private,root/"build"/"owner.zip",run_id=777777,
        serial=7,confirmation=CONFIRM,risk_acceptance=RISK)
print("SYNTHETIC_OWNER_RISK_RELEASE_FIXTURE_ONLY")
'@
    $made = $source | & $python -B - $tmp
    if ($LASTEXITCODE -ne 0 -or $made -cne 'SYNTHETIC_OWNER_RISK_RELEASE_FIXTURE_ONLY') {
        throw 'OWNER_RISK_SYNTHETIC_FIXTURE_FAILED'
    }
    $params = @{
        PackPath = Join-Path $tmp 'build/owner.zip'
        OwnerTrustPath = Join-Path $tmp 'keys/public_production.pem'
        PythonPath = $python
        MinSerial = 7
    }
    $bad = @'
throw "DO_NOT_EXECUTE"
python -I -X disable_remote_debug -
'@
    $found = & $consumer @params -SourceText $bad | ConvertFrom-Json
    if ($found.finding_count -ne 1 -or
        $found.status -cne 'PUBLIC_PREVENTION_RULE_MATCH' -or
        $found.owner_signature -cne 'VALID' -or
        $found.owner_risk_accepted -ne $true -or
        $found.independent_human_qa_approved -ne $false -or
        $found.auto_fix_applied -ne $false -or
        $found.supplied_source_executed -ne $false) {
        throw 'OWNER_RISK_CONSUMER_INTEGRATION_FAILED'
    }
    $good = & $consumer @params -SourceText 'python -I -X disable-remote-debug -' | ConvertFrom-Json
    if ($good.finding_count -ne 0) {
        throw 'OWNER_RISK_CORRECT_FLAG_FALSE_POSITIVE'
    }
    $unrelated = & $consumer @params -SourceText 'Get-Command foo -UseFuzzyMatching' | ConvertFrom-Json
    if ($unrelated.finding_count -ne 0) {
        throw 'OWNER_RISK_UNRELATED_RULE_LEAK'
    }
    $blocked = $false
    $params.MinSerial = 8
    try { $null = & $consumer @params -SourceText $bad }
    catch {
        if ($_.Exception.Message -match 'UCIE_OWNER_RISK_RELEASE_VERIFICATION_FAILED') {
            $blocked = $true
        } else { throw }
    }
    if (-not $blocked) { throw 'OWNER_RISK_ROLLBACK_NOT_BLOCKED' }
    Write-Output 'UCIE_OWNER_RISK_CONSUMER=PASS_SYNTHETIC_ONLY'
}
finally {
    $env:PYTHONPATH = $previous
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction Stop
}
exit 0
