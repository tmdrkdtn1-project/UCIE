# UCIE authored only: real Windows PowerShell user-pipe acceptance on clean CI.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true' -or $env:RUNNER_OS -ne 'Windows') {
    throw 'UCIE_DISPOSABLE_WINDOWS_CI_REQUIRED'
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if ((Split-Path $root -Leaf) -ine 'UCIE') { throw 'UCIE_ROOT_MISMATCH' }
# Build ONE exact UCIE-owned synthetic acceptance payload in pwsh (UTF-8).
# -EncodedCommand passes Unicode intact to both native PowerShell engines.
$synthetic = @'
$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$py = (Get-Command python -ErrorAction Stop).Source
$env:PYTHONPATH = Join-Path $root 'src'
# PS5.1 defaults to ASCII for native command pipelines: set explicit UTF-8.
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)

function Invoke-UCIESyntheticReview {
    param([Parameter(Mandatory)][string]$Language,
          [Parameter(Mandatory)][string]$Code)
    $lines = @($Code | & $py -B -m ucie_miner.code_review_v1 --ucie-root $root --language $Language)
    if ($LASTEXITCODE -ne 0 -or $lines.Count -ne 1) {
        throw 'UCIE_REAL_MANUAL_CLI_FAILED'
    }
    return ($lines[0] | ConvertFrom-Json)
}
$watch = [System.Diagnostics.Stopwatch]::StartNew()
$sourceA = "# UCIE 합성 코드: 한글과 이모지 🐼" + [char]10 + "Resolve-Path -Relative '.directory'" + [char]10
$sourceB = "# UCIE 합성 코드: 한글과 이모지 🐻" + [char]10 + "Resolve-Path -Relative '.directory'" + [char]10
$psA = Invoke-UCIESyntheticReview -Language 'powershell' -Code $sourceA
$psB = Invoke-UCIESyntheticReview -Language 'powershell' -Code $sourceB
if ($psA.finding_count -ne 1 -or $psB.finding_count -ne 1 -or
    $psA.findings[0].line -ne 2 -or
    $psA.findings[0].rule_id -ne 'PS_RESOLVE_PATH_DOT_PREFIX' -or
    $psA.findings[0].version_evidence.tested_release -ne 'PowerShell 7.6.6' -or
    $psA.source_sha256 -eq $psB.source_sha256 -or
    $psA.source_executed -ne $false -or
    $psA.database_writes -ne 0 -or
    $psA.auto_applied -ne $false -or
    $psA.production_approved -ne $false -or
    $psA.findings[0].public_library.approved_or_exportable -ne $false) {
    throw 'UCIE_REAL_POWERSHELL_CLI_ACCEPTANCE_FAILED'
}
$pythonSource = @(
    'import os',
    'from concurrent.futures import ThreadPoolExecutor',
    'def validate(folder, callback):',
    '    iterator = os.scandir(folder)',
    '    with ThreadPoolExecutor(max_workers=2) as pool:',
    '        return pool.submit(callback, iterator).result()',
    ''
) -join [char]10
$python = Invoke-UCIESyntheticReview -Language 'python' -Code $pythonSource
if ($python.finding_count -ne 1 -or
    $python.findings[0].rule_id -ne 'PY_SCANDIR_SHARED_ITERATOR_RACE' -or
    $python.findings[0].public_library.approved_or_exportable -ne $false -or
    $python.source_executed -ne $false -or
    $python.database_writes -ne 0) {
    throw 'UCIE_REAL_PYTHON_CLI_ACCEPTANCE_FAILED'
}
$empty = Invoke-UCIESyntheticReview -Language 'python' -Code 'pass'
if ($empty.finding_count -ne 0 -or
    $empty.status -ne 'NO_KNOWN_PATTERN_NOT_SAFETY_PASS' -or
    $empty.full_code_safety_verified -ne $false) {
    throw 'UCIE_NO_PATTERN_UNSAFE_PASS'
}
$invalid = @('if (' | & $py -B -m ucie_miner.code_review_v1 --ucie-root $root --language powershell)
if ($LASTEXITCODE -ne 2 -or $invalid.Count -ne 1) {
    throw 'UCIE_INVALID_SYNTAX_DID_NOT_FAIL_CLOSED'
}
$negative = $invalid[0] | ConvertFrom-Json
if ($negative.status -ne 'CODE_REVIEW_FAIL_CLOSED' -or
    $invalid[0].Contains('if (') -or
    $negative.production_approved -ne $false) {
    throw 'UCIE_INVALID_SYNTAX_OR_SOURCE_ECHO'
}
$watch.Stop()
$receipt = @{
    schema = 'UCIE_V1_REAL_SHELL_PIPE_ACCEPTANCE_V1'
    status = 'MANUAL_CLI_ACCEPTED_ISOLATED_CI_ONLY'
    syntax_positive_python = $true
    syntax_positive_powershell = $true
    input_unicode_distinct_hash = $true
    correct_position = $true
    source_linked_pr_unapproved = $true
    empty_result_not_safety_pass = $true
    malformed_input_fail_closed = $true
    elapsed_ms = [int]$watch.ElapsedMilliseconds
    product_v1_accepted = $false
    owner_windows_host_tested = $false
    local_checkout_modified = $false
    automatic_rule_promotion = $false
}
[Console]::Out.WriteLine('UCIE_V1_REAL_SHELL_ACCEPTANCE=' +
    (ConvertTo-Json -InputObject $receipt -Compress -Depth 5))
'@
$encoded = [Convert]::ToBase64String(
    [System.Text.Encoding]::Unicode.GetBytes($synthetic))
$summaries = @()
foreach ($engine in @('pwsh', 'powershell.exe')) {
    $exe = (Get-Command $engine -ErrorAction Stop).Source
    $lines = @(& $exe -NoProfile -NonInteractive -EncodedCommand $encoded)
    if ($LASTEXITCODE -ne 0) { throw ('UCIE_CI_SHELL_FAILED:' + $engine) }
    $recs = @($lines | Where-Object {
        $_ -is [string] -and $_.StartsWith('UCIE_V1_REAL_SHELL_ACCEPTANCE=')
    })
    if ($recs.Count -ne 1) { throw ('UCIE_CI_SHELL_RECEIPT_MISSING:' + $engine) }
    $item = $recs[0].Substring('UCIE_V1_REAL_SHELL_ACCEPTANCE='.Length) |
        ConvertFrom-Json
    if ($item.status -ne 'MANUAL_CLI_ACCEPTED_ISOLATED_CI_ONLY' -or
        $item.product_v1_accepted -ne $false -or
        $item.input_unicode_distinct_hash -ne $true) {
        throw ('UCIE_CI_SHELL_RECEIPT_INVALID:' + $engine)
    }
    $summaries += [pscustomobject]@{
        shell = $engine
        manual_cli_accepted_in_disposable_ci = $true
        elapsed_ms = $item.elapsed_ms
        production_approved = $false
    }
}
$final = @{
    schema = 'UCIE_V1_DUAL_WINDOWS_SHELL_ACCEPTANCE_V1'
    status = 'DUAL_WINDOWS_SHELL_MANUAL_CLI_GO_ISOLATED_ONLY'
    engine_count = $summaries.Count
    engines = @($summaries)
    owner_local_deployment = 'NOT_PERFORMED'
    full_product_v1_accepted = $false
    independent_qa_signed = $false
    production_database_writes = 0
    new_schedulers = 0
}
Write-Output ('UCIE_V1_DUAL_WINDOWS_SHELL_ACCEPTANCE=' +
    (ConvertTo-Json -InputObject $final -Compress -Depth 6))
