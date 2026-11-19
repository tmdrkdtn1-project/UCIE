# UCIE P10 disposable Windows CI fixture ONLY.
# Proves ACL is attached at creation in Windows PowerShell 5.1 / pwsh 7+.
# The fixture is generated only under RUNNER_TEMP, never owner UCIE paths.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('WindowsPowerShell51', 'PowerShell7')]
    [string]$Runtime
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or
    [string]::IsNullOrWhiteSpace($env:RUNNER_TEMP) -or
    -not (Test-Path -LiteralPath $env:RUNNER_TEMP -PathType Container)) {
    throw 'UCIE_P10_TEST_REQUIRES_EPHEMERAL_WINDOWS_GITHUB_RUNNER'
}
$temporaryRoot = [IO.Path]::GetFullPath($env:RUNNER_TEMP)
$fixture = Join-Path $temporaryRoot ('UCIE_P10_SYNTHETIC_ACL_' + [guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $fixture) {
    throw 'UCIE_P10_SYNTHETIC_FIXTURE_COLLISION'
}
$current = [Security.Principal.WindowsIdentity]::GetCurrent().User
$system = [Security.Principal.SecurityIdentifier]::new('S-1-5-18')
$security = [Security.AccessControl.DirectorySecurity]::new()
$security.SetOwner($current)
$security.SetAccessRuleProtection($true, $false)
$inherit = ([Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
    [Security.AccessControl.InheritanceFlags]::ObjectInherit)
foreach ($sid in @($current, $system)) {
    $rule = [Security.AccessControl.FileSystemAccessRule]::new(
        $sid, [Security.AccessControl.FileSystemRights]::FullControl,
        $inherit, [Security.AccessControl.PropagationFlags]::None,
        [Security.AccessControl.AccessControlType]::Allow)
    $security.AddAccessRule($rule)
}
try {
    if ($Runtime -eq 'WindowsPowerShell51') {
        if ($PSVersionTable.PSVersion.Major -ne 5) {
            throw 'UCIE_P10_EXPECTED_PS51'
        }
        $null = [IO.Directory]::CreateDirectory($fixture, $security)
    } else {
        if ($PSVersionTable.PSVersion.Major -lt 7) {
            throw 'UCIE_P10_EXPECTED_PS7_OR_NEWER'
        }
        $null = [IO.FileSystemAclExtensions]::CreateDirectory($security, $fixture)
    }
    $acl = Get-Acl -LiteralPath $fixture
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne
        $current.Value -or -not $acl.AreAccessRulesProtected) {
        throw 'UCIE_P10_CI_ACL_OWNER_OR_INHERITANCE_INVALID'
    }
    $aces = @($acl.Access)
    if ($aces.Count -ne 2) {
        throw 'UCIE_P10_CI_ACL_ACE_COUNT_INVALID'
    }
    $allowed = @($current.Value, $system.Value)
    $seen = @{}
    foreach ($ace in $aces) {
        $sid = $ace.IdentityReference.Translate(
            [Security.Principal.SecurityIdentifier]).Value
        if ($sid -notin $allowed -or $seen.ContainsKey($sid) -or
            $ace.AccessControlType -ne
            [Security.AccessControl.AccessControlType]::Allow -or
            $ace.IsInherited -or
            (($ace.FileSystemRights -band
                [Security.AccessControl.FileSystemRights]::FullControl) -ne
                [Security.AccessControl.FileSystemRights]::FullControl)) {
            throw 'UCIE_P10_CI_ACL_ALLOW_RULE_INVALID'
        }
        $seen[$sid] = $true
    }
    if (-not $seen.ContainsKey($current.Value) -or
        -not $seen.ContainsKey($system.Value)) {
        throw 'UCIE_P10_CI_ACL_EXPECTED_PRINCIPALS_MISSING'
    }
    Write-Output ('UCIE_P10_EPHEMERAL_ACL_CREATION_PASS_' + $Runtime)
} finally {
    if (Test-Path -LiteralPath $fixture -PathType Container) {
        $actual = [IO.Path]::GetFullPath($fixture)
        if (-not $actual.StartsWith(
            $temporaryRoot.TrimEnd('\') + '\',
            [StringComparison]::OrdinalIgnoreCase) -or
            (Split-Path -Path $actual -Leaf) -notmatch '^UCIE_P10_SYNTHETIC_ACL_[a-f0-9]{32}$') {
            throw 'UCIE_P10_CI_FIXTURE_CLEANUP_SCOPE_REFUSED'
        }
        Remove-Item -LiteralPath $actual -Recurse -Force
    }
}
