# UCIE-only owner-host read-only Library browser launcher.
# The script deliberately does NOT register a service or change an existing task.
[CmdletBinding()]
param([ValidateRange(0,65535)][int]$Port = 0)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'EXPECTED_UCIE_ROOT_D_DRIVE'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_VENV_PYTHON_NOT_FOUND'
}
if (-not (Test-Path -LiteralPath (Join-Path $src 'ucie_miner\library_browser.py') -PathType Leaf)) {
    throw 'UCIE_LIBRARY_BROWSER_NOT_INSTALLED'
}
$old = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    & $python -B -m ucie_miner.library_browser --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_LIBRARY_BROWSER_EXIT_NONZERO' }
}
finally {
    $env:PYTHONPATH = $old
}
