# UCIE V0.3: Windows owner local-only evidence comparison browser.
# No existing tasks, databases, services or V0.2 files modified.
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
    'ucie_miner\library_browser_v03.py',
    'ucie_miner\library_compare.py',
    'ucie_miner\library_explore.py',
    'ucie_miner\library_browser_v02.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $relative) -PathType Leaf)) {
        throw 'UCIE_V03_SOURCE_NOT_INSTALLED'
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_PYTHON_NOT_FOUND'
}
$previous = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_browser_v03 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_LIBRARY_V03_NONZERO_EXIT' }
} finally {
    $env:PYTHONPATH = $previous
}
