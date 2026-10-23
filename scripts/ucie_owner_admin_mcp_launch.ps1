# UCIE-only owner-controlled local MCP tools activation and existing tunnel launch.
# IMPORTANT: This does not bypass the existing require_runtime_approval gate.
# Does not change profile, tunnel ID, scheduled tasks, other projects, or files.
# Usage:
#   .\scripts\ucie_owner_admin_mcp_launch.ps1 -Mode Probe
#   .\scripts\ucie_owner_admin_mcp_launch.ps1 -Mode Launch -OwnerOnlyConfirmed
# Launch mode requires the user to have independently confirmed that the
# UCIE tunnel's ChatGPT app connection is restricted to the owner.
[CmdletBinding()]
param(
    [ValidateSet('Probe', 'Launch')]
    [string]$Mode = 'Probe',
    [switch]$OwnerOnlyConfirmed
)
$ErrorActionPreference = 'Stop'

$serverFile = 'D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py'
$expectedHash = '83b58b68ad0c15a32991e03e82b3c309a5e045da1d4c9a4c8ca3101d8b010d8e'
$profile = 'D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml'
$python = 'D:\UCIE_DATA\.venv_mcp\Scripts\python.exe'
$adminSource = 'D:\UCIE_PREVIEW\UCIE_ADMIN\src'
$librarySource = 'D:\UCIE_PREVIEW\UCIE\src'
$libraryApp = 'D:\UCIE_DATA\library_app'

