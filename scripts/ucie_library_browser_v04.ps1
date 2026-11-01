# UCIE V0.4: review-only evidence dossier browser, not a deployment task.
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
    'ucie_miner\library_review_v04.py',
    'ucie_miner\library_browser_v04.py',
    'ucie_miner\library_browser_v03.py',
    'ucie_miner\library_explore.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $relative) -PathType Leaf)) {
        throw 'UCIE_V04_SOURCE_NOT_INSTALLED'
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_VENV_PYTHON_NOT_FOUND'
}
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_browser_v04 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_LIBRARY_V04_EXIT_NONZERO' }
} finally {
    $env:PYTHONPATH = $prior
}
