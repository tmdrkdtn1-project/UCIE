# UCIE-only owner-local Slack Evidence Reader connection launcher.
# Preview status is read-only. Enroll prompts for the token *inside Windows*.
[CmdletBinding()]
param(
    [ValidateSet('Preview','Enroll','Verify')]
    [string]$Mode = 'Preview'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = 'D:\UCIE'
$src = 'D:\UCIE\src'
$python = 'D:\UCIE\.venv\Scripts\python.exe'
$module = 'D:\UCIE\src\ucie_miner\ucie_slack_windows_reader_v1.py'
foreach ($path in @($root,$src,$python,$module)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw 'UCIE_SLACK_OWNER_LAUNCHER_REQUIRED_PATH_ABSENT'
    }
    $item = Get-Item -LiteralPath $path -ErrorAction Stop
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'UCIE_SLACK_OWNER_LAUNCHER_REPARSE_REJECTED'
    }
}
# Avoid importing non-UCIE modules through the caller's PYTHONPATH.
# Preserve and restore even if the child exits with an error.
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    $action = switch ($Mode) {
        'Preview' { 'status' }
        'Enroll' { 'enroll' }
        'Verify' { 'verify' }
        default { throw 'UCIE_SLACK_OWNER_LAUNCHER_UNKNOWN_MODE' }
    }
    & $python -m ucie_miner.ucie_slack_windows_reader_v1 $action
    $code = [int]$LASTEXITCODE
    if ($code -ne 0) {
        throw ('UCIE_SLACK_OWNER_LAUNCHER_BLOCKED_EXIT_' + $code)
    }
}
finally {
    $env:PYTHONPATH = $previousPythonPath
}
