# UCIE Local V1 (OWNER MACHINE ONLY): one command, one localhost product.
# First-party UCIE existing venv, no admin rights, installation, scheduler,
# network fetching, repository mutation or cloud deployment.
param(
    [ValidateRange(1024, 65535)]
    [int] $Port = 8767
)
$ErrorActionPreference = 'Stop'
$root = 'D:\UCIE'
$python = 'D:\UCIE\.venv\Scripts\python.exe'
$source = 'D:\UCIE\src'

if (-not (Test-Path -LiteralPath $root -PathType Container) -or
    -not (Test-Path -LiteralPath (Join-Path $root '.git') -PathType Container) -or
    -not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $source -PathType Container)) {
    throw 'UCIE_LOCAL_V1_EXACT_OWNER_ENVIRONMENT_REQUIRED'
}

$oldPythonPath = $env:PYTHONPATH
Push-Location -LiteralPath $root
try {
    # Never inherit a different project's Python modules.
    $env:PYTHONPATH = $source
    Write-Host ("UCIE Local V1 - http://127.0.0.1:{0}/local" -f $Port)
    Write-Host 'Ctrl+C closes the foreground localhost server.'
    & $python -B -m ucie_miner.local_v1_app_v01 --port $Port --open-browser
    if ($LASTEXITCODE -ne 0) {
        throw 'UCIE_LOCAL_V1_START_FAILED'
    }
}
finally {
    $env:PYTHONPATH = $oldPythonPath
    Pop-Location
}
