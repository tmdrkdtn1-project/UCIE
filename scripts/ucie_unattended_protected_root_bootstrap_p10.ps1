# UCIE P10 one-directory protected host-root bootstrap (owner approval REQUIRED).
# DEFAULT: READ-ONLY INSPECT. -Apply touches ONLY ONE NEW UCIE directory.
# No existing UCIE bridge, miner, C40, task, Git, credential, rules, or
# private project / user profile content may be accessed or modified.
[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$Approval = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$approvalPhrase = 'APPROVE_UCIE_PROGRAMFILES_ROOT_ONE_DIRECTORY_ONLY'
$leafName = 'UCIE_UnattendedHost'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'UCIE_P10_WINDOWS_REQUIRED'
}
if ($Apply -and $Approval -cne $approvalPhrase) {
    throw 'UCIE_P10_EXACT_OWNER_APPROVAL_REQUIRED'
}
if (-not $Apply -and -not [string]::IsNullOrWhiteSpace($Approval)) {
    throw 'UCIE_P10_APPROVAL_WITHOUT_APPLY_REFUSED'
}
$parent = [Environment]::GetFolderPath([Environment+SpecialFolder]::ProgramFiles)
if ([string]::IsNullOrWhiteSpace($parent) -or
    -not [IO.Path]::IsPathRooted($parent) -or
    $parent -notmatch '^[A-Za-z]:\\') {
    throw 'UCIE_P10_PROGRAMFILES_PATH_NOT_TRUSTED'
}
$target = Join-Path -Path $parent -ChildPath $leafName
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$adminRole = [Security.Principal.WindowsBuiltInRole]::Administrator
$adminToken = ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole($adminRole)
$adminSid = 'S-1-5-32-544'
$systemSid = 'S-1-5-18'
$trustedInstallerSid = 'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464'
$allowedOwnerSids = @($adminSid, $systemSid, $trustedInstallerSid)
$trustedWriters = @($adminSid, $systemSid, $trustedInstallerSid)
$mutatingMask = ([Security.AccessControl.FileSystemRights]::Write -bor
    [Security.AccessControl.FileSystemRights]::Delete -bor
    [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor
    [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
    [Security.AccessControl.FileSystemRights]::TakeOwnership)

function Test-UcieNoReparseAncestors([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    $cursor = $Path
    while (-not [string]::IsNullOrWhiteSpace($cursor)) {
        try {
            $item = Get-Item -LiteralPath $cursor -Force
            if ([bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                return $false
            }
        } catch { return $false }
        $up = Split-Path -Path $cursor -Parent
        if ([string]::IsNullOrWhiteSpace($up) -or $up -ceq $cursor) { break }
        $cursor = $up
    }
    return $true
}

function Test-UcieExactNewDacl([string]$Path) {
    if (-not (Test-UcieNoReparseAncestors $Path)) { return $false }
    try {
        $acl = Get-Acl -LiteralPath $Path
        $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        if ($owner -cne $adminSid -or -not [bool]$acl.AreAccessRulesProtected) {
            return $false
        }
        $aces = @($acl.Access)
        if ($aces.Count -ne 2) { return $false }
        $seen = @{}
        foreach ($ace in $aces) {
            $sid = $ace.IdentityReference.Translate(
                [Security.Principal.SecurityIdentifier]).Value
            if ($sid -notin @($adminSid, $systemSid) -or
                $ace.AccessControlType -ne
                [Security.AccessControl.AccessControlType]::Allow -or
                $ace.IsInherited -or $seen.ContainsKey($sid) -or
                (($ace.FileSystemRights -band
                  [Security.AccessControl.FileSystemRights]::FullControl) -ne
                  [Security.AccessControl.FileSystemRights]::FullControl)) {
                return $false
            }
            $seen[$sid] = $true
        }
        return ($seen.ContainsKey($adminSid) -and $seen.ContainsKey($systemSid))
    } catch { return $false }
}

$parentUnlinked = Test-UcieNoReparseAncestors $parent
$parentAclReadable = $false
$parentOwnerTrusted = $false
$foreignWriterPresent = $true
$unknownAllowSidPresent = $true
$parentDaclCanonical = $false
if ($parentUnlinked) {
    try {
        $acl = Get-Acl -LiteralPath $parent
        $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        $parentOwnerTrusted = $allowedOwnerSids -contains $owner
        $parentDaclCanonical = [bool]$acl.AreAccessRulesCanonical
        $foreignWriterPresent = $false
        $unknownAllowSidPresent = $false
        foreach ($ace in $acl.Access) {
            if ($ace.AccessControlType -ne
                [Security.AccessControl.AccessControlType]::Allow) { continue }
            $sid = $null
            try {
                $sid = $ace.IdentityReference.Translate(
                    [Security.Principal.SecurityIdentifier]).Value
            } catch {
                $unknownAllowSidPresent = $true
                continue
            }
            if (($ace.FileSystemRights -band $mutatingMask) -ne 0 -and
                $trustedWriters -notcontains $sid) {
                $foreignWriterPresent = $true
            }
        }
        $parentAclReadable = $true
    } catch {
        $parentAclReadable = $false
    }
}
$targetExists = Test-Path -LiteralPath $target
$parentGate = $parentUnlinked -and $parentAclReadable -and
    $parentOwnerTrusted -and $parentDaclCanonical -and
    -not $foreignWriterPresent -and -not $unknownAllowSidPresent
$created = $false
$newAclVerified = $false
$status = 'UCIE_P10_PARENT_OR_ACL_REVIEW_NO_GO'
if ($parentGate -and $targetExists) {
    $status = 'UCIE_P10_TARGET_ALREADY_EXISTS_NO_OVERWRITE'
} elseif ($parentGate -and -not $Apply) {
    $status = 'UCIE_P10_PARENT_OBSERVED_CANDIDATE_OWNER_APPROVAL_PENDING'
} elseif ($parentGate -and $Apply -and -not $adminToken) {
    $status = 'UCIE_P10_ELEVATED_OWNER_ADMIN_TOKEN_REQUIRED_NO_INSTALL'
} elseif ($parentGate -and $Apply) {
    # Caller must have *fresh* scoped owner approval in addition to being
    # in the elevated Administrators token; this creates no service.
    # Fail closed on a detected race. An already existing target is NEVER fixed.
    if (Test-Path -LiteralPath $target) {
        throw 'UCIE_P10_TARGET_RACE_OR_PREEXISTING_NO_GO'
    }
    $security = [Security.AccessControl.DirectorySecurity]::new()
    $adminIdentity = [Security.Principal.SecurityIdentifier]::new($adminSid)
    $systemIdentity = [Security.Principal.SecurityIdentifier]::new($systemSid)
    $security.SetOwner($adminIdentity)
    $security.SetAccessRuleProtection($true, $false)
    $inheritance = ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [Security.AccessControl.InheritanceFlags]::ObjectInherit)
    foreach ($sid in @($adminIdentity, $systemIdentity)) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            $sid, [Security.AccessControl.FileSystemRights]::FullControl,
            $inheritance, [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow)
        $security.AddAccessRule($rule)
    }
    if ($PSVersionTable.PSVersion.Major -lt 6) {
        $null = [IO.Directory]::CreateDirectory($target, $security)
    } else {
        $null = [IO.FileSystemAclExtensions]::CreateDirectory($security, $target)
    }
    $created = $true
    $newAclVerified = Test-UcieExactNewDacl $target
    if ($newAclVerified) {
        $status = 'UCIE_P10_ONE_PROTECTED_DIRECTORY_CREATED_ACL_RECHECK_ONLY'
    } else {
        $status = 'UCIE_P10_CREATED_BUT_ACL_FAILED_MANUAL_HOLD'
    }
}
# Do not print raw usernames, SIDs, or personally identifying local paths.
[pscustomobject]@{
    schema = 'UCIE_ONE_OWNER_PROTECTED_ROOT_BOOTSTRAP_P10_V1'
    project_id = 'UCIE'
    status = $status
    target_identifier = 'WINDOWS_PROGRAMFILES_UCIE_UNATTENDEDHOST_ONE_ROOT'
    parent_exists_unlinked = [bool]$parentUnlinked
    parent_acl_readable = [bool]$parentAclReadable
    parent_owner_well_known_system_or_administrators = [bool]$parentOwnerTrusted
    parent_dacl_canonical = [bool]$parentDaclCanonical
    parent_foreign_mutating_allow_ace_present = [bool]$foreignWriterPresent
    parent_unresolved_allow_identity = [bool]$unknownAllowSidPresent
    protected_parent_preflight_passed = [bool]$parentGate
    caller_elevated_administrator = [bool]$adminToken
    target_preexisted = [bool]$targetExists
    target_created_this_invocation = [bool]$created
    target_exact_admin_and_system_acl_verified = [bool]$newAclVerified
    existing_ucie_bridge_modified = $false
    existing_ucie_miner_modified = $false
    scheduled_task_registered = $false
    c40_process_restarted = $false
    github_credential_read = $false
    git_pushed = $false
    owner_host_signer_provisioned = $false
    external_antireplay_anchor_provisioned = $false
    service_writer_identity_provisioned = $false
    rule_auto_promotion_enabled = $false
    unattended_worker_activated = $false
} | ConvertTo-Json -Depth 4 -Compress
if ($Apply -and -not ($created -and $newAclVerified)) {
    throw 'UCIE_P10_PROTECTED_HOST_ROOT_NOT_ACCEPTED_NO_GO'
}
