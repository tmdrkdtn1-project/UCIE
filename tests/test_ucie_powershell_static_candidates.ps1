# Tests ONLY UCIE-authored synthetic PowerShell source strings. This file
# never evaluates or executes the contents passed to the AST scanner.
$ErrorActionPreference = 'Stop'
. (Join-Path (Join-Path $PSScriptRoot '..') 'scripts/ucie_powershell_static_candidates.ps1')

function Assert-UCIE {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

$source = @'
Get-Command 'Get-FuzzyDuplicat' -UseFuzzyMatching -FuzzyMinimumDistance 1
Resolve-Path '.directory\*.txt' -Relative
'@
$result = Find-UCIEPowerShellCandidate -SourceText $source
Assert-UCIE ($result.finding_count -eq 2) 'Expected two static candidate findings'
Assert-UCIE (($result.findings | Where-Object { $_.pattern_code -eq 'PS_FUZZY_GET_COMMAND_DUPLICATES' }).Count -eq 1) 'Missing fuzzy candidate'
Assert-UCIE (($result.findings | Where-Object { $_.pattern_code -eq 'PS_RESOLVE_PATH_DOT_PREFIX' }).Count -eq 1) 'Missing relative candidate'
Assert-UCIE ($result.parser_executed_supplied_code -eq $false) 'Scanner unexpectedly claims execution'
Assert-UCIE ($result.source_files_read -eq 0) 'Scanner unexpectedly read files'
Assert-UCIE ($result.persistent_writes -eq 0) 'Scanner unexpectedly persisted data'
Assert-UCIE ($result.production_approved -eq $false) 'Scanner unexpectedly approved production'
Assert-UCIE ($result.approved_rules -eq 0) 'Scanner promoted a rule'

$negative = Find-UCIEPowerShellCandidate -SourceText @'
Get-Command 'Get-FuzzyDuplicat'
Resolve-Path 'directory\file.txt'
'@
Assert-UCIE ($negative.finding_count -eq 0) 'False positive for commands without candidate switches'

$inert = Find-UCIEPowerShellCandidate -SourceText @'
throw 'SHOULD_NEVER_EXECUTE'
Get-Command Get-FuzzyDuplicat -UseFuzzyMatching
'@
Assert-UCIE ($inert.finding_count -eq 1) 'Inert text parse did not inspect command'
$first = $result.source_sha256
$second = (Find-UCIEPowerShellCandidate -SourceText $source).source_sha256
Assert-UCIE ($first -ceq $second) 'Nondeterministic digest'

$badSyntax = $false
try {
    $null = Find-UCIEPowerShellCandidate -SourceText 'function broken {'
}
catch { $badSyntax = $true }
Assert-UCIE ($badSyntax) 'Invalid syntax did not fail closed'

$oversized = $false
try {
    $null = Find-UCIEPowerShellCandidate -SourceText ('x' * 131073)
}
catch { $oversized = $true }
Assert-UCIE ($oversized) 'Oversized input did not fail closed'

Write-Output 'UCIE_POWERSHELL_STATIC_TESTS=PASS_SYNTHETIC_CANDIDATE_ONLY'
