# UCIE-only MCP activation diagnosis. No runtime or tunnel modifications.
# Use: & 'D:\UCIE_PREVIEW\UCIE_ADMIN\scripts\inspect_ucie_mcp_activation.ps1'
$ErrorActionPreference = 'Stop'

$server = 'D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py'
$profile = 'D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml'
$python = 'D:\UCIE_DATA\.venv_mcp\Scripts\python.exe'
$adminSource = 'D:\UCIE_PREVIEW\UCIE_ADMIN\src'
$librarySource = 'D:\UCIE_PREVIEW\UCIE\src'
$libraryApp = 'D:\UCIE_DATA\library_app'
$expectedHash = '83b58b68ad0c15a32991e03e82b3c309a5e045da1d4c9a4c8ca3101d8b010d8e'
$expectedTunnelId = [string]$env:UCIE_EXPECTED_TUNNEL_ID

if (-not (Test-Path -LiteralPath $server -PathType Leaf)) {
    throw 'UCIE local MCP server is missing; no operation performed'
}

$hash = (Get-FileHash -LiteralPath $server -Algorithm SHA256).Hash.ToLowerInvariant()
$profilePresent = Test-Path -LiteralPath $profile -PathType Leaf
$profileHasId = $false
$profileMatchesExpected = $null
$profileStdioHint = $false
$profilePythonHint = $false
if ($profilePresent) {
    $raw = [System.IO.File]::ReadAllText($profile)
    if ($raw.Length -gt 150000) {
        throw 'UCIE tunnel profile unexpectedly large; no operation performed'
    }
    $ids = @([regex]::Matches($raw, 'tunnel_[0-9a-fA-F]{32}') | ForEach-Object { $_.Value.ToLowerInvariant() } | Select-Object -Unique)
    $profileHasId = ($ids.Count -eq 1)
    if ($expectedTunnelId) {
        $profileMatchesExpected = ($ids -contains $expectedTunnelId.ToLowerInvariant())
    }
    $profileStdioHint = (
        $raw.Contains('mcp_stdio_server') -or
        $raw.Contains('private_lib.mcp_stdio_server')
    )
    $profilePythonHint = (
        $raw.Contains('python.exe') -or
        $raw.Contains('pythonw.exe')
    )
}

# Win32_Process WQL limits observation to processes whose command line
# explicitly contains UCIE. Never enumerate other project processes.
$ucieProcesses = @()
try {
    $ucieProcesses = @(
        Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%UCIE%'" |
        Where-Object {
            ([string]$_.Name -match '(tunnel|python|uv)') -and
            ([string]$_.CommandLine -match 'UCIE')
        } |
        ForEach-Object {
            [pscustomobject]@{
                pid = $_.ProcessId
                executable = $_.Name
                parent_pid = $_.ParentProcessId
                tunnel_run = (
                    [string]$_.CommandLine -match '(?i)(^|\s)run(\s|$)'
                )
                references_expected_profile = (
                    [string]$_.CommandLine -match
                    '(?i)ucie-private-c40(\.yaml)?'
                )
                references_mcp_server = (
                    [string]$_.CommandLine -match
                    '(?i)mcp_stdio_server'
                )
                has_profile_argument = (
                    [string]$_.CommandLine -match '(?i)--profile'
                )
            }
        }
    )
}
catch {
    $ucieProcesses = @()
}

$ucieTunnelTasks = @()
try {
    $ucieTunnelTasks = @(
        Get-ScheduledTask -TaskName '*UCIE*' -ErrorAction SilentlyContinue |
        Where-Object { $_.TaskName -match '(?i)(tunnel|mcp)' } |
        ForEach-Object {
            [pscustomobject]@{
                task_name = $_.TaskName
                state = [string]$_.State
                action_count = @($_.Actions).Count
                action_references_ucie = [bool](
                    @($_.Actions | Where-Object {
                        ([string]$_.Execute + ' ' + [string]$_.Arguments) -match 'UCIE'
                    }).Count
                )
            }
        }
    )
}
catch {
    $ucieTunnelTasks = @()
}

