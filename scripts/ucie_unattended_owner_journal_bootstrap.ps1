# UCIE-only unattended operation journal: owner-approved *one new directory*.
# Default is READ ONLY. -Apply demands one exact explicit approval.
# No modification to D:\UCIE\.ucie_bridge_state, scheduler, process, Git,
# credentials, external rollback anchor, owner keys or rule promotion.
[CmdletBinding()]
param(
    [switch]$Apply,
    [string]$Approval = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$parent = 'D:\UCIE_DATA'
$target = 'D:\UCIE_DATA\ucie_unattended_state'
$approvalPhrase = 'APPROVE_UCIE_NEW_OPERATIONS_DIRECTORY_ONLY'
$noExecution = 'UCIE_OWNER_OPERATIONS_DIRECTORY_INSPECTION_ONLY'
$platform = [Environment]::OSVersion.Platform
if ($platform -ne [PlatformID]::Win32NT) {
    throw 'UCIE_BOOTSTRAP_WINDOWS_NT_REQUIRED'
}
if ($Apply -and $Approval -cne $approvalPhrase) {
    throw 'UCIE_BOOTSTRAP_EXPLICIT_SCOPED_APPROVAL_REQUIRED'
}
if (-not $Apply -and -not [string]::IsNullOrEmpty($Approval)) {
    throw 'UCIE_BOOTSTRAP_APPROVAL_WITHOUT_APPLY_DENIED'
}
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    throw 'UCIE_BOOTSTRAP_PREEXISTING_PARENT_MISSING'
}

