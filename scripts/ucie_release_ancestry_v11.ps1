# UCIE: owner-triggered published release tag ancestry observation (no rule approval).
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ItemId,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,42}$')][string]$ReleaseTag
)
$ErrorActionPreference='Stop'
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root,'D:\UCIE',[StringComparison]::OrdinalIgnoreCase)) { throw 'UCIE_OWNER_ROOT_REQUIRED' }
$python=Join-Path $root '.venv\Scripts\python.exe'
$src=Join-Path $root 'src'
foreach ($p in @('ucie_miner\library_release_ancestry_v11.py','ucie_miner\library_observation_receipts_v10.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $p) -PathType Leaf)) { throw 'UCIE_RELEASE_DEPENDENCY_MISSING' }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'UCIE_OWNER_VENV_MISSING' }
$old=$env:PYTHONPATH
try {
    $env:PYTHONPATH=$src
    & $python -B -m ucie_miner.library_release_ancestry_v11 --check-public --item-id $ItemId --release-tag $ReleaseTag
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_PUBLIC_RELEASE_CHECK_NO_GO' }
} finally {
    $env:PYTHONPATH=$old
}
