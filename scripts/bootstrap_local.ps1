# UCIE-only Windows bootstrap. No scheduler, collector, or other project access.
[CmdletBinding()]
param([switch]$Setup, [switch]$StagePreview)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
# Optional source portability preview ONLY. Never permits a new owner runtime
# task, Python environment, Git checkout, database or C40 tunnel cutover.
# The current D:\UCIE default/Install/Setup behavior below is unchanged.
if ($StagePreview) {
    if ($Setup) { throw 'UCIE_STAGE_PREVIEW_MUTATING_ACTION_DENIED' }
    $parent = Split-Path -Path $root -Parent
    if (-not [string]::Equals((Split-Path -Path $root -Leaf), 'UCIE',
        [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals((Split-Path -Path $parent -Leaf), 'UCIE_PROJECT',
        [StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_STAGE_PREVIEW_EXACT_HIERARCHY_REQUIRED'
    }
    foreach ($path in @($parent, $root, $PSScriptRoot, $PSCommandPath)) {
        $entry = Get-Item -LiteralPath $path -Force -ErrorAction Stop
        if (-not $entry.PSIsContainer -or
            (($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            throw 'UCIE_STAGE_PREVIEW_INDIRECT_PATH_DENIED'
        }
    }
    Write-Output 'UCIE_STAGE_PREVIEW_ONLY_NO_SETUP_OR_TASK_MUTATION'
    Write-Output ('STAGED_CODE_ROOT=' + $root)
    Write-Output 'GIT_VENV_RUNTIME_MCP_TUNNEL_NOT_INSPECTED_OR_MODIFIED'
    Write-Output 'LIVE_ROOT_CUTOVER_AUTHORIZED=FALSE'
    return
}
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
