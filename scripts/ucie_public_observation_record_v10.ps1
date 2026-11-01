[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ItemId)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) { throw 'UCIE_OWNER_ROOT_REQUIRED' }
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
foreach ($p in @('ucie_miner\library_observation_receipts_v10.py','ucie_miner\library_public_proof_v09.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $p) -PathType Leaf)) { throw 'UCIE_PUBLIC_OBSERVATION_DEPENDENCY_MISSING' }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'UCIE_OWNER_PYTHON_NOT_FOUND' }
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_observation_receipts_v10 --record-public --item-id $ItemId
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_PUBLIC_OBSERVATION_NOT_RECORDED' }
} finally {
    $env:PYTHONPATH = $prior
}
