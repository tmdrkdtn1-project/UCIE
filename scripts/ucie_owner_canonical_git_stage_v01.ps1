# W15: UCIE-only reversible canonical Git staging. Default: no host access.
[CmdletBinding()]
param([switch]$Apply,[switch]$Rollback,[string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W15_CANONICAL_GIT_STAGE_V01'
$parent='D:\UCIE_PROJECT'
$target=Join-Path $parent 'UCIE'
$archive=Join-Path $parent 'ARCHIVE'
$preserved=Join-Path $archive 'UCIE_W15_ORIGINAL_CODE_STAGE_V01'
$scratch=Join-Path $parent '_UCIE_W15_PUBLIC_MAIN_PREP_V01'
$journal=Join-Path $archive 'UCIE_W15_CANONICAL_GIT_JOURNAL_V01.json'
$receipt=Join-Path $archive 'UCIE_W15_CANONICAL_GIT_STAGE_RECEIPT_V01.json'
$marker=Join-Path $archive '.ucie_owner_runtime_opt_in_v01'
$remote='https://github.com/tmdrkdtn1-project/UCIE.git'
$requiredAncestor='3515c14f5c82202ea13eac7b5a3e94fbb7ac94b9'
$taskNames=@('UCIE-PublicMiner-Hourly','UCIE-Internal-Minute','UCIE-LocalV1-Web','UCIE-C40-Recover')

if (-not $Apply -and -not $Rollback) {
    [pscustomobject]@{
        schema=$schema;status='UCIE_W15_CONTRACT_ONLY_NO_HOST_ACCESS'
        code_only_stage_moved=$false;network_used=$false
        live_git_tasks_c40_sqlite_modified=$false;live_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if ($Apply.IsPresent -eq $Rollback.IsPresent) { throw 'UCIE_W15_EXACT_ONE_MODE_REQUIRED' }
$required=if ($Apply) {'AUTHORIZE_UCIE_W15_CANONICAL_STAGE_SWAP'} else {'AUTHORIZE_UCIE_W15_CANONICAL_STAGE_ROLLBACK'}
if ($OwnerApproval -cne $required) { throw 'UCIE_W15_EXPLICIT_OWNER_APPROVAL_REQUIRED' }
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive) {
    throw 'UCIE_W15_INTERACTIVE_OWNER_WINDOWS_REQUIRED'
}
function Direct([string]$path,[bool]$folder) {
    $item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if ([bool]$item.PSIsContainer -ne $folder) { throw 'UCIE_W15_PATH_TYPE_MISMATCH' }
    # Get-Item returns FileInfo for receipt/script files. FileInfo has
    # Directory, not Parent; DirectoryInfo has Parent (Windows PS 5.1).
    $node=$item
    while ($null -ne $node) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'UCIE_W15_REPARSE_PATH_DENIED'
        }
        if ($node -is [System.IO.FileInfo]) {
            $node=$node.Directory
        } else {
            $node=$node.Parent
        }
    }
}
function Absent([string]$path) {
    if (Test-Path -LiteralPath $path) { throw 'UCIE_W15_PREEXISTING_STATE_NO_OVERWRITE' }
}
function Archive {
    Direct $parent $true
    Direct $archive $true
    $acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
    $who=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
    if (-not $acl.AreAccessRulesProtected -or $owner -ne $who) {
        throw 'UCIE_W15_PRIVATE_ARCHIVE_ACL_REQUIRED'
    }
}
function NoTaskPointsAtTarget {
    Import-Module ScheduledTasks -ErrorAction Stop
    foreach ($name in $taskNames) {
        $task=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
        foreach ($action in @($task.Actions)) {
            foreach ($field in @([string]$action.Execute,[string]$action.Arguments,
                                 [string]$action.WorkingDirectory)) {
                if ($field.IndexOf($target,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
                    throw 'UCIE_W15_TASK_ALREADY_BOUND_NEW_ROOT'
                }
            }
        }
    }
}
function NoRuntime([string]$root) {
    foreach ($path in @((Join-Path $root '.venv'),(Join-Path $root 'runtime'),$marker)) {
        if (Test-Path -LiteralPath $path) { throw 'UCIE_W15_RUNTIME_OR_MARKER_PRESENT' }
    }
}
function OriginalStage([string]$root) {
    Direct $root $true
    foreach ($p in @('.git','.venv','runtime')) {
        if (Test-Path -LiteralPath (Join-Path $root $p)) {
            throw 'UCIE_W15_NOT_CODE_ONLY_STAGE'
        }
    }
    $sourceReceipt=Join-Path $root 'UCIE_CODE_ONLY_STAGE_VERIFIED_V01.json'
    Direct $sourceReceipt $false
    $r=Get-Content -LiteralPath $sourceReceipt -Encoding UTF8 -Raw | ConvertFrom-Json
    if ($r.schema -ne 'UCIE_PR305_OWNER_CODE_ONLY_STAGE_ONCE_V01' -or
        $r.status -ne 'UCIE_CODE_ONLY_STAGE_232_FILES_VERIFIED__LIVE_CUTOVER_NO_GO' -or
        $r.verified_files -ne 232 -or $r.destination_written -ne $true -or
        $r.live_cutover_authorized -ne $false) {
        throw 'UCIE_W15_OLD_STAGE_RECEIPT_MISMATCH'
    }
    return (Get-FileHash -LiteralPath $sourceReceipt -Algorithm SHA256).Hash.ToLowerInvariant()
}
function GitRead([string]$root,[string[]]$argv) {
    $out=(& git -C $root @argv 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_W15_GIT_QUERY_FAILED' }
    return $out
}
function MainRoot([string]$root) {
    Direct $root $true
    Direct (Join-Path $root '.git') $true
    if ((GitRead $root @('branch','--show-current')) -cne 'main' -or
        (GitRead $root @('remote','get-url','origin')) -cne $remote -or
        (GitRead $root @('status','--porcelain=v1','--untracked-files=all')).Length -ne 0) {
        throw 'UCIE_W15_UNEXPECTED_PUBLIC_MAIN_REPOSITORY'
    }
    $head=GitRead $root @('rev-parse','HEAD')
    if ($head -cnotmatch '^[0-9a-f]{40}$') { throw 'UCIE_W15_INVALID_HEAD' }
    & git -C $root merge-base --is-ancestor $requiredAncestor HEAD 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'UCIE_W15_REQUIRED_W14_ANCESTOR_MISSING' }
    return $head
}
function SaveJson([string]$path,[object]$value) {
    Absent $path
    $temp=Join-Path $archive ('UCIE_W15_' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.File]::WriteAllText($temp,(ConvertTo-Json $value -Depth 5 -Compress),
                               [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temp,$path)
    } finally {
        if (Test-Path -LiteralPath $temp) {
            Remove-Item -LiteralPath $temp -ErrorAction Stop
        }
    }
}

Archive
NoTaskPointsAtTarget
$git=Get-Command git -ErrorAction Stop
$previousPrompt=$env:GIT_TERMINAL_PROMPT
$previousLocks=$env:GIT_OPTIONAL_LOCKS
$previousSmudge=$env:GIT_LFS_SKIP_SMUDGE
$env:GIT_TERMINAL_PROMPT='0'
$env:GIT_OPTIONAL_LOCKS='0'
$env:GIT_LFS_SKIP_SMUDGE='1'
try {
    if ($Apply) {
        Direct $target $true
        NoRuntime $target
        $sourceHash=OriginalStage $target
        foreach ($p in @($scratch,$preserved,$journal,$receipt)) { Absent $p }
        # Approved public UCIE main only, retain full first-party main ancestry.
        & $git.Source -c core.hooksPath=NUL -c credential.helper= clone -q --no-tags --single-branch --branch main -- $remote $scratch *> $null
        if ($LASTEXITCODE -ne 0) { throw 'UCIE_W15_PUBLIC_CLONE_FAILED_HOLD' }
        $head=MainRoot $scratch
        NoRuntime $scratch
        SaveJson $journal ([ordered]@{
            schema=$schema;status='UCIE_W15_PRE_SWAP_JOURNAL'
            public_main_sha=$head;code_only_receipt_sha256=$sourceHash
            original_code_stage_preserved=$false;task_or_c40_modified=$false
        })
        $movedOld=$false;$movedNew=$false
        try {
            Move-Item -LiteralPath $target -Destination $preserved -ErrorAction Stop
            $movedOld=$true
            Move-Item -LiteralPath $scratch -Destination $target -ErrorAction Stop
            $movedNew=$true
            if ((MainRoot $target) -cne $head -or
                (OriginalStage $preserved) -cne $sourceHash) {
                throw 'UCIE_W15_POST_MOVE_SOURCE_MISMATCH'
            }
            $result=[ordered]@{
                schema=$schema;status='UCIE_W15_CANONICAL_GIT_STAGE_READY_NO_RUNTIME'
                public_main_sha=$head;preserved_code_only_stage=$true
                source_only_git_root=$true;public_network_clone_used=$true
                live_git_tasks_c40_sqlite_modified=$false
                new_runtime_or_venv_created=$false;live_cutover_authorized=$false
            }
            SaveJson $receipt $result
        } catch {
            $restored=$false
            try {
                if ($movedNew -and (Test-Path -LiteralPath $target) -and
                    -not (Test-Path -LiteralPath $scratch)) {
                    Move-Item -LiteralPath $target -Destination $scratch -ErrorAction Stop
                }
                if ($movedOld -and (Test-Path -LiteralPath $preserved) -and
                    -not (Test-Path -LiteralPath $target)) {
                    Move-Item -LiteralPath $preserved -Destination $target -ErrorAction Stop
                }
                $restored=([bool](Test-Path -LiteralPath $target) -and
                           -not (Test-Path -LiteralPath $preserved))
            } catch { $restored=$false }
            if (-not $restored) { throw 'UCIE_W15_PARTIAL_SWAP_MANUAL_RECOVERY_REQUIRED' }
            throw 'UCIE_W15_SWAP_ABORTED_ORIGINAL_STAGE_RESTORED'
        }
        $result | ConvertTo-Json -Compress
        return
    }
    Direct $target $true
    NoRuntime $target
    Absent $scratch
    Direct $preserved $true
    Direct $journal $false
    Direct $receipt $false
    $j=Get-Content -LiteralPath $journal -Raw -Encoding UTF8 | ConvertFrom-Json
    $r=Get-Content -LiteralPath $receipt -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($j.schema -ne $schema -or $r.schema -ne $schema -or
        $j.status -ne 'UCIE_W15_PRE_SWAP_JOURNAL' -or
        $r.status -ne 'UCIE_W15_CANONICAL_GIT_STAGE_READY_NO_RUNTIME' -or
        $j.public_main_sha -cne $r.public_main_sha -or
        (MainRoot $target) -cne $j.public_main_sha -or
        (OriginalStage $preserved) -cne $j.code_only_receipt_sha256) {
        throw 'UCIE_W15_ROLLBACK_CONTRACT_MISMATCH'
    }
    Move-Item -LiteralPath $target -Destination $scratch -ErrorAction Stop
    try {
        Move-Item -LiteralPath $preserved -Destination $target -ErrorAction Stop
    } catch {
        if (-not (Test-Path -LiteralPath $target)) {
            Move-Item -LiteralPath $scratch -Destination $target -ErrorAction Stop
        }
        throw 'UCIE_W15_ROLLBACK_FAILED_RECOVERY_REQUIRES_REVIEW'
    }
    [pscustomobject]@{
        schema=$schema;status='UCIE_W15_ORIGINAL_CODE_STAGE_RESTORED'
        canonical_public_clone_retained_in_scratch=$true
        live_git_tasks_c40_sqlite_modified=$false
        live_cutover_authorized=$false
    } | ConvertTo-Json -Compress
} finally {
    $env:GIT_TERMINAL_PROMPT=$previousPrompt
    $env:GIT_OPTIONAL_LOCKS=$previousLocks
    $env:GIT_LFS_SKIP_SMUDGE=$previousSmudge
}
