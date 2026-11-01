# UCIE V0.7 one-shot read-only public audit receipt for the owner.
[CmdletBinding()]
param([ValidateRange(1,20)][int]$Top = 10)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'EXPECTED_UCIE_ROOT_D_DRIVE'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
if (-not (Test-Path -LiteralPath (Join-Path $src 'ucie_miner\library_audit_v07.py') -PathType Leaf)) {
    throw 'UCIE_V07_AUDIT_MODULE_MISSING'
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_VENV_PYTHON_NOT_FOUND'
}
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_audit_v07 --top $Top
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_V07_SOURCE_AUDIT_NO_GO' }
} finally {
    $env:PYTHONPATH = $prior
}
