# UCIE W09 SkillBook 001 read-only release gate preflight.
# Default shows blockers only. -RunSynthetic explicitly creates/cleans tiny
# synthetic temp fixtures through W08 then checks the in-memory receipt.
# No package, signing, export, scheduler or operating DB mutation.
[CmdletBinding()]
param([switch]$RunSynthetic)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
$gate = Join-Path $src 'ucie_miner\skillbook_w09_release_gate_v01.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $gate -PathType Leaf)) {
    throw 'UCIE_W09_PREFLIGHT_SOURCE_MISSING'
}
$before = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    $arguments = @('-B', '-m', 'ucie_miner.skillbook_w09_release_gate_v01')
    if ($RunSynthetic.IsPresent) { $arguments += '--run-synthetic' }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_W09_RECEIPT_INTEGRITY_NO_GO' }
} finally {
    $env:PYTHONPATH = $before
}
