# UCIE W11 public miner synthetic shutdown phases, owner-only.
# Read-only preview is default. -RunSynthetic uses disposable temp fixtures.
# Does not run public miner, edit scheduled tasks, network or operating DB.
[CmdletBinding()]
param([switch]$RunSynthetic)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$module = Join-Path $root 'src\ucie_miner\public_miner_shutdown_phase_w11.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $module -PathType Leaf)) {
    throw 'UCIE_W11_SYNTHETIC_PROBE_PREREQUISITES_MISSING'
}
$previous = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $arguments = @('-B', '-m', 'ucie_miner.public_miner_shutdown_phase_w11')
    if ($RunSynthetic.IsPresent) { $arguments += '--run-synthetic' }
    $lines = & $python @arguments
    $result = $LASTEXITCODE
    if ($result -ne 0 -or $null -eq $lines) {
        throw 'UCIE_W11_SYNTHETIC_SHUTDOWN_NO_GO'
    }
    $report = ($lines | Out-String) | ConvertFrom-Json -ErrorAction Stop
    if ($report.schema -cne 'UCIE_W11_PUBLIC_MINER_SHUTDOWN_PHASE_SYNTHETIC_V01') {
        throw 'UCIE_W11_INVALID_SOURCE_SCHEMA'
    }
    if ($RunSynthetic.IsPresent) {
        if ($report.status -cne 'FIRST_PARTY_SYNTHETIC_PHASES_CLASSIFIED_NO_PRODUCTION_CLAIM' -or
            $report.passed -ne 4 -or
            $report.real_public_miner_executed -cne $false -or
            $report.task_scheduler_mutations -ne 0 -or
            $report.owner_operating_db_writes -ne 0 -or
            $report.production_termination_root_cause_proven -cne $false) {
            throw 'UCIE_W11_SYNTHETIC_REPORT_FAILED_VALIDATION'
        }
    } else {
        if ($report.status -cne 'SYNTHETIC_PHASE_LAB_NOT_RUN_NO_SCHEDULER_PROOF' -or
            $report.synthetic_subprocesses_started -ne 0) {
            throw 'UCIE_W11_PREVIEW_NOT_READONLY'
        }
    }
    $lines
} finally {
    $env:PYTHONPATH = $previous
}
