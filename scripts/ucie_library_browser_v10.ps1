[CmdletBinding()]
param([ValidateRange(0,65535)][int]$Port = 0)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) { throw 'UCIE_OWNER_ROOT_REQUIRED' }
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
foreach ($p in @('ucie_miner\library_observation_receipts_v10.py','ucie_miner\library_browser_v10.py','ucie_miner\library_browser_v09.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $p) -PathType Leaf)) { throw 'UCIE_OBSERVATION_BROWSER_DEPENDENCY_MISSING' }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'UCIE_OWNER_PYTHON_NOT_FOUND' }
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_browser_v10 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_V10_BROWSER_NONZERO_EXIT' }
} finally {
    $env:PYTHONPATH = $prior
}
