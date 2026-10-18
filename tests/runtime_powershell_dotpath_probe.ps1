# UCIE-owned public PowerShell #28087 behavior probe on disposable CI runners.
# Test only freshly created synthetic paths. Do NOT execute/download upstream code
# or certify pre/post upstream commits, specific release inclusion, or rule approval.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path (Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts') 'ucie_safe_powershell_results.ps1')
$work = Join-Path ([System.IO.Path]::GetTempPath()) ('ucie-ps-dotpath-' + [guid]::NewGuid().ToString('N'))
$cases = [System.Collections.Generic.List[object]]::new()
$dotCorrect = 0
$baselineCorrect = $false
$guardCorrect = $true

[System.IO.Directory]::CreateDirectory($work) | Out-Null
try {
    foreach ($name in @('.directory', '..directory', 'directory')) {
        $dir = Join-Path $work $name
        [System.IO.Directory]::CreateDirectory($dir) | Out-Null
        [System.IO.File]::WriteAllText((Join-Path $dir 'file1.txt'), 'synthetic')
        [System.IO.File]::WriteAllText((Join-Path $dir 'file2.txt'), 'synthetic')
    }
    Push-Location -LiteralPath $work
    try {
        foreach ($name in @('.directory', '..directory', 'directory')) {
            $search = Join-Path $name '*.txt'
            $expected = @(
                (Join-Path (Join-Path '.' $name) 'file1.txt'),
                (Join-Path (Join-Path '.' $name) 'file2.txt')
            )
            $native = @(Resolve-Path -Path $search -Relative -ErrorAction Stop)
            $safe = @(Resolve-UCIESafeRelativePath -BaseDirectory $work -SearchPattern $search)
            $want = @($expected | Sort-Object)
            $got = @($native | Sort-Object)
            $guardGot = @($safe | Sort-Object)
            $nativeMatch = ($got.Count -eq 2 -and
                            $got[0] -ceq $want[0] -and $got[1] -ceq $want[1])
            $guardMatch = ($guardGot.Count -eq 2 -and
                           $guardGot[0] -ceq $want[0] -and
                           $guardGot[1] -ceq $want[1])
            if (-not $guardMatch) { $guardCorrect = $false }
            if ($name -eq 'directory') {
                $baselineCorrect = $nativeMatch
            }
            elseif ($nativeMatch) {
                $dotCorrect++
            }
            $cases.Add([pscustomobject]@{
                case_id = $name
                synthetic_expected_count = 2
                native_count = $got.Count
                native_matches_expected = [bool]$nativeMatch
                safe_count = $guardGot.Count
                safe_matches_expected = [bool]$guardMatch
            })
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    # Delete ONLY this newly created disposable CI fixture, not user files.
    if ([System.IO.Directory]::Exists($work)) {
        [System.IO.Directory]::Delete($work, $true)
    }
}
if (-not $baselineCorrect -or -not $guardCorrect -or $cases.Count -ne 3) {
    throw 'UCIE_DOTPATH_SYNTHETIC_BASELINE_OR_SAFE_GUARD_REGRESSION'
}
$behavior = if ($dotCorrect -eq 0) {
    'DOT_PREFIX_BUG_OBSERVED_ON_RUNNER'
}
elseif ($dotCorrect -eq 2) {
    'FIXED_LIKE_BEHAVIOR_NOT_UPSTREAM_COMMIT_PROOF'
}
else {
    'MIXED_NATIVE_BEHAVIOR_REVIEW_REQUIRED'
}
$report = [ordered]@{
    schema = 'UCIE_PS_DOTPATH_RUNTIME_EVIDENCE_V1'
    status = 'OBSERVED_ON_DISPOSABLE_CI_NO_GO'
    source = 'PowerShell/PowerShell'
    public_pr = 'https://github.com/PowerShell/PowerShell/pull/28087'
    pinned_upstream_merge_sha = '373f6a7b7972a0a4b73bfd9737a0d768d28b347e'
    rule_id = 'PS_RESOLVE_PATH_DOT_PREFIX'
    platform = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
    runtime_version = $PSVersionTable.PSVersion.ToString()
    runner_source_sha = [string]$env:GITHUB_SHA
    native_behavior = $behavior
    dot_prefix_cases_matching_expected = $dotCorrect
    baseline_case_passed = $baselineCorrect
    guarded_cases_passed = $guardCorrect
    observations = @($cases.ToArray())
    upstream_pre_fix_binary_verified = $false
    upstream_post_fix_binary_verified = $false
    independent_before_after_verified = $false
    affected_release_inclusion_verified = $false
    license_review_approved = $false
    rule_approved = $false
    production_approved = $false
    auto_promoted = $false
    persistent_project_writes = 0
}
Write-Output ('UCIE_PS_DOTPATH_RUNTIME_EVIDENCE=' +
              ($report | ConvertTo-Json -Compress -Depth 6))
