# W19: owner-only reversible DISABLED three-task stage after locked data handoff.
# Never enables/stops tasks, starts LocalV1, restarts C40 or claims tunnel GO.
[CmdletBinding()]
param([switch]$Apply,[switch]$Rollback,[switch]$ContractOnly,
      [string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W19_OWNER_DATA_TASK_STAGE_V01'
$root='D:\UCIE_PROJECT\UCIE'
$old='D:\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$marker=$archive + '\.ucie_owner_runtime_opt_in_v01'
$journal=$archive + '\UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json'
$rollbackReceipt=$archive + '\UCIE_W19_OWNER_DATA_TASK_ROLLBACK_V01.json'
$privateData=$archive + '\UCIE_W19_LOCKSTEP_FINAL_DATA_V01'
$targetRuntime=$root + '\runtime'
$python=$root + '\.venv\Scripts\python.exe'
$handoff=$root + '\scripts\ucie_owner_w19_lockstep_handoff_v01.py'
$rebinder=$root + '\scripts\ucie_owner_task_rebind_v01.ps1'
$w13Journal=$archive + '\UCIE_W13_TASK_REBIND_V01.json'
$markerText='UCIE_OWNER_RELOCATED_RUNTIME_OPT_IN_V01' + [char]10
$applyApproval='AUTHORIZE_UCIE_W19_STAGED_FINAL_DATA_AND_DISABLED_TASK_REBIND'
$rollbackApproval='AUTHORIZE_UCIE_W19_RESTORE_OLD_DISABLED_TASK_ACTIONS'
$w13Approval='AUTHORIZE_UCIE_W13_THREE_TASK_MAINTENANCE_REBIND'
$w19DataApproval='AUTHORIZE_UCIE_W19_LOCKSTEP_FINAL_SQLITE_HANDOFF'
$w18Commit='853736a0c82c0c348665b6b8acb99e3c3a6d4825'
$specs=@(
    [pscustomobject]@{
        Name='UCIE-PublicMiner-Hourly'
        OldExe='D:\UCIE\.venv\Scripts\python.exe'
        OldArgs='"D:\UCIE\scripts\public_miner_cycle.py"'
        NewExe='D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe'
        NewArgs='"D:\UCIE_PROJECT\UCIE\scripts\public_miner_cycle.py" --owner-relocated-runtime'
    },
    [pscustomobject]@{
        Name='UCIE-Internal-Minute'
        OldExe='D:\UCIE\.venv\Scripts\python.exe'
        OldArgs='-B "D:\UCIE\scripts\internal_minute_tick.py"'
        NewExe='D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe'
        NewArgs='-B "D:\UCIE_PROJECT\UCIE\scripts\internal_minute_tick.py" --owner-relocated-runtime'
    },
    [pscustomobject]@{
        Name='UCIE-LocalV1-Web'
        OldExe='D:\UCIE\.venv\Scripts\pythonw.exe'
        OldArgs='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'
        NewExe='D:\UCIE_PROJECT\UCIE\.venv\Scripts\pythonw.exe'
        NewArgs='-B "D:\UCIE_PROJECT\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767 --owner-relocated-runtime'
    }
)
if (-not $Apply -and -not $Rollback) { $ContractOnly=$true }
if ($ContractOnly) {
    if ($Apply -or $Rollback) { throw 'UCIE_W19_CONTRACT_MUTATION_DENIED' }
    [pscustomobject]@{
        schema=$schema;status='UCIE_W19_CONTRACT_ONLY_NO_HOST_ACCESS'
        tasks_queried=$false;sqlite_opened=$false;marker_created=$false
        task_actions_changed=$false;c40_accessed=$false
        tasks_enabled=0;live_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if ($Apply.IsPresent -eq $Rollback.IsPresent) {
    throw 'UCIE_W19_EXACT_ONE_MODE_REQUIRED'
}
$approval=if ($Apply) {$applyApproval} else {$rollbackApproval}
if (-not [string]::Equals($OwnerApproval,$approval,[StringComparison]::Ordinal)) {
    throw 'UCIE_W19_EXPLICIT_OWNER_APPROVAL_REQUIRED'
}
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive) {
    throw 'UCIE_W19_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
function Direct([string]$path,[bool]$directory) {
    $node=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if ([bool]$node.PSIsContainer -ne $directory) {
        throw 'UCIE_W19_WRONG_PATH_TYPE'
    }
    while ($null -ne $node -and
           $node.FullName.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'UCIE_W19_REPARSE_PATH_DENIED'
        }
        if ($node -is [System.IO.FileInfo]) {$node=$node.Directory}
        else {$node=$node.Parent}
    }
}
function AssertAbsent([string]$path) {
    # Get-Item also catches dangling reparse entries which Test-Path can miss.
    $entry=Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    if ($null -ne $entry -or [IO.File]::Exists($path) -or
        [IO.Directory]::Exists($path)) {
        throw 'UCIE_W19_ALREADY_EXISTS_NO_REAPPLY'
    }
}
function ShaText([string]$value) {
    $h=[Security.Cryptography.SHA256]::Create()
    try {
        $bytes=[Text.Encoding]::UTF8.GetBytes($value)
        return [BitConverter]::ToString($h.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()
    } finally {$h.Dispose()}
}
function TaskItem([string]$name) {
    $t=Get-ScheduledTask -TaskName $name -TaskPath '\' -ErrorAction Stop
    if (@($t.Actions).Count -ne 1 -or [string]$t.State -ne 'Disabled') {
        throw 'UCIE_W19_TASK_NOT_DISABLED_SINGLE_ACTION'
    }
    $raw=[string]$t.Principal.UserId
    try {
        $sid=if ($raw -match '^S-1-[0-9-]+$') {$raw} else {
            ([Security.Principal.NTAccount]::new($raw)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
    } catch { throw 'UCIE_W19_TASK_OWNER_NOT_VERIFIED' }
    if ($sid -ne $script:ownerSid) { throw 'UCIE_W19_TASK_OWNER_MISMATCH' }
    return $t
}
function Same($action,[string]$exe,[string]$args,[string]$work) {
    return ([string]::Equals([string]$action.Execute,$exe,[StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals([string]$action.Arguments,$args,[StringComparison]::Ordinal) -and
            [string]::Equals([string]$action.WorkingDirectory,$work,[StringComparison]::OrdinalIgnoreCase))
}
function ConfirmThree([bool]$newMode) {
    foreach ($s in $specs) {
        $t=TaskItem $s.Name
        $valid=if ($newMode) {Same $t.Actions[0] $s.NewExe $s.NewArgs $root}
               else {Same $t.Actions[0] $s.OldExe $s.OldArgs $old}
        if (-not $valid) { throw 'UCIE_W19_TASK_ACTION_DRIFT_HOLD' }
    }
}
function C40Hash {
    $t=Get-ScheduledTask -TaskName 'UCIE-C40-Recover' -TaskPath '\' -ErrorAction Stop
    if (@($t.Actions).Count -ne 1) { throw 'UCIE_W19_C40_ACTION_COUNT_CHANGED' }
    $a=$t.Actions[0]
    return ShaText ((@([string]$a.Execute,[string]$a.Arguments,
                      [string]$a.WorkingDirectory)) -join [char]0)
}
function PrivateJson([string]$path,$body) {
    AssertAbsent $path
    $tmp=Join-Path $archive ('UCIE_W19_' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.File]::WriteAllText($tmp,(ConvertTo-Json $body -Depth 7 -Compress),
                               [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($tmp,$path)
    } finally {
        if (Test-Path -LiteralPath $tmp) {Remove-Item -LiteralPath $tmp -ErrorAction Stop}
    }
}
$expectedScript=Join-Path $root 'scripts\ucie_owner_w19_data_task_stage_v01.ps1'
if (-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
        $expectedScript,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_W19_EXACT_NEW_CHECKOUT_SCRIPT_REQUIRED'
}
foreach ($path in @($old,$root,$archive)) {Direct $path $true}
foreach ($path in @($python,$handoff,$rebinder,$expectedScript)) {Direct $path $false}
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
$script:ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if (-not $acl.AreAccessRulesProtected -or
    $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:ownerSid) {
    throw 'UCIE_W19_PRIVATE_OWNER_ACL_REQUIRED'
}
Import-Module ScheduledTasks -ErrorAction Stop
$priorC40=C40Hash
$prior=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    & git -C $root merge-base --is-ancestor $w18Commit HEAD 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'UCIE_W19_STAGED_GIT_ANCESTRY_HOLD'}
} finally {$env:GIT_OPTIONAL_LOCKS=$prior}
if ($Apply) {
    ConfirmThree $false
    foreach ($path in @($marker,$journal,$w13Journal,$privateData,$targetRuntime)) {
        AssertAbsent $path
    }
    # A private recovery journal is persisted BEFORE opening operating SQLite.
    PrivateJson $journal ([ordered]@{
        schema=$schema;status='UCIE_W19_OWNER_STAGE_STARTED_NOT_LIVE'
        owner_sid_sha256=(ShaText $script:ownerSid)
        old_root=$old;new_root=$root;c40_action_sha256=$priorC40
        task_names=@($specs | ForEach-Object {$_.Name})
        task_actions_initial='THREE_ORIGINAL_DISABLED'
        tasks_enabled=0;sqlite_handoff_completed=$false
        rollback_requires_disabled_tasks=$true
    })
    # Direct host invocation preserves stdin TTY; piping to Out-String
    # can make Python's interactive owner gate fail on Windows PowerShell.
    & $python -I -B $handoff --prepare --owner-approval $w19DataApproval
    if ($LASTEXITCODE -ne 0) {
        throw 'UCIE_W19_FINAL_HANDOFF_FAILED_PRESERVE_PARTIAL_NO_RETRY'
    }
    $privateManifest=Join-Path $privateData 'private_handoff_manifest.json'
    Direct $privateManifest $false
    $handoffReceipt=Get-Content -LiteralPath $privateManifest -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($handoffReceipt.schema -ne 'UCIE_W19_OWNER_LOCKSTEP_SQLITE_HANDOFF_V01' -or
        $handoffReceipt.status -ne 'UCIE_W19_ALL_SQLITE_WRITER_LOCKS_HELD_DURING_HANDOFF' -or
        @($handoffReceipt.dbs).Count -ne 10 -or
        $handoffReceipt.sqlite_writer_barrier_held -ne $true -or
        $handoffReceipt.tasks_rebound_or_enabled -ne $false -or
        $handoffReceipt.c40_tunnel_health_verified -ne $false -or
        $handoffReceipt.live_cutover_authorized -ne $false) {
        throw 'UCIE_W19_DATA_RECEIPT_NOT_ACCEPTED'
    }
    ConfirmThree $false
    if ((C40Hash) -ne $priorC40) {throw 'UCIE_W19_C40_ACTION_DRIFT'}
    AssertAbsent $marker
    [IO.File]::WriteAllBytes($marker,[Text.Encoding]::ASCII.GetBytes($markerText))
    & powershell.exe -NoProfile -NonInteractive -File $rebinder -Apply -OwnerApproval $w13Approval
    if ($LASTEXITCODE -ne 0) {
        throw 'UCIE_W19_W13_APPLY_FAILED_USE_OWNER_ROLLBACK_REVIEW'
    }
    Direct $w13Journal $false
    ConfirmThree $true
    if ((C40Hash) -ne $priorC40) {throw 'UCIE_W19_C40_ACTION_DRIFT'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W19_THREE_TASKS_REBOUND_DISABLED__LIVE_ACTIVATION_HOLD'
        final_sqlite_count=10;sqlite_writer_barrier_held=$true
        tasks_rebound_disabled=3;tasks_enabled=0;c40_action_unchanged=$true
        c40_tunnel_live_health_verified=$false
        rollback_journals_preserved=$true;old_runtime_preserved=$true
        live_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
# Rollback restores only old task actions and removes ONLY this exact W19
# opt-in marker; leaves old data and both private/new snapshots preserved.
Direct $journal $false
Direct $w13Journal $false
Direct $marker $false
if (Test-Path -LiteralPath $rollbackReceipt) {
    throw 'UCIE_W19_ROLLBACK_ALREADY_RECORDED'
}
$record=Get-Content -LiteralPath $journal -Encoding UTF8 -Raw | ConvertFrom-Json
if ($record.schema -ne $schema -or $record.old_root -ne $old -or
    $record.new_root -ne $root -or
    $record.owner_sid_sha256 -ne (ShaText $script:ownerSid) -or
    $record.c40_action_sha256 -ne $priorC40 -or
    @($record.task_names).Count -ne 3) {
    throw 'UCIE_W19_ROLLBACK_JOURNAL_MISMATCH'
}
foreach ($i in 0..2) {
    if ($record.task_names[$i] -ne $specs[$i].Name) {
        throw 'UCIE_W19_ROLLBACK_TASK_NAME_MISMATCH'
    }
}
$bytes=[IO.File]::ReadAllBytes($marker)
$expected=[Text.Encoding]::ASCII.GetBytes($markerText)
if ($bytes.Length -ne $expected.Length) {throw 'UCIE_W19_OWNER_MARKER_DRIFT'}
for ($i=0;$i -lt $bytes.Length;$i++) {
    if ($bytes[$i] -ne $expected[$i]) {throw 'UCIE_W19_OWNER_MARKER_DRIFT'}
}
# W13 rollback independently checks Disabled task owners and C40 hash.
& powershell.exe -NoProfile -NonInteractive -File $rebinder -Rollback -OwnerApproval $w13Approval
if ($LASTEXITCODE -ne 0) {
    throw 'UCIE_W19_W13_ROLLBACK_FAILED_MANUAL_REVIEW'
}
ConfirmThree $false
if ((C40Hash) -ne $priorC40) {throw 'UCIE_W19_C40_ACTION_DRIFT'}
Remove-Item -LiteralPath $marker -Force -ErrorAction Stop
PrivateJson $rollbackReceipt ([ordered]@{
    schema=$schema;status='UCIE_W19_DISABLED_TASK_ACTION_ROLLBACK_RECORDED'
    tasks_restored=3;c40_action_unchanged=$true;marker_removed=$true
    new_sqlite_data_retained=$true;original_sqlite_not_replaced=$true
    live_cutover_authorized=$false
})
[pscustomobject]@{
    schema=$schema;status='UCIE_W19_OLD_THREE_TASK_ACTIONS_RESTORED_DISABLED'
    tasks_restored=3;tasks_enabled=0;c40_action_unchanged=$true
    new_root_data_preserved_for_review=$true
    live_cutover_authorized=$false
} | ConvertTo-Json -Compress
