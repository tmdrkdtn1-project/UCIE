# UCIE-only stdio tunnel instance diagnosis. READ ONLY.
# Never prints raw command lines, tunnel IDs, profiles, secrets, or
# information about processes outside the exact UCIE_DATA tree.
# Does not launch, terminate, or modify any process, service, task, or file.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'

$ucieRoot = 'D:\UCIE_DATA\'
$expectedClient = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$expectedPython = 'D:\UCIE_DATA\.venv_mcp\Scripts\python.exe'
$profile = 'D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml'

$expectedTunnelId = $null
$profileStatus = 'NOT_VERIFIED'
try {
    $profileFile = Get-Item -LiteralPath $profile -ErrorAction Stop
    if ($profileFile.PSIsContainer -or
        ($profileFile.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        $profileFile.Length -gt 150000) {
        throw 'UCIE_PROFILE_INVALID'
    }
    $rawProfile = [System.IO.File]::ReadAllText($profile)
    $ids = @([regex]::Matches($rawProfile, 'tunnel_[0-9a-fA-F]{32}') |
        ForEach-Object { $_.Value.ToLowerInvariant() } | Select-Object -Unique)
    $rawProfile = $null
    if ($ids.Count -ne 1) { throw 'UCIE_TUNNEL_ID_NOT_UNIQUE' }
    $expectedTunnelId = $ids[0]
    $profileStatus = 'ONE_ID_CONFIRMED'
}
catch {
    $profileStatus = 'NOT_VERIFIED'
}

$clients = @()
$clientScan = 'NOT_VERIFIED'
try {
    # The WQL filter avoids enumerating processes not owned by UCIE_DATA.
    $clients = @(
        Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
        Where-Object {
            ([string]$_.ExecutablePath).StartsWith(
                $ucieRoot, [StringComparison]::OrdinalIgnoreCase)
        } |
        ForEach-Object {
            $cmd = [string]$_.CommandLine
            [pscustomobject]@{
                pid = [int]$_.ProcessId
                parent_pid = [int]$_.ParentProcessId
                created_utc = ([datetime]$_.CreationDate).ToUniversalTime().ToString('o')
                pinned_executable = [string]::Equals(
                    [string]$_.ExecutablePath, $expectedClient,
                    [StringComparison]::OrdinalIgnoreCase)
                references_c40_profile = [bool]($cmd -match '(?i)ucie-private-c40')
                references_explicit_profile_file = $cmd.Contains('--profile-file')
                supplies_tunnel_id_flag = $cmd.Contains('--control-plane.tunnel-id')
                mentions_expected_tunnel_id = [bool](
                    $expectedTunnelId -and
                    $cmd.IndexOf($expectedTunnelId, [StringComparison]::OrdinalIgnoreCase) -ge 0)
            }
        }
    )
    $clientScan = 'COMPLETE'
}
catch {
    $clients = @()
    $clientScan = 'NOT_VERIFIED'
}

$servers = @()
$serverScan = 'NOT_VERIFIED'
try {
    $servers = @(
        Get-CimInstance Win32_Process -Filter "Name = 'python.exe' AND ExecutablePath LIKE '%UCIE_DATA%'" -ErrorAction Stop |
        Where-Object {
            [string]::Equals([string]$_.ExecutablePath, $expectedPython,
                [StringComparison]::OrdinalIgnoreCase) -and
            ([string]$_.CommandLine -match '(?i)mcp_stdio_server')
        } |
        ForEach-Object {
            [pscustomobject]@{
                pid = [int]$_.ProcessId
                parent_pid = [int]$_.ParentProcessId
                created_utc = ([datetime]$_.CreationDate).ToUniversalTime().ToString('o')
            }
        }
    )
    $serverScan = 'COMPLETE'
}
catch {
    $servers = @()
    $serverScan = 'NOT_VERIFIED'
}

$explicitMatches = @($clients | Where-Object {
    $_.supplies_tunnel_id_flag -and $_.mentions_expected_tunnel_id
}).Count
$status = 'UCIE_LOCAL_INSTANCE_COUNT_OBSERVED'
if ($clientScan -ne 'COMPLETE' -or $serverScan -ne 'COMPLETE' -or
    $profileStatus -ne 'ONE_ID_CONFIRMED') {
    $status = 'UCIE_INSTANCE_OBSERVATION_INCOMPLETE'
}

[pscustomobject]@{
    status = $status
    profile_status = $profileStatus
    tunnel_client_scan = $clientScan
    local_ucie_tunnel_client_count = $clients.Count
    local_explicit_expected_tunnel_id_count = $explicitMatches
    possible_local_duplicate = ($clients.Count -gt 1)
    explicit_same_id_duplicate = ($explicitMatches -gt 1)
    ucie_tunnel_clients = $clients
    mcp_python_scan = $serverScan
    local_ucie_mcp_python_count = $servers.Count
    mcp_python_children = $servers
    other_hosts_or_platform_instances_visible = $false
    command_lines_or_tunnel_ids_printed = $false
    processes_started_or_stopped = $false
    files_modified = $false
} | ConvertTo-Json -Depth 6 -Compress
