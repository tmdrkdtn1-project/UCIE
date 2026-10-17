# UCIE-owned inert PowerShell AST candidate scanner.
# No Invoke-Expression, scriptblock creation from input, file traversal,
# system configuration changes, external code execution or persistence.

# Conservative constant-folding only. Never evaluate conditions, call
# Get-Alias, perform variable expansion or interpret the supplied script.
function Test-UCIEConstantUnreachableCommand {
    param([System.Management.Automation.Language.Ast]$Command)
    $cursor = $Command.Parent
    while ($null -ne $cursor) {
        if ($cursor -is [System.Management.Automation.Language.IfStatementAst]) {
            foreach ($clause in $cursor.Clauses) {
                $block = $clause.Item2
                $inside = ($Command.Extent.StartOffset -ge $block.Extent.StartOffset -and
                           $Command.Extent.EndOffset -le $block.Extent.EndOffset)
                if ($inside) {
                    $literal = ($clause.Item1.Extent.Text -replace '[()\s]', '').ToLowerInvariant()
                    if ($literal -in @('$false', '0')) {
                        return $true
                    }
                }
            }
        }
        $cursor = $cursor.Parent
    }
    return $false
}

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
    $definitions = @($nodes | Where-Object {
        $_ -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        -not (Test-UCIEConstantUnreachableCommand -Command $_)
    })
    foreach ($cmd in $nodes) {
        if ($cmd -isnot [System.Management.Automation.Language.CommandAst]) {
            continue
        }
        if (Test-UCIEConstantUnreachableCommand -Command $cmd) {
            continue
        }
        $name = $cmd.GetCommandName()
        if ([string]::IsNullOrEmpty($name)) {
            continue
        }
        # Explicit source-defined functions can shadow built-in commands or
        # aliases; do not falsely classify these as real Get-Command calls.
        $shadowed = @($definitions | Where-Object {
            $_.Name -ieq $name -and
            $_.Extent.StartOffset -lt $cmd.Extent.StartOffset
        })
        if ($shadowed.Count -gt 0) { continue }
        $parameters = @(
            $cmd.CommandElements |
                Where-Object { $_ -is [System.Management.Automation.Language.CommandParameterAst] } |
                ForEach-Object { $_.ParameterName }
        )
        $pattern = $null
        $publicPr = $null
        $guidance = $null
        if (($name -in @('Get-Command', 'gcm')) -and
                $parameters -contains 'UseFuzzyMatching') {
            $pattern = 'PS_FUZZY_GET_COMMAND_DUPLICATES'
            $publicPr = 'https://github.com/PowerShell/PowerShell/pull/28042'
            $guidance = 'Inspect fuzzy matches for duplicate Name/CommandType/Source identities before using results'
        }
        elseif (($name -in @('Resolve-Path', 'rvpa')) -and
                $parameters -contains 'Relative') {
            $pattern = 'PS_RESOLVE_PATH_DOT_PREFIX'
            $publicPr = 'https://github.com/PowerShell/PowerShell/pull/28087'
            $guidance = 'Review dot-prefixed relative paths and use an anchored base-directory conversion if needed'
        }
        elseif ($name -in @('python', 'python.exe', 'python3', 'python3.exe',
                             'python3.14', 'python3.15', 'py', 'py.exe')) {
            # Approved CPython PR #159014 documents a silent-no-op typo.
            # Analyze ONLY a literal -X option immediately followed by the
            # misspelled literal. Never resolve shell expressions or aliases.
            $elements = @($cmd.CommandElements)
            for ($i = 1; $i -lt ($elements.Count - 1); $i++) {
                $switch = $elements[$i]
                $arg = $elements[$i + 1]
                if ($switch -is [System.Management.Automation.Language.CommandParameterAst] -and
                    $switch.ParameterName -ceq 'X' -and
                    $arg -is [System.Management.Automation.Language.StringConstantExpressionAst] -and
                    $arg.Value -ceq 'disable_remote_debug') {
                    $pattern = 'PS_PYTHON_REMOTE_DEBUG_XOPTION_TYPO'
                    $publicPr = 'https://github.com/python/cpython/pull/159014'
                    $guidance = 'Use Python -X disable-remote-debug (hyphens), not disable_remote_debug; confirm target interpreter setting'
                    break
                }
            }
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