function Test-UcieUnlinkedPath([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    $at = $Path
    while (-not [string]::IsNullOrWhiteSpace($at)) {
        $item = Get-Item -LiteralPath $at -Force
        if ([bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            return $false
        }
        $up = Split-Path -Path $at -Parent
        if ([string]::IsNullOrWhiteSpace($up) -or $up -ceq $at) { break }
        $at = $up
    }
    return $true
}

function Get-UcieAclRisk([string]$Path, [string]$CurrentSid) {
    $result = [ordered]@{
        acl_readable = $false
        owner_is_current_or_builtin_system_administrators = $false
        broad_write_allow_detected = $true
    }
    try {
        $acl = Get-Acl -LiteralPath $Path
        $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        $result.owner_is_current_or_builtin_system_administrators = (
            $owner -eq $CurrentSid -or
            $owner -eq 'S-1-5-18' -or $owner -eq 'S-1-5-32-544')
        $broad = @('S-1-1-0', 'S-1-5-11', 'S-1-5-32-545')
        $allowWrite = ([Security.AccessControl.FileSystemRights]::Write -bor
            [Security.AccessControl.FileSystemRights]::Modify -bor
            [Security.AccessControl.FileSystemRights]::FullControl)
        $unsafe = $false
        foreach ($ace in $acl.Access) {
            if ($ace.AccessControlType -ne
                [Security.AccessControl.AccessControlType]::Allow) {
                continue
            }
            $aceSid = $null
            try {
                $aceSid = $ace.IdentityReference.Translate(
                    [Security.Principal.SecurityIdentifier]).Value
            } catch {
                $unsafe = $true
                continue
            }
            # Any writable ACE outside current owner/SYSTEM/Administrators
            # can replace the new operations directory beneath this parent.
            $trustedSids = @($CurrentSid, 'S-1-5-18', 'S-1-5-32-544')
            if (($ace.FileSystemRights -band $allowWrite) -and
                (($broad -contains $aceSid) -or ($trustedSids -notcontains $aceSid))) {
                $unsafe = $true
            }
        }
        $result.broad_write_allow_detected = $unsafe
        $result.acl_readable = $true
    } catch {
        $result.acl_readable = $false
        $result.broad_write_allow_detected = $true
    }
    return $result
}

$currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$currentSid = [string]$currentIdentity.User.Value
$parentUnlinked = Test-UcieUnlinkedPath $parent
$parentAcl = Get-UcieAclRisk $parent $currentSid
$parentSafe = (
    $parentUnlinked -and $parentAcl.acl_readable -and
    $parentAcl.owner_is_current_or_builtin_system_administrators -and
    -not $parentAcl.broad_write_allow_detected
)
$existingTarget = (Test-Path -LiteralPath $target)
$targetReady = $false
$created = $false
$targetAcl = $null

if ($existingTarget) {
    # Never apply ACL to or overwrite an existing directory in this helper.
    $targetReady = $false
} elseif ($parentSafe -and $Apply) {
    # Apply the DACL at the instant of creation. Do NOT create an inherited
    # broad-write folder then remove permissions later (TOCTOU).
    $userSid = [Security.Principal.SecurityIdentifier]::new($currentSid)
    $systemSid = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
    $security = [Security.AccessControl.DirectorySecurity]::new()
    $security.SetOwner($userSid)
    $security.SetAccessRuleProtection($true, $false)
    $inherit = ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
        [Security.AccessControl.InheritanceFlags]::ObjectInherit)
    foreach ($sid in @($userSid, $systemSid)) {
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            $sid,
            [Security.AccessControl.FileSystemRights]::FullControl,
            $inherit,
            [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow)
        $security.AddAccessRule($rule)
    }
    # On Windows PowerShell 5.1 Directory.CreateDirectory(String, DirectorySecurity)
    # ensures creation with ACL. On PowerShell 7+ use the .NET extension.
    if ($PSVersionTable.PSVersion.Major -lt 6) {
        $null = [IO.Directory]::CreateDirectory($target, $security)
    } else {
        $null = [IO.FileSystemAclExtensions]::CreateDirectory($security, $target)
    }
    $created = $true
}

if ((Test-Path -LiteralPath $target -PathType Container) -and
    (Test-UcieUnlinkedPath $target)) {
    $targetAcl = Get-Acl -LiteralPath $target
    $targetOwner = $targetAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value
    $aces = @($targetAcl.Access)
    $allowed = @($currentSid, 'S-1-5-18')
    $exact = ($targetOwner -eq $currentSid -and
        [bool]$targetAcl.AreAccessRulesProtected -and $aces.Count -eq 2)
    foreach ($ace in $aces) {
        $sid = $null
        try {
            $sid = $ace.IdentityReference.Translate(
                [Security.Principal.SecurityIdentifier]).Value
        } catch {
            $exact = $false
            continue
        }
        if ($sid -notin $allowed -or
            $ace.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            (($ace.FileSystemRights -band
                [Security.AccessControl.FileSystemRights]::FullControl) -ne
                [Security.AccessControl.FileSystemRights]::FullControl)) {
            $exact = $false
        }
    }
    $targetReady = $exact
}

$status = $noExecution
if (-not $parentSafe) {
    $status = 'UCIE_PARENT_OWNER_OR_ACL_UNSAFE_NO_INSTALL'
} elseif ($existingTarget) {
    $status = 'UCIE_OPERATIONS_DIRECTORY_ALREADY_EXISTS_NO_OVERWRITE'
} elseif ($Apply -and $created -and $targetReady) {
    $status = 'UCIE_OWNER_OPERATIONS_DIRECTORY_CREATED_ACL_VERIFIED'
} elseif ($Apply -and $created) {
    $status = 'UCIE_OPERATIONS_DIRECTORY_CREATED_BUT_ACL_NOT_VERIFIED_HOLD'
}

[pscustomobject]@{
    schema = 'UCIE_OWNER_OPERATIONS_DIRECTORY_BOOTSTRAP_V1'
    project_id = 'UCIE'
    status = $status
    target_directory = $target
    parent_exists_with_no_reparse_ancestors = [bool]$parentUnlinked
    parent_owner_scoped_and_no_broad_allow_write = [bool]$parentSafe
    target_previously_existed = [bool]$existingTarget
    target_created_in_this_invocation = [bool]$created
    target_acl_exact_owner_and_system_only = [bool]$targetReady
    existing_bridge_state_modified = $false
    scheduled_task_modified = $false
    service_restarted = $false
    github_token_read = $false
    git_pushed = $false
    external_antirollback_anchor_configured = $false
    owner_signing_key_provisioned = $false
    auto_rule_promotion_enabled = $false
    unattended_automation_activated = $false
} | ConvertTo-Json -Depth 4 -Compress

if ($Apply -and -not ($created -and $targetReady)) {
    throw 'UCIE_OWNER_OPERATIONS_DIRECTORY_BOOTSTRAP_INCOMPLETE_NO_GO'
}
