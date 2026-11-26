# UCIE B4 independently observed first-party PowerShell command precedence.
# Disposable Windows Github Actions runner only. This UCIE authored script
# does not accept commands, paths, customer data or external source code.
# It creates one temporary alias inside a fresh -NoProfile pwsh process,
# observes Get-Command resolution and removes it before exit.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

if ($PSVersionTable.PSVersion.Major -ne 7) {
    throw 'UCIE held-out native smoke requires a pinned PowerShell 7.x runner'
}
$sourceCommit = '7c8d9e7e0ed2fc1f2caf50746fe9fef720ca2a0a'
$cmdletBefore = Get-Command -Name Get-Date -CommandType Cmdlet -ErrorAction Stop
if ($cmdletBefore.CommandType -ne 'Cmdlet') {
    throw 'UCIE first party cmdlet baseline missing'
}
$aliasBefore = Get-Alias -Name Get-Date -ErrorAction SilentlyContinue
if ($null -ne $aliasBefore) {
    throw 'Cannot inject alias: baseline already contains Get-Date alias'
}

try {
    Set-Alias -Name Get-Date -Value Get-Location -Scope Local -ErrorAction Stop
    $implicit = Get-Command -Name Get-Date -ErrorAction Stop
    $qualifiedType = Get-Command -Name Get-Date -CommandType Cmdlet -ErrorAction Stop
    $allCandidates = @(Get-Command -Name Get-Date -All -ErrorAction Stop)
    $aliasPresent = @($allCandidates | Where-Object CommandType -eq 'Alias').Count -ge 1
    $cmdletPresent = @($allCandidates | Where-Object CommandType -eq 'Cmdlet').Count -ge 1

    if ($implicit.CommandType -ne 'Alias') {
        throw 'Expected Alias to shadow same-named loaded Cmdlet'
    }
    if ($qualifiedType.CommandType -ne 'Cmdlet') {
        throw 'Explicit -CommandType Cmdlet did not disambiguate'
    }
    if (-not ($aliasPresent -and $cmdletPresent)) {
        throw 'Get-Command -All failed to reveal both loaded command types'
    }
    $runtimeVersion = $PSVersionTable.PSVersion.ToString()
    $result = [ordered]@{
        schema = 'UCIE_B4_HELDOUT_POWERSHELL_NATIVE_DISPOSABLE_V01'
        status = 'FIRST_PARTY_WINDOWS_RUNNER_PWSH_OBSERVATION_ONLY'
        source_tag = 'v7.5.4'
        pinned_source_commit = $sourceCommit
        source_version_equals_runtime = ($runtimeVersion -eq '7.5.4')
        observed_pwsh_version = $runtimeVersion
        first_party_synthetic_names_only = $true
        implicit_resolution = [string]$implicit.CommandType
        explicit_cmdlet_resolution = [string]$qualifiedType.CommandType
        hidden_alias_visible_with_all = $aliasPresent
        hidden_cmdlet_visible_with_all = $cmdletPresent
        actual_owner_host_tested = $false
        actual_customer_code_read = $false
        official_source_commit_binary_reexecuted = $false
        independent_upstream_qa_verified = $false
        source_license_redistribution_approved = $false
        author_approved_export = $false
        auto_promoted = $false
        network_requests = 0
        operating_database_writes = 0
    }
    $result | ConvertTo-Json -Compress -Depth 4
}
finally {
    Remove-Item -LiteralPath 'Alias:\Get-Date' -Force -ErrorAction SilentlyContinue
}
