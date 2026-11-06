# UCIE exact public miner TaskScheduler post-receipt action exit timeline.
# READ ONLY. Filters only \UCIE-PublicMiner-Hourly, fixed public run history.
# No task edits, no network, no private project census, no event GUID output.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$module = Join-Path $root 'src\ucie_miner\public_miner_exit_timeline_v01.py'
$python = Join-Path $root '.venv\Scripts\python.exe'
$history = Join-Path $root 'runtime\run_history.jsonl'
if (-not (Test-Path -LiteralPath $module -PathType Leaf) -or
    -not (Test-Path -LiteralPath $python -PathType Leaf) -or
    -not (Test-Path -LiteralPath $history -PathType Leaf) -or
    ((Get-Item -LiteralPath $history).Attributes -band
        [System.IO.FileAttributes]::ReparsePoint)) {
    throw 'UCIE_FIXED_PUBLIC_EVENT_TIMELINE_PREREQUISITE_NO_GO'
}
$rawReceipts = @(Get-Content -LiteralPath $history -Tail 2 -Encoding UTF8 -ErrorAction Stop)
if ($rawReceipts.Count -ne 2) { throw 'UCIE_TWO_PUBLIC_RECEIPTS_NOT_AVAILABLE' }
$receipts = @()
foreach ($line in $rawReceipts) {
    if ([Text.Encoding]::UTF8.GetByteCount($line) -gt 4096) {
        throw 'UCIE_PUBLIC_RECEIPT_OVERSIZED'
    }
    $parsed = $line | ConvertFrom-Json -ErrorAction Stop
    $receipts += [pscustomobject][ordered]@{
        schema = $parsed.schema
        status = $parsed.status
        started_utc = $parsed.started_utc
        finished_utc = $parsed.finished_utc
        verification_pass = $parsed.verification_pass
        production_approved = $parsed.production_approved
    }
}
# Filter in Windows event provider by this exact public-only task.
# Never enumerate unrelated task events. Instance GUID remains in memory only.
$query = "*[System[(EventID=100 or EventID=102 or EventID=200 or EventID=201) and TimeCreated[timediff(@SystemTime) <= 21600000]] and EventData[Data[@Name='TaskName']='\UCIE-PublicMiner-Hourly']]"
$events = @(Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -FilterXPath $query -MaxEvents 80 -ErrorAction Stop)
$instances = @{}
$expected = Join-Path $root '.venv\Scripts\python.exe'
foreach ($event in $events) {
    if ($event.Id -notin @(100,102,200,201)) { continue }
    [xml]$xml = $event.ToXml()
    $data = $xml.SelectSingleNode("/*[local-name()='Event']/*[local-name()='EventData']")
    if ($null -eq $data) { continue }
    $name = $data.SelectSingleNode("./*[local-name()='Data' and @Name='TaskName']")
    if ($null -eq $name -or $name.InnerText -cne '\UCIE-PublicMiner-Hourly') {
        continue
    }
    $instanceField = if ($event.Id -in @(100,102)) {
        'InstanceId'
    } else { 'TaskInstanceId' }
    $instanceNode = $data.SelectSingleNode(
        "./*[local-name()='Data' and @Name='$instanceField']")
    $guid = [guid]::Empty
    if ($null -eq $instanceNode -or
        -not [guid]::TryParse([string]$instanceNode.InnerText, [ref]$guid)) {
        continue
    }
    $id = $guid.ToString('D')
    if (-not $instances.ContainsKey($id)) {
        $instances[$id] = @{ duplicated = $false }
    }
    $state = $instances[$id]
    $eventKey = [string]$event.Id
    if ($state.ContainsKey($eventKey)) {
        $state.duplicated = $true
        continue
    }
    $action = $data.SelectSingleNode(
        "./*[local-name()='Data' and @Name='ActionName']")
    $code = $data.SelectSingleNode(
        "./*[local-name()='Data' and @Name='ResultCode']")
    $parsedCode = $null
    if ($event.Id -eq 201 -and $null -ne $code) {
        $candidate = [string]$code.InnerText
        $numeric = [int64]0
        if ([int64]::TryParse($candidate, [ref]$numeric) -and
            $numeric -ge 0 -and $numeric -le 4294967295L) {
            $parsedCode = $numeric
        }
    }
    $state[$eventKey] = [pscustomobject]@{
        utc = ([DateTimeOffset]$event.TimeCreated).ToUniversalTime().ToString('o')
        action_valid = ($null -ne $action -and
            [string]::Equals([string]$action.InnerText, $expected,
                [StringComparison]::OrdinalIgnoreCase))
        result = $parsedCode
    }
}
$records = @()
foreach ($state in $instances.Values) {
    if (-not ($state.ContainsKey('100') -and $state.ContainsKey('200') -and
              $state.ContainsKey('201') -and $state.ContainsKey('102'))) {
        continue
    }
    if ($null -eq $state['201'].result) { continue }
    $records += [pscustomobject][ordered]@{
        event_100_utc = $state['100'].utc
        event_200_utc = $state['200'].utc
        event_201_utc = $state['201'].utc
        event_102_utc = $state['102'].utc
        action_is_exact_python = (
            $state['200'].action_valid -and $state['201'].action_valid)
        result_code_201 = $state['201'].result
        event_duplicated = [bool]$state.duplicated
    }
    if ($records.Count -ge 16) { break }
}
$payload = [pscustomobject][ordered]@{
    schema = 'UCIE_PUBLIC_MINER_EXACT_TASK_TIMELINE_INPUT_V01'
    source = 'OWNER_EXACT_TASK_XPATH_READONLY'
    receipts = $receipts
    instances = $records
    task_writes = $false
} | ConvertTo-Json -Depth 8 -Compress
$oldPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $root 'src'
    $output = $payload | & $python -B -m ucie_miner.public_miner_exit_timeline_v01
    $exitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $oldPath
}
if ($null -eq $output) { throw 'UCIE_POST_RECEIPT_TIMELINE_OUTPUT_MISSING' }
$report = ($output | Out-String) | ConvertFrom-Json -ErrorAction Stop
if ($report.schema -cne 'UCIE_PUBLIC_MINER_POST_RECEIPT_EXIT_TIMELINE_V01') {
    throw 'UCIE_POST_RECEIPT_TIMELINE_WRONG_SCHEMA'
}
if ($exitCode -ne 0 -and $report.status -cne
    'EXACT_TASK_POST_RECEIPT_EXIT_NOT_PROVEN_NO_GO') {
    throw 'UCIE_POST_RECEIPT_TIMELINE_INTERNAL_FAILURE_NO_GO'
}
# Even with 2 matching events the report cannot approve scheduler/repair.
$output
