# UCIE-owned candidate safe-call adapters. Never invokes a discovered command.
# Do not import or auto-promote as a production rule without separate review.

function Get-UCIEUniqueCommandResults {
    [CmdletBinding()]
    param([Parameter(Mandatory)][object[]]$Commands)
    $seen = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($command in $Commands) {
        if ($null -eq $command -or $null -eq $command.Name -or
                $null -eq $command.CommandType) {
            throw 'Invalid command-result metadata'
        }
        $module = [string]$command.Source
        $identity = ('{0}|{1}|{2}' -f [string]$command.Name,
                     [string]$command.CommandType, $module)
        if ($seen.Add($identity)) {
            Write-Output $command
        }
    }
}

function Resolve-UCIESafeRelativePath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$BaseDirectory,
        [Parameter(Mandatory)][string]$SearchPattern
    )
    $base = [System.IO.Path]::GetFullPath($BaseDirectory)
    if (-not [System.IO.Directory]::Exists($base)) {
        throw 'Base directory does not exist'
    }
    if ([System.IO.Path]::IsPathRooted($SearchPattern)) {
        throw 'Only relative, caller-reviewed glob patterns are accepted'
    }
    # Only caller-selected paths; never evaluates code from file names.
    $paths = @(Resolve-Path -Path (Join-Path $base $SearchPattern) -ErrorAction Stop)
    foreach ($entry in $paths) {
        $rel = [System.IO.Path]::GetRelativePath($base, [string]$entry.ProviderPath)
        $sep = [System.IO.Path]::DirectorySeparatorChar
        if ([System.IO.Path]::IsPathRooted($rel) -or
                $rel -eq '..' -or
                $rel.StartsWith(('..' + $sep))) {
            throw 'Resolved path escapes base directory'
        }
        Write-Output (Join-Path '.' $rel)
    }
}
