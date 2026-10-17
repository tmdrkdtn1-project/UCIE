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

# One real observed CPython security-control misconfiguration:
# the wrong underscore spelling is silently ignored on supported Python.
# Only analyze fixed PowerShell command syntax; never launch 'python'.
$wrongOption = Find-UCIEPowerShellCandidate -SourceText @'
python -I -X disable_remote_debug -c 'raise Exception("DO_NOT_EXECUTE")'
'@
Assert-UCIE ($wrongOption.finding_count -eq 1) 'Missing actual Python xoption typo finding'
Assert-UCIE ($wrongOption.findings[0].pattern_code -eq 'PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO') 'Wrong flag pattern'
Assert-UCIE ($wrongOption.findings[0].public_evidence -ceq 'https://github.com/python/cpython/pull/159014') 'Untrusted Python PR identity'
Assert-UCIE ($wrongOption.parser_executed_supplied_code -eq $false) 'Unsafe Python command execution implied'

$correctOption = Find-UCIEPowerShellCandidate -SourceText "python -I -X disable-remote-debug -"
Assert-UCIE ($correctOption.finding_count -eq 0) 'Correct Python flag must not be flagged'

$otherCommand = Find-UCIEPowerShellCandidate -SourceText "Write-Output -X disable_remote_debug"
Assert-UCIE ($otherCommand.finding_count -eq 0) 'Non-Python command was incorrectly flagged'

$dynamicOption = Find-UCIEPowerShellCandidate -SourceText 'python -X $option -'
Assert-UCIE ($dynamicOption.finding_count -eq 0) 'Dynamic PowerShell expression must remain unclassified'

$unreachableOption = Find-UCIEPowerShellCandidate -SourceText 'if ($false) { python -X disable_remote_debug - }'
Assert-UCIE ($unreachableOption.finding_count -eq 0) 'Provably dead branch should not be flagged'

$negative = Find-UCIEPowerShellCandidate -SourceText @'
Get-Command 'Get-FuzzyDuplicat'
Resolve-Path 'directory\file.txt'
'@
Assert-UCIE ($negative.finding_count -eq 0) 'False positive for commands without candidate switches'

$aliasFinding = Find-UCIEPowerShellCandidate -SourceText 'gcm Get-FuzzyDuplicat -UseFuzzyMatching'
Assert-UCIE ($aliasFinding.finding_count -eq 1) 'gcm alias candidate was missed'
Assert-UCIE ($aliasFinding.findings[0].pattern_code -eq 'PS_FUZZY_GET_COMMAND_DUPLICATES') 'Alias matched wrong pattern'

$dead = Find-UCIEPowerShellCandidate -SourceText 'if ($false) { Get-Command Get-Foo -UseFuzzyMatching }'
Assert-UCIE ($dead.finding_count -eq 0) 'Unreachable literal false branch was flagged'

$possible = Find-UCIEPowerShellCandidate -SourceText 'if ($condition) { Get-Command Get-Foo -UseFuzzyMatching }'
Assert-UCIE ($possible.finding_count -eq 1) 'Unknown condition must remain a review candidate'

$trueBranch = Find-UCIEPowerShellCandidate -SourceText 'if ($true) { gcm Get-Foo -UseFuzzyMatching }'
Assert-UCIE ($trueBranch.finding_count -eq 1) 'Literal true branch must be analyzed'

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
