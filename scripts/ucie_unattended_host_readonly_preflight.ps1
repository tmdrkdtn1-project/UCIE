# UCIE-specific Windows unattended-host readiness inspection (READ ONLY).
# No service/task creation, restart, token access, file modification, process
# termination, private project enumeration, tunnel registration, or promotion.
# No conclusion here constitutes OS owner authorization or production GO.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repo = 'D:\UCIE'
$gitDir = Join-Path $repo '.git'
$miner = Join-Path $repo 'scripts\public_miner_cycle.py'
$python = Join-Path $repo '.venv\Scripts\python.exe'
$profile = 'D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml'
$client = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$taskName = 'UCIE-PublicMiner-Hourly'
$supervisorTask = 'UCIE-C40-Supervisor'
$expectedRemote = 'https://github.com/tmdrkdtn1-project/UCIE.git'

function Test-RegularNoLink([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return (-not [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint))
}
function Test-DirectoryNoLink([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return (-not [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint))
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principalSid = [string]$identity.User.Value
$rootValid = Test-DirectoryNoLink $repo
$gitPresent = $rootValid -and (Test-Path -LiteralPath $gitDir)
$workerPresent = Test-RegularNoLink $miner
$pythonPresent = Test-RegularNoLink $python
$profilePresent = Test-RegularNoLink $profile
$clientPresent = Test-RegularNoLink $client

$originMatches = $false
$clean = $false
if ($rootValid -and $gitPresent -and (Get-Command git -ErrorAction SilentlyContinue)) {
    $origin = @(git -C $repo config --get remote.origin.url 2>$null)
    $originExit = $LASTEXITCODE
    $originMatches = ($originExit -eq 0 -and $origin.Count -eq 1 -and
        ([string]$origin[0] -ceq $expectedRemote))
    $status = @(git -C $repo status --porcelain --untracked-files=no 2>$null)
    $statusExit = $LASTEXITCODE
    $clean = ($statusExit -eq 0 -and $status.Count -eq 0)
    $origin = $null
    $status = $null
}

$minerTaskPresent = $false
$minerTaskOwnerCurrent = $false
$minerTaskActionExact = $false
$minerState = 'NOT_FOUND'
$scheduled = Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -ne $scheduled) {
    $minerTaskPresent = $true
    $minerState = [string]$scheduled.State
    $minerTaskOwnerCurrent = ([string]$scheduled.Principal.UserId -ieq [string]$identity.Name -or
        [string]$scheduled.Principal.UserId -ieq $principalSid)
    if ($scheduled.Actions.Count -eq 1) {
        $exe = [string]$scheduled.Actions[0].Execute
        $arguments = [string]$scheduled.Actions[0].Arguments
        $minerTaskActionExact = ($exe -ieq $python -or
            $exe -ieq (Join-Path $repo '.venv\Scripts\pythonw.exe')) -and
            ($arguments.Trim('"') -ieq $miner)
    }
}
$supervisor = Get-ScheduledTask -TaskPath '\' -TaskName $supervisorTask -ErrorAction SilentlyContinue
$supervisorAlreadyExists = $null -ne $supervisor

$runtimeHash = $null
$profileHash = $null
if ($clientPresent) {
    $runtimeHash = (Get-FileHash -LiteralPath $client -Algorithm SHA256).Hash.ToLowerInvariant()
}
if ($profilePresent) {
    $profileHash = (Get-FileHash -LiteralPath $profile -Algorithm SHA256).Hash.ToLowerInvariant()
}


# Inspect only the dedicated UCIE journal directory. Owner name/SID, ACL
# entries and any unknown local identity are never emitted in the report.
# A protected ACL is a necessary observation, NOT owner authorization.
$journalDir = Join-Path $repo '.ucie_bridge_state'
$journalDirPresent = Test-DirectoryNoLink $journalDir
$journalOwnerCurrent = $false
$journalAclProtected = $false
$journalBroadWriteDenied = $false
if ($journalDirPresent) {
    try {
        $journalAcl = Get-Acl -LiteralPath $journalDir
        $journalOwnerSid = $journalAcl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
        $journalOwnerCurrent = $journalOwnerSid -eq $principalSid
        $journalAclProtected = [bool]$journalAcl.AreAccessRulesProtected
        $unsafeAce = $false
        $broadSids = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545')
        $rights = ([System.Security.AccessControl.FileSystemRights]::Write -bor
            [System.Security.AccessControl.FileSystemRights]::Modify -bor
            [System.Security.AccessControl.FileSystemRights]::FullControl)
        foreach ($ace in $journalAcl.Access) {
            if ($ace.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) {
                continue
            }
            $aceSid = $ace.IdentityReference.Translate(
                [System.Security.Principal.SecurityIdentifier]).Value
            if ($broadSids -contains $aceSid -and ($ace.FileSystemRights -band $rights)) {
                $unsafeAce = $true
            }
        }
        $journalBroadWriteDenied = -not $unsafeAce
    } catch {
        $journalOwnerCurrent = $false
        $journalAclProtected = $false
        $journalBroadWriteDenied = $false
    }
}

# These are bounded *observations*, not permission grants.
[pscustomobject]@{
    schema = 'UCIE_WINDOWS_HOST_READONLY_PREFLIGHT_V1'
    project_id = 'UCIE'
    status = 'READONLY_OBSERVATION_HOST_ACTIVATION_NOT_AUTHORIZED'
    current_user_sid_present = -not [string]::IsNullOrWhiteSpace($principalSid)
    root_exact_exists_and_not_linked = [bool]$rootValid
    git_checkout_exists = [bool]$gitPresent
    git_origin_exact_ucie_https = [bool]$originMatches
    git_tracked_worktree_clean = [bool]$clean
    public_miner_file_present = [bool]$workerPresent
    python_executable_present = [bool]$pythonPresent
    existing_hourly_miner_task_present = [bool]$minerTaskPresent
    existing_hourly_miner_principal_matches_current_user = [bool]$minerTaskOwnerCurrent
    existing_hourly_miner_action_matches = [bool]$minerTaskActionExact
    existing_hourly_miner_state = $minerState
    c40_profile_regular_file_present = [bool]$profilePresent
    c40_client_regular_file_present = [bool]$clientPresent
    c40_profile_sha256 = $profileHash
    c40_client_sha256 = $runtimeHash
    future_supervisor_task_name_is_already_occupied = [bool]$supervisorAlreadyExists
    ucie_journal_dir_regular_and_not_linked = [bool]$journalDirPresent
    ucie_journal_owner_sid_matches_current_user = [bool]$journalOwnerCurrent
    ucie_journal_acl_inheritance_disabled = [bool]$journalAclProtected
    ucie_journal_broad_write_ace_denied = [bool]$journalBroadWriteDenied
    owner_acl_independently_verified = $false
    monotonic_external_anchor_verified = $false
    short_lived_github_credential_verified = $false
    c40_live_functional_probe_verified = $false
    actual_host_service_installed = $false
    service_restarted = $false
    git_pushed = $false
    task_registered = $false
    automatic_rule_promotions = 0
} | ConvertTo-Json -Depth 4 -Compress
