# UCIE-only owner-local read-only federation; no scheduled task or service install.
[CmdletBinding()]
param([ValidateRange(0,65535)][int]$Port = 0)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
foreach ($name in @(
    'ucie_miner\skillbook_catalog_union_v01.py',
    'ucie_miner\library_browser_skillbook_v01.py',
    'ucie_miner\library_search.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $name) -PathType Leaf)) {
        throw 'UCIE_FEDERATED_SOURCE_MISSING'
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_OWNER_PYTHON_NOT_FOUND'
}
$before = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.skillbook_catalog_union_v01 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_FEDERATED_BROWSER_EXIT_NONZERO' }
} finally {
    $env:PYTHONPATH = $before
}
