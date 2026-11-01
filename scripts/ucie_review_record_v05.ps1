# Explicit owner-only V0.5 review CLAIM intake. Never marks a rule PASS.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[0-9a-f]{64}$')][string]$ItemId,
    [Parameter(Mandatory=$true)]
    [ValidateSet('VERSION_APPLICABILITY','LICENSE','INDEPENDENT_REGRESSION','SECURITY_REVIEW')]
    [string]$Gate,
    [Parameter(Mandatory=$true)]
    [ValidateLength(20,230)][string]$EvidenceUrl,
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[0-9a-f]{64}$')][string]$ClaimedSha256,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9.+_-]{0,31}$')]
    [string]$VersionHint = 'UNDETERMINED'
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
foreach ($p in @('ucie_miner\library_review_records_v05.py',
                  'ucie_miner\library_review_v04.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $p) -PathType Leaf)) {
        throw 'UCIE_V05_MISSING_DEPENDENCY'
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_OWNER_VENV_PYTHON_REQUIRED'
}
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    $argsV05 = @('-B','-m','ucie_miner.library_review_records_v05',
        '--item-id',$ItemId,'--gate',$Gate,'--evidence-url',$EvidenceUrl,
        '--claimed-sha256',$ClaimedSha256,'--version-hint',$VersionHint,
        '--record-unverified')
    & $python @argsV05
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_PUBLIC_CLAIM_NOT_ACCEPTED' }
} finally {
    $env:PYTHONPATH = $prior
}
