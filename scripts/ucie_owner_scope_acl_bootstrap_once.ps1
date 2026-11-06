# UCIE-only protected scope directory; one-time local owner action, never enrolls.
# Preview is READ ONLY. Apply creates ONE scope directory with explicit ACL.
[CmdletBinding()]
param(
    [ValidateSet('Preview','Apply')] [string]$Mode = 'Preview',
    [switch]$OwnerOnlyConfirmed
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root='D:\UCIE_HUB'
$parent='D:\UCIE_HUB\04_MIGRATION'
$target='D:\UCIE_HUB\04_MIGRATION\UCIE_OWNER_SCOPED_QA_V1'
$taskName='UCIE-C40-Recover'
$ownerConfirm='UCIE_OWNER_SCOPE_ACL_ONLY'
$adminSid=[Security.Principal.SecurityIdentifier]::new('S-1-5-32-544')
$systemSid=[Security.Principal.SecurityIdentifier]::new('S-1-5-18')

function Resolve-TaskSid {
    param([string]$UserId)
    if($UserId -match '^S-1-[0-9]+(?:-[0-9]+)+$'){return $UserId}
    try{
        return ([Security.Principal.NTAccount]::new($UserId)).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    } catch {throw 'UCIE_OWNER_ACL_TASK_OWNER_UNRESOLVED'}
}

function Assert-ExactOwnerAndParents {
    $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
    $principal=New-Object Security.Principal.WindowsPrincipal($identity)
    if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
        throw 'UCIE_OWNER_ACL_ADMIN_TOKEN_REQUIRED'
    }
    $tasks=@(Get-ScheduledTask -TaskName $taskName -ErrorAction Stop |
        Where-Object { [string]$_.TaskPath -eq [string][char]92 })
    if($tasks.Count -ne 1){throw 'UCIE_OWNER_ACL_EXACT_TASK_REQUIRED'}
    $task=$tasks[0]
    if([string]$task.State -ne 'Running' -or
       [string]$task.Principal.RunLevel -ne 'Highest' -or
       [string]$task.Principal.LogonType -ne 'Interactive' -or
       -not [string]::Equals(
          (Resolve-TaskSid -UserId ([string]$task.Principal.UserId)),
          $identity.User.Value,[StringComparison]::OrdinalIgnoreCase)){
        throw 'UCIE_OWNER_ACL_PRINCIPAL_MISMATCH'
    }
    foreach($dir in @($root,$parent)){
        if(-not (Test-Path -LiteralPath $dir -PathType Container)){
            throw 'UCIE_OWNER_ACL_REQUIRED_PARENT_MISSING'
        }
        $item=Get-Item -LiteralPath $dir -ErrorAction Stop
        if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
            throw 'UCIE_OWNER_ACL_PARENT_REPARSE_DENIED'
        }
    }
    if(Test-Path -LiteralPath $target){throw 'UCIE_OWNER_ACL_SCOPE_ALREADY_EXISTS'}
    return $identity.User
}

