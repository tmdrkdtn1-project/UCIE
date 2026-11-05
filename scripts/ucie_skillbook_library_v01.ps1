# UCIE only: owner-local read-only SkillBook V0.1 browser. Not a task or service.
[CmdletBinding()]
param([ValidateRange(0,65535)][int]$Port = 0)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
foreach ($name in @(
    'ucie_miner\skillbook_scandir_recipe_v01.py',
    'ucie_miner\skillbook_product_v01.py',
    'ucie_miner\library_browser_skillbook_v01.py',
    'ucie_miner\library_browser_v11.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $name) -PathType Leaf)) {
        throw 'UCIE_SKILLBOOK_SOURCE_MISSING'
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_OWNER_PYTHON_NOT_FOUND'
}
$before = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_browser_skillbook_v01 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_SKILLBOOK_BROWSER_EXIT_NONZERO' }
} finally {
    $env:PYTHONPATH = $before
}
