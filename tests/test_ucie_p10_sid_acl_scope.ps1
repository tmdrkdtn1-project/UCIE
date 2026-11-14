# UCIE synthetic-only ACL SID identity regression.
# No filesystem changes, scheduler, processes, credentials or network.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'UCIE_TEST_WINDOWS_ONLY'
}
$foreign = [Security.Principal.SecurityIdentifier]::new(
    'S-1-5-21-111111111-222222222-333333333-444444444')
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$acl = [Security.AccessControl.DirectorySecurity]::new()
$acl.SetAccessRuleProtection($true, $false)
$inherit = [Security.AccessControl.InheritanceFlags]::None
$propagate = [Security.AccessControl.PropagationFlags]::None
$kind = [Security.AccessControl.AccessControlType]::Allow
$read = [Security.AccessControl.FileSystemAccessRule]::new(
    $foreign, [Security.AccessControl.FileSystemRights]::ReadAndExecute,
    $inherit, $propagate, $kind)
$write = [Security.AccessControl.FileSystemAccessRule]::new(
    $system, [Security.AccessControl.FileSystemRights]::Write,
    $inherit, $propagate, $kind)
$acl.AddAccessRule($read)
$acl.AddAccessRule($write)
$raw = @($acl.GetAccessRules(
    $true, $true, [Security.Principal.SecurityIdentifier]))
if ($raw.Count -ne 2) { throw 'UCIE_TEST_EXPECTED_TWO_SID_ACES' }
$mutating = ([Security.AccessControl.FileSystemRights]::Write -bor
    [Security.AccessControl.FileSystemRights]::Delete -bor
    [Security.AccessControl.FileSystemRights]::DeleteSubdirectoriesAndFiles -bor
    [Security.AccessControl.FileSystemRights]::ChangePermissions -bor
    [Security.AccessControl.FileSystemRights]::TakeOwnership)
$readonlyForeign = 0
$trustedWriter = 0
$unknownSid = 0
foreach ($ace in $raw) {
    if ($ace.IdentityReference -isnot
        [Security.Principal.SecurityIdentifier]) {
        throw 'UCIE_TEST_SID_TYPE_REQUIRED'
    }
    $sid = $ace.IdentityReference.Value
    if ([string]::IsNullOrWhiteSpace($sid)) {
        throw 'UCIE_TEST_SID_EMPTY'
    }
    if ($sid -eq $foreign.Value) {
        $unknownSid++
        if (($ace.FileSystemRights -band $mutating) -ne 0) {
            throw 'UCIE_TEST_FALSE_FOREIGN_READ_WRITE_POSITIVE'
        }
        $readonlyForeign++
    }
    if ($sid -eq $system.Value -and
        ($ace.FileSystemRights -band $mutating) -ne 0) {
        $trustedWriter++
    }
}
if ($readonlyForeign -ne 1 -or $trustedWriter -ne 1 -or
    $unknownSid -ne 1) {
    throw 'UCIE_TEST_ACL_CLASSIFICATION_FAILED'
}
# Reclassify the same unmapped foreign SID as a real write principal.
$acl.RemoveAccessRuleSpecific($read)
$foreignWrite = [Security.AccessControl.FileSystemAccessRule]::new(
    $foreign, [Security.AccessControl.FileSystemRights]::Write,
    $inherit, $propagate, $kind)
$acl.AddAccessRule($foreignWrite)
$foreignMutatorRejected = $false
foreach ($ace in $acl.GetAccessRules(
        $true, $true, [Security.Principal.SecurityIdentifier])) {
    if ($ace.IdentityReference.Value -eq $foreign.Value -and
        ($ace.FileSystemRights -band $mutating) -ne 0) {
        $foreignMutatorRejected = $true
    }
}
if (-not $foreignMutatorRejected) {
    throw 'UCIE_TEST_UNMAPPED_FOREIGN_WRITER_MUST_BE_DENIED'
}
Write-Output 'UCIE_P10_SID_DIRECT_ACL_FIXTURE_PASS'
