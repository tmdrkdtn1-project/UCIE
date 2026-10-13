# Explicit opt-out for the UCIE-owned task only.
[CmdletBinding()]
param([switch]$Remove)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'EXPECTED_UCIE_ROOT_D_DRIVE'
}
$name = 'UCIE-PublicMiner-Hourly'
$task = Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Output 'TASK_STATUS=ALREADY_ABSENT'
    return
}
if (-not $Remove) {
    Write-Output 'PREVIEW_ONLY: .\scripts\remove_hourly_task.ps1 -Remove'
    return
}
Unregister-ScheduledTask -TaskPath '\' -TaskName $name -Confirm:$false -ErrorAction Stop
Write-Output 'UCIE_TASK_REMOVED=TRUE'
Write-Output 'LEARNING_DB_UNCHANGED=TRUE'
