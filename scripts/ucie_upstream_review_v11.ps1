# UCIE V1.1: offline safe regression + source-linked review packet.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ItemId)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root,'D:\UCIE',[StringComparison]::OrdinalIgnoreCase)) { throw 'UCIE_OWNER_ROOT_REQUIRED' }
$python=Join-Path $root '.venv\Scripts\python.exe'
$src=Join-Path $root 'src'
foreach ($p in @('ucie_miner\library_upstream_review_v11.py','ucie_miner\library_safety_regression_v10.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $p) -PathType Leaf)) { throw 'UCIE_REVIEW_DEPENDENCY_MISSING' }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'UCIE_OWNER_VENV_MISSING' }
$old=$env:PYTHONPATH
try {
    $env:PYTHONPATH=$src
    & $python -B -m ucie_miner.library_upstream_review_v11 --item-id $ItemId
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_REVIEW_BUNDLE_NO_GO' }
} finally {
    $env:PYTHONPATH=$old
}
