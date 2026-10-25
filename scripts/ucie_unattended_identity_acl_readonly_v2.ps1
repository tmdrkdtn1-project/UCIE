# UCIE-only P4 identity and ACL diagnostics; no administrative changes.
# Reads two fixed UCIE directories and the single existing miner task.
# Emits BOOLEAN/STATE summaries only, no raw SID, username, ACL or token.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = 'D:\UCIE'
$existingBridge = 'D:\UCIE\.ucie_bridge_state'
$proposedOps = 'D:\UCIE_DATA\ucie_unattended_state'
$minerTask = 'UCIE-PublicMiner-Hourly'
$supervisorTask = 'UCIE-C40-Supervisor'

function Test-UcieUnlinkedDirectory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    $p = $Path
    while (-not [string]::IsNullOrWhiteSpace($p)) {
        $item = Get-Item -LiteralPath $p -Force
        if ([bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            return $false
        }
        $next = Split-Path -Path $p -Parent
        if ([string]::IsNullOrWhiteSpace($next) -or $next -ceq $p) { break }
        $p = $next
    }
    return $true
}

function Resolve-UcieAccountSid([string]$Account) {
    if ([string]::IsNullOrWhiteSpace($Account)) { return $null }
    try {
        if ($Account -match '^S-\d+-') {
            return ([Security.Principal.SecurityIdentifier]::new($Account)).Value
        }
        return ([Security.Principal.NTAccount]::new($Account)).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    } catch {
        return $null
    }
}

function Get-UcieAclSummary([string]$Path, [string]$CurrentSid) {
    $out = [ordered]@{
        exists_unlinked = $false
        acl_readable = $false
        owned_by_current_user = $false
        owner_is_builtin_administrators = $false
        owner_is_local_system = $false
        inheritance_disabled = $false
        broad_allow_write_ace_found = $false
        acl_requires_owner_review = $true
    }
    if (-not (Test-UcieUnlinkedDirectory $Path)) { return $out }
    $out.exists_unlinked = $true
    try {
        $acl = Get-Acl -LiteralPath $Path
        $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        $out.owned_by_current_user = [string]::Equals(
            $owner, $CurrentSid, [StringComparison]::OrdinalIgnoreCase)
        $out.owner_is_builtin_administrators = $owner -eq 'S-1-5-32-544'
        $out.owner_is_local_system = $owner -eq 'S-1-5-18'
        $out.inheritance_disabled = [bool]$acl.AreAccessRulesProtected
        $publicSids = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545')
        $danger = [System.Security.AccessControl.FileSystemRights]::Write -bor
            [System.Security.AccessControl.FileSystemRights]::Modify -bor
            [System.Security.AccessControl.FileSystemRights]::FullControl
        foreach ($ace in $acl.Access) {
            if ($ace.AccessControlType -ne
                [System.Security.AccessControl.AccessControlType]::Allow) {
                continue
            }
            $aceSid = Resolve-UcieAccountSid ([string]$ace.IdentityReference.Value)
            if ($publicSids -contains $aceSid -and ($ace.FileSystemRights -band $danger)) {
                $out.broad_allow_write_ace_found = $true
            }
        }
        $out.acl_readable = $true
        # Treat this as a negative screen only. Neither "no broad write"
        # nor nominal owner match is a signed host security attestation.
        $out.acl_requires_owner_review = (-not $out.owned_by_current_user -or
            -not $out.inheritance_disabled -or $out.broad_allow_write_ace_found)
    } catch {
        $out.acl_requires_owner_review = $true
    }
    return $out
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentSid = [string]$identity.User.Value
$task = Get-ScheduledTask -TaskPath '\' -TaskName $minerTask -ErrorAction SilentlyContinue
$taskPresent = $null -ne $task
$principalResolvable = $false
$principalMatchesCurrent = $false
$taskLogonType = 'UNKNOWN'
$taskRunLevel = 'UNKNOWN'
$taskState = 'NOT_FOUND'
if ($taskPresent) {
    $taskSid = Resolve-UcieAccountSid ([string]$task.Principal.UserId)
    $principalResolvable = -not [string]::IsNullOrWhiteSpace($taskSid)
    $principalMatchesCurrent = ($principalResolvable -and
        [string]::Equals($taskSid, $currentSid, [StringComparison]::OrdinalIgnoreCase))
    $taskLogonType = [string]$task.Principal.LogonType
    $taskRunLevel = [string]$task.Principal.RunLevel
    $taskState = [string]$task.State
}
$supervisorPresent = $null -ne (Get-ScheduledTask -TaskPath '\' -TaskName $supervisorTask -ErrorAction SilentlyContinue)

[pscustomobject]@{
    schema = 'UCIE_WINDOWS_IDENTITY_ACL_READONLY_DIAGNOSTIC_V2'
    project_id = 'UCIE'
    status = 'DIAGNOSTIC_OBSERVATION_ONLY_NOT_HOST_APPROVAL'
    root_exists_and_no_reparse_ancestors = (Test-UcieUnlinkedDirectory $root)
    miner_task_present = [bool]$taskPresent
    miner_task_account_sid_resolvable = [bool]$principalResolvable
    miner_task_sid_matches_current_user = [bool]$principalMatchesCurrent
    miner_task_logon_type = $taskLogonType
    miner_task_run_level = $taskRunLevel
    miner_task_state = $taskState
    supervisor_task_name_occupied = [bool]$supervisorPresent
    existing_bridge_directory = (Get-UcieAclSummary $existingBridge $currentSid)
    proposed_independent_operations_directory = (Get-UcieAclSummary $proposedOps $currentSid)
    private_owner_key_provisioned_or_read = $false
    windows_acl_modified = $false
    existing_bridge_files_modified = $false
    scheduled_task_modified = $false
    service_restarted = $false
    github_push_performed = $false
    production_rule_promoted = $false
    operator_install_authorized = $false
} | ConvertTo-Json -Depth 5 -Compress
