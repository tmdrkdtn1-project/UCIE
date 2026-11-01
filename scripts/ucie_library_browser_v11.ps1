# UCIE V1.1: local-only review browser; no automatic release checks.
[CmdletBinding()]
param([ValidateRange(0,65535)][int]$Port=0)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root,'D:\UCIE',[StringComparison]::OrdinalIgnoreCase)) { throw 'UCIE_OWNER_ROOT_REQUIRED' }
$python=Join-Path $root '.venv\Scripts\python.exe'
$src=Join-Path $root 'src'
foreach ($p in @('ucie_miner\library_browser_v11.py','ucie_miner\library_browser_v10.py',
                 'ucie_miner\library_upstream_review_v11.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $p) -PathType Leaf)) { throw 'UCIE_V11_DEPENDENCY_MISSING' }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'UCIE_OWNER_VENV_MISSING' }
$old=$env:PYTHONPATH
try {
    $env:PYTHONPATH=$src
    & $python -B -m ucie_miner.library_browser_v11 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_V11_BROWSER_NO_GO' }
} finally {
    $env:PYTHONPATH=$old
}
