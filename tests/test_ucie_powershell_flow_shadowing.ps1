# Inert PowerShell AST fixture suite, unrelated to runtime approval or GO.
$ErrorActionPreference = 'Stop'
. (Join-Path (Join-Path $PSScriptRoot '..') 'scripts/ucie_powershell_static_candidates.ps1')

$fixtures = @(
    @{ id='positive-rvpa-alias'; expected=$true; code='rvpa .directory\*.txt -Relative' },
    @{ id='positive-gcm-original'; expected=$true; code='gcm Get-Foo -UseFuzzyMatching' },
    @{ id='positive-gcm-before-shadow'; expected=$true; code=@'
gcm Get-Foo -UseFuzzyMatching
function gcm { 'custom' }
'@ },
    @{ id='positive-dead-shadow'; expected=$true; code=@'
if ($false) { function gcm { 'custom' } }
gcm Get-Foo -UseFuzzyMatching
'@ },
    @{ id='negative-gcm-function-shadow'; expected=$false; code=@'
function gcm { 'custom' }
gcm Get-Foo -UseFuzzyMatching
'@ },
    @{ id='negative-get-command-shadow'; expected=$false; code=@'
function Get-Command { 'custom' }
Get-Command Get-Foo -UseFuzzyMatching
'@ },
    @{ id='negative-resolve-path-shadow'; expected=$false; code=@'
function Resolve-Path { 'custom' }
Resolve-Path .directory\*.txt -Relative
'@ },
    @{ id='negative-literal-dead-branch'; expected=$false; code='if ($false) { rvpa .directory\*.txt -Relative }' }
)

$tp=0; $tn=0; $fp=0; $fn=0
$observations = [System.Collections.Generic.List[object]]::new()
foreach ($fixture in $fixtures) {
    $result = Find-UCIEPowerShellCandidate -SourceText $fixture.code
    $observed = ($result.finding_count -gt 0)
    if ($fixture.expected -and $observed) { $tp++ }
    elseif ($fixture.expected) { $fn++ }
    elseif ($observed) { $fp++ }
    else { $tn++ }
    $observations.Add([pscustomobject]@{
        case_id=$fixture.id
        expected_flag=$fixture.expected
        observed_flag=$observed
        finding_count=$result.finding_count
        source_sha256=$result.source_sha256
    })
}
if ($tp -ne 4 -or $tn -ne 4 -or $fp -ne 0 -or $fn -ne 0) {
    throw "Unexpected scoped synthetic calibration TP=$tp TN=$tn FP=$fp FN=$fn"
}
$report = [pscustomobject]@{
    schema='UCIE_PS_FLOW_SHADOWING_SYNTHETIC_V1'
    status='SYNTHETIC_CALIBRATION_ONLY'
    fixture_count=$fixtures.Count
    true_positive=$tp
    true_negative=$tn
    false_positive=$fp
    false_negative=$fn
    observations=@($observations.ToArray())
    real_world_accuracy_verified=$false
    parser_executed_supplied_code=$false
    approvals_verified=0
    production_approved=$false
    persistent_writes=0
}
Write-Output ('UCIE_PS_FLOW_SHADOWING=' + ($report | ConvertTo-Json -Compress -Depth 6))
