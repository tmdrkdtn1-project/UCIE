# UCIE W21 owner-only ONE maintenance: W19 data+disabled rebind, W20 LocalV1.
# Never enables PublicMiner/InternalMinute, touches C40 tunnel, overwrites DB.
[CmdletBinding()]
param([switch]$ContractOnly,[switch]$ApplyLocal,[switch]$RollbackLocal,
      [string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W21_OWNER_SINGLE_LOCAL_MAINTENANCE_V01'
$old='D:\UCIE'
$root='D:\UCIE_PROJECT\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
# Concatenation protects contract-only on Linux without D: drive.
$path=$root+'\scripts\ucie_owner_w21_single_local_maintenance_v01.ps1'
$w19=$root+'\scripts\ucie_owner_w19_data_task_stage_v01.ps1'
$w20=$root+'\scripts\ucie_owner_w20_local_pilot_v01.ps1'
$w19Journal=$archive+'\UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json'
$w13Journal=$archive+'\UCIE_W13_TASK_REBIND_V01.json'
$w20Journal=$archive+'\UCIE_W20_LOCAL_PILOT_JOURNAL_V01.json'
$w20Rollback=$archive+'\UCIE_W20_LOCAL_PILOT_ROLLBACK_V01.json'
$w19Rollback=$archive+'\UCIE_W19_OWNER_DATA_TASK_ROLLBACK_V01.json'
$marker=$archive+'\.ucie_owner_runtime_opt_in_v01'
$journal=$archive+'\UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01.json'
$rollbackReceipt=$archive+'\UCIE_W21_LOCAL_MAINTENANCE_ROLLBACK_V01.json'
$privateData=$archive+'\UCIE_W19_LOCKSTEP_FINAL_DATA_V01'
$targetRuntime=$root+'\runtime'
$c40='UCIE-C40-Recover'
$base='5a996565b828e88dfd3dffa78662bb6182e6c5ec'
$applyApproval='AUTHORIZE_UCIE_W21_SINGLE_FINAL_DATA_AND_LOCALV1_MAINTENANCE'
$rollbackApproval='AUTHORIZE_UCIE_W21_SINGLE_LOCAL_MAINTENANCE_ROLLBACK'
$w19Approval='AUTHORIZE_UCIE_W19_STAGED_FINAL_DATA_AND_DISABLED_TASK_REBIND'
$w19RollbackApproval='AUTHORIZE_UCIE_W19_RESTORE_OLD_DISABLED_TASK_ACTIONS'
$w20Approval='AUTHORIZE_UCIE_W20_OWNER_LOCALV1_PILOT_ONLY'
$w20RollbackApproval='AUTHORIZE_UCIE_W20_OWNER_LOCALV1_ROLLBACK'
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
if (-not $ApplyLocal -and -not $RollbackLocal) {$ContractOnly=$true}
if ($ContractOnly) {
    if ($ApplyLocal -or $RollbackLocal) {throw 'UCIE_W21_CONTRACT_MUTATION_DENIED'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W21_CONTRACT_ONLY_NO_HOST_ACCESS'
        owner_sqlite_opened=$false;tasks_queried=$false
        c40_task_queried=$false;localv1_started=$false
        writer_tasks_enabled=0;journal_written=$false
        full_live_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if ($ApplyLocal.IsPresent -eq $RollbackLocal.IsPresent) {
    throw 'UCIE_W21_EXACT_ONE_OWNER_OPERATION_REQUIRED'
}
$required=if($ApplyLocal){$applyApproval}else{$rollbackApproval}
if (-not [string]::Equals($OwnerApproval,$required,[StringComparison]::Ordinal)) {
    throw 'UCIE_W21_EXPLICIT_OWNER_MAINTENANCE_APPROVAL_REQUIRED'
}
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive) {
    throw 'UCIE_W21_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
function Direct([string]$p,[bool]$directory) {
    $node=Get-Item -LiteralPath $p -Force -ErrorAction Stop
    if ([bool]$node.PSIsContainer -ne $directory) {
        throw 'UCIE_W21_PATH_TYPE_MISMATCH'
    }
    while ($null -ne $node -and
           $node.FullName.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'UCIE_W21_REPARSE_PATH_DENIED'
        }
        if ($node -is [System.IO.FileInfo]) {$node=$node.Directory}
        else {$node=$node.Parent}
    }
}
function Absent([string]$p) {
    $item=Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    if ($null -ne $item -or [IO.File]::Exists($p) -or
        [IO.Directory]::Exists($p)) {throw 'UCIE_W21_EXISTING_OUTPUT_NO_RETRY'}
}
function HashText([string]$v) {
    $hash=[Security.Cryptography.SHA256]::Create()
    try {
        $bytes=[Text.Encoding]::UTF8.GetBytes($v)
        return [BitConverter]::ToString($hash.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()
    } finally {$hash.Dispose()}
}
function SavePrivate([string]$dest,$value) {
    Absent $dest
    $temp=$archive+'\UCIE_W21_'+[guid]::NewGuid().ToString('N')+'.tmp'
    try {
        [IO.File]::WriteAllText($temp,(ConvertTo-Json $value -Depth 6 -Compress),
                               [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temp,$dest)
    } finally {
        if (Test-Path -LiteralPath $temp) {
            Remove-Item -LiteralPath $temp -ErrorAction Stop
        }
    }
}
function GetOwnerTask([string]$name) {
    $task=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
    if (@($task.Actions).Count -ne 1) {throw 'UCIE_W21_TASK_ACTION_COUNT_DRIFT'}
    $id=[string]$task.Principal.UserId
    try {
        $sid=if($id -match '^S-1-[0-9-]+$') {$id} else {
            ([Security.Principal.NTAccount]::new($id)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
    } catch {throw 'UCIE_W21_TASK_OWNER_UNVERIFIED'}
    if ($sid -ne $script:ownerSid) {throw 'UCIE_W21_TASK_OWNER_MISMATCH'}
    return $task
}
function ActionEquals($task,$spec,[bool]$isNew) {
    $action=$task.Actions[0]
    $exe=if($isNew){$spec.NewExe}else{$spec.OldExe}
    $expectedArguments=if($isNew){$spec.NewArgs}else{$spec.OldArgs}
    $work=if($isNew){$root}else{$old}
    return ([string]::Equals([string]$action.Execute,$exe,
                [StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals([string]$action.Arguments,$expectedArguments,
                [StringComparison]::Ordinal) -and
            [string]::Equals([string]$action.WorkingDirectory,$work,
                [StringComparison]::OrdinalIgnoreCase))
}
function OriginalDisabled {
    foreach($spec in $specs) {
        $task=GetOwnerTask $spec.Name
        if ([string]$task.State -ne 'Disabled' -or
            -not (ActionEquals $task $spec $false)) {
            throw 'UCIE_W21_OLD_TASK_NOT_DISABLED_OR_ACTION_DRIFT'
        }
    }
}
function NewLocalOnly {
    foreach($index in 0..2) {
        $task=GetOwnerTask $specs[$index].Name
        if (-not (ActionEquals $task $specs[$index] $true)) {
            throw 'UCIE_W21_STAGED_TASK_ACTION_DRIFT'
        }
        if ($index -lt 2 -and [string]$task.State -ne 'Disabled') {
            throw 'UCIE_W21_TWO_WRITER_TASKS_NOT_DISABLED'
        }
        if ($index -eq 2 -and [string]$task.State -eq 'Disabled') {
            throw 'UCIE_W21_LOCAL_PILOT_NOT_ENABLED'
        }
    }
}
# W27 pre-rebind rollback gate: this is only a RECORD-ONLY rollback
# eligibility gate for a failed W19 BEFORE its own journal. The original
# three tasks must still be Disabled with OLD_EXACT actions; W22/W24 owner
# ResumeOld is the distinct operation that may later start LocalV1/writers.
# A partial W19 stage, relocated runtime, marker, or any W13/W20 artifact
# MUST stay on the manual-review path. Never erase the failed intent.
function AssertPreRebindNoStage {
    foreach($p in @($w19Journal,$w13Journal,$w20Journal,
                    $w20Rollback,$w19Rollback,$marker,
                    $privateData,$targetRuntime)) {
        Absent $p
    }
    OriginalDisabled
    if ((C40Hash) -ne $c40Before) {
        throw 'UCIE_W27_PRE_REBIND_C40_ACTION_DRIFT_HOLD'
    }
}
function C40Hash {
    $task=GetOwnerTask $c40
    $a=$task.Actions[0]
    return HashText ((@([string]$a.Execute,[string]$a.Arguments,
                        [string]$a.WorkingDirectory)) -join [char]0)
}
function HealthyLocal {
    try {
        $p=Invoke-RestMethod -Uri 'http://127.0.0.1:18767/local/health' -Method Get -TimeoutSec 3 -ErrorAction Stop
        return ($p.schema -eq 'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01' -and
                $p.status -eq 'LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE' -and
                $p.bound_host -eq '127.0.0.1' -and $p.bound_port -eq 18767 -and
                $p.owner_acceptance_verified -eq $true -and
                $p.online_release_authorized -eq $false -and
                $p.operating_database_writes -eq 0)
    } catch {return $false}
}
if (-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),$path,
                          [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_W21_EXACT_NEWROOT_SCRIPT_REQUIRED'
}
foreach($p in @($old,$root,$archive)) {Direct $p $true}
foreach($p in @($path,$w19,$w20)) {Direct $p $false}
$script:ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
if (-not $acl.AreAccessRulesProtected -or
    $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:ownerSid) {
    throw 'UCIE_W21_PRIVATE_ARCHIVE_OWNER_ACL_REQUIRED'
}
$prior=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    & git -C $root merge-base --is-ancestor $base HEAD 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'UCIE_W21_W20_GIT_ANCESTRY_MISSING'}
} finally {$env:GIT_OPTIONAL_LOCKS=$prior}
Import-Module ScheduledTasks -ErrorAction Stop
$c40Before=C40Hash
if ($ApplyLocal) {
    OriginalDisabled
    foreach($p in @($journal,$rollbackReceipt,$w19Journal,$w13Journal,
                    $w20Journal,$w20Rollback,$w19Rollback,$marker,
                    $privateData,$targetRuntime)) {Absent $p}
    SavePrivate $journal ([ordered]@{
        schema=$schema;status='UCIE_W21_LOCAL_MAINTENANCE_INTENT_HOLD'
        owner_sid_sha256=(HashText $script:ownerSid)
        c40_action_sha256=$c40Before
        source_root=$old;new_root=$root
        three_python_tasks_original_disabled=$true
        c40_mcp_round_trip_verified=$false
        owner_live_cutover_authorized=$false
    })
    $childStage='W19_OWNER_APPLY'
    try {
        # Preserve interactive Python input: DO NOT pipe this to Out-String.
        & $w19 -Apply -OwnerApproval $w19Approval
        $childStage='W19_STAGE_JOURNAL_REQUIRED'
        Direct $w19Journal $false
        $childStage='W13_REBIND_JOURNAL_REQUIRED'
        Direct $w13Journal $false
        $childStage='POST_W19_C40_ACTION_CHECK'
        if ((C40Hash) -ne $c40Before) {
            throw 'UCIE_W21_C40_ACTION_DRIFT_AFTER_W19'
        }
        $childStage='W20_LOCAL_PILOT'
        & $w20 -PilotLocal -OwnerApproval $w20Approval
        $childStage='W20_PILOT_JOURNAL_REQUIRED'
        Direct $w20Journal $false
        $childStage='NEW_LOCALV1_TASK_ACTIONS_CHECK'
        NewLocalOnly
        $childStage='NEW_LOCALV1_HTTP_HEALTH_CHECK'
        if (-not (HealthyLocal)) {throw 'UCIE_W21_LOCAL_HEALTH_NOT_ACCEPTED'}
        $childStage='POST_W20_C40_ACTION_CHECK'
        if ((C40Hash) -ne $c40Before) {
            throw 'UCIE_W21_C40_ACTION_DRIFT_AFTER_W20'
        }
        [pscustomobject]@{
            schema=$schema
            status='UCIE_W21_LOCAL_ONLY_HEALTHY__WRITERS_AND_C40_HOLD'
            localv1_loopback_health='PASS'
            two_writer_task_actions_rebound_but_disabled=$true
            writer_tasks_enabled=0
            c40_task_action_unchanged=$true
            c40_mcp_round_trip_verified=$false
            original_sqlite_restored_or_deleted_by_w21=$false
            full_operating_cutover_authorized=$false
        } | ConvertTo-Json -Compress
        return
    } catch {
        # Never echo untrusted exception text: it may contain private paths,
        # task arguments, or other sensitive information. Report only a
        # restricted UCIE error identifier (if exact) and exception class.
        # This first-party diagnostic is an additional stdout receipt;
        # preserve the original stable W21 failure identifier for callers.
        $raw=[string]$_.Exception.Message
        $reason='UCIE_W25_NONCANONICAL_CHILD_EXCEPTION'
        if($raw -cmatch '^UCIE_[A-Z0-9_]{5,100}$'){
            $reason=$raw
        }
        $kind=$_.Exception.GetType().Name
        if($kind -notmatch '^[A-Za-z][A-Za-z0-9]{0,60}$'){
            $kind='UnclassifiedError'
        }
        [pscustomobject]@{
            schema='UCIE_W25_W21_SANITIZED_CHILD_FAILURE_V01'
            status='UCIE_W21_NESTED_STAGE_FAILURE__REVIEW_REQUIRED'
            stage=$childStage
            reason_code=$reason
            exception_class=$kind
            private_path_or_error_text_exposed=$false
            recovery_requires_owner_review=$true
            owner_maintenance_retry_authorized=$false
            full_cutover_authorized=$false
        } | ConvertTo-Json -Compress
        # Preserve all partial state. NO blind retry or automatic DB rollback.
        throw 'UCIE_W21_LOCAL_ONCE_FAILED_PRESERVE_RECEIPTS_EXPLICIT_ROLLBACK_ONLY'
    }
}
# Rollback runs only after exact owner approval; never rewrites either DB set.
Direct $journal $false
Absent $rollbackReceipt
$record=Get-Content -LiteralPath $journal -Raw -Encoding UTF8 |
    ConvertFrom-Json -ErrorAction Stop
if ($record.schema -ne $schema -or
    $record.status -ne 'UCIE_W21_LOCAL_MAINTENANCE_INTENT_HOLD' -or
    $record.owner_sid_sha256 -ne (HashText $script:ownerSid) -or
    $record.c40_action_sha256 -ne $c40Before -or
    $record.source_root -ne $old -or $record.new_root -ne $root) {
    throw 'UCIE_W21_ROLLBACK_INTENT_INVALID'
}
$rollbackPhase='STAGED_REBIND'
if (Test-Path -LiteralPath $w20Journal) {
    Absent $w20Rollback
    & $w20 -RollbackLocal -OwnerApproval $w20RollbackApproval
    $rollbackPhase='W20_PILOT_ROLLBACK'
} elseif (Test-Path -LiteralPath $w13Journal) {
    Direct $marker $false
    & $w19 -Rollback -OwnerApproval $w19RollbackApproval
    $rollbackPhase='W13_W19_REBIND_ROLLBACK'
} else {
    # W27: W19 never journaled, W13/W20 never staged. Do not call either
    # W19/W20 rollback: neither has a stage to reverse. This branch is
    # deliberately blocked by ANY W19 journal, marker, copied DB path,
    # W13/W20 journal or rollback, or mismatched original task/C40 action.
    AssertPreRebindNoStage
    $rollbackPhase='W27_PRE_REBIND_ORIGINAL_DISABLED_NO_DATA_STAGE'
}
OriginalDisabled
if ((C40Hash) -ne $c40Before) {throw 'UCIE_W21_C40_CHANGED_DURING_ROLLBACK'}
SavePrivate $rollbackReceipt ([ordered]@{
    schema=$schema;status='UCIE_W21_ROLLBACK_OLD_ACTIONS_DISABLED'
    writer_tasks_enabled=0;original_sqlite_overwritten=$false
    new_private_sqlite_kept=($rollbackPhase -cne 'W27_PRE_REBIND_ORIGINAL_DISABLED_NO_DATA_STAGE');c40_action_unchanged=$true
    rollback_phase=$rollbackPhase
    pre_rebind_no_w19_stage=($rollbackPhase -ceq 'W27_PRE_REBIND_ORIGINAL_DISABLED_NO_DATA_STAGE')
    full_operating_cutover_authorized=$false
})
[pscustomobject]@{
    schema=$schema
    status='UCIE_W21_LOCAL_MAINTENANCE_ROLLBACK_RECORDED__DATA_PRESERVED'
    original_three_task_actions_restored_disabled=$true
    new_private_sqlite_kept=($rollbackPhase -cne 'W27_PRE_REBIND_ORIGINAL_DISABLED_NO_DATA_STAGE')
    rollback_phase=$rollbackPhase
    pre_rebind_no_w19_stage=($rollbackPhase -ceq 'W27_PRE_REBIND_ORIGINAL_DISABLED_NO_DATA_STAGE')
    c40_action_unchanged=$true
    full_operating_cutover_authorized=$false
} | ConvertTo-Json -Compress
