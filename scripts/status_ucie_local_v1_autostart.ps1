# UCIE Local V1 owner-only autostart status: read-only, UCIE task + loopback only.
[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int] $Port = 18767
)
$ErrorActionPreference = 'Stop'
Import-Module ScheduledTasks -ErrorAction Stop
$taskName = 'UCIE-LocalV1-Web'
$task = Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
$taskState = 'NOT_REGISTERED'
$lastResult = $null
$expectedAction = $false
$windowless = $false
$consoleMode = $false
if ($null -ne $task) {
    $taskState = [string] $task.State
    $info = Get-ScheduledTaskInfo -TaskName $taskName -TaskPath '\' -ErrorAction Stop
    $lastResult = $info.LastTaskResult
    $actions = @($task.Actions)
    if ($actions.Count -eq 1) {
        $consoleMode = [string]::Equals($actions[0].Execute,
            'D:\UCIE\.venv\Scripts\python.exe',
            [System.StringComparison]::OrdinalIgnoreCase)
        $windowless = [string]::Equals($actions[0].Execute,
            'D:\UCIE\.venv\Scripts\pythonw.exe',
            [System.StringComparison]::OrdinalIgnoreCase)
        $expectedAction = (($consoleMode -or $windowless) -and
            $actions[0].Arguments -eq
                ('-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port ' + $Port) -and
            [string]::Equals($actions[0].WorkingDirectory,
                'D:\UCIE', [System.StringComparison]::OrdinalIgnoreCase))
    }
}
$health = 'NOT_RESPONDING'
$schema = $null
try {
    $uri = 'http://127.0.0.1:' + $Port + '/local/health'
    $result = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 2 -ErrorAction Stop
    $schema = [string] $result.schema
    if ($schema -eq 'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01' -and
        $result.owner_acceptance_verified -eq $true -and
        $result.online_release_authorized -eq $false) {
        $health = 'UCIE_LOCAL_V1_HEALTHY'
    }
    else {
        $health = 'FOREIGN_OR_UNEXPECTED_HTTP_RESPONSE'
    }
}
catch {
    $health = 'NOT_RESPONDING'
}
[PSCustomObject]@{
    task_name = $taskName
    task_state = $taskState
    task_action_matches_exact_ucie = $expectedAction
    windowless_background_mode = ($expectedAction -and $windowless)
    console_mode = ($expectedAction -and $consoleMode)
    last_task_result = $lastResult
    health = $health
    app_schema = $schema
    local_url = ('http://127.0.0.1:' + $Port + '/local')
    cloudflare_tunnel_inspected_or_modified = $false
    public_miner_task_modified = $false
    customer_release_authorized = $false
} | ConvertTo-Json -Depth 4
