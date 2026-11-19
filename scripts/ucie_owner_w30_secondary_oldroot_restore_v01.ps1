# UCIE W30 secondary recovery for a FAILED W29 old-root restore only.
# Never run on a healthy owner host. Default no host. No W19/W21/W22/W24.
# This is source-under-review: CI mocks must not touch owner Task Scheduler.
[CmdletBinding()]
param(
    [switch]$ContractOnly,
    [switch]$InspectReadOnly,
    [switch]$RecoverPartial,
    [switch]$ResumePartial,
    [string]$OwnerApproval=''
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W30_OWNER_SECONDARY_OLDROOT_RESTORE_V01'
$root='D:\UCIE_PROJECT\UCIE'
$old='D:\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$self=$root+'\scripts\ucie_owner_w30_secondary_oldroot_restore_v01.ps1'
$w29Source=$root+'\scripts\ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1'
$w29Commit='ddcbb9ebc02b6908ab5f7a558f81b01a1e09d831'
$w29Blob='848cb03f50dc455fc61935a484c3d71e82506c90'
$w29Schema='UCIE_W29_OWNER_OLDROOT_REHEARSAL_AND_RESTORE_V01'
$priorW29Intent=$archive+'\UCIE_W29_OWNER_OLDROOT_REHEARSAL_INTENT_V01.json'
$priorW29Recovery=$archive+'\UCIE_W29_OWNER_OLDROOT_RECOVERY_INTENT_V01.json'
$priorW29Restored=$archive+'\UCIE_W29_OWNER_OLDROOT_RESTORED_V01.json'
$w30Intent=$archive+'\UCIE_W30_OWNER_SECONDARY_RECOVERY_INTENT_V01.json'
$w30Retry=$archive+'\UCIE_W30_OWNER_SECONDARY_RETRY_INTENT_V01.json'
$w30Restored=$archive+'\UCIE_W30_OWNER_SECONDARY_RESTORED_V01.json'
$port=18767
$names=@('UCIE-PublicMiner-Hourly','UCIE-Internal-Minute','UCIE-LocalV1-Web')
$specs=@(
    [pscustomobject]@{Name=$names[0];Exe='D:\UCIE\.venv\Scripts\python.exe';Arguments='"D:\UCIE\scripts\public_miner_cycle.py"'},
    [pscustomobject]@{Name=$names[1];Exe='D:\UCIE\.venv\Scripts\python.exe';Arguments='-B "D:\UCIE\scripts\internal_minute_tick.py"'},
    [pscustomobject]@{Name=$names[2];Exe='D:\UCIE\.venv\Scripts\pythonw.exe';Arguments='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'}
)
$history=@(
    'UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json',
    'UCIE_W22_ORIGINAL_AVAILABILITY_RESTORED_V01.json',
    'UCIE_W24_OWNER_RECOVERED_RETRY_INTENT_V01.json',
    'UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01.json',
    'UCIE_W24_PRE_REBIND_OWNER_RECOVERY_INTENT_V01.json',
    'UCIE_W24_PRE_REBIND_OWNER_RECOVERY_RECEIPT_V01.json'
)
$staged=@(
    $archive+'\UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json',
    $archive+'\UCIE_W19_OWNER_DATA_TASK_ROLLBACK_V01.json',
    $archive+'\UCIE_W13_TASK_REBIND_V01.json',
    $archive+'\UCIE_W20_LOCAL_PILOT_JOURNAL_V01.json',
    $archive+'\UCIE_W20_LOCAL_PILOT_ROLLBACK_V01.json',
    $archive+'\UCIE_W21_LOCAL_MAINTENANCE_ROLLBACK_V01.json',
    $archive+'\UCIE_W19_LOCKSTEP_FINAL_DATA_V01',
    $archive+'\.ucie_owner_runtime_opt_in_v01',
    $root+'\runtime',
    $archive+'\UCIE_W28_OWNER_NEW_TRANSACTION_INTENT_V01.json',
    $archive+'\UCIE_W28_OWNER_NEW_TRANSACTION_RECOVERY_INTENT_V01.json',
    $archive+'\UCIE_W28_OWNER_NEW_TRANSACTION_RESTORED_V01.json'
)
$modeCount=@($InspectReadOnly.IsPresent,$RecoverPartial.IsPresent,$ResumePartial.IsPresent) |
    Where-Object {$_ -eq $true} | Measure-Object | Select-Object -ExpandProperty Count
if($modeCount -eq 0){$ContractOnly=$true}
if($ContractOnly){
    if($modeCount -ne 0){throw 'UCIE_W30_CONTRACT_MUTATION_MODE_CONFLICT'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W30_CONTRACT_ONLY_NO_HOST_ACCESS'
        owner_task_queried=$false;sqlite_opened=$false
        c40_or_port_probed=$false;archive_read=$false
        journal_written=$false;task_scheduler_changed=$false
        historical_receipts_modified=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if($modeCount -ne 1){throw 'UCIE_W30_EXACT_ONE_OWNER_MODE_REQUIRED'}
$approval=if($InspectReadOnly){
    'AUTHORIZE_UCIE_W30_READONLY_FAILED_W29_RESTORE_INSPECTION'
} elseif($RecoverPartial){
    'AUTHORIZE_UCIE_W30_NEW_SECONDARY_RECOVERY_ONLY_AFTER_FAILED_W29'
} else {
    'AUTHORIZE_UCIE_W30_ONE_BOUNDED_RETRY_OF_PARTIAL_SECONDARY_RECOVERY'
}
if(-not [string]::Equals($OwnerApproval,$approval,[StringComparison]::Ordinal)){
    throw 'UCIE_W30_EXPLICIT_OWNER_MODE_APPROVAL_REQUIRED'
}
if($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive){
    throw 'UCIE_W30_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    throw 'UCIE_W30_SAME_OWNER_UAC_ELEVATION_REQUIRED'
}
$script:ownerSid=$identity.User.Value

function Direct([string]$path,[bool]$directory) {
    $item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if([bool]$item.PSIsContainer -ne $directory){throw 'UCIE_W30_DIRECT_PATH_TYPE_HOLD'}
    while($null -ne $item -and
          $item.FullName.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)){
        if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
            throw 'UCIE_W30_REPARSE_PATH_DENIED'
        }
        if($item -is [IO.FileInfo]){$item=$item.Directory}else{$item=$item.Parent}
    }
}
function Absent([string]$path) {
    $found=Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    if($null -ne $found -or [IO.File]::Exists($path) -or
       [IO.Directory]::Exists($path)){
        throw 'UCIE_W30_ALREADY_EXISTS_NO_BLIND_RETRY'
    }
}
function ReadBounded([string]$path) {
    Direct $path $false
    $item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if($item.Length -lt 2 -or $item.Length -gt 1048576){
        throw 'UCIE_W30_PRIVATE_RECEIPT_SIZE_HOLD'
    }
    return Get-Content -LiteralPath $path -Raw -Encoding UTF8 |
        ConvertFrom-Json -ErrorAction Stop
}
function SaveW30([string]$path,$value) {
    if($path -cnotin @($w30Intent,$w30Retry,$w30Restored)){
        throw 'UCIE_W30_UNLISTED_DESTINATION_DENIED'
    }
    Absent $path
    $temp=$archive+'\UCIE_W30_'+[guid]::NewGuid().ToString('N')+'.tmp'
    try {
        [IO.File]::WriteAllText($temp,(ConvertTo-Json $value -Depth 7 -Compress),
                               [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temp,$path)
    } finally {
        if(Test-Path -LiteralPath $temp){
            Remove-Item -LiteralPath $temp -ErrorAction Stop
        }
    }
}
function VerifyW29FailedRecovery([string]$baseline) {
    Absent $priorW29Restored
    $first=ReadBounded $priorW29Intent
    $second=ReadBounded $priorW29Recovery
    $ownerHash=ShaText $script:ownerSid
    if($first.schema -cne $w29Schema -or
       $first.status -cne 'UCIE_W29_OWNER_REHEARSAL_INTENT' -or
       $first.owner_sid_sha256 -cne $ownerHash -or
       $first.c40_action_sha256 -cne $baseline -or
       $first.original_old_actions_verified -ne $true -or
       $first.sqlite_copy_or_task_rebind_authorized -ne $false -or
       $first.full_cutover_authorized -ne $false -or
       $second.schema -cne $w29Schema -or
       $second.status -cne 'UCIE_W29_OWNER_OLD_RESTORE_INTENT' -or
       $second.owner_sid_sha256 -cne $ownerHash -or
       $second.c40_action_sha256 -cne $baseline -or
       $second.original_old_task_actions_verified -ne $true -or
       $second.full_cutover_authorized -ne $false -or
       @($first.original_task_names).Count -ne 3 -or
       @($first.original_task_states).Count -ne 3){
        throw 'UCIE_W30_FAILED_W29_RECEIPT_LINEAGE_HOLD'
    }
    foreach($i in 0..2){
        if($first.original_task_names[$i] -cne $names[$i] -or
           $first.original_task_states[$i] -cne @('Ready','Ready','Running')[$i]){
            throw 'UCIE_W30_W29_ORIGINAL_THREE_TASK_STATES_HOLD'
        }
    }
}
function CheckRecoveryCandidate([string]$baseline) {
    AssertNoStagedData
    if((C40Hash) -cne $baseline){
        throw 'UCIE_W30_C40_CHANGED_SECONDARY_RECOVERY_HOLD'
    }
    foreach($i in 0,1){
        $state=[string](CheckOld $i).State
        if($state -notin @('Ready','Running','Disabled')){
            throw 'UCIE_W30_ORIGINAL_WRITER_STATE_DRIFT_HOLD'
        }
    }
    $localState=[string](CheckOld 2).State
    $p=PortState
    if($p -eq 'FREE'){
        if($localState -notin @('Disabled','Ready') -or (HealthyOld)){
            throw 'UCIE_W30_LOCAL_TASK_AND_PORT_INCONSISTENT_HOLD'
        }
    } elseif($p -eq 'ONE_LOOPBACK_LISTENER'){
        if($localState -ne 'Running' -or -not (HealthyOld)){
            throw 'UCIE_W30_LISTENER_IDENTITY_UNVERIFIED_HOLD'
        }
    } else {
        throw 'UCIE_W30_FOREIGN_PORT_NO_UNKNOWN_PID_KILL'
    }
    return $(if($p -eq 'FREE'){'OLD_LOCAL_NEEDS_START'}else{'OLD_LOCAL_ALREADY_HEALTHY'})
}
function VerifyOldRestored([string]$baseline) {
    foreach($i in 0,1){
        if([string](CheckOld $i).State -notin @('Ready','Running')){
            throw 'UCIE_W30_TWO_OLD_WRITER_SCHEDULES_NOT_READY'
        }
    }
    if([string](CheckOld 2).State -ne 'Running' -or
       (PortState) -ne 'ONE_LOOPBACK_LISTENER' -or
       -not (HealthyOld) -or
       (C40Hash) -cne $baseline){
        throw 'UCIE_W30_FINAL_OLD_LOCAL_OR_C40_HEALTH_HOLD'
    }
    AssertNoStagedData
}
function ValidateW30InitialIntent([string]$baseline) {
    $record=ReadBounded $w30Intent
    if($record.schema -cne $schema -or
       $record.status -cne 'UCIE_W30_SECONDARY_RECOVERY_INTENT' -or
       $record.owner_sid_sha256 -cne (ShaText $script:ownerSid) -or
       $record.c40_action_sha256 -cne $baseline -or
       $record.w29_failed_restore_receipts_verified -ne $true -or
       $record.full_cutover_authorized -ne $false){
        throw 'UCIE_W30_RETRY_INITIAL_INTENT_LINEAGE_HOLD'
    }
}
function InvokeW30JournaledRecovery([string]$baseline,[string]$entryPath,[string]$phase) {
    [void](CheckRecoveryCandidate $baseline)
    # Recovery and retry EACH have their own durable, one-shot intent BEFORE
    # modifying any original UCIE Task Scheduler state.
    SaveW30 $entryPath ([ordered]@{
        schema=$schema
        status=$phase
        owner_sid_sha256=(ShaText $script:ownerSid)
        c40_action_sha256=$baseline
        w29_failed_restore_receipts_verified=$true
        original_old_task_actions_verified=$true
        full_cutover_authorized=$false
    })
    $result=InvokeW29RestoreOld $baseline
    VerifyOldRestored $baseline
    SaveW30 $w30Restored ([ordered]@{
        schema=$schema;status='UCIE_W30_SECONDARY_OLDROOT_SERVICE_RESTORED'
        restoration=$result
        old_local_http_healthy=$true
        original_writer_schedules_enabled=2
        c40_action_unchanged=$true
        w29_prior_recovery_intent_preserved=$true
        original_sqlite_opened_or_overwritten=$false
        task_listener_pid_identity_verified=$false
        c40_mcp_round_trip_verified=$false
        full_cutover_authorized=$false
    })
    return $result
}
# Never execute or dot-source the entire W29 mutating coordinator.
# An exact first-party Git blob pin precedes AST function extraction.
if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
                        [IO.Path]::GetFullPath($self),
                        [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W30_EXACT_FIRST_PARTY_ENTRYPOINT_REQUIRED'
}
foreach($dir in @($old,$root,$archive)){Direct $dir $true}
foreach($file in @($self,$w29Source)){Direct $file $false}
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
if(-not $acl.AreAccessRulesProtected -or
   $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:ownerSid){
    throw 'UCIE_W30_PROTECTED_ARCHIVE_SAME_OWNER_HOLD'
}
$priorGitLocks=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    $remote=(& git -C $root remote get-url origin 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or
       $remote -cne 'https://github.com/tmdrkdtn1-project/UCIE.git'){
        throw 'UCIE_W30_FIRST_PARTY_REMOTE_HOLD'
    }
    & git -C $root merge-base --is-ancestor $w29Commit HEAD 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw 'UCIE_W30_W29_SOURCE_ANCESTRY_HOLD'}
    $sourceBlob=(& git -C $root rev-parse 'HEAD:scripts/ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1' 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $sourceBlob -cne $w29Blob){
        throw 'UCIE_W30_PINNED_W29_SOURCE_BLOB_MISMATCH'
    }
    $changes=(& git -C $root status --porcelain --untracked-files=all 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $changes){
        throw 'UCIE_W30_DIRTY_OWNER_CHECKOUT_HOLD'
    }
} finally {$env:GIT_OPTIONAL_LOCKS=$priorGitLocks}

