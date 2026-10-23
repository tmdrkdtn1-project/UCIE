# UCIE-only observed duplicate C40 tunnel resolution.
# Default Inspect is read-only. StopOld terminates ONLY PID 30664 with
# the exact previously observed parent, start time, binary, C40 and tunnel ID.
# No wildcard stopping, task editing, service restart or profile changes.
# No raw commands, tunnel IDs, credentials or unrelated processes are printed.
[CmdletBinding()]
param(
    [ValidateSet('Inspect', 'StopOld')]
    [string]$Mode = 'Inspect',
    [string]$Approval = ''
)
$ErrorActionPreference = 'Stop'

$clientExe = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$ucieRoot = 'D:\UCIE_DATA\'
$profilePath = 'D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml'

$oldPid = 30664
$newPid = 22468
$oldParent = 14252
$newParent = 31596
$oldStarted = '2026-10-22T01:20:03.7681990Z'
$newStarted = '2026-10-23T07:30:42.1284490Z'

if ($Mode -eq 'StopOld' -and $Approval -cne 'STOP_UCIE_OLD_C40_ONCE') {
    throw 'UCIE_EXPLICIT_OLD_CLIENT_STOP_APPROVAL_REQUIRED'
}
$profile = Get-Item -LiteralPath $profilePath -ErrorAction Stop
if ($profile.PSIsContainer -or $profile.Length -gt 150000 -or
    ($profile.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'UCIE_C40_PROFILE_UNTRUSTED_STOP'
}
$profileText = [IO.File]::ReadAllText($profilePath)
$tunnelIds = @([regex]::Matches($profileText, 'tunnel_[0-9a-fA-F]{32}') |
    ForEach-Object { $_.Value.ToLowerInvariant() } | Select-Object -Unique)
$profileText = $null
if ($tunnelIds.Count -ne 1) { throw 'UCIE_C40_TUNNEL_ID_NOT_UNIQUE_STOP' }
$id = $tunnelIds[0]

function Get-UCIEClients {
    # Query UCIE_DATA-owned binaries only. Never return the raw command lines.
    return @(
        Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
        Where-Object { ([string]$_.ExecutablePath).StartsWith(
            $ucieRoot, [StringComparison]::OrdinalIgnoreCase) }
    )
}

function Confirm-ObservedClient($proc, $expectedPid, $expectedParent, $expectedStarted) {
    if ($null -eq $proc -or [int]$proc.ProcessId -ne $expectedPid -or
        [int]$proc.ParentProcessId -ne $expectedParent -or
        -not [string]::Equals([string]$proc.ExecutablePath, $clientExe,
            [StringComparison]::OrdinalIgnoreCase) -or
        $proc.CreationDate.ToUniversalTime().ToString('o') -cne $expectedStarted) {
        throw 'UCIE_CLIENT_IDENTITY_CHANGED_STOP'
    }
    $line = [string]$proc.CommandLine
    if (-not $line.Contains('--profile-file') -or
        -not $line.Contains('--control-plane.tunnel-id') -or
        $line.IndexOf('ucie-private-c40', [StringComparison]::OrdinalIgnoreCase) -lt 0 -or
        $line.IndexOf($id, [StringComparison]::OrdinalIgnoreCase) -lt 0) {
        throw 'UCIE_CLIENT_PROFILE_OR_TUNNEL_MISMATCH_STOP'
    }
}

$clients = @(Get-UCIEClients)
if ($clients.Count -ne 2) {
    throw 'UCIE_EXPECTED_EXACTLY_TWO_CLIENTS_NOT_OBSERVED_STOP'
}
$oldMatch = @($clients | Where-Object { [int]$_.ProcessId -eq $oldPid })
$newMatch = @($clients | Where-Object { [int]$_.ProcessId -eq $newPid })
if ($oldMatch.Count -ne 1 -or $newMatch.Count -ne 1) {
    throw 'UCIE_OBSERVED_PROCESS_SET_CHANGED_STOP'
}
Confirm-ObservedClient $oldMatch[0] $oldPid $oldParent $oldStarted
Confirm-ObservedClient $newMatch[0] $newPid $newParent $newStarted

if ($Mode -eq 'Inspect') {
    [pscustomobject]@{
        status = 'UCIE_DUPLICATE_OLD_CLIENT_EXACT_MATCH_READY'
        old_pid = $oldPid
        keep_new_pid = $newPid
        shared_tunnel_identity_confirmed = $true
        process_stopped = $false
        files_modified = $false
    } | ConvertTo-Json -Compress
    return
}

# Explicit one-time owner authorization + exact PID and start-time lease.
# Never touch the new instance or the child Python processes.
Stop-Process -Id $oldPid -ErrorAction Stop
Start-Sleep -Seconds 2

$remaining = @(Get-UCIEClients)
$oldStillAlive = @($remaining | Where-Object { [int]$_.ProcessId -eq $oldPid }).Count -gt 0
$newStillAlive = @($remaining | Where-Object {
    [int]$_.ProcessId -eq $newPid -and
    $_.CreationDate.ToUniversalTime().ToString('o') -ceq $newStarted
}).Count -eq 1

$status = 'UCIE_OLD_DUPLICATE_STOP_RESULT_NEEDS_ATTENTION'
if (-not $oldStillAlive -and $newStillAlive -and $remaining.Count -eq 1) {
    $status = 'UCIE_LOCAL_C40_DUPLICATE_RESOLVED_ONE_CLIENT_REMAINS'
}

[pscustomobject]@{
    status = $status
    stopped_old_pid = $oldPid
    retained_new_pid = $newPid
    old_still_running = $oldStillAlive
    new_still_running = $newStillAlive
    local_ucie_client_count_after = $remaining.Count
    command_lines_or_tunnel_ids_printed = $false
    child_python_processes_terminated_by_script = $false
    other_projects_touched = $false
    tasks_or_services_modified = $false
    files_modified = $false
    chatgpt_tool_stability_verified = $false
} | ConvertTo-Json -Compress
