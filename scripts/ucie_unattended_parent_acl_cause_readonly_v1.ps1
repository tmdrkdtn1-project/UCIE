# UCIE-only parent ACL cause diagnostic. READ-ONLY; NO OWNER/SID/ACE dump.
# Only inspects the fixed existing D:\UCIE_DATA parent.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$parent = 'D:\UCIE_DATA'
$expectedTarget = 'D:\UCIE_DATA\ucie_unattended_state'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentSid = [string]$identity.User.Value
$wellKnown = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545')
$trusted = @($currentSid, 'S-1-5-18', 'S-1-5-32-544')
$writeMask = ([Security.AccessControl.FileSystemRights]::Write -bor
    [Security.AccessControl.FileSystemRights]::Delete -bor
    [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor
    [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
    [Security.AccessControl.FileSystemRights]::TakeOwnership)

$exists = Test-Path -LiteralPath $parent -PathType Container
$noLinks = $false
$aclRead = $false
$ownerCurrent = $false
$ownerAdmins = $false
$ownerSystem = $false
$ownerOther = $false
$aclInherited = $false
$wideWriter = $false
$foreignWriter = $false
$unresolvedAllow = $false
$wideWriterInherited = $false
$foreignWriterInherited = $false
$allowAceCount = 0

if ($exists) {
    $noLinks = $true
    $at = $parent
    while (-not [string]::IsNullOrWhiteSpace($at)) {
        $item = Get-Item -LiteralPath $at -Force
        if ([bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            $noLinks = $false
        }
        $next = Split-Path -Path $at -Parent
        if ([string]::IsNullOrWhiteSpace($next) -or $next -ceq $at) { break }
        $at = $next
    }
    try {
        $acl = Get-Acl -LiteralPath $parent
        $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        $ownerCurrent = $owner -eq $currentSid
        $ownerAdmins = $owner -eq 'S-1-5-32-544'
        $ownerSystem = $owner -eq 'S-1-5-18'
        $ownerOther = -not ($ownerCurrent -or $ownerAdmins -or $ownerSystem)
        $aclInherited = -not [bool]$acl.AreAccessRulesProtected
        foreach ($ace in $acl.Access) {
            if ($ace.AccessControlType -ne
                [Security.AccessControl.AccessControlType]::Allow) { continue }
            $allowAceCount += 1
            $sid = $null
            try {
                $sid = $ace.IdentityReference.Translate(
                    [Security.Principal.SecurityIdentifier]).Value
            } catch {
                $unresolvedAllow = $true
                continue
            }
            if (($ace.FileSystemRights -band $writeMask) -eq 0) { continue }
            if ($wellKnown -contains $sid) {
                $wideWriter = $true
                if ($ace.IsInherited) { $wideWriterInherited = $true }
            }
            if ($trusted -notcontains $sid) {
                $foreignWriter = $true
                if ($ace.IsInherited) { $foreignWriterInherited = $true }
            }
        }
        $aclRead = $true
    } catch {
        $aclRead = $false
    }
}

$targetExists = Test-Path -LiteralPath $expectedTarget
$ownerAllowed = $ownerCurrent -or $ownerAdmins -or $ownerSystem
$parentAllowed = ($exists -and $noLinks -and $aclRead -and $ownerAllowed -and
    -not $wideWriter -and -not $foreignWriter -and -not $unresolvedAllow)

[pscustomobject]@{
    schema = 'UCIE_OWNER_PARENT_ACL_CAUSE_READONLY_V1'
    project_id = 'UCIE'
    status = 'READONLY_PARENT_CAUSE_OBSERVED_NOT_INSTALL_APPROVAL'
    checked_parent = $parent
    proposed_target = $expectedTarget
    parent_exists = [bool]$exists
    parent_and_ancestors_unlinked = [bool]$noLinks
    acl_readable = [bool]$aclRead
    parent_owned_by_current_user = [bool]$ownerCurrent
    parent_owned_by_builtin_administrators = [bool]$ownerAdmins
    parent_owned_by_local_system = [bool]$ownerSystem
    parent_owned_by_other = [bool]$ownerOther
    parent_acl_inheritance_enabled = [bool]$aclInherited
    broad_account_mutating_allow_ace = [bool]$wideWriter
    foreign_account_mutating_allow_ace = [bool]$foreignWriter
    unresolved_allow_ace_identity = [bool]$unresolvedAllow
    broad_mutating_ace_inherited = [bool]$wideWriterInherited
    foreign_mutating_ace_inherited = [bool]$foreignWriterInherited
    allow_ace_count = [int]$allowAceCount
    existing_target_present = [bool]$targetExists
    guarded_parent_criteria_met = [bool]$parentAllowed
    host_security_attested = $false
    owner_install_approved = $false
    directory_created = $false
    existing_acl_changed = $false
    scheduled_task_changed = $false
    c40_restarted = $false
    github_push_performed = $false
    rule_promoted = $false
} | ConvertTo-Json -Depth 3 -Compress
