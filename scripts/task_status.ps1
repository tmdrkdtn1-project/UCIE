# UCIE task status, no writes and no project access.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'EXPECTED_UCIE_ROOT_D_DRIVE'
}
$taskName = 'UCIE-PublicMiner-Hourly'
$task = Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Output 'TASK_STATUS=NOT_REGISTERED'
} else {
    $task | Select-Object TaskName, State
    Get-ScheduledTaskInfo -TaskPath '\' -TaskName $taskName |
        Select-Object LastRunTime, NextRunTime, LastTaskResult
}
$last = Join-Path $root 'runtime\last_run.json'
if (Test-Path -LiteralPath $last -PathType Leaf) {
    Write-Output 'LAST_UCIE_RUN_RECEIPT:'
    Get-Content -LiteralPath $last -Raw -Encoding UTF8
} else {
    Write-Output 'LAST_UCIE_RUN_RECEIPT=NOT_FOUND'
}
