# W25 read-only post-recovery prerequisite survey, never reproduces a
# Disabled W19 apply or authorizes a new outage. Default NO HOST ACCESS.
[CmdletBinding()]
param([switch]$ContractOnly,[switch]$CheckLocal,[string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W25_W19_PREJOURNAL_POSTRECOVERY_READONLY_V01'
$approval='AUTHORIZE_UCIE_W25_READONLY_POSTRECOVERY_W19_PREREQUISITES'
$old='D:\UCIE'
$root='D:\UCIE_PROJECT\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$scriptPath=$root+'\scripts\ucie_owner_w25_w19_prejournal_probe_v01.ps1'
$w19=$root+'\scripts\ucie_owner_w19_data_task_stage_v01.ps1'
$w19Python=$root+'\scripts\ucie_owner_w19_lockstep_handoff_v01.py'
$rebinder=$root+'\scripts\ucie_owner_task_rebind_v01.ps1'
$python=$root+'\.venv\Scripts\python.exe'
$w18Base='853736a0c82c0c348665b6b8acb99e3c3a6d4825'
$w24Base='2d21ba8fabb8ec773927aa537b050b49f7f9cbe7'
$names=@('UCIE-PublicMiner-Hourly','UCIE-Internal-Minute','UCIE-LocalV1-Web')
$specs=@(
    [pscustomobject]@{Name=$names[0];Executable='D:\UCIE\.venv\Scripts\python.exe';Arguments='"D:\UCIE\scripts\public_miner_cycle.py"'},
    [pscustomobject]@{Name=$names[1];Executable='D:\UCIE\.venv\Scripts\python.exe';Arguments='-B "D:\UCIE\scripts\internal_minute_tick.py"'},
    [pscustomobject]@{Name=$names[2];Executable='D:\UCIE\.venv\Scripts\pythonw.exe';Arguments='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'}
)
if(-not $CheckLocal){$ContractOnly=$true}
if($ContractOnly){
    if($CheckLocal){throw 'UCIE_W25_CONTRACT_MUTATION_DENIED'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W25_CONTRACT_ONLY_NO_HOST_ACCESS'
        owner_tasks_queried=$false;private_archive_accessed=$false
        sqlite_opened=$false;port_probed=$false;c40_queried=$false
        task_or_c40_modified=$false;journal_written=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if(-not [string]::Equals($OwnerApproval,$approval,[StringComparison]::Ordinal)){
    throw 'UCIE_W25_EXPLICIT_READONLY_OWNER_APPROVAL_REQUIRED'
}
if($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive){
    throw 'UCIE_W25_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
$caller=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($caller)
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    throw 'UCIE_W25_OWNER_ELEVATED_READONLY_TOKEN_REQUIRED'
}
$script:ownerSid=$caller.User.Value
function Direct([string]$p,[bool]$dir){
    $item=Get-Item -LiteralPath $p -Force -ErrorAction Stop
    if([bool]$item.PSIsContainer -ne $dir){throw 'UCIE_W25_WRONG_PATH_TYPE'}
    while($null -ne $item -and
          $item.FullName.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)){
        if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
            throw 'UCIE_W25_REPARSE_PATH_DENIED'
        }
        if($item -is [IO.FileInfo]){$item=$item.Directory}else{$item=$item.Parent}
    }
}
function Absent([string]$p){
    $item=Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    if($null -ne $item -or [IO.File]::Exists($p) -or [IO.Directory]::Exists($p)){
        throw 'UCIE_W25_STAGED_ARTIFACT_PRESENT_NO_FRESH_ATTEMPT'
    }
}
function ShaText([string]$value){
    $sha=[Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString(
            $sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($value))
        ).Replace('-','').ToLowerInvariant()
    } finally {$sha.Dispose()}
}
function ReadPrivate([string]$p){
    Direct $p $false
    if((Get-Item -LiteralPath $p).Length -gt 1048576){
        throw 'UCIE_W25_RECEIPT_TOO_LARGE_HOLD'
    }
    return Get-Content -LiteralPath $p -Raw -Encoding UTF8 |
        ConvertFrom-Json -ErrorAction Stop
}
function OwnerTask([string]$name){
    $task=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
    if(@($task.Actions).Count -ne 1){throw 'UCIE_W25_TASK_ACTION_COUNT_HOLD'}
    $id=[string]$task.Principal.UserId
    try {
        $sid=if($id -match '^S-1-[0-9-]+$'){$id}else{
            ([Security.Principal.NTAccount]::new($id)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
    } catch {throw 'UCIE_W25_TASK_OWNER_UNVERIFIED'}
    if($sid -ne $script:ownerSid){throw 'UCIE_W25_TASK_OWNER_CHANGED_HOLD'}
    return $task
}
function C40Hash {
    $task=OwnerTask 'UCIE-C40-Recover'
    if([string]$task.State -ne 'Running'){throw 'UCIE_W25_C40_TASK_NOT_RUNNING'}
    $a=$task.Actions[0]
    return ShaText ((@([string]$a.Execute,[string]$a.Arguments,
                       [string]$a.WorkingDirectory)) -join [char]0)
}
if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
                        [IO.Path]::GetFullPath($scriptPath),
                        [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W25_EXACT_NEWROOT_SCRIPT_REQUIRED'
}
foreach($p in @($old,$root,$archive)){Direct $p $true}
foreach($p in @($scriptPath,$w19,$w19Python,$rebinder,$python)){Direct $p $false}
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
if(-not $acl.AreAccessRulesProtected -or
   $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:ownerSid){
    throw 'UCIE_W25_OWNER_ONLY_ARCHIVE_ACL_REQUIRED'
}
# All Git operations here are read-only; disable optional lock writes.
$prior=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    $remote=(& git -C $root remote get-url origin 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $remote -cne
       'https://github.com/tmdrkdtn1-project/UCIE.git'){
        throw 'UCIE_W25_FIRST_PARTY_REMOTE_DRIFT'
    }
    foreach($ancestor in @($w18Base,$w24Base)){
        & git -C $root merge-base --is-ancestor $ancestor HEAD 2>$null | Out-Null
        if($LASTEXITCODE -ne 0){throw 'UCIE_W25_EXPECTED_W19_ANCESTRY_MISSING'}
    }
    $dirty=(& git -C $root status --porcelain --untracked-files=all 2>$null |
            Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $dirty.Length -gt 0){
        throw 'UCIE_W25_CANONICAL_CHECKOUT_DIRTY_HOLD'
    }
} finally {$env:GIT_OPTIONAL_LOCKS=$prior}
$w22=ReadPrivate ($archive+'\UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json')
$w22Done=ReadPrivate ($archive+'\UCIE_W22_ORIGINAL_AVAILABILITY_RESTORED_V01.json')
$w24=ReadPrivate ($archive+'\UCIE_W24_OWNER_RECOVERED_RETRY_INTENT_V01.json')
$w21=ReadPrivate ($archive+'\UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01.json')
$recoveryIntent=ReadPrivate ($archive+'\UCIE_W24_PRE_REBIND_OWNER_RECOVERY_INTENT_V01.json')
$recovery=ReadPrivate ($archive+'\UCIE_W24_PRE_REBIND_OWNER_RECOVERY_RECEIPT_V01.json')
$ownerHash=ShaText $script:ownerSid
Import-Module ScheduledTasks -ErrorAction Stop
$c40Baseline=C40Hash
if($w22.schema -ne 'UCIE_W22_OWNER_QUIESCE_LOCAL_MAINTENANCE_V01' -or
   $w22.status -ne 'UCIE_W22_OWNER_MAINTENANCE_QUIESCE_INTENT' -or
   $w22Done.status -ne 'UCIE_W22_ORIGINAL_TASK_SCHEDULES_AND_LOCAL_HTTP_RESTORED' -or
   $w24.schema -ne 'UCIE_W24_OWNER_RECOVERED_RETRY_V01' -or
   $w24.status -ne 'UCIE_W24_OWNER_RECOVERED_RETRY_INTENT' -or
   $w21.schema -ne 'UCIE_W21_OWNER_SINGLE_LOCAL_MAINTENANCE_V01' -or
   $w21.status -ne 'UCIE_W21_LOCAL_MAINTENANCE_INTENT_HOLD' -or
   $recoveryIntent.schema -ne 'UCIE_W24_PRE_REBIND_OWNER_RECOVERY_V01' -or
   $recoveryIntent.status -ne 'OWNER_PRE_REBIND_RECOVERY_INTENT' -or
   $recovery.schema -ne 'UCIE_W24_PRE_REBIND_OWNER_RECOVERY_V01' -or
   $recovery.status -ne 'UCIE_W24_PRE_REBIND_ORIGINAL_SERVICE_RESTORED' -or
   $recovery.localv1_http_healthy -ne $true -or
   $recovery.original_writer_schedules_enabled -ne 2 -or
   $recovery.c40_action_unchanged -ne $true -or
   $w21.source_root -ne $old -or $w21.new_root -ne $root -or
   $w24.owner_sid_sha256 -ne $ownerHash -or
   $w21.owner_sid_sha256 -ne $ownerHash -or
   $w22.owner_sid_sha256 -ne $ownerHash -or
   $recoveryIntent.owner_sid_sha256 -ne $ownerHash -or
   $recoveryIntent.c40_action_sha256 -ne $c40Baseline -or
   $w24.c40_action_sha256 -ne $c40Baseline -or
   $w21.c40_action_sha256 -ne $c40Baseline -or
   $w22.c40_action_sha256 -ne $c40Baseline){
    throw 'UCIE_W25_PRIOR_INCIDENT_PROVENANCE_OR_C40_DRIFT'
}
$expectedStates=@('Ready','Ready','Running')
foreach($idx in 0..2){
    $spec=$specs[$idx]
    $t=OwnerTask $spec.Name
    $a=$t.Actions[0]
    if([string]$t.State -cne $expectedStates[$idx] -and
       -not ($idx -lt 2 -and [string]$t.State -ceq 'Running')){
        throw 'UCIE_W25_EXPECTED_RESTORED_TASK_STATE_HOLD'
    }
    if(-not [string]::Equals([string]$a.Execute,$spec.Executable,
                             [StringComparison]::OrdinalIgnoreCase) -or
       -not [string]::Equals([string]$a.Arguments,$spec.Arguments,
                             [StringComparison]::Ordinal) -or
       -not [string]::Equals([string]$a.WorkingDirectory,$old,
                             [StringComparison]::OrdinalIgnoreCase)){
        throw 'UCIE_W25_RESTORED_TASK_ACTION_DRIFT'
    }
}
# Original W19 stage journal was never created; do not delete old intents.
foreach($p in @(
    $archive+'\UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json',
    $archive+'\UCIE_W19_OWNER_DATA_TASK_ROLLBACK_V01.json',
    $archive+'\UCIE_W13_TASK_REBIND_V01.json',
    $archive+'\UCIE_W20_LOCAL_PILOT_JOURNAL_V01.json',
    $archive+'\UCIE_W20_LOCAL_PILOT_ROLLBACK_V01.json',
    $archive+'\UCIE_W19_LOCKSTEP_FINAL_DATA_V01',
    $archive+'\.ucie_owner_runtime_opt_in_v01',
    $root+'\runtime'
)){Absent $p}
# Running old-root state does not reproduce the W19 Disabled-state preflight.
try {
    $h=Invoke-RestMethod -Uri 'http://127.0.0.1:18767/local/health' -Method Get -TimeoutSec 3 -ErrorAction Stop
    if($h.schema -ne 'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01' -or
       $h.status -ne 'LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE' -or
       $h.bound_host -ne '127.0.0.1' -or
       [int]$h.bound_port -ne 18767 -or
       $h.owner_acceptance_verified -ne $true -or
       $h.online_release_authorized -ne $false -or
       $h.operating_database_writes -ne 0){
        throw 'UCIE_W25_OLD_LOCAL_HTTP_SCHEMA_DRIFT'
    }
} catch {
    throw 'UCIE_W25_OLD_LOCAL_HTTP_HEALTH_UNVERIFIED_HOLD'
}
[pscustomobject]@{
    schema=$schema
    status='UCIE_W25_RUNNING_OLD_ROOT_PREREQUISITES_VERIFIED__W19_DISABLED_PREJOURNAL_NOT_REPLAYED'
    old_task_action_and_owner_check='PASS'
    owner_only_archive_and_receipts='PASS'
    historic_w19_git_ancestor_check='PASS'
    source_files_direct='PASS'
    absent_w19_stage_rebind_and_new_runtime='PASS'
    old_localv1_http_health='PASS'
    prior_w21_nested_error_reason='NOT_CAPTURED'
    root_cause_verified=$false
    operating_sqlite_opened=$false
    task_or_c40_modified=$false
    journal_written=$false
    c40_mcp_round_trip_verified=$false
    full_cutover_authorized=$false
} | ConvertTo-Json -Compress
