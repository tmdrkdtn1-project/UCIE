# UCIE W14 offline owner runtime preparation. Not live cutover.
# Runs ONLY in exact staged owner checkout. Never reads operating DB or Task/C40.
[CmdletBinding()]
param([switch]$Prepare,[string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W14_OFFLINE_RUNTIME_V01'
$root='D:\UCIE_PROJECT\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$wheelhouse=Join-Path $archive 'UCIE_W14_OWNER_APPROVED_WHEELS'
$wheelManifest=Join-Path $wheelhouse 'UCIE_W14_WHEEL_SHA256_V01.json'
$receipt=Join-Path $archive 'UCIE_W14_OFFLINE_RUNTIME_RECEIPT_V01.json'
$venv=Join-Path $root '.venv'
$py=Join-Path $venv 'Scripts\python.exe'
$approval='AUTHORIZE_UCIE_W14_OFFLINE_VENV_PREPARATION'
$w13Commit='0f6f44f2bcfdfc27414fe39602ad5d28dedd1b25'

if (-not $Prepare) {
    [pscustomobject]@{
        schema=$schema
        status='UCIE_W14_CONTRACT_ONLY_NO_HOST_CHANGES'
        operating_root_modified=$false
        operating_sqlite_opened=$false
        network_requested=$false
        c40_or_task_changed=$false
        new_environment_created=$false
        owner_runtime_data_migrated=$false
        live_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if ($OwnerApproval -cne $approval) {
    throw 'UCIE_W14_EXPLICIT_OWNER_OFFLINE_PREP_APPROVAL_REQUIRED'
}
if (-not [Environment]::UserInteractive -or $env:OS -ne 'Windows_NT') {
    throw 'UCIE_W14_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
$expectedScript=Join-Path $root 'scripts\ucie_owner_offline_runtime_prepare_v01.ps1'
if (-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
        $expectedScript,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_W14_EXACT_STAGED_SCRIPT_PATH_REQUIRED'
}
function Assert-Direct([string]$path,[bool]$directory) {
    $item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if ([bool]$item.PSIsContainer -ne $directory) {
        throw 'UCIE_W14_PATH_TYPE_MISMATCH'
    }
    $node=$item
    while ($null -ne $node) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'UCIE_W14_REPARSE_PATH_DENIED'
        }
        if ($node -is [System.IO.FileInfo]) {
            $node=$node.Directory
        } else {
            $node=$node.Parent
        }
    }
}
Assert-Direct 'D:\UCIE_PROJECT' $true
Assert-Direct $root $true
Assert-Direct $archive $true
Assert-Direct $wheelhouse $true
Assert-Direct $wheelManifest $false
Assert-Direct $expectedScript $false
Assert-Direct (Join-Path $root '.git') $true
Assert-Direct (Join-Path $root 'src\ucie_miner') $true
Assert-Direct (Join-Path $root 'scripts\ucie_owner_root_gate_v01.py') $false
Assert-Direct (Join-Path $root 'scripts\ucie_owner_task_rebind_v01.ps1') $false
Assert-Direct (Join-Path $root 'src\ucie_miner\local_v1_app_v01.py') $false

$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
$who=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
if (-not $acl.AreAccessRulesProtected -or $owner -ne $who) {
    throw 'UCIE_W14_PRIVATE_ARCHIVE_OWNER_ACL_REQUIRED'
}
if ((Test-Path -LiteralPath $venv) -or (Test-Path -LiteralPath $receipt)) {
    throw 'UCIE_W14_ALREADY_PARTIALLY_OR_FULLY_PREPARED_NO_OVERWRITE'
}

# The only source update is performed separately in the clean staged checkout,
# by the owner. Do not fetch, pull, switch branch or clean any Git repository.
$previousLock=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    $head=(& git -C $root rev-parse HEAD 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $head -notmatch '^[0-9a-f]{40}$') {
        throw 'UCIE_W14_GIT_HEAD_UNVERIFIED'
    }
    $branch=(& git -C $root branch --show-current 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') {
        throw 'UCIE_W14_CANONICAL_MAIN_BRANCH_REQUIRED'
    }
    & git -C $root merge-base --is-ancestor $w13Commit HEAD 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_W14_W13_ANCESTRY_MISSING' }
    $dirty=(& git -C $root status --porcelain --untracked-files=no 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $dirty.Length -gt 0) {
        throw 'UCIE_W14_TRACKED_SOURCE_NOT_CLEAN'
    }
} finally { $env:GIT_OPTIONAL_LOCKS=$previousLock }

# Only owner-curated, SHA-pinned local wheels may execute. No PyPI/network,
# no dynamic package source builds and no private wheel names in receipts.
$manifest=Get-Content -LiteralPath $wheelManifest -Raw -Encoding UTF8 | ConvertFrom-Json
$wheels=@($manifest.wheels)
if ($manifest.schema -ne 'UCIE_W14_WHEEL_SHA256_V01' -or
    $wheels.Count -lt 1 -or $wheels.Count -gt 30) {
    throw 'UCIE_W14_WHEEL_MANIFEST_INVALID'
}
$all=@(Get-ChildItem -LiteralPath $wheelhouse -Force)
if ($all.Count -ne $wheels.Count+1) {
    throw 'UCIE_W14_WHEELHOUSE_UNLISTED_FILE_OR_SUBDIRECTORY'
}
$seen=@{}
foreach ($row in $wheels) {
    $name=[string]$row.name
    if ($name -cnotmatch '^[A-Za-z0-9][A-Za-z0-9_.+-]{0,180}\.whl$' -or
        $seen.ContainsKey($name) -or
        [string]$row.sha256 -cnotmatch '^[a-f0-9]{64}$' -or
        [long]$row.bytes -le 0 -or [long]$row.bytes -gt 134217728) {
        throw 'UCIE_W14_WHEEL_MANIFEST_ENTRY_INVALID'
    }
    $seen[$name]=$true
    $wheel=Join-Path $wheelhouse $name
    Assert-Direct $wheel $false
    $item=Get-Item -LiteralPath $wheel -Force -ErrorAction Stop
    if ($item.Length -ne [long]$row.bytes -or
        (Get-FileHash -LiteralPath $wheel -Algorithm SHA256).Hash.ToLowerInvariant() -cne [string]$row.sha256) {
        throw 'UCIE_W14_UNTRUSTED_WHEEL_HASH_OR_LENGTH'
    }
}
foreach ($item in $all) {
    if ($item.Name -eq 'UCIE_W14_WHEEL_SHA256_V01.json') { continue }
    if (-not $seen.ContainsKey($item.Name)) {
        throw 'UCIE_W14_WHEELHOUSE_EXTRA_FILE'
    }
}

$launcher=Get-Command py -ErrorAction Stop
$version=(& $launcher.Source -3.15 --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $version.StartsWith('Python 3.15')) {
    throw 'UCIE_W14_PYTHON_315_NOT_AVAILABLE'
}

# Single owner-controlled mutation: create a fresh venv in the new location.
# If creation/install fails, preserve the partial venv for review; do not
# delete/retry it or touch the operating D:\UCIE venv.
& $launcher.Source -3.15 -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'UCIE_W14_VENV_CREATE_FAILED_HOLD' }
Assert-Direct $py $false
Assert-Direct (Join-Path $venv 'Scripts\pythonw.exe') $false
$actualVersion=(& $py -I -B --version 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or -not $actualVersion.StartsWith('Python 3.15')) {
    throw 'UCIE_W14_VENV_PYTHON_VERSION_FAILED_HOLD'
}

# No index access and no source distributions. Install only local wheels.
$dependencies=@('setuptools>=68','cryptography>=50.0.2,<51')
& $py -I -B -m pip install --no-index --no-cache-dir --disable-pip-version-check --only-binary ':all:' --find-links $wheelhouse @dependencies *> $null
if ($LASTEXITCODE -ne 0) { throw 'UCIE_W14_OFFLINE_WHEEL_INSTALL_FAILED_HOLD' }
& $py -I -B -m pip check *> $null
if ($LASTEXITCODE -ne 0) { throw 'UCIE_W14_DEPENDENCY_CHECK_FAILED_HOLD' }
$probe="import sys;sys.path.insert(0,r'D:\UCIE_PROJECT\UCIE\src');import cryptography;import ucie_miner.local_v1_app_v01;print('UCIE_W14_OFFLINE_IMPORT_OK')"
$result=(& $py -I -B -c $probe 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $result -ne 'UCIE_W14_OFFLINE_IMPORT_OK') {
    throw 'UCIE_W14_OFFLINE_LOCAL_APP_IMPORT_FAILED_HOLD'
}
# No runtime/SQLite or W12 owner opt-in marker is created by this tool.
$receiptData=[ordered]@{
    schema=$schema;status='UCIE_W14_ISOLATED_OFFLINE_PYTHON_RUNTIME_PREPARED'
    git_head=$head;python_version=$actualVersion
    local_wheel_count=$wheels.Count;offline_dependency_import_ok=$true
    operating_root_modified=$false;operating_sqlite_opened=$false
    c40_or_task_changed=$false;runtime_database_migrated=$false
    owner_runtime_opt_in_marker_created=$false
    python_tasks_started=0;live_cutover_authorized=$false
}
$temp=Join-Path $archive ('UCIE_W14_' + [guid]::NewGuid().ToString('N') + '.tmp')
try {
    [IO.File]::WriteAllText($temp,(ConvertTo-Json $receiptData -Compress -Depth 4),
                           [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($temp,$receipt)
} finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -ErrorAction Stop }
}
$receiptData | ConvertTo-Json -Compress -Depth 4
