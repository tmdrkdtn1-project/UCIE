# READ ONLY: TaskScheduler Operational events for the EXACT UCIE public miner.
# No all-task enumeration, log export, service change or task mutation.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$task = Get-ScheduledTask -TaskPath '\' -TaskName 'UCIE-PublicMiner-Hourly' -ErrorAction SilentlyContinue
if ($null -eq $task) {
    [pscustomobject]@{
        schema = 'UCIE_EXACT_PUBLIC_MINER_TASK_EVENT_TRIAGE_V01'
        status = 'UCIE_PUBLIC_MINER_TASK_MISSING_NO_GO'
        events_readable = $false
        record_count = 0
        event_ids = @()
        event_rows = @()
        event_proof_for_two_cycles = $false
        task_changed = $false
    } | ConvertTo-Json -Depth 6 -Compress
    return
}
# XPath filters by BOTH task name and a limited event ID/time range on host.
# Never use wildcards, other task names, or raw event Message strings.
$query = "*[System[(EventID=100 or EventID=101 or EventID=102 or EventID=103 or EventID=107 or EventID=110 or EventID=111 or EventID=200 or EventID=201 or EventID=202 or EventID=203) and TimeCreated[timediff(@SystemTime) <= 21600000]] and EventData[Data[@Name='TaskName']='\UCIE-PublicMiner-Hourly']]"
$readable = $false
$rows = @()
try {
    $events = @(Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -FilterXPath $query -MaxEvents 64 -ErrorAction Stop)
    $readable = $true
    foreach ($event in $events) {
        if ($event.Id -notin @(100,101,102,103,107,110,111,200,201,202,203)) { continue }
        [xml]$xml = $event.ToXml()
        $data = $xml.SelectSingleNode("/*[local-name()='Event']/*[local-name()='EventData']")
        if ($null -eq $data) { continue }
        $nameNode = $data.SelectSingleNode("./*[local-name()='Data' and @Name='TaskName']")
        if ($null -eq $nameNode -or $nameNode.InnerText -cne '\UCIE-PublicMiner-Hourly') { continue }
        $resultNode = $data.SelectSingleNode("./*[local-name()='Data' and @Name='ResultCode']")
        $safeResult = $null
        if ($null -ne $resultNode) {
            $raw = [string]$resultNode.InnerText
            if ($raw -match '^(?:0x)?[0-9a-fA-F]{1,10}$' -and $raw.Length -le 12) {
                $safeResult = $raw
            }
        }
        $rows += [pscustomobject][ordered]@{
            event_id = [int]$event.Id
            event_utc = ([DateTimeOffset]$event.TimeCreated).ToUniversalTime().ToString('o')
            result_code_if_present = $safeResult
        }
        if ($rows.Count -ge 24) { break }
    }
} catch {
    # Access denied / no matching event / invalid event XML are NOT success.
    $readable = $false
    $rows = @()
}
$eventIds = @($rows | ForEach-Object { $_.event_id })
$settings = $task.Settings
$maxRun = if ($null -eq $settings) { $null } else { [string]$settings.ExecutionTimeLimit }
if ($null -ne $maxRun -and $maxRun.Length -gt 32) { $maxRun = 'UNTRUSTED_NO_GO' }
[pscustomobject][ordered]@{
    schema = 'UCIE_EXACT_PUBLIC_MINER_TASK_EVENT_TRIAGE_V01'
    status = if ($readable) {
        'EXACT_UCIE_TASK_EVENT_ROWS_OBSERVED_NOT_CYCLE_PROOF'
    } else {
        'UCIE_EXACT_TASK_EVENTS_NOT_AVAILABLE_NO_GO'
    }
    events_readable = $readable
    record_count = $rows.Count
    event_ids = $eventIds
    event_rows = $rows
    observed_termination_event_111 = (111 -in $eventIds)
    observed_action_completed_event_201 = (201 -in $eventIds)
    observed_task_completed_event_102 = (102 -in $eventIds)
    execution_time_limit = $maxRun
    stop_if_going_on_batteries = if ($null -eq $settings) { $null } else { [bool]$settings.StopIfGoingOnBatteries }
    disallow_start_if_on_batteries = if ($null -eq $settings) { $null } else { [bool]$settings.DisallowStartIfOnBatteries }
    task_state = [string]$task.State
    event_proof_for_two_cycles = $false
    event_payload_or_user_id_returned = $false
    other_task_events_requested = $false
    task_changed = $false
    operating_db_writes = 0
    public_network_requests = 0
} | ConvertTo-Json -Depth 6 -Compress
