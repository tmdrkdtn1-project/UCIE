# UCIE-owned inert PowerShell AST candidate scanner.
# No Invoke-Expression, scriptblock creation from input, file traversal,
# system configuration changes, external code execution or persistence.

function Find-UCIEPowerShellCandidate {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$SourceText)

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($SourceText)
    if ($bytes.Length -eq 0 -or $bytes.Length -gt 131072) {
        throw 'Invalid or oversized inert PowerShell input'
    }
    $tokens = $null
    $errors = $null
    $syntaxTree = [System.Management.Automation.Language.Parser]::ParseInput(
        $SourceText, [ref]$tokens, [ref]$errors)
    if ($errors.Count -gt 0) {
        throw 'Invalid PowerShell input syntax'
    }
    $nodes = @($syntaxTree.FindAll({ param($node) $true }, $true))
    if ($nodes.Count -gt 10000) {
        throw 'PowerShell syntax tree complexity exceeded'
    }
    $found = [System.Collections.Generic.List[object]]::new()
    foreach ($cmd in $nodes) {
        if ($cmd -isnot [System.Management.Automation.Language.CommandAst]) {
            continue
        }
        $name = $cmd.GetCommandName()
        if ([string]::IsNullOrEmpty($name)) {
            continue
        }
        $parameters = @(
            $cmd.CommandElements |
                Where-Object { $_ -is [System.Management.Automation.Language.CommandParameterAst] } |
                ForEach-Object { $_.ParameterName }
        )
        $pattern = $null
        $publicPr = $null
        $guidance = $null
        if ([string]::Equals($name, 'Get-Command',
                             [System.StringComparison]::OrdinalIgnoreCase) -and
                $parameters -contains 'UseFuzzyMatching') {
            $pattern = 'PS_FUZZY_GET_COMMAND_DUPLICATES'
            $publicPr = 'https://github.com/PowerShell/PowerShell/pull/28042'
            $guidance = 'Inspect fuzzy matches for duplicate Name/CommandType/Source identities before using results'
        }
        elseif ([string]::Equals($name, 'Resolve-Path',
                                 [System.StringComparison]::OrdinalIgnoreCase) -and
                $parameters -contains 'Relative') {
            $pattern = 'PS_RESOLVE_PATH_DOT_PREFIX'
            $publicPr = 'https://github.com/PowerShell/PowerShell/pull/28087'
            $guidance = 'Review dot-prefixed relative paths and use an anchored base-directory conversion if needed'
        }
        if ($null -eq $pattern) {
            continue
        }
        if ($found.Count -ge 100) {
            throw 'Too many candidate findings'
        }
        $found.Add([pscustomobject]@{
            pattern_code = $pattern
            line = $cmd.Extent.StartLineNumber
            column = $cmd.Extent.StartColumnNumber
            confidence = 'STATIC_HEURISTIC_REVIEW_REQUIRED'
            public_evidence = $publicPr
            safe_fix_guidance = $guidance
            runtime_bug_reproduced = $false
        })
    }

    $sourceDigest = [Convert]::ToHexString(
        [System.Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
    return [pscustomobject]@{
        schema = 'UCIE_POWERSHELL_STATIC_CANDIDATES_V1'
        source_sha256 = $sourceDigest
        finding_count = $found.Count
        findings = @($found.ToArray())
        parser_executed_supplied_code = $false
        confidence = 'HUMAN_REVIEW_REQUIRED'
        approved_rules = 0
        source_files_read = 0
        persistent_writes = 0
        production_approved = $false
    }
}
