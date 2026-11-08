# Remove ONLY the verified UCIE-LocalV1-Web task. PREVIEW unless -Apply.
# Does not stop an unrelated process, delete files, touch other schedules
# or change Cloudflare routes.
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch] $Apply,
    [ValidateRange(1024, 65535)]
    [int] $Port = 18767
)
$ErrorActionPreference = 'Stop'
Import-Module ScheduledTasks -ErrorAction Stop
$name = 'UCIE-LocalV1-Web'
$path = '\'
$existing = Get-ScheduledTask -TaskName $name -TaskPath $path -ErrorAction SilentlyContinue
if ($null -eq $existing) {
    Write-Output 'UCIE_LOCAL_V1_AUTOSTART_NOT_REGISTERED_NO_CHANGES'
    return
}
$expectedArgs = '-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port ' + $Port
$actions = @($existing.Actions)
if ($actions.Count -ne 1 -or
    -not [string]::Equals($actions[0].Execute,
        'D:\UCIE\.venv\Scripts\python.exe',
        [System.StringComparison]::OrdinalIgnoreCase) -or
    $actions[0].Arguments -ne $expectedArgs) {
    throw 'UCIE_AUTOSTART_TASK_IDENTITY_MISMATCH_DO_NOT_REMOVE'
}
$user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
if ($existing.Principal.UserId -ne $user) {
    throw 'UCIE_AUTOSTART_TASK_PRINCIPAL_MISMATCH_DO_NOT_REMOVE'
}
if (-not $Apply) {
    Write-Output 'UCIE_LOCAL_V1_AUTOSTART_REMOVE_PREVIEW_ONLY'
    return
}
if ($PSCmdlet.ShouldProcess($name, 'stop and unregister only this verified UCIE task')) {
    if ($existing.State -eq 'Running') {
        Stop-ScheduledTask -TaskName $name -TaskPath $path -ErrorAction Stop
    }
    Unregister-ScheduledTask -TaskName $name -TaskPath $path -Confirm:$false -ErrorAction Stop
    Write-Output 'UCIE_LOCAL_V1_AUTOSTART_TASK_REMOVED_NO_OTHER_CHANGES'
}