$parseTokens=$null;$parseErrors=$null
$w29Ast=[Management.Automation.Language.Parser]::ParseFile(
    $w29Source,[ref]$parseTokens,[ref]$parseErrors)
if(@($parseErrors).Count -ne 0){throw 'UCIE_W30_W29_SOURCE_AST_INVALID'}
$approvedW29Functions=@(
    'ShaText','ReadReceipt','OwnerTask','CheckOld','C40Hash',
    'PortState','HealthyOld','AssertRecoveredHistory','AssertNoStagedData',
    'WaitHealthyOld','InvokeW29RestoreOld'
)
foreach($functionName in $approvedW29Functions){
    $functionAsts=@($w29Ast.FindAll({
        param($node)
        ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
         $node.Name -ceq $functionName)
    },$true))
    if($functionAsts.Count -ne 1){
        throw 'UCIE_W30_W29_FUNCTION_NOT_UNIQUE_OR_MISSING'
    }
    . ([scriptblock]::Create($functionAsts[0].Extent.Text))
}
Import-Module ScheduledTasks -ErrorAction Stop
$baseline=C40Hash
AssertRecoveredHistory $baseline
AssertNoStagedData
VerifyW29FailedRecovery $baseline

if($InspectReadOnly){
    Absent $w30Restored
    if(Test-Path -LiteralPath $w30Retry){
        throw 'UCIE_W30_SECONDARY_RETRY_ALREADY_RECORDED_HOLD'
    }
    if(Test-Path -LiteralPath $w30Intent){
        ValidateW30InitialIntent $baseline
    }
    $candidate=CheckRecoveryCandidate $baseline
    [pscustomobject]@{
        schema=$schema
        status='UCIE_W30_FAILED_W29_SECONDARY_RECOVERY_READONLY_CANDIDATE'
        old_local_status=$candidate
        w30_attempt_already_recorded=[bool](Test-Path -LiteralPath $w30Intent)
        old_w29_failure_intents_preserved=$true
        original_sqlite_opened=$false
        tasks_changed=$false
        journal_written=$false
        c40_mcp_round_trip_verified=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
Absent $w30Restored
if($RecoverPartial){
    Absent $w30Intent
    Absent $w30Retry
    $entryPath=$w30Intent
    $phase='UCIE_W30_SECONDARY_RECOVERY_INTENT'
} else {
    Absent $w30Retry
    ValidateW30InitialIntent $baseline
    $entryPath=$w30Retry
    $phase='UCIE_W30_SECONDARY_BOUNDED_RETRY_INTENT'
}
try {
    $outcome=InvokeW30JournaledRecovery $baseline $entryPath $phase
} catch {
    $code=[string]$_.Exception.Message
    if($code -cnotmatch '^UCIE_(W29|W30)_[A-Z0-9_]{5,100}$'){
        $code='UCIE_W30_NONCANONICAL_RESTORE_FAILURE'
    }
    [pscustomobject]@{
        schema=$schema
        status='UCIE_W30_SECONDARY_RECOVERY_INCOMPLETE_PRESERVE_RECEIPTS'
        stage='JOURNALED_SECONDARY_RESTORE'
        reason_code=$code
        w30_recovery_record_may_exist=$true
        third_blind_attempt_authorized=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    throw 'UCIE_W30_SECONDARY_RESTORE_HOLD_NO_BLIND_RETRY'
}
[pscustomobject]@{
    schema=$schema
    status='UCIE_W30_ORIGINAL_LOCAL_AND_TWO_WRITERS_RESTORED__C40_MCP_HOLD'
    restoration=$outcome
    old_local_http_healthy=$true
    original_writer_schedules_enabled=2
    original_w29_receipts_preserved=$true
    original_sqlite_opened_or_overwritten=$false
    task_listener_pid_identity_verified=$false
    c40_mcp_round_trip_verified=$false
    full_cutover_authorized=$false
} | ConvertTo-Json -Compress