if ($Mode -eq 'Launch' -and -not $OwnerOnlyConfirmed) {
    throw 'UCIE_OWNER_ONLY_AUDIENCE_NOT_ATTESTED: do not publish admin tools to readonly users'
}
foreach ($path in @($serverFile, $profile, $python, $adminSource, $librarySource, $libraryApp)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw 'UCIE_ONLY_ACTIVATION_INPUT_MISSING'
    }
}
if ((Get-FileHash -LiteralPath $serverFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw 'UCIE_SERVER_SHA_MISMATCH_STOP'
}
if ((Get-Item -LiteralPath $serverFile).LinkType) {
    throw 'UCIE_SERVER_SYMLINK_DENIED'
}
$profileText = [System.IO.File]::ReadAllText($profile)
if ($profileText.Length -gt 150000 -or -not $profileText.Contains('mcp_stdio_server')) {
    throw 'UCIE_PROFILE_LAYOUT_MISMATCH_STOP'
}
# Tunnel ID is taken ONLY from the already-verified UCIE C40 profile.
$ids = @([regex]::Matches($profileText, 'tunnel_[0-9a-fA-F]{32}') |
    ForEach-Object { $_.Value.ToLowerInvariant() } | Select-Object -Unique)
if ($ids.Count -ne 1) {
    throw 'UCIE_PROFILE_TUNNEL_ID_NOT_UNIQUE_STOP'
}
$tunnelId = $ids[0]
$profileText = $null

if ($Mode -eq 'Launch') {
    # Do not duplicate/restart an active UCIE tunnel. Only test UCIE profile matches.
    $active = @(
        Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%ucie-private-c40.yaml%'" |
        Where-Object { [string]$_.Name -match '(?i)(tunnel.client|tunnel-client)' }
    )
    if ($active.Count -gt 0) {
        throw 'UCIE_TUNNEL_ALREADY_RUNNING_DO_NOT_DUPLICATE'
    }
}

$client = $null
if ($Mode -eq 'Launch') {
    $client = Get-Command tunnel-client -CommandType Application -ErrorAction SilentlyContinue
    if ($null -eq $client) {
        throw 'UCIE_TUNNEL_CLIENT_BINARY_NOT_ON_PATH_STOP'
    }
}

# The owner enters the previously approved operator value locally. No value
# is printed, persisted, inferred from code, committed or sent to ChatGPT.
Write-Host 'Enter the existing UCIE MCP operator approval value, locally.'
$secret = Read-Host -AsSecureString 'UCIE owner approval'
if ($null -eq $secret -or $secret.Length -eq 0) {
    throw 'UCIE_OWNER_APPROVAL_NOT_PROVIDED'
}

$oldApproval = $env:UCIE_MCP_OWNER_APPROVAL
$oldTunnelId = $env:UCIE_MCP_TUNNEL_ID
$oldAdminGate = $env:UCIE_ADMIN_TOOLS_ENABLED
$oldPythonPath = $env:PYTHONPATH
$bstr = [IntPtr]::Zero

try {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    $env:UCIE_MCP_OWNER_APPROVAL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    $env:UCIE_MCP_TUNNEL_ID = $tunnelId
    $env:UCIE_ADMIN_TOOLS_ENABLED = '1'
    $env:PYTHONPATH = @($adminSource, $librarySource, $libraryApp) -join ';'

    # First prove actual existing gate and actual 9 tools in ONE ephemeral
    # child interpreter. The owner approval value never enters stdout.
    $probe = @'
import asyncio
import importlib
import inspect
import json
import sys

stage = "IMPORT_UCIE_MCP"
try:
    m = importlib.import_module("private_lib.mcp_stdio_server")
    stage = "EXISTING_OPERATOR_GATE_AND_MAKE_SERVER"
    server = m.make_server()
    stage = "LIST_UCIE_TOOLS"
    listing = server.list_tools()
    if inspect.isawaitable(listing):
        listing = asyncio.run(listing)
    names = sorted(t.name for t in listing)
    admin = [n for n in names if n.startswith("ucie_admin_")]
    if len(admin) != 9 or "search_ucie_evidence" not in names:
        print(json.dumps({
            "status":"UCIE_OWNER_LOCAL_ADMIN_REGISTRATION_INCOMPLETE",
            "stage":stage,"admin_count":len(admin),
            "legacy_search_preserved":"search_ucie_evidence" in names,
            "live_chatgpt_tools_verified":False
        }))
        sys.exit(3)
    print(json.dumps({
        "status":"UCIE_OWNER_LOCAL_ADMIN_9_REGISTERED",
        "admin_count":9,
        "admin_tool_names":admin,
        "legacy_search_preserved":True,
        "live_chatgpt_tools_verified":False
    }))
except Exception as exc:
    print(json.dumps({
        "status":"UCIE_OWNER_LOCAL_ADMIN_NOT_VERIFIED",
        "stage":stage,
        "exception_type":type(exc).__name__,
        "live_chatgpt_tools_verified":False
    }))
    sys.exit(2)
'@

    # Use a tempfile-free stdin process; no Python files or approval logs.
    $raw = $probe | & $python -B - 2>&1
    $exit = $LASTEXITCODE
    $lines = @($raw | ForEach-Object { [string]$_ })
    $resultLine = @($lines | Where-Object { $_.StartsWith('{') } | Select-Object -Last 1)
    if ($resultLine.Count -ne 1) {
        Write-Output '{"status":"UCIE_OWNER_LOCAL_PROBE_NO_RESULT","live_chatgpt_tools_verified":false}'
        throw 'UCIE_LOCAL_PROBE_FAILED_STOP'
    }
    # Output the bounded structured result ONLY, not runtime stderr.
    Write-Output $resultLine[0]
    if ($exit -ne 0) {
        throw 'UCIE_LOCAL_OPERATOR_GATE_OR_TOOL_REGISTRATION_FAILED_STOP'
    }

    if ($Mode -eq 'Launch') {
        Write-Output '{"status":"UCIE_OWNER_ONLY_TUNNEL_RUN_STARTED","live_chatgpt_tools_verified":false}'
        # Official Secure MCP Tunnel supported command. Blocks in this
        # console; operator must keep this process alive. No task/service
        # registration, new tunnel, or changes to its profile.
        & $client.Source run --profile $profile
        if ($LASTEXITCODE -ne 0) {
            throw 'UCIE_OWNER_TUNNEL_CLIENT_EXITED_WITH_ERROR'
        }
        Write-Output '{"status":"UCIE_OWNER_TUNNEL_RUN_EXITED","live_chatgpt_tools_verified":false}'
    }
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
    $secret.Dispose()
    $env:UCIE_MCP_OWNER_APPROVAL = $oldApproval
    $env:UCIE_MCP_TUNNEL_ID = $oldTunnelId
    $env:UCIE_ADMIN_TOOLS_ENABLED = $oldAdminGate
    $env:PYTHONPATH = $oldPythonPath
}
