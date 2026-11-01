# UCIE V1.2: read-only quality observation inspection, never triggers data collection.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) { throw 'UCIE_OWNER_ROOT_D_DRIVE_REQUIRED' }
$python=Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'UCIE_OWNER_PYTHON_NOT_FOUND' }
$prior=$env:PYTHONPATH
try {
    $env:PYTHONPATH=Join-Path $root 'src'
    & $python -B -m ucie_miner.library_quality_loop_v12 --inspect
    if ($LASTEXITCODE -ne 0) { throw 'STAGE17_QUALITY_SNAPSHOT_UNAVAILABLE' }
} finally {
    $env:PYTHONPATH=$prior
}
