# UCIE V0.6-V0.7: source-bound read-only local browser.
[CmdletBinding()]
param([ValidateRange(0,65535)][int]$Port = 0)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'EXPECTED_UCIE_ROOT_D_DRIVE'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
foreach ($relative in @(
    'ucie_miner\library_proof_assessment_v06.py',
    'ucie_miner\library_audit_v07.py',
    'ucie_miner\library_browser_v07.py',
    'ucie_miner\library_browser_v05.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $relative) -PathType Leaf)) {
        throw 'UCIE_V07_SOURCE_NOT_INSTALLED'
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_VENV_PYTHON_NOT_FOUND'
}
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_browser_v07 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_AUDIT_BROWSER_V07_NONZERO_EXIT' }
} finally {
    $env:PYTHONPATH = $prior
}
