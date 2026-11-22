# UCIE P8: resolve *scope* of foreign LocalAppData ACEs, read-only.
# Reads only the ACL of the already-identified Windows KnownFolder parent.
# Does NOT enumerate files, descendants, private accounts, or unrelated paths.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'UCIE_P8_WINDOWS_REQUIRED'
}
$localParent = [Environment]::GetFolderPath(
    [Environment+SpecialFolder]::LocalApplicationData)
if ([string]::IsNullOrWhiteSpace($localParent) -or
    $localParent -notmatch '^[A-Za-z]:\\' -or
    -not [IO.Path]::IsPathRooted($localParent)) {
    throw 'UCIE_P8_LOCALAPPDATA_PATH_INVALID'
}
$child = Join-Path -Path $localParent -ChildPath 'UCIE_Unattended_State'
$ownerSid = [string][Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$trusted = @($ownerSid, 'S-1-5-18', 'S-1-5-32-544')
$wide = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545')
$exists = Test-Path -LiteralPath $localParent -PathType Container
$childExists = Test-Path -LiteralPath $child
$aclReadable = $false
$ownerMatches = $false
$unlinked = $false
$foreignCount = 0
$foreignInheritOnly = 0
$foreignEffective = 0
$foreignInherited = 0
$foreignChildInheritable = 0
$foreignEffectiveDeleteChild = $false
$foreignEffectiveDeleteParent = $false
$foreignEffectiveChangeDaclOrOwner = $false
$foreignEffectiveCreateChild = $false
$foreignEffectiveWriteData = $false
$foreignBroadEffective = $false
$unresolvedAllow = $false
$aclInheritance = $false

if ($exists) {
    $unlinked = $true
    $cursor = $localParent
    while (-not [string]::IsNullOrWhiteSpace($cursor)) {
        try {
            $node = Get-Item -LiteralPath $cursor -Force
            if ([bool]($node.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                $unlinked = $false
            }
        } catch {
            $unlinked = $false
        }
        $up = Split-Path -Path $cursor -Parent
        if ([string]::IsNullOrWhiteSpace($up) -or $up -ceq $cursor) { break }
        $cursor = $up
    }
    try {
        $acl = Get-Acl -LiteralPath $localParent
        $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        $ownerMatches = $owner -eq $ownerSid
        $aclInheritance = -not [bool]$acl.AreAccessRulesProtected
        $modifying = ([Security.AccessControl.FileSystemRights]::Write -bor
            [Security.AccessControl.FileSystemRights]::Delete -bor
            [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor
            [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
            [Security.AccessControl.FileSystemRights]::TakeOwnership)
        foreach ($ace in $acl.Access) {
            if ($ace.AccessControlType -ne
                [Security.AccessControl.AccessControlType]::Allow) { continue }
            try {
                $sid = $ace.IdentityReference.Translate(
                    [Security.Principal.SecurityIdentifier]).Value
            } catch {
                $unresolvedAllow = $true
                continue
            }
            if ($trusted -contains $sid) { continue }
            if (($ace.FileSystemRights -band $modifying) -eq 0) { continue }
            $foreignCount++
            if ($ace.IsInherited) { $foreignInherited++ }
            $inheritOnly = (
                (($ace.PropagationFlags -band
                    [Security.AccessControl.PropagationFlags]::InheritOnly) -ne 0) -and
                $ace.InheritanceFlags -ne [Security.AccessControl.InheritanceFlags]::None
            )
            if ($ace.InheritanceFlags -ne
                [Security.AccessControl.InheritanceFlags]::None) {
                $foreignChildInheritable++
            }
            if ($inheritOnly) {
                $foreignInheritOnly++
                continue
            }
            $foreignEffective++
            if ($wide -contains $sid) { $foreignBroadEffective = $true }
            if (($ace.FileSystemRights -band
                [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles) -ne 0) {
                $foreignEffectiveDeleteChild = $true
            }
            if (($ace.FileSystemRights -band
                [Security.AccessControl.FileSystemRights]::Delete) -ne 0) {
                $foreignEffectiveDeleteParent = $true
            }
            $aclMutation = ([Security.AccessControl.FileSystemRights]::ChangePermissions -bor
                [Security.AccessControl.FileSystemRights]::TakeOwnership)
            if (($ace.FileSystemRights -band $aclMutation) -ne 0) {
                $foreignEffectiveChangeDaclOrOwner = $true
            }
            if (($ace.FileSystemRights -band
                [Security.AccessControl.FileSystemRights]::CreateDirectories) -ne 0) {
                $foreignEffectiveCreateChild = $true
            }
            if (($ace.FileSystemRights -band
                [Security.AccessControl.FileSystemRights]::Write) -ne 0) {
                $foreignEffectiveWriteData = $true
            }
        }
        $aclReadable = $true
    } catch {
        $aclReadable = $false
    }
}
$observedOnlyInherit = $foreignCount -gt 0 -and $foreignEffective -eq 0 -and
    $foreignInheritOnly -eq $foreignCount
$status = 'UCIE_FOREIGN_ACE_APPLICABILITY_UNRESOLVED_NO_INSTALL'
if (-not $exists -or -not $aclReadable -or -not $unlinked -or
    -not $ownerMatches -or $childExists -or $unresolvedAllow) {
    $status = 'UCIE_OWNER_LOCALAPPDATA_SCOPE_PRECONDITION_NO_GO'
} elseif ($foreignEffectiveDeleteChild -or $foreignEffectiveDeleteParent -or
    $foreignEffectiveChangeDaclOrOwner -or $foreignBroadEffective) {
    $status = 'UCIE_FOREIGN_EFFECTIVE_DESTRUCTIVE_PARENT_RIGHTS_NO_GO'
} elseif ($observedOnlyInherit) {
    $status = 'UCIE_FOREIGN_ACE_INHERIT_ONLY_CHILD_DACL_REVIEW_REQUIRED'
} else {
    $status = 'UCIE_FOREIGN_NONDESTRUCTIVE_PARENT_RIGHTS_REVIEW_REQUIRED'
}

[pscustomobject]@{
    schema = 'UCIE_OWNER_LOCALAPPDATA_ACE_SCOPE_READONLY_V2'
    project_id = 'UCIE'
    status = $status
    target_identifier = 'CURRENT_OWNER_LOCALAPPDATA_UCIE_UNATTENDED_STATE'
    parent_exists = [bool]$exists
    parent_reparse_free = [bool]$unlinked
    parent_acl_readable = [bool]$aclReadable
    parent_owned_by_current_user = [bool]$ownerMatches
    parent_acl_inheritance_enabled = [bool]$aclInheritance
    foreign_mutating_allow_count = [int]$foreignCount
    foreign_mutating_inherit_only_count = [int]$foreignInheritOnly
    foreign_mutating_effective_on_parent_count = [int]$foreignEffective
    foreign_mutating_inherited_count = [int]$foreignInherited
    foreign_mutating_can_inherit_to_children_count = [int]$foreignChildInheritable
    foreign_effective_parent_delete_child = [bool]$foreignEffectiveDeleteChild
    foreign_effective_parent_delete = [bool]$foreignEffectiveDeleteParent
    foreign_effective_parent_change_dacl_or_owner = [bool]$foreignEffectiveChangeDaclOrOwner
    foreign_effective_parent_create_child = [bool]$foreignEffectiveCreateChild
    foreign_effective_parent_write = [bool]$foreignEffectiveWriteData
    foreign_broad_effective_modify = [bool]$foreignBroadEffective
    unresolved_allow_ace_identity = [bool]$unresolvedAllow
    target_already_exists = [bool]$childExists
    os_accesscheck_executed = $false
    security_grant_authorized = $false
    new_directory_created = $false
    existing_acl_changed = $false
    service_restarted = $false
    git_pushed = $false
    automatic_rule_promotion = $false
} | ConvertTo-Json -Depth 3 -Compress
