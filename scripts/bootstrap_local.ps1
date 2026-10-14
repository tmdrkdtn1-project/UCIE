# UCIE-only Windows bootstrap. No scheduler, collector, or other project access.
[CmdletBinding()]
param([switch]$Setup)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_ROOT_MUST_BE_D_UCIE'
}
if ((Get-Item -LiteralPath $root -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'UCIE_ROOT_REPARSE_POINT_DENIED'
}
$venv = Join-Path $root '.venv'
$python = Join-Path $venv 'Scripts\python.exe'
$runtime = Join-Path $root 'runtime'
$database = Join-Path $runtime 'public_miner.sqlite3'
if ((Test-Path -LiteralPath $runtime) -and
    ((Get-Item -LiteralPath $runtime -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'UCIE_RUNTIME_REPARSE_POINT_DENIED'
}
Write-Output 'PROJECT=UCIE'
Write-Output ('ROOT=' + $root)
Write-Output ('SETUP_REQUESTED=' + $Setup.IsPresent)
Write-Output ('VENV_EXISTS=' + (Test-Path -LiteralPath $python -PathType Leaf))
Write-Output ('RUNTIME_EXISTS=' + (Test-Path -LiteralPath $runtime -PathType Container))
Write-Output ('SQLITE_DB_EXISTS=' + (Test-Path -LiteralPath $database -PathType Leaf))
Write-Output ('LAST_RECEIPT_EXISTS=' + (Test-Path -LiteralPath (Join-Path $runtime 'last_run.json') -PathType Leaf))
if ($Setup) {
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        if (Test-Path -LiteralPath $venv) { throw 'EXISTING_VENV_INCOMPLETE_NO_OVERWRITE' }
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if ($null -eq $launcher) { throw 'PYTHON_LAUNCHER_MISSING' }
        & py -3.15 -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw 'VENV_CREATE_FAILED' }
    }
    & $python -c "import sys; assert sys.version_info[:2] == (3,15), 'Python 3.15 is required'"
    if ($LASTEXITCODE -ne 0) { throw 'VENV_PYTHON_VERSION_MISMATCH' }
    & $python -m pip install --disable-pip-version-check -e $root
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_INSTALL_FAILED' }
    & $python -m unittest discover -s (Join-Path $root 'tests') -v
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_TESTS_FAILED' }
    if (-not (Test-Path -LiteralPath $runtime)) {
        New-Item -ItemType Directory -Path $runtime | Out-Null
    }
    Write-Output 'LOCAL_TESTS=PASS'
    Write-Output 'SCHEDULER_REGISTERED_BY_SCRIPT=NO'
    Write-Output 'COLLECTOR_RUN_BY_SCRIPT=NO'
    Write-Output 'SQLITE_CREATED_BY_SCRIPT=NO'
}