function Assert-SafeAcl {
    param([string]$Directory,[Security.Principal.SecurityIdentifier]$Owner,
          [switch]$RequireExactOwner)
    $acl=Get-Acl -LiteralPath $Directory -ErrorAction Stop
    $ownerSid=''
    try {
        $ownerSid=([Security.Principal.NTAccount]::new([string]$acl.Owner)).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    } catch {
        if([string]$acl.Owner -match '^S-1-[0-9]+(?:-[0-9]+)+$'){
            $ownerSid=[string]$acl.Owner
        }
    }
    $allowed=@($Owner.Value,$adminSid.Value,$systemSid.Value)
    if($ownerSid -notin $allowed){throw 'UCIE_OWNER_ACL_OWNER_NOT_ALLOWED'}
    if($RequireExactOwner -and $ownerSid -ne $Owner.Value){
        throw 'UCIE_OWNER_ACL_TARGET_OWNER_MISMATCH'
    }
    $mask=([Security.AccessControl.FileSystemRights]::Write -bor
        [Security.AccessControl.FileSystemRights]::Modify -bor
        [Security.AccessControl.FileSystemRights]::FullControl -bor
        [Security.AccessControl.FileSystemRights]::Delete -bor
        [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
        [Security.AccessControl.FileSystemRights]::TakeOwnership)
    foreach($ace in @($acl.Access)){
        if([string]$ace.AccessControlType -ne 'Allow'){continue}
        if(([int64]$ace.FileSystemRights -band [int64]$mask) -eq 0){continue}
        $sid=''
        try{
            $sid=$ace.IdentityReference.Translate(
                [Security.Principal.SecurityIdentifier]).Value
        } catch {
            throw 'UCIE_OWNER_ACL_UNRESOLVED_WRITE_PRINCIPAL'
        }
        if($sid -notin $allowed){throw 'UCIE_OWNER_ACL_UNTRUSTED_WRITE_PRINCIPAL'}
    }
    return $true
}

function Test-Prerequisites {
    try {
        $owner=Assert-ExactOwnerAndParents
        $null=Assert-SafeAcl -Directory $parent -Owner $owner
        return [pscustomobject]@{ready=$true;reason='NONE';owner=$owner}
    } catch {
        $reason=[string]$_.Exception.Message
        if($reason -notmatch '^UCIE_OWNER_ACL_[A-Z0-9_]+$'){
            $reason='UCIE_OWNER_ACL_UNAVAILABLE_OR_UNEXPECTED'
        }
        return [pscustomobject]@{ready=$false;reason=$reason;owner=$null}
    }
}

$probe=Test-Prerequisites
if($Mode -eq 'Preview'){
    [pscustomobject]@{
        schema='UCIE_OWNER_SCOPED_ACL_BOOTSTRAP_V1'
        status='UCIE_OWNER_SCOPE_ACL_PREVIEW_ONLY'
        ready_to_create=[bool]$probe.ready
        blocker_code=[string]$probe.reason
        scope_directory_exists=(Test-Path -LiteralPath $target)
        task_or_process_modified=$false
        grant_created=$false
        directory_created=$false
        operating_db_modified=$false
    } | ConvertTo-Json -Compress
    return
}
if(-not $OwnerOnlyConfirmed){throw 'UCIE_OWNER_ACL_OWNER_CONFIRM_REQUIRED'}
if(-not $probe.ready){throw 'UCIE_OWNER_ACL_PREVIEW_NOT_READY'}
$typed=Read-Host 'CREATE ONLY protected UCIE scoped consent directory; type UCIE_OWNER_SCOPE_ACL_ONLY'
if($typed -cne $ownerConfirm){throw 'UCIE_OWNER_ACL_CONFIRMATION_REJECTED'}

# Revalidate AFTER confirmation. Do not change the parent ACL or existing data.
$second=Test-Prerequisites
if(-not $second.ready -or -not $second.owner.Value.Equals($probe.owner.Value)){
    throw 'UCIE_OWNER_ACL_PRECONDITION_CHANGED'
}

$security=New-Object System.Security.AccessControl.DirectorySecurity
$security.SetAccessRuleProtection($true,$false)
$security.SetOwner($second.owner)
$security.SetGroup($adminSid)
$inherit=([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
    [Security.AccessControl.InheritanceFlags]::ObjectInherit)
foreach($principalSid in @($second.owner,$adminSid,$systemSid)){
    $rule=[Security.AccessControl.FileSystemAccessRule]::new(
        $principalSid,[Security.AccessControl.FileSystemRights]::FullControl,
        $inherit,[Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow
    )
    $security.AddAccessRule($rule)
}
# Windows PowerShell 5.1/.NET Framework supports ACL at creation time.
$directory=[IO.Directory]::CreateDirectory($target,$security)
if(-not [string]::Equals([string]$directory.FullName,$target,
    [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_OWNER_ACL_TARGET_MISMATCH'
}
$null=Assert-SafeAcl -Directory $target -Owner $second.owner -RequireExactOwner
if(Test-Path -LiteralPath (Join-Path $target 'grant.json')){
    throw 'UCIE_OWNER_ACL_UNEXPECTED_GRANT_CREATED'
}
[pscustomobject]@{
    schema='UCIE_OWNER_SCOPED_ACL_BOOTSTRAP_V1'
    status='UCIE_OWNER_SCOPE_ACL_DIRECTORY_CREATED_ONLY'
    owner_only_acl_verified=$true
    scope_directory_exists=$true
    grant_created=$false
    owner_authenticated_mcp_tools_registered=$false
    task_or_process_modified=$false
    operating_db_modified=$false
} | ConvertTo-Json -Compress
