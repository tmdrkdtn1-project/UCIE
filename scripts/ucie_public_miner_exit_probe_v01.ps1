# UCIE public miner first-party synthetic process-exit preflight.
# Preview only unless -RunSynthetic. Never starts production collection.
[CmdletBinding()]
param([switch]$RunSynthetic)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$source = Join-Path $root 'src\ucie_miner\public_miner_exit_probe_v01.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $source -PathType Leaf)) {
    throw 'UCIE_EXIT_SYNTHETIC_PROBE_PREREQUISITES_MISSING'
}
$before = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $arguments = @('-B', '-m', 'ucie_miner.public_miner_exit_probe_v01')
    if ($RunSynthetic.IsPresent) { $arguments += '--run-synthetic' }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_EXIT_SYNTHETIC_PROBE_NO_GO' }
} finally {
    $env:PYTHONPATH = $before
}
