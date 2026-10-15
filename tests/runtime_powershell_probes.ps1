# UCIE-authored PowerShell public runtime probes, disposable hosted CI only.
# Never calls SSH, creates a runspace connection, installs a scheduled task,
# downloads external code, runs upstream tests, or reads an operating project.
$ErrorActionPreference = 'Stop'
$items = [System.Collections.Generic.List[object]]::new()
$version = $PSVersionTable.PSVersion.ToString()
$root = Join-Path ([System.IO.Path]::GetTempPath()) ('ucie-runtime-' + [guid]::NewGuid().ToString('N'))
$original = $env:PSModulePath
$guardedFailures = 0
. (Join-Path $PSScriptRoot '..\scripts\ucie_safe_powershell_results.ps1')
[System.IO.Directory]::CreateDirectory($root) | Out-Null
try {
    $roots = @()
    foreach ($i in 1..2) {
        $parent = Join-Path $root ("modules" + $i)
        $module = Join-Path $parent 'DuplicateFuzzyModule'
        [System.IO.Directory]::CreateDirectory($module) | Out-Null
        New-ModuleManifest -Path (Join-Path $module 'DuplicateFuzzyModule.psd1') -ModuleVersion '1.0' -CmdletsToExport 'Get-FuzzyDuplicate' | Out-Null
        $roots += $parent
    }
    try {
        $env:PSModulePath = ($roots -join [System.IO.Path]::PathSeparator)
        $found = @(Get-Command 'Get-FuzzyDuplicat' -UseFuzzyMatching -FuzzyMinimumDistance 1 -ErrorAction Stop)
        $matches = @($found | Where-Object { $_.Name -eq 'Get-FuzzyDuplicate' })
        $ok = ($found.Count -eq 1 -and $matches.Count -eq 1)
        $safe = @(Get-UCIEUniqueCommandResults -Commands $found)
        $guardedOk = ($safe.Count -eq 1 -and $safe[0].Name -eq 'Get-FuzzyDuplicate')
        if (-not $guardedOk) { $guardedFailures++ }
        $items.Add(@{
            pattern = 'PS_FUZZY_GET_COMMAND_DUPLICATES'
            coverage = 'PUBLIC_RUNTIME_BEHAVIOR'
            state = $(if ($ok) { 'OBSERVED_EXPECTED_BEHAVIOR' } else { 'OBSERVED_MISMATCH' })
            observed_command_count = $found.Count
            guarded_result_count = $safe.Count
            guarded_state = $(if ($guardedOk) { 'GUARDED_BEHAVIOR_OBSERVED' } else { 'GUARDED_MISMATCH' })
        })
    }
    catch {
        $guardedFailures++
        $items.Add(@{ pattern='PS_FUZZY_GET_COMMAND_DUPLICATES'; coverage='PUBLIC_RUNTIME_BEHAVIOR'; state='PROBE_ERROR'; guarded_state='GUARD_PROBE_ERROR' })
    }
    finally {
        $env:PSModulePath = $original
    }

    try {
        $relativeRoot = Join-Path $root 'relative'
        [System.IO.Directory]::CreateDirectory($relativeRoot) | Out-Null
        foreach ($name in @('.directory', '..directory', 'directory')) {
            $folder = Join-Path $relativeRoot $name
            [System.IO.Directory]::CreateDirectory($folder) | Out-Null
            [System.IO.File]::WriteAllText((Join-Path $folder 'file1.txt'), 'x')
            [System.IO.File]::WriteAllText((Join-Path $folder 'file2.txt'), 'y')
        }
        $match = $true
        $guardedMatch = $true
        Push-Location -LiteralPath $relativeRoot
        try {
            foreach ($name in @('.directory', '..directory', 'directory')) {
                $found = @(Resolve-Path -Path (Join-Path $name '*.txt') -Relative -ErrorAction Stop)
                $safeFound = @(Resolve-UCIESafeRelativePath -BaseDirectory $relativeRoot -SearchPattern (Join-Path $name '*.txt'))
                $expected = @((Join-Path (Join-Path '.' $name) 'file1.txt'), (Join-Path (Join-Path '.' $name) 'file2.txt'))
                if ($found.Count -ne 2) { $match = $false }
                if ($safeFound.Count -ne 2) { $guardedMatch = $false; continue }
                $observed = @($found | Sort-Object)
                $expectedSorted = @($expected | Sort-Object)
                if ($found.Count -eq 2 -and (($observed[0] -cne $expectedSorted[0]) -or ($observed[1] -cne $expectedSorted[1]))) {
                    $match = $false
                }
                $safeSorted = @($safeFound | Sort-Object)
                if (($safeSorted[0] -cne $expectedSorted[0]) -or ($safeSorted[1] -cne $expectedSorted[1])) {
                    $guardedMatch = $false
                }
            }
        }
        finally { Pop-Location }
        if (-not $guardedMatch) { $guardedFailures++ }
        $items.Add(@{
            guarded_state = $(if ($guardedMatch) { 'GUARDED_BEHAVIOR_OBSERVED' } else { 'GUARDED_MISMATCH' })
            pattern = 'PS_RESOLVE_PATH_DOT_PREFIX'
            coverage = 'PUBLIC_RUNTIME_BEHAVIOR'
            state = $(if ($match) { 'OBSERVED_EXPECTED_BEHAVIOR' } else { 'OBSERVED_MISMATCH' })
        })
    }
    catch {
        $guardedFailures++
        $items.Add(@{ pattern='PS_RESOLVE_PATH_DOT_PREFIX'; coverage='PUBLIC_RUNTIME_BEHAVIOR'; state='PROBE_ERROR'; guarded_state='GUARD_PROBE_ERROR' })
    }

    $items.Add(@{
        pattern = 'PS_SSH_PATH_WITHOUT_RUNSPACE'
        coverage = 'SDK_HOST_TLS_AND_SSH_PROCESS_ISOLATION_REQUIRED'
        state = 'NOT_REPRODUCED'
    })
}
finally {
    $env:PSModulePath = $original
    # Delete only this freshly created, independently named CI disposable folder.
    if ([System.IO.Directory]::Exists($root)) {
        [System.IO.Directory]::Delete($root, $true)
    }
}
$out = [ordered]@{
    schema = 'UCIE_SAFE_POWERSHELL_BEHAVIOR_OBSERVATION_V2'
    guarded_checks_passed = ($guardedFailures -eq 0)
    native_runtime_regression_gate = 'NO_GO'
    runtime = 'PowerShell'
    version = $version
    observations = @($items.ToArray())
    pinned_pre_fix_revision_tested = $false
    pinned_post_fix_revision_tested = $false
    upstream_code_checked_out = $false
    independent_before_after_verified = $false
    production_approved = $false
}
Write-Output ('UCIE_POWERSHELL_BEHAVIOR=' + ($out | ConvertTo-Json -Compress -Depth 6))
# This probe is observational, not an upstream fix/production conformance gate.
# Mismatches are reported verbatim and never converted into 'PASS' or approval.
exit $(if ($guardedFailures -eq 0) { 0 } else { 1 })
