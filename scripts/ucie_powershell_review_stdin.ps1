# Trusted UCIE-owned stdin adapter; source bytes are always data for AST ParseInput.
# Never dot-source or invoke code from supplied stdin, no file discovery/writes.
$ErrorActionPreference = 'Stop'
try {
    # Read raw stdin bytes before any console codepage can transform Korean,
    # non-BMP Unicode or CRLF. Windows PowerShell 5.1 Console.In may decode
    # redirected input using an OEM codepage instead of UTF-8.
    $inputStream = [Console]::OpenStandardInput()
    $memory = New-Object System.IO.MemoryStream
    [byte[]]$buffer = New-Object byte[] 4096
    try {
        while ($true) {
            # Read at most MAX+1 bytes, even when the caller invokes this
            # adapter directly and bypasses the Python CLI's 16-KiB limit.
            $remaining = 16385 - [int]$memory.Length
            if ($remaining -le 0) { throw 'UCIE_SOURCE_REJECTED' }
            $count = $inputStream.Read($buffer, 0,
                [Math]::Min($buffer.Length, $remaining))
            if ($count -eq 0) { break }
            $memory.Write($buffer, 0, $count)
            if ($memory.Length -gt 16384) { throw 'UCIE_SOURCE_REJECTED' }
        }
        $bytes = $memory.ToArray()
    } finally {
        $memory.Dispose()
        $inputStream.Dispose()
    }
    if ($bytes.Length -eq 0) { throw 'UCIE_SOURCE_REJECTED' }
    # Reject malformed/overlong UTF-8 rather than silently substituting
    # replacement glyphs and accepting a changed source SHA-256.
    $source = ([System.Text.UTF8Encoding]::new($false, $true)).GetString($bytes)
    . (Join-Path $PSScriptRoot 'ucie_powershell_static_candidates.ps1')
    $result = Find-UCIEPowerShellCandidate -SourceText $source
    if ($null -eq $result) { throw 'UCIE_RECEIPT_MISSING' }
    [Console]::Out.WriteLine((ConvertTo-Json -InputObject $result -Depth 6 -Compress))
} catch {
    [Console]::Error.WriteLine('UCIE_POWERSHELL_AST_SCAN_REJECTED')
    exit 2
}
