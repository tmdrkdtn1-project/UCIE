# Accuracy CALIBRATION of UCIE-authored synthetic PowerShell source only.
# ParseInput does not execute SourceText, load files, run commands or write DB.
$ErrorActionPreference = 'Stop'
. (Join-Path (Join-Path $PSScriptRoot '..') 'scripts/ucie_powershell_static_candidates.ps1')

$fixtures = @(
    @{ id='p-fuzzy'; expected=$true; code='Get-Command Get-Foo -UseFuzzyMatching' },
    @{ id='p-relative'; expected=$true; code="Resolve-Path '.directory\*.txt' -Relative" },
    # Calibration: fixed built-in gcm alias now recognized without lookup.
    @{ id='p-alias-known-fn'; expected=$true; code='gcm Get-Foo -UseFuzzyMatching' },
    @{ id='n-exact'; expected=$false; code='Get-Command Get-Foo' },
    @{ id='n-absolute'; expected=$false; code='Resolve-Path .directory\file.txt' },
    # Calibration: literal if ($false) branch is excluded from candidates.
    @{ id='n-unreachable-known-fp'; expected=$false; code='if ($false) { Get-Command Get-Foo -UseFuzzyMatching }' }
)
$tp=0; $tn=0; $fp=0; $fn=0
$observations = [System.Collections.Generic.List[object]]::new()
foreach ($fixture in $fixtures) {
    $result = Find-UCIEPowerShellCandidate -SourceText $fixture.code
    $detected = ($result.finding_count -gt 0)
    if ($fixture.expected -and $detected) { $tp++ }
    elseif ($fixture.expected) { $fn++ }
    elseif ($detected) { $fp++ }
    else { $tn++ }
    $observations.Add([pscustomobject]@{
        case_id=$fixture.id
        expected_flag=$fixture.expected
        observed_flag=$detected
        source_sha256=$result.source_sha256
    })
}
if ($tp -ne 3 -or $fn -ne 0 -or $fp -ne 0 -or $tn -ne 3) {
    throw 'Unexpected synthetic calibration confusion matrix'
}
$output = [pscustomobject]@{
    schema='UCIE_POWERSHELL_SYNTHETIC_ACCURACY_V1'
    status='SYNTHETIC_CALIBRATION_ONLY'
    total=$fixtures.Count
    true_positive=$tp; false_positive=$fp
    false_negative=$fn; true_negative=$tn
    precision_ppm=[int][math]::Floor($tp * 1000000 / ($tp+$fp))
    recall_ppm=[int][math]::Floor($tp * 1000000 / ($tp+$fn))
    observations=@($observations.ToArray())
    independent_label_validation=$false
    real_world_accuracy_verified=$false
    production_approved=$false
    rulepack_signed=$false
    persistent_writes=0
}
Write-Output ('UCIE_PS_SYNTHETIC_ACCURACY=' + ($output | ConvertTo-Json -Compress -Depth 5))
