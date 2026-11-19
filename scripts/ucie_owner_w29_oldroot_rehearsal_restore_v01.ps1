# UCIE W29: one-shot old-root quiesce-and-immediate-restoration rehearsal.
# Owner host execution is NOT authorized by PR merge or CI. Default: NO HOST.
# Does NOT invoke W19, W21, W22, W24, migrate DBs, or modify C40.
[CmdletBinding()]
param(
    [switch]$ContractOnly,
    [switch]$OwnerPreflightReadOnly,
    [switch]$RehearseOld,
    [switch]$RecoverOld,
    [string]$OwnerApproval=''
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W29_OWNER_OLDROOT_REHEARSAL_AND_RESTORE_V01'
$root='D:\UCIE_PROJECT\UCIE'
$old='D:\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$self=$root+'\scripts\ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1'
$w28Base='d120f0783a7bdc107b08a70a3887aa497a593a7c'
$intent=$archive+'\UCIE_W29_OWNER_OLDROOT_REHEARSAL_INTENT_V01.json'
$recoveryIntent=$archive+'\UCIE_W29_OWNER_OLDROOT_RECOVERY_INTENT_V01.json'
$restored=$archive+'\UCIE_W29_OWNER_OLDROOT_RESTORED_V01.json'
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
$modeCount=@($OwnerPreflightReadOnly.IsPresent,$RehearseOld.IsPresent,$RecoverOld.IsPresent) |
    Where-Object {$_ -eq $true} | Measure-Object | Select-Object -ExpandProperty Count
if($modeCount -eq 0){$ContractOnly=$true}
if($ContractOnly){
    if($modeCount -ne 0){throw 'UCIE_W29_CONTRACT_AND_OWNER_MODE_CONFLICT'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W29_CONTRACT_ONLY_NO_HOST_ACCESS'
        task_scheduler_queried=$false;task_scheduler_changed=$false
        operating_sqlite_opened=$false;c40_queried_or_modified=$false
        port_probed=$false;private_archive_read=$false
        owner_journal_written=$false;original_services_interrupted=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if($modeCount -ne 1){throw 'UCIE_W29_EXACT_ONE_OWNER_MODE_REQUIRED'}
$needed=if($OwnerPreflightReadOnly){
    'AUTHORIZE_UCIE_W29_READONLY_PRE_REHEARSAL_PREFLIGHT'
} elseif($RehearseOld){
    'AUTHORIZE_UCIE_W29_EXPLICIT_OLD_SERVICE_STOP_AND_IMMEDIATE_RESTORE_REHEARSAL'
} else {
    'AUTHORIZE_UCIE_W29_RECOVER_ALREADY_STARTED_OLDROOT_REHEARSAL'
}
if(-not [string]::Equals($needed,$OwnerApproval,[StringComparison]::Ordinal)){
    throw 'UCIE_W29_EXPLICIT_MODE_SPECIFIC_OWNER_APPROVAL_REQUIRED'
}
if($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive){
    throw 'UCIE_W29_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    throw 'UCIE_W29_OWNER_ELEVATED_TOKEN_REQUIRED_BEFORE_HOST_ACCESS'
}
$script:ownerSid=$identity.User.Value

function ShaText([string]$value) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try {return [BitConverter]::ToString(
        $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($value))
    ).Replace('-','').ToLowerInvariant()} finally {$sha.Dispose()}
}
function Direct([string]$path,[bool]$directory) {
    $item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if([bool]$item.PSIsContainer -ne $directory){throw 'UCIE_W29_DIRECT_PATH_TYPE_HOLD'}
    while($null -ne $item -and
          $item.FullName.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)){
        if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
            throw 'UCIE_W29_REPARSE_OR_REDIRECT_PATH_DENIED'
        }
        if($item -is [IO.FileInfo]){$item=$item.Directory}else{$item=$item.Parent}
    }
}
function Absent([string]$path) {
    $found=Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    if($null -ne $found -or [IO.File]::Exists($path) -or
       [IO.Directory]::Exists($path)){throw 'UCIE_W29_UNEXPECTED_EXISTING_PRIVATE_OUTPUT_HOLD'}
}
function AssertNoStagedData {
    foreach($p in $staged){Absent $p}
}
function ReadReceipt([string]$name) {
    $path=Join-Path $archive $name
    Direct $path $false
    $file=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if($file.Length -lt 2 -or $file.Length -gt 1048576){
        throw 'UCIE_W29_HISTORICAL_PRIVATE_RECEIPT_SIZE_HOLD'
    }
    return Get-Content -LiteralPath $path -Encoding UTF8 -Raw |
        ConvertFrom-Json -ErrorAction Stop
}
function SavePrivate([string]$path,$value) {
    if($path -cnotin @($intent,$recoveryIntent,$restored)){
        throw 'UCIE_W29_UNLISTED_JOURNAL_DESTINATION_DENIED'
    }
    Absent $path
    $tmp=$archive+'\UCIE_W29_'+[guid]::NewGuid().ToString('N')+'.tmp'
    try {
        [IO.File]::WriteAllText($tmp,(ConvertTo-Json $value -Compress -Depth 7),
                               [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($tmp,$path)
    } finally {
        if(Test-Path -LiteralPath $tmp){
            Remove-Item -LiteralPath $tmp -ErrorAction Stop
        }
    }
}
function OwnerTask([string]$taskName) {
    $task=Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction Stop
    if(@($task.Actions).Count -ne 1){
        throw 'UCIE_W29_SINGLE_TASK_ACTION_REQUIRED'
    }
    $raw=[string]$task.Principal.UserId
    try {
        $sid=if($raw -match '^S-1-[0-9-]+$'){$raw}else{
            ([Security.Principal.NTAccount]::new($raw)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
    } catch {throw 'UCIE_W29_TASK_OWNER_SID_UNRESOLVED'}
    if($sid -ne $script:ownerSid){throw 'UCIE_W29_TASK_OWNER_MISMATCH_HOLD'}
    return $task
}
function CheckOld([int]$idx) {
    $spec=$specs[$idx]
    $task=OwnerTask $spec.Name
    $a=$task.Actions[0]
    if(-not [string]::Equals([string]$a.Execute,$spec.Exe,
                           [StringComparison]::OrdinalIgnoreCase) -or
       -not [string]::Equals([string]$a.Arguments,$spec.Arguments,
                           [StringComparison]::Ordinal) -or
       -not [string]::Equals([string]$a.WorkingDirectory,$old,
                           [StringComparison]::OrdinalIgnoreCase)){
        throw 'UCIE_W29_EXACT_OLD_TASK_ACTION_DRIFT'
    }
    return $task
}
function C40Hash {
    $task=OwnerTask 'UCIE-C40-Recover'
    if([string]$task.State -ne 'Running'){
        throw 'UCIE_W29_C40_TASK_NOT_RUNNING_HOLD'
    }
    $a=$task.Actions[0]
    return ShaText ((@([string]$a.Execute,[string]$a.Arguments,
                       [string]$a.WorkingDirectory)) -join [char]0)
}
function PortState {
    $sockets=@(Get-NetTCPConnection -State Listen -ErrorAction Stop |
               Where-Object {$_.LocalPort -eq $port})
    if($sockets.Count -eq 0){return 'FREE'}
    if($sockets.Count -ne 1){return 'FOREIGN_OR_MULTIPLE_HOLD'}
    if([string]$sockets[0].LocalAddress -ne '127.0.0.1'){
        return 'FOREIGN_OR_MULTIPLE_HOLD'
    }
    return 'ONE_LOOPBACK_LISTENER'
}
function HealthyOld {
    try {
        $v=Invoke-RestMethod -Uri 'http://127.0.0.1:18767/local/health' -Method Get -TimeoutSec 2 -ErrorAction Stop
        return ($v.schema -eq 'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01' -and
                $v.status -eq 'LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE' -and
                $v.bound_host -eq '127.0.0.1' -and
                [int]$v.bound_port -eq 18767 -and
                $v.owner_acceptance_verified -eq $true -and
                $v.online_release_authorized -eq $false -and
                $v.operating_database_writes -eq 0)
    } catch {return $false}
}
function AssertRecoveredHistory([string]$baseline) {
    foreach($n in $history){[void](ReadReceipt $n)}
    $w22=ReadReceipt $history[0]
    $w22done=ReadReceipt $history[1]
    $w24=ReadReceipt $history[2]
    $w21=ReadReceipt $history[3]
    $emergency=ReadReceipt $history[4]
    $restoration=ReadReceipt $history[5]
    $hash=ShaText $script:ownerSid
    if($w22.schema -ne 'UCIE_W22_OWNER_QUIESCE_LOCAL_MAINTENANCE_V01' -or
       $w22.status -ne 'UCIE_W22_OWNER_MAINTENANCE_QUIESCE_INTENT' -or
       $w22done.status -ne 'UCIE_W22_ORIGINAL_TASK_SCHEDULES_AND_LOCAL_HTTP_RESTORED' -or
       $w22done.old_local_http_healthy -ne $true -or
       $w24.schema -ne 'UCIE_W24_OWNER_RECOVERED_RETRY_V01' -or
       $w24.status -ne 'UCIE_W24_OWNER_RECOVERED_RETRY_INTENT' -or
       $w21.schema -ne 'UCIE_W21_OWNER_SINGLE_LOCAL_MAINTENANCE_V01' -or
       $w21.status -ne 'UCIE_W21_LOCAL_MAINTENANCE_INTENT_HOLD' -or
       $emergency.schema -ne 'UCIE_W24_PRE_REBIND_OWNER_RECOVERY_V01' -or
       $emergency.status -ne 'OWNER_PRE_REBIND_RECOVERY_INTENT' -or
       $restoration.schema -ne 'UCIE_W24_PRE_REBIND_OWNER_RECOVERY_V01' -or
       $restoration.status -ne 'UCIE_W24_PRE_REBIND_ORIGINAL_SERVICE_RESTORED' -or
       $restoration.localv1_http_healthy -ne $true -or
       $restoration.original_writer_schedules_enabled -ne 2 -or
       $w22.owner_sid_sha256 -cne $hash -or
       $w24.owner_sid_sha256 -cne $hash -or
       $w21.owner_sid_sha256 -cne $hash -or
       $emergency.owner_sid_sha256 -cne $hash -or
       $w22.c40_action_sha256 -cne $baseline -or
       $w24.c40_action_sha256 -cne $baseline -or
       $w21.c40_action_sha256 -cne $baseline -or
       $emergency.c40_action_sha256 -cne $baseline) {
        throw 'UCIE_W29_HISTORICAL_OWNER_OR_C40_RECEIPT_DRIFT'
    }
}
function AssertOriginalLive {
    foreach($i in 0..2) {
        $t=CheckOld $i
        $expected=@('Ready','Ready','Running')[$i]
        if([string]$t.State -cne $expected){
            throw 'UCIE_W29_ORIGINAL_LIVE_STATE_DRIFT_HOLD'
        }
    }
    if((PortState) -ne 'ONE_LOOPBACK_LISTENER' -or -not (HealthyOld)){
        throw 'UCIE_W29_ORIGINAL_LOCAL_HTTP_UNVERIFIED'
    }
}
function WaitFreePort {
    for($i=0;$i -lt 24;$i++){
        if((PortState) -eq 'FREE'){return $true}
        Start-Sleep -Milliseconds 300
    }
    return $false
}
function WaitHealthyOld {
    for($i=0;$i -lt 40;$i++){
        if((PortState) -eq 'ONE_LOOPBACK_LISTENER' -and
           [string](CheckOld 2).State -eq 'Running' -and
           (HealthyOld)){return $true}
        Start-Sleep -Milliseconds 350
    }
    return $false
}
function ReadW29Intent([string]$baseline) {
    Direct $intent $false
    $record=Get-Content -LiteralPath $intent -Encoding UTF8 -Raw |
        ConvertFrom-Json -ErrorAction Stop
    if($record.schema -ne $schema -or
       $record.status -ne 'UCIE_W29_OWNER_REHEARSAL_INTENT' -or
       $record.owner_sid_sha256 -cne (ShaText $script:ownerSid) -or
       $record.c40_action_sha256 -cne $baseline -or
       $record.original_old_actions_verified -ne $true -or
       @($record.original_task_names).Count -ne 3 -or
       @($record.original_task_states).Count -ne 3){
        throw 'UCIE_W29_OWNER_REHEARSAL_JOURNAL_MISMATCH_HOLD'
    }
    for($i=0;$i -lt 3;$i++){
        if($record.original_task_names[$i] -cne $names[$i] -or
           $record.original_task_states[$i] -cne @('Ready','Ready','Running')[$i]){
            throw 'UCIE_W29_ORIGINAL_TASK_RECOVERY_LINEAGE_HOLD'
        }
    }
}
# Extractable core for disposable Windows PowerShell negative/positive tests.
# Must only restore old exact tasks; must not call W19/W21/W22/W24.
function InvokeW29RestoreOld([string]$baseline) {
    AssertNoStagedData
    foreach($i in 0..2){[void](CheckOld $i)}
    if((C40Hash) -cne $baseline){
        throw 'UCIE_W29_C40_ACTION_CHANGED_BEFORE_RESTORE'
    }
    $local=CheckOld 2
    $localState=[string]$local.State
    if($localState -eq 'Running' -and
       (PortState) -eq 'ONE_LOOPBACK_LISTENER' -and (HealthyOld)){
        $localResult='ALREADY_RUNNING_OLD_HTTP_HEALTHY'
    } else {
        if((PortState) -ne 'FREE'){
            throw 'UCIE_W29_FOREIGN_LISTENER_NO_UNKNOWN_PID_KILL'
        }
        if($localState -notin @('Disabled','Ready')){
            throw 'UCIE_W29_UNEXPECTED_OLD_LOCAL_STATE_HOLD'
        }
        if($localState -eq 'Disabled'){
            Enable-ScheduledTask -TaskPath '\' -TaskName $names[2] -ErrorAction Stop | Out-Null
        }
        Start-ScheduledTask -TaskPath '\' -TaskName $names[2] -ErrorAction Stop
        if(-not (WaitHealthyOld)){
            throw 'UCIE_W29_ORIGINAL_LOCAL_HTTP_RESTART_FAILED_HOLD'
        }
        $localResult='STARTED_OLD_LOCAL_AND_HTTP_HEALTHY'
    }
    # Only original old writer schedules; NEVER force-run either collector.
    foreach($i in 0,1){
        $t=CheckOld $i
        $state=[string]$t.State
        if($state -eq 'Disabled'){
            Enable-ScheduledTask -TaskPath '\' -TaskName $names[$i] -ErrorAction Stop | Out-Null
        } elseif($state -notin @('Ready','Running')){
            throw 'UCIE_W29_OLD_WRITER_STATE_DRIFT_HOLD'
        }
    }
    foreach($i in 0,1){
        if([string](CheckOld $i).State -notin @('Ready','Running')){
            throw 'UCIE_W29_OLD_WRITER_SCHEDULE_NOT_RESTORED'
        }
    }
    if(-not (WaitHealthyOld) -or (C40Hash) -cne $baseline){
        throw 'UCIE_W29_RESTORE_FINAL_LOCAL_OR_C40_HOLD'
    }
    AssertNoStagedData
    return $localResult
}
function InvokeW29RehearsalQuiesce([string]$baseline) {
    foreach($i in 0..2){
        [void](CheckOld $i)
        Disable-ScheduledTask -TaskPath '\' -TaskName $names[$i] -ErrorAction Stop |
            Out-Null
    }
    # Stop ONLY known original UCIE Scheduled Task; no direct PID termination.
    Stop-ScheduledTask -TaskPath '\' -TaskName $names[2] -ErrorAction Stop
    foreach($i in 0..2){
        if([string](CheckOld $i).State -ne 'Disabled'){
            throw 'UCIE_W29_OLD_TASK_NOT_DISABLED_AFTER_QUIESCE'
        }
    }
    if(-not (WaitFreePort)){
        throw 'UCIE_W29_PORT_NOT_RELEASED_BY_OLD_LOCAL_TASK'
    }
    if((C40Hash) -cne $baseline){throw 'UCIE_W29_C40_ACTION_DRIFT_AFTER_QUIESCE'}
    AssertNoStagedData
}
function InvokeW29JournaledRestore([string]$baseline) {
    ReadW29Intent $baseline
    Absent $recoveryIntent
    Absent $restored
    AssertNoStagedData
    foreach($i in 0..2){[void](CheckOld $i)}
    # The recovery intent is durable BEFORE the first restore mutation.
    # A failed/incomplete attempt keeps this file and is NOT blind-retried.
    SavePrivate $recoveryIntent ([ordered]@{
        schema=$schema;status='UCIE_W29_OWNER_OLD_RESTORE_INTENT'
        owner_sid_sha256=(ShaText $script:ownerSid)
        c40_action_sha256=$baseline
        original_old_task_actions_verified=$true
        full_cutover_authorized=$false
    })
    $localResult=InvokeW29RestoreOld $baseline
    SavePrivate $restored ([ordered]@{
        schema=$schema;status='UCIE_W29_OLD_ROOT_LOCAL_HTTP_AND_TWO_WRITERS_RESTORED'
        restoration=$localResult
        old_local_http_healthy=$true;original_writer_schedules_enabled=2
        c40_action_unchanged=$true
        original_operating_sqlite_opened_or_overwritten=$false
        task_listener_pid_identity_verified=$false
        c40_mcp_round_trip_verified=$false
        full_cutover_authorized=$false
    })
    return $localResult
}
# Host/root provenance gates run AFTER exact owner approval and UAC.
if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
                        [IO.Path]::GetFullPath($self),
                        [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W29_EXACT_NEWROOT_FIRST_PARTY_SCRIPT_REQUIRED'
}
foreach($path in @($old,$root,$archive)){Direct $path $true}
Direct $self $false
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
if(-not $acl.AreAccessRulesProtected -or
   $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:ownerSid){
    throw 'UCIE_W29_PRIVATE_ARCHIVE_SAME_OWNER_ACL_HOLD'
}
$prior=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try{
    $remote=(& git -C $root remote get-url origin 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or
       $remote -cne 'https://github.com/tmdrkdtn1-project/UCIE.git'){
        throw 'UCIE_W29_FIRST_PARTY_REMOTE_DRIFT'
    }
    & git -C $root merge-base --is-ancestor $w28Base HEAD 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw 'UCIE_W29_PINNED_W28_ANCESTRY_MISSING'}
    $dirty=(& git -C $root status --porcelain --untracked-files=all 2>$null |
            Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $dirty){
        throw 'UCIE_W29_OWNER_CHECKOUT_NOT_CLEAN'
    }
} finally {$env:GIT_OPTIONAL_LOCKS=$prior}
Import-Module ScheduledTasks -ErrorAction Stop
$baseline=C40Hash
AssertRecoveredHistory $baseline
AssertNoStagedData
if($OwnerPreflightReadOnly){
    foreach($path in @($intent,$recoveryIntent,$restored)){Absent $path}
    AssertOriginalLive
    [pscustomobject]@{
        schema=$schema;status='UCIE_W29_OWNER_READONLY_OLDROOT_REHEARSAL_PREFLIGHT_PASS'
        original_task_actions_and_states='THREE_OLD_EXACT_READY_READY_RUNNING'
        old_local_http_healthy=$true
        prior_private_receipts_preserved=$true;new_w29_receipts_absent=$true
        c40_action_unchanged=$true;operating_sqlite_opened=$false
        task_or_c40_modified=$false;journal_written=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if($RehearseOld){
    foreach($path in @($intent,$recoveryIntent,$restored)){Absent $path}
    AssertOriginalLive
    SavePrivate $intent ([ordered]@{
        schema=$schema;status='UCIE_W29_OWNER_REHEARSAL_INTENT'
        owner_sid_sha256=(ShaText $script:ownerSid)
        c40_action_sha256=$baseline
        original_task_names=@($names)
        original_task_states=@('Ready','Ready','Running')
        original_old_actions_verified=$true
        original_old_local_http_healthy=$true
        sqlite_copy_or_task_rebind_authorized=$false
        full_cutover_authorized=$false
    })
    $quiesceStatus='QUIESCE_ACCEPTED'
    try {
        InvokeW29RehearsalQuiesce $baseline
    } catch {
        # Only canonical first-party UCIE failure IDs leave this scope.
        $reason=[string]$_.Exception.Message
        if($reason -cnotmatch '^UCIE_W29_[A-Z0-9_]{5,100}$'){
            $reason='UCIE_W29_QUIESCE_NONCANONICAL_EXCEPTION'
        }
        $quiesceStatus=$reason
    }
    # Always attempt the separately journaled old-root restore once.
    # If it cannot be proven safe, preserve the intent and return HOLD.
    try {
        $result=InvokeW29JournaledRestore $baseline
    } catch {
        throw 'UCIE_W29_REHEARSAL_RECOVERY_HOLD_KEEP_ALL_RECEIPTS_NO_BLIND_RETRY'
    }
    [pscustomobject]@{
        schema=$schema
        status='UCIE_W29_OLD_SERVICE_RESTORED_REHEARSAL_ONLY'
        quiesce_phase=$quiesceStatus
        localv1_restoration=$result
        old_local_http_healthy=$true
        original_writer_schedules_enabled=2
        c40_action_unchanged=$true
        sqlite_opened_or_overwritten=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
# -RecoverOld is an explicitly approved one-shot recovery of a previously
# started W29 rehearsal; a recovery intent already existing is NEVER retried.
Absent $recoveryIntent
Absent $restored
$result=InvokeW29JournaledRestore $baseline
[pscustomobject]@{
    schema=$schema
    status='UCIE_W29_OLD_SERVICE_RESTORED_MANUAL_OWNER_RECOVERY'
    localv1_restoration=$result
    old_local_http_healthy=$true;original_writer_schedules_enabled=2
    task_listener_pid_identity_verified=$false
    c40_mcp_round_trip_verified=$false
    sqlite_opened_or_overwritten=$false
    full_cutover_authorized=$false
} | ConvertTo-Json -Compress