$oldGate = $env:UCIE_ADMIN_TOOLS_ENABLED
$oldPath = $env:PYTHONPATH
$localProbe = $null
try {
    $env:UCIE_ADMIN_TOOLS_ENABLED = '1'
    $env:PYTHONPATH = @(
        $adminSource
        $librarySource
        $libraryApp
    ) -join ';'
    # This is an isolated one-process tool name discovery. The program
    # never invokes a write tool, changes a file, or starts a tunnel.
    $source = @'
import asyncio
import importlib
import inspect
import json
import sys
import traceback
from pathlib import Path

stage = "IMPORT_PACKAGE"
try:
    module = importlib.import_module("private_lib.mcp_stdio_server")
    stage = "BUILD_EXISTING_UCIE_MCP"
    server = module.make_server()
    stage = "LIST_TOOLS"
    async def inspect_tools():
        tools = server.list_tools()
        return await tools if inspect.isawaitable(tools) else tools
    tools = asyncio.run(inspect_tools())
    names = sorted(t.name for t in tools)
    admin = [n for n in names if n.startswith("ucie_admin_")]
    result = {
        "status": "LOCAL_MCP_TOOL_REGISTRATION_OBSERVED",
        "admin_count": len(admin),
        "admin_tool_names": admin,
        "legacy_search_present": "search_ucie_evidence" in names,
        "live_chatgpt_registration_proven": False,
    }
except Exception as exc:
    frames = traceback.extract_tb(exc.__traceback__)
    result = {
        "status": "LOCAL_MCP_TOOL_REGISTRATION_NOT_PROVEN",
        "failed_stage": stage,
        "error_type": type(exc).__name__,
        "location": [
            {"file": Path(f.filename).name, "line": f.lineno}
            for f in frames[-3:]
        ],
        "live_chatgpt_registration_proven": False,
    }
print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
'@
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        $localProbe = [pscustomobject]@{
            status = 'UCIE_MCP_INTERPRETER_MISSING'
        }
    }
    else {
        $text = $source | & $python -B - 2>&1
        $exitCode = $LASTEXITCODE
        $jsonLine = @($text | ForEach-Object { [string]$_ } |
            Where-Object { $_.TrimStart().StartsWith('{') } |
            Select-Object -Last 1)
        if ($jsonLine.Count -gt 0) {
            try {
                $localProbe = $jsonLine[0] | ConvertFrom-Json
            }
            catch {
                $localProbe = [pscustomobject]@{
                    status = 'LOCAL_PROBE_INVALID_JSON'
                    exit_code = $exitCode
                }
            }
        }
        else {
            $localProbe = [pscustomobject]@{
                status = 'LOCAL_PROBE_NO_JSON'
                exit_code = $exitCode
            }
        }
    }
}
finally {
    $env:UCIE_ADMIN_TOOLS_ENABLED = $oldGate
    $env:PYTHONPATH = $oldPath
}

[pscustomobject]@{
    status = 'UCIE_MCP_ACTIVATION_CHECKPOINT_READ_ONLY'
    server_hash_matches_admin_patch = ($hash -eq $expectedHash)
    expected_ucie_profile_present = $profilePresent
    profile_contains_one_tunnel_id = $profileHasId
    profile_matches_locally_supplied_expected_id = $profileMatchesExpected
    profile_mentions_stdio_server = $profileStdioHint
    profile_mentions_python = $profilePythonHint
    ucie_candidate_processes = $ucieProcesses
    ucie_tunnel_scheduled_tasks = $ucieTunnelTasks
    locally_registered_tools = $localProbe
    operating_server_restarted = $false
    tunnel_modified = $false
    file_written = $false
} | ConvertTo-Json -Depth 7
