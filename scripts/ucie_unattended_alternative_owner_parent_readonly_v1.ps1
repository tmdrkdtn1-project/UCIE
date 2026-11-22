# UCIE P7 Windows owner-local alternative journal parent READ-ONLY probe.
# Reads only the LocalAppData DIRECTORY ACL and each ancestor's reparse flag.
# Never lists user files/children, outputs account names, SID, full home path,
# ACL rows, tokens, or any unrelated project metadata.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'UCIE_ALTERNATIVE_PARENT_WINDOWS_REQUIRED'
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$ownerSid = [string]$identity.User.Value
$localParent = [Environment]::GetFolderPath(
    [Environment+SpecialFolder]::LocalApplicationData)
if ([string]::IsNullOrWhiteSpace($localParent) -or
    $localParent -notmatch '^[A-Za-z]:\\' -or
    -not [IO.Path]::IsPathRooted($localParent)) {
    throw 'UCIE_OWNER_LOCALAPPDATA_NOT_TRUSTED'
}
$leafName = 'UCIE_Unattended_State'
$target = Join-Path -Path $localParent -ChildPath $leafName
$parentExists = Test-Path -LiteralPath $localParent -PathType Container
$ancestorsUnlinked = $false
$parentAclReadable = $false
$ownerCurrent = $false
$ownerAdmins = $false
$ownerSystem = $false
$ownerOther = $false
$parentAclInheritance = $false
$foreignMutatingAllow = $false
$broadMutatingAllow = $false
$unresolvedAllowIdentity = $false
$foreignDeleteChild = $false
$allowAceCount = 0
$candidateExists = Test-Path -LiteralPath $target

if ($parentExists) {
    $ancestorsUnlinked = $true
    $cursor = $localParent
    while (-not [string]::IsNullOrWhiteSpace($cursor)) {
        try {
            $node = Get-Item -LiteralPath $cursor -Force
            if ([bool]($node.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                $ancestorsUnlinked = $false
            }
        } catch {
            $ancestorsUnlinked = $false
        }
        $upper = Split-Path -Path $cursor -Parent
        if ([string]::IsNullOrWhiteSpace($upper) -or $upper -ceq $cursor) {
            break
        }
        $cursor = $upper
    }
    try {
        $acl = Get-Acl -LiteralPath $localParent
        $aclOwner = $acl.GetOwner(
            [Security.Principal.SecurityIdentifier]).Value
        $ownerCurrent = $aclOwner -eq $ownerSid
        $ownerAdmins = $aclOwner -eq 'S-1-5-32-544'
        $ownerSystem = $aclOwner -eq 'S-1-5-18'
        $ownerOther = -not ($ownerCurrent -or $ownerAdmins -or $ownerSystem)
        $parentAclInheritance = -not [bool]$acl.AreAccessRulesProtected
        $wideSids = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545')
        $trustedSids = @($ownerSid, 'S-1-5-18', 'S-1-5-32-544')
        $modifyMask = ([Security.AccessControl.FileSystemRights]::Write -bor
            [Security.AccessControl.FileSystemRights]::Delete -bor
            [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor
            [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
            [Security.AccessControl.FileSystemRights]::TakeOwnership)
        foreach ($ace in $acl.Access) {
            if ($ace.AccessControlType -ne
                [Security.AccessControl.AccessControlType]::Allow) {
                continue
            }
            $allowAceCount += 1
            try {
                $sid = $ace.IdentityReference.Translate(
                    [Security.Principal.SecurityIdentifier]).Value
            } catch {
                $unresolvedAllowIdentity = $true
                continue
            }
            if (($ace.FileSystemRights -band $modifyMask) -eq 0) {
                continue
            }
            if ($wideSids -contains $sid) {
                $broadMutatingAllow = $true
            }
            if ($trustedSids -notcontains $sid) {
                $foreignMutatingAllow = $true
                if (($ace.FileSystemRights -band
                    [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles) -ne 0) {
                    $foreignDeleteChild = $true
                }
            }
        }
        $parentAclReadable = $true
    } catch {
        $parentAclReadable = $false
    }
}

$parentCandidateSafe = (
    $parentExists -and $ancestorsUnlinked -and $parentAclReadable -and
    $ownerCurrent -and -not $ownerOther -and
    -not $foreignMutatingAllow -and -not $broadMutatingAllow -and
    -not $unresolvedAllowIdentity -and -not $candidateExists
)
$status = 'UCIE_LOCALAPPDATA_PARENT_UNTRUSTED_NO_INSTALL'
if ($parentCandidateSafe) {
    $status = 'UCIE_LOCALAPPDATA_PARENT_CANDIDATE_REVIEW_ONLY'
}

[pscustomobject]@{
    schema = 'UCIE_OWNER_ALTERNATIVE_JOURNAL_PARENT_READONLY_V1'
    project_id = 'UCIE'
    status = $status
    candidate_identifier = 'CURRENT_OWNER_LOCALAPPDATA_UCIE_UNATTENDED_STATE'
    parent_directory_exists = [bool]$parentExists
    parent_and_ancestors_unlinked = [bool]$ancestorsUnlinked
    parent_acl_readable = [bool]$parentAclReadable
    parent_owned_by_current_user = [bool]$ownerCurrent
    parent_owned_by_administrators = [bool]$ownerAdmins
    parent_owned_by_system = [bool]$ownerSystem
    parent_owned_by_other = [bool]$ownerOther
    parent_acl_inheritance_enabled = [bool]$parentAclInheritance
    parent_broad_modifying_allow_ace = [bool]$broadMutatingAllow
    parent_foreign_modifying_allow_ace = [bool]$foreignMutatingAllow
    parent_foreign_delete_child_allow_ace = [bool]$foreignDeleteChild
    parent_unresolved_allow_ace_identity = [bool]$unresolvedAllowIdentity
    parent_allow_ace_count = [int]$allowAceCount
    candidate_already_exists = [bool]$candidateExists
    candidate_parent_meets_conservative_screen = [bool]$parentCandidateSafe
    candidate_host_independently_attested = $false
    candidate_install_approved = $false
    new_directory_created = $false
    existing_acl_changed = $false
    c40_process_restarted = $false
    scheduled_task_modified = $false
    github_token_read = $false
    git_pushed = $false
    rule_auto_promoted = $false
    new_autonomous_service_installed = $false
} | ConvertTo-Json -Depth 3 -Compress
