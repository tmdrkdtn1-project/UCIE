# UCIE SkillBook 001 W08 synthetic-only first-party QA (one-shot).
# Writes/removes bounded new synthetic fixtures in system temp.
# No real source directory argument, no public network, no scheduler/DB change.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
$module = Join-Path $src 'ucie_miner\skillbook_scandir_qa_v01.py'
if (-not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $module -PathType Leaf)) {
    throw 'UCIE_W08_QA_RUNTIME_MISSING'
}
$before = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.skillbook_scandir_qa_v01
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_SKILLBOOK_W08_SYNTHETIC_QA_NO_GO' }
} finally {
    $env:PYTHONPATH = $before
}
