# Trusted UCIE-owned stdin adapter; source bytes are always data for AST ParseInput.
# Never dot-source or invoke code from supplied stdin, no file discovery/writes.
$ErrorActionPreference = 'Stop'
try {
    $source = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrEmpty($source) -or
        [System.Text.Encoding]::UTF8.GetByteCount($source) -gt 16384) {
        throw 'UCIE_SOURCE_REJECTED'
    }
    . (Join-Path $PSScriptRoot 'ucie_powershell_static_candidates.ps1')
    $result = Find-UCIEPowerShellCandidate -SourceText $source
    if ($null -eq $result) { throw 'UCIE_RECEIPT_MISSING' }
    [Console]::Out.WriteLine((ConvertTo-Json -InputObject $result -Depth 6 -Compress))
} catch {
    [Console]::Error.WriteLine('UCIE_POWERSHELL_AST_SCAN_REJECTED')
    exit 2
}
