# UCIE V0.8-V0.9: explicit public evidence source re-check on owner Windows PC.
[CmdletBinding()]
param(
    [ValidateRange(1,5)][int]$Top = 5,
    [ValidatePattern('^[0-9a-f]{64}$')][string]$ItemId
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_OWNER_ROOT_REQUIRED'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
$src = Join-Path $root 'src'
foreach ($p in @(
    'ucie_miner\library_public_probe_v08.py',
    'ucie_miner\library_public_proof_v09.py',
    'ucie_miner\library_audit_v07.py'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $src $p) -PathType Leaf)) {
        throw 'UCIE_PUBLIC_PROOF_MODULE_MISSING'
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'UCIE_OWNER_PYTHON_NOT_FOUND'
}
$prior = $env:PYTHONPATH
try {
    $env:PYTHONPATH = $src
    $params = @('-B','-m','ucie_miner.library_public_proof_v09','--check-public','--top',[string]$Top)
    if ($PSBoundParameters.ContainsKey('ItemId')) {
        $params += @('--item-id', $ItemId)
    }
    & $python @params
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_PUBLIC_SOURCE_PROOF_NO_GO' }
} finally {
    $env:PYTHONPATH = $prior
}
