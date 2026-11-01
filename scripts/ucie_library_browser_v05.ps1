# UCIE V0.5 read-only browser. Does NOT start or modify collector/task.
[CmdletBinding()]
param([ValidateRange(0,65535)][int]$Port = 0)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
foreach ($p in @(
    'ucie_miner\library_browser_v05.py',
    'ucie_miner\library_review_records_v05.py',
    'ucie_miner\library_browser_v04.py',
    'ucie_miner\library_review_v04.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $p) -PathType Leaf)) {
        throw 'UCIE_V05_MISSING_DEPENDENCY'
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_OWNER_VENV_PYTHON_REQUIRED'
}
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_browser_v05 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_V05_BROWSER_FAILED' }
} finally {
    $env:PYTHONPATH = $prior
}
