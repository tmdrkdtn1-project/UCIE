# UCIE-only owner-controlled local MCP tools activation and existing tunnel launch.
# IMPORTANT: This does not bypass the existing require_runtime_approval gate.
# Does not change profile, tunnel ID, scheduled tasks, other projects, or files.
# Usage:
#   .\scripts\ucie_owner_admin_mcp_launch.ps1 -Mode Probe
# Operator explicitly types APPROVE; this is a one-process consent action.
#   .\scripts\ucie_owner_admin_mcp_launch.ps1 -Mode Launch -OwnerOnlyConfirmed
#   .\scripts\ucie_owner_admin_mcp_launch.ps1 -Mode Background -OwnerOnlyConfirmed
# Background runs one independent hidden Windows child after operator approval.
# It persists after closing the launching console, not after Windows reboot.
# No scheduled task/service, new tunnel or global environment changes.
# Launch mode requires the user to have independently confirmed that the
# UCIE tunnel's ChatGPT app connection is restricted to the owner.
[CmdletBinding()]
param(
    [ValidateSet('Probe', 'Launch', 'Background')]
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
$clientExe = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$healthFile = 'D:\UCIE_DATA\mcp_tunnel_profiles\c40_health.url'
$expectedOwnerMarker = 'UCIE_PRIVATE_READONLY_APPROVED'
$libraryAdapter = Join-Path $librarySource 'ucie_miner\public_library_mcp_adapter.py'
$adminRegistration = Join-Path $adminSource 'ucie_admin\mcp_registration.py'

if ($Mode -in @('Launch', 'Background') -and -not $OwnerOnlyConfirmed) {
    throw 'UCIE_OWNER_ONLY_AUDIENCE_NOT_ATTESTED: do not publish admin tools to readonly users'
}
foreach ($path in @($serverFile, $profile, $python, $adminSource, $librarySource, $libraryApp)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw 'UCIE_ONLY_ACTIVATION_INPUT_MISSING'
    }
}
# Both overlapping UCIE Python worktrees have a ucie_miner package.
# Verify PR77's indexed Library adapter and PR78 admin registration coexist.
foreach ($path in @($libraryAdapter, $adminRegistration)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
        ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'UCIE_MCP_REQUIRED_PACKAGE_SOURCE_MISSING_OR_LINKED'
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

if ($Mode -in @('Launch', 'Background')) {
    # The previous UCIE client may run without a C40 filename argument.
    # Inspect only UCIE tunnel-client processes; do not scan unrelated projects.
    $active = @(
        Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe'" |
        Where-Object { ([string]$_.CommandLine).Contains('UCIE') }
    )
    if ($active.Count -gt 0) {
        throw 'UCIE_TUNNEL_ALREADY_RUNNING_DO_NOT_DUPLICATE'
    }
}

if ($Mode -in @('Launch', 'Background')) {
    if (-not (Test-Path -LiteralPath $clientExe -PathType Leaf)) {
        throw 'UCIE_C40_PINNED_TUNNEL_CLIENT_MISSING_STOP'
    }
    if (-not (Test-Path -LiteralPath (Split-Path -Parent $healthFile) -PathType Container)) {
        throw 'UCIE_C40_HEALTH_FILE_PARENT_MISSING_STOP'
    }
}

# Previous operator-approved 2026-10-22 session contract:
# Owner types APPROVE; the already-existing UCIE readonly marker is applied
# only to the current process and its children. This is NOT a reusable token.
# The marker by itself MUST NOT authorize admin access to shared clients.
$ownerDecision = Read-Host 'UCIE one-session authorization: type APPROVE'
if ($ownerDecision -cne 'APPROVE') {
    throw 'UCIE_OWNER_EXPLICIT_APPROVAL_REQUIRED'
}

$oldApproval = $env:UCIE_MCP_OWNER_APPROVAL
$oldTunnelId = $env:UCIE_MCP_TUNNEL_ID
$oldAdminGate = $env:UCIE_ADMIN_TOOLS_ENABLED
$oldPythonPath = $env:PYTHONPATH

try {
    $env:UCIE_MCP_OWNER_APPROVAL = $expectedOwnerMarker
    $env:UCIE_MCP_TUNNEL_ID = $tunnelId
    $env:UCIE_ADMIN_TOOLS_ENABLED = '1'
    # PR77 Library source MUST precede PR78's older ucie_miner package.
    # PR78-only ucie_admin is still resolved from its own distinct package.
    $env:PYTHONPATH = @($librarySource, $adminSource, $libraryApp) -join ';'

    # First prove actual existing gate and actual 9 tools in ONE ephemeral
    # child interpreter. The owner approval value never enters stdout.
    $probe = @'
import asyncio
import importlib
import inspect
import json
import sys
from pathlib import Path

stage = "IMPORT_UCIE_MCP"
try:
    # Fail closed on UCIE package shadowing before make_server() inserts
    # the admin worktree at sys.path[0]. Cache PR77's verified package first.
    stage = "VERIFY_LIBRARY_ADAPTER_ORIGIN"
    adapter = importlib.import_module("ucie_miner.public_library_mcp_adapter")
    expected_adapter = (Path(r"D:\UCIE_PREVIEW\UCIE\src")
                        / "ucie_miner" / "public_library_mcp_adapter.py").resolve()
    if Path(adapter.__file__).resolve() != expected_adapter:
        raise ImportError("UCIE_LIBRARY_ADAPTER_SHADOWED")
    stage = "IMPORT_UCIE_MCP"
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
    # Listing a tool is not evidence that its handler can execute.
    # Actual legacy public-only lookup runs with the same process env and
    # working directory as the impending foreground C40 tunnel launcher.
    stage = "CALL_EXISTING_PUBLIC_SEARCH"
    search_result = server.call_tool("search_ucie_evidence", {"query":"python","top":1})
    if inspect.isawaitable(search_result):
        search_result = asyncio.run(search_result)
    def legacy_ok(value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return False
        if isinstance(value, dict):
            return value.get("status") == "UCIE_PUBLIC_METADATA_EVIDENCE_REVIEW_ONLY"
        if isinstance(value, (list, tuple)):
            return any(legacy_ok(item) for item in value)
        if getattr(value, "isError", False):
            return False
        if hasattr(value, "text"):
            return legacy_ok(value.text)
        if hasattr(value, "content"):
            return legacy_ok(value.content)
        return False
    if not legacy_ok(search_result):
        raise ValueError("UCIE_LEGACY_PUBLIC_SEARCH_CONTRACT_NOT_MET")
    print(json.dumps({
        "status":"UCIE_OWNER_LOCAL_ADMIN_AND_LEGACY_SEARCH_VERIFIED",
        "admin_count":9,
        "admin_tool_names":admin,
        "legacy_search_preserved":True,
        "legacy_search_call_verified":True,
        "library_adapter_origin_verified":True,
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
    $raw = $probe | & $python -B - 2>$null
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


    if ($Mode -eq 'Background') {
        # One-session approval and actual local MCP search have passed.
        # The hidden independent child inherits process-only authorization.
        $activeBeforeStart = @(
            Get-CimInstance Win32_Process -Filter "Name = 'tunnel-client.exe'" |
            Where-Object { ([string]$_.CommandLine).Contains('UCIE') }
        )
        if ($activeBeforeStart.Count -ne 0) {
            throw 'UCIE_TUNNEL_ALREADY_RUNNING_DO_NOT_DUPLICATE'
        }
        $args = @(
            'run', '--profile-file', ('"' + $profile + '"'),
            '--control-plane.tunnel-id', $tunnelId,
            '--health.url-file', ('"' + $healthFile + '"')
        )
        $child = Start-Process -FilePath $clientExe -ArgumentList $args `
            -WorkingDirectory $libraryApp -WindowStyle Hidden -PassThru -ErrorAction Stop
        if ($null -eq $child -or $child.Id -le 0) {
            throw 'UCIE_BACKGROUND_START_RETURNED_NO_PID'
        }
        Start-Sleep -Seconds 2
        $observed = Get-CimInstance Win32_Process -Filter "ProcessId = $($child.Id)" -ErrorAction Stop
        if ($null -eq $observed -or
            -not [string]::Equals([string]$observed.ExecutablePath, $clientExe,
                [StringComparison]::OrdinalIgnoreCase) -or
            ([string]$observed.CommandLine).IndexOf(
                'ucie-private-c40', [StringComparison]::OrdinalIgnoreCase) -lt 0) {
            throw 'UCIE_BACKGROUND_TUNNEL_NOT_RUNNING_AS_EXPECTED'
        }
        [pscustomobject]@{
            status = 'UCIE_OWNER_BACKGROUND_TUNNEL_PROCESS_OBSERVED'
            pid = [int]$child.Id
            window = 'HIDDEN'
            startup_task_registered = $false
            closes_with_launching_console = $false
            survives_windows_logoff_or_reboot = $false
            tool_calls_verified_in_chatgpt = $false
        } | ConvertTo-Json -Compress
    }
    if ($Mode -eq 'Launch') {
        Write-Output '{"status":"UCIE_OWNER_ONLY_TUNNEL_RUN_STARTED","live_chatgpt_tools_verified":false}'
        # Official Secure MCP Tunnel supported command. Blocks in this
        # console; operator must keep this process alive. No task/service
        # registration, new tunnel, or changes to its profile.
        & $clientExe run --profile-file $profile --control-plane.tunnel-id $tunnelId --health.url-file $healthFile
        if ($LASTEXITCODE -ne 0) {
            throw 'UCIE_OWNER_TUNNEL_CLIENT_EXITED_WITH_ERROR'
        }
        Write-Output '{"status":"UCIE_OWNER_TUNNEL_RUN_EXITED","live_chatgpt_tools_verified":false}'
    }
}
finally {
    $ownerDecision = $null
    $env:UCIE_MCP_OWNER_APPROVAL = $oldApproval
    $env:UCIE_MCP_TUNNEL_ID = $oldTunnelId
    $env:UCIE_ADMIN_TOOLS_ENABLED = $oldAdminGate
    $env:PYTHONPATH = $oldPythonPath
}
