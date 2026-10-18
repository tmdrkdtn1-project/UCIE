# UCIE-owned inert reproduction of PowerShell/PowerShell PR #28042.
# Disposable CI runners only. Never invoke discovered Get-FuzzyDuplicate,
# use real project paths, import external code or write outside this fixture.
[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$fixture = Join-Path ([System.IO.Path]::GetTempPath()) ('ucie-fuzzy-' + [guid]::NewGuid().ToString('N'))
$oldModules = $env:PSModulePath
[System.IO.Directory]::CreateDirectory($fixture) | Out-Null
try {
    $roots = @(1..2 | ForEach-Object {
        $base = Join-Path $fixture ("ModuleRoot{0}" -f $_)
        $module = Join-Path $base 'DuplicateFuzzyModule'
        [System.IO.Directory]::CreateDirectory($module) | Out-Null
        New-ModuleManifest -Path (Join-Path $module 'DuplicateFuzzyModule.psd1') -ModuleVersion '1.0' -CmdletsToExport 'Get-FuzzyDuplicate' | Out-Null
        $base
    })
    # Exactly the upstream reproduction: two discoverable copies of the same
    # module, a one-character fuzzy lookup, and a bounded expected result.
    $env:PSModulePath = $roots -join [System.IO.Path]::PathSeparator
    $matches = @(Get-Command Get-FuzzyDuplicat -UseFuzzyMatching -FuzzyMinimumDistance 1)
    $identities = @($matches | ForEach-Object {
        '{0}|{1}|{2}' -f $_.Name, $_.CommandType, $_.Source
    })
    $scores = @($matches | ForEach-Object { $_.Score })
    $isFixedLike = ($matches.Count -eq 1 -and
        $matches[0].Name -ceq 'Get-FuzzyDuplicate' -and
        $matches[0].Score -eq 1)
    $behavior = if ($isFixedLike) {
        'FIXED_LIKE_DUPLICATE_FILTERING'
    }
    elseif ($matches.Count -gt 1 -and @($identities | Select-Object -Unique).Count -eq 1) {
        'DUPLICATE_FUZZY_RESULTS_OBSERVED'
    }
    else {
        'UNEXPECTED_FUZZY_OUTPUT_REVIEW_REQUIRED'
    }
    $result = [ordered]@{
        schema = 'UCIE_PS_FUZZY_RUNTIME_EVIDENCE_V1'
        source = 'PowerShell/PowerShell'
        public_pr = 'https://github.com/PowerShell/PowerShell/pull/28042'
        pinned_merge_sha = 'bd8cb01a7d5b86129c45eaa14ab5830a63b1283f'
        rule_id = 'PS_FUZZY_GET_COMMAND_DUPLICATES'
        platform = [System.Runtime.InteropServices.RuntimeInformation]::OSDescription
        runtime_version = $PSVersionTable.PSVersion.ToString()
        ci_commit_sha = [string]$env:GITHUB_SHA
        native_behavior = $behavior
        fuzzy_result_count = $matches.Count
        distinct_identity_count = @($identities | Select-Object -Unique).Count
        scores = $scores
        exactly_one_result_with_score_one = [bool]$isFixedLike
        upstream_pre_fix_binary_verified = $false
        upstream_post_fix_binary_verified = $false
        released_version_fix_coverage_proven = $false
        independent_human_qa_approved = $false
        license_review_approved = $false
        owner_approved = $false
        auto_fix = $false
        private_files_scanned = 0
        persistent_project_writes = 0
    }
    Write-Output ('UCIE_PS_FUZZY_RUNTIME_EVIDENCE=' +
        ($result | ConvertTo-Json -Depth 5 -Compress))
    if ($matches.Count -lt 1 -or $matches.Count -gt 20) {
        throw 'UCIE_FUZZY_REPRO_UNBOUNDED_OR_EMPTY'
    }
}
finally {
    $env:PSModulePath = $oldModules
    if ([System.IO.Directory]::Exists($fixture)) {
        [System.IO.Directory]::Delete($fixture, $true)
    }
}
