# W22 owner maintenance: first quiesce exact old 3 UCIE tasks, then W21.
# Default is no-host. NEVER kills a PID or scans another project's command line.
# If a foreign Python still owns 18767 after stopping ONLY the UCIE task,
# stop at HOLD and preserve a private journal. C40 task is never mutated.
[CmdletBinding()]
param([switch]$ContractOnly,[switch]$ApplyLocal,[switch]$ResumeOld,
      [string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W22_OWNER_QUIESCE_LOCAL_MAINTENANCE_V01'
$root='D:\UCIE_PROJECT\UCIE'
$old='D:\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$scriptPath=$root+'\scripts\ucie_owner_w22_quiesce_resume_local_v01.ps1'
$w21=$root+'\scripts\ucie_owner_w21_single_local_maintenance_v01.ps1'
$w21Journal=$archive+'\UCIE_W21_LOCAL_MAINTENANCE_INTENT_V01.json'
$w19Journal=$archive+'\UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json'
$w13Journal=$archive+'\UCIE_W13_TASK_REBIND_V01.json'
$w20Journal=$archive+'\UCIE_W20_LOCAL_PILOT_JOURNAL_V01.json'
$w19Rollback=$archive+'\UCIE_W19_OWNER_DATA_TASK_ROLLBACK_V01.json'
$w20Rollback=$archive+'\UCIE_W20_LOCAL_PILOT_ROLLBACK_V01.json'
$w21Rollback=$archive+'\UCIE_W21_LOCAL_MAINTENANCE_ROLLBACK_V01.json'
$targetRuntime=$root+'\runtime'
$w19Data=$archive+'\UCIE_W19_LOCKSTEP_FINAL_DATA_V01'
$marker=$archive+'\.ucie_owner_runtime_opt_in_v01'
$python=$root+'\.venv\Scripts\python.exe'
$w19Python=$root+'\scripts\ucie_owner_w19_lockstep_handoff_v01.py'
$w23Lineage=$root+'\scripts\ucie_owner_w23_w19_lineage_gate_v01.py'
$w23Approval='AUTHORIZE_UCIE_W23_READONLY_W19_LINEAGE_BEFORE_TASK_STOP'
$intent=$archive+'\UCIE_W22_OWNER_MAINTENANCE_INTENT_V01.json'
$resumeReceipt=$archive+'\UCIE_W22_ORIGINAL_AVAILABILITY_RESTORED_V01.json'
$approvalApply='AUTHORIZE_UCIE_W22_EXACT_OLD_TASK_QUIESCE_AND_W21_LOCAL_ONLY'
$approvalResume='AUTHORIZE_UCIE_W22_RESTORE_ORIGINAL_SCHEDULES_AND_LOCALV1'
$w21Apply='AUTHORIZE_UCIE_W21_SINGLE_FINAL_DATA_AND_LOCALV1_MAINTENANCE'
$w21Rollback='AUTHORIZE_UCIE_W21_SINGLE_LOCAL_MAINTENANCE_ROLLBACK'
$base='44ae75fdcdcbdd4940076e0e58c3b6ea7bed729f'
$port=18767
$names=@(
    'UCIE-PublicMiner-Hourly',
    'UCIE-Internal-Minute',
    'UCIE-LocalV1-Web'
)
$specs=@(
    [pscustomobject]@{
        Name=$names[0];Executable='D:\UCIE\.venv\Scripts\python.exe'
        Arguments='"D:\UCIE\scripts\public_miner_cycle.py"'
    },
    [pscustomobject]@{
        Name=$names[1];Executable='D:\UCIE\.venv\Scripts\python.exe'
        Arguments='-B "D:\UCIE\scripts\internal_minute_tick.py"'
    },
    [pscustomobject]@{
        Name=$names[2];Executable='D:\UCIE\.venv\Scripts\pythonw.exe'
        Arguments='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'
    }
)
if (-not $ApplyLocal -and -not $ResumeOld) {$ContractOnly=$true}
if ($ContractOnly) {
    if ($ApplyLocal -or $ResumeOld) {throw 'UCIE_W22_CONTRACT_MUTATION_DENIED'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W22_CONTRACT_ONLY_NO_HOST_ACCESS'
        owner_tasks_queried=$false;sqlite_opened=$false;c40_queried=$false
        port_probed=$false;task_stopped_or_enabled=$false
        intent_written=$false;full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if ($ApplyLocal.IsPresent -eq $ResumeOld.IsPresent) {
    throw 'UCIE_W22_EXACT_ONE_MODE_REQUIRED'
}
$required=if($ApplyLocal){$approvalApply}else{$approvalResume}
if (-not [string]::Equals($OwnerApproval,$required,[StringComparison]::Ordinal)) {
    throw 'UCIE_W22_EXPLICIT_OWNER_APPROVAL_REQUIRED'
}
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive) {
    throw 'UCIE_W22_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
function Direct([string]$p,[bool]$dir) {
    $node=Get-Item -LiteralPath $p -Force -ErrorAction Stop
    if ([bool]$node.PSIsContainer -ne $dir) {throw 'UCIE_W22_WRONG_PATH_TYPE'}
    while ($null -ne $node -and
           $node.FullName.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'UCIE_W22_REPARSE_PATH_DENIED'
        }
        if ($node -is [IO.FileInfo]) {$node=$node.Directory}
        else {$node=$node.Parent}
    }
}
function Absent([string]$p) {
    $found=Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
    if ($null -ne $found -or [IO.File]::Exists($p) -or [IO.Directory]::Exists($p)) {
        throw 'UCIE_W22_EXISTING_RECEIPT_OR_OUTPUT_HOLD'
    }
}
function ShaText([string]$s) {
    $hash=[Security.Cryptography.SHA256]::Create()
    try {
        $bytes=[Text.Encoding]::UTF8.GetBytes($s)
        return [BitConverter]::ToString($hash.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()
    } finally {$hash.Dispose()}
}
function SavePrivate([string]$p,$obj) {
    Absent $p
    $tmp=$archive+'\UCIE_W22_'+[guid]::NewGuid().ToString('N')+'.tmp'
    try {
        [IO.File]::WriteAllText($tmp,(ConvertTo-Json $obj -Compress -Depth 6),
                               [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($tmp,$p)
    } finally {
        if(Test-Path -LiteralPath $tmp) {
            Remove-Item -LiteralPath $tmp -ErrorAction Stop
        }
    }
}
function OwnerTask([string]$name) {
    $t=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
    if (@($t.Actions).Count -ne 1) {throw 'UCIE_W22_TASK_ACTION_COUNT_HOLD'}
    $id=[string]$t.Principal.UserId
    try {
        $sid=if($id -match '^S-1-[0-9-]+$'){$id}else{
            ([Security.Principal.NTAccount]::new($id)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
    } catch {throw 'UCIE_W22_TASK_OWNER_SID_UNVERIFIED'}
    if($sid -ne $script:ownerSid) {throw 'UCIE_W22_TASK_OWNER_MISMATCH'}
    return $t
}
function CheckOld([int]$index) {
    $s=$specs[$index]
    $t=OwnerTask $s.Name
    $a=$t.Actions[0]
    if (-not [string]::Equals([string]$a.Execute,$s.Executable,
                              [StringComparison]::OrdinalIgnoreCase) -or
        -not [string]::Equals([string]$a.Arguments,$s.Arguments,
                              [StringComparison]::Ordinal) -or
        -not [string]::Equals([string]$a.WorkingDirectory,$old,
                              [StringComparison]::OrdinalIgnoreCase)) {
        throw 'UCIE_W22_ORIGINAL_TASK_ACTION_DRIFT_HOLD'
    }
    return $t
}
function C40ActionHash {
    $task=OwnerTask 'UCIE-C40-Recover'
    $a=$task.Actions[0]
    return ShaText ((@([string]$a.Execute,[string]$a.Arguments,
                      [string]$a.WorkingDirectory)) -join [char]0)
}
function PortState {
    # No process/commandline introspection; only count and exact bound IP.
    $listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop |
        Where-Object {$_.LocalPort -eq $port})
    if(@($listeners).Count -eq 0){return 'FREE'}
    if(@($listeners).Count -ne 1){return 'MULTIPLE_HOLD'}
    if([string]$listeners[0].LocalAddress -ne '127.0.0.1') {
        return 'NON_LOOPBACK_HOLD'
    }
    return 'ONE_LOOPBACK_LISTENER'
}
function HealthyOld {
    try {
        $p=Invoke-RestMethod -Uri 'http://127.0.0.1:18767/local/health' -Method Get -TimeoutSec 2 -ErrorAction Stop
        return ($p.schema -eq 'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01' -and
                $p.status -eq 'LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE' -and
                $p.bound_host -eq '127.0.0.1' -and [int]$p.bound_port -eq $port -and
                $p.owner_acceptance_verified -eq $true -and
                $p.online_release_authorized -eq $false -and
                $p.operating_database_writes -eq 0)
    } catch {return $false}
}
function WaitFreePort {
    for($i=0;$i -lt 30;$i++){
        if((PortState) -eq 'FREE'){return $true}
        Start-Sleep -Milliseconds 300
    }
    return $false
}
function CheckOldDisabled {
    foreach($i in 0..2) {
        $task=CheckOld $i
        if([string]$task.State -ne 'Disabled') {
            throw 'UCIE_W22_OLD_TASK_NOT_DISABLED'
        }
    }
}
$expected=[IO.Path]::GetFullPath($scriptPath)
if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
                        $expected,[StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W22_EXACT_NEWROOT_SCRIPT_REQUIRED'
}
foreach($p in @($old,$root,$archive)) {Direct $p $true}
foreach($p in @($scriptPath,$w21)) {Direct $p $false}
$script:ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
if(-not $acl.AreAccessRulesProtected -or
   $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:ownerSid){
    throw 'UCIE_W22_PRIVATE_OWNER_ACL_REQUIRED'
}
$previous=$env:GIT_OPTIONAL_LOCKS;$env:GIT_OPTIONAL_LOCKS='0'
try {
    $remote=(& git -C $root remote get-url origin 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or
       -not [string]::Equals($remote,
           'https://github.com/tmdrkdtn1-project/UCIE.git',
           [StringComparison]::Ordinal)) {
        throw 'UCIE_W22_CANONICAL_FIRST_PARTY_REMOTE_REQUIRED'
    }
    & git -C $root merge-base --is-ancestor $base HEAD 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw 'UCIE_W22_W21_ANCESTOR_REQUIRED'}
    $dirty=(& git -C $root status --porcelain --untracked-files=all 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $dirty.Length -gt 0) {
        throw 'UCIE_W22_STAGED_GIT_WORKTREE_NOT_CLEAN'
    }
} finally {$env:GIT_OPTIONAL_LOCKS=$previous}
Import-Module ScheduledTasks -ErrorAction Stop
$baseline=C40ActionHash
if($ApplyLocal) {
    Absent $intent
    Absent $resumeReceipt
    foreach($p in @($w21Journal,$w19Journal,$w13Journal,$w20Journal,
                    $w19Rollback,$w20Rollback,$w21Rollback,$targetRuntime,
                    $w19Data,$marker)) {Absent $p}
    # W23 repairs Windows PowerShell 5.1 native argument quoting: never
    # forward a multiline Python -c program. Use a checked-in Python FILE
    # with ASCII-only arguments, directly (no pipelines, preserving TTY).
    # This is before W22 intent creation / task disable / any SQLite open.
    Direct $python $false
    Direct $w19Python $false
    Direct $w23Lineage $false
    & $python -I -B $w23Lineage --check-owner --owner-approval $w23Approval
    if($LASTEXITCODE -ne 0) {
        throw 'UCIE_W22_W19_PRIVATE_LINEAGE_GATE_HOLD_BEFORE_OUTAGE'
    }
    $states=@('Ready','Ready','Running')
    foreach($i in 0..2){
        $t=CheckOld $i
        if([string]$t.State -cne $states[$i]){
            throw 'UCIE_W22_EXACT_ORIGINAL_STATES_REQUIRED'
        }
    }
    if([string](OwnerTask 'UCIE-C40-Recover').State -ne 'Running') {
        throw 'UCIE_W22_C40_TASK_NOT_RUNNING_HOLD'
    }
    if((PortState) -ne 'ONE_LOOPBACK_LISTENER' -or -not (HealthyOld)) {
        throw 'UCIE_W22_ORIGINAL_LOCALV1_HEALTH_OR_PORT_HOLD'
    }
    # PRIVATE intent before disabling, stopping, or writing SQLite.
    SavePrivate $intent ([ordered]@{
        schema=$schema;status='UCIE_W22_OWNER_MAINTENANCE_QUIESCE_INTENT'
        owner_sid_sha256=(ShaText $script:ownerSid)
        c40_action_sha256=$baseline
        original_task_names=@($names)
        original_task_states=$states
        original_tasks_exact_old_actions=$true
        old_local_port_present=$true
        original_database_overwritten=$false
        c40_mcp_round_trip_verified=$false
        full_cutover_authorized=$false
    })
    # Scheduled jobs may run between observations; W19 still obtains all DB
    # writer locks. This stage never falsely claims a global non-SQLite freeze.
    foreach($i in 0..2) {
        [void](CheckOld $i)
        Disable-ScheduledTask -TaskPath '\' -TaskName $names[$i] -ErrorAction Stop | Out-Null
    }
    # Stop only the exactly owner-bound UCIE LocalV1 Scheduled Task; DO NOT
    # kill the unknown Python socket owner, even if the listener survives.
    try {
        Stop-ScheduledTask -TaskPath '\' -TaskName $names[2] -ErrorAction Stop
    } catch {
        if((PortState) -ne 'FREE'){
            throw 'UCIE_W22_LOCAL_TASK_STOP_FAILED_PORT_HELD_EXPLICIT_RESUME'
        }
    }
    CheckOldDisabled
    if(-not (WaitFreePort)) {
        throw 'UCIE_W22_LISTENER_NOT_RELEASED_BY_OLD_TASK_EXPLICIT_RESUME'
    }
    if((C40ActionHash) -ne $baseline){
        throw 'UCIE_W22_C40_ACTION_DRIFT_STOP'
    }
    & $w21 -ApplyLocal -OwnerApproval $w21Apply
    if((C40ActionHash) -ne $baseline) {
        throw 'UCIE_W22_C40_ACTION_DRIFT_AFTER_W21'
    }
    Direct $w21Journal $false
    # W21 itself verifies new-root LocalV1 and writer Disabled states.
    [pscustomobject]@{
        schema=$schema
        status='UCIE_W22_W21_LOCAL_ONLY_PILOT_STAGED__TWO_WRITERS_C40_HOLD'
        old_three_tasks_quiesced_before_handoff=$true
        original_local_listener_released_before_pilot=$true
        owner_w21_local_stage_invoked=$true
        writer_tasks_enabled=0
        c40_action_unchanged=$true
        c40_mcp_round_trip_verified=$false
        original_sqlite_replaced_or_deleted=$false
        original_task_availability_automatically_restored=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
# -ResumeOld: exact stateful rollback of W21 (if staged) followed by
# OLD LocalV1 availability + original two enabled writer schedules.
Direct $intent $false
Absent $resumeReceipt
$record=Get-Content -LiteralPath $intent -Raw -Encoding UTF8 |
    ConvertFrom-Json -ErrorAction Stop
if($record.schema -ne $schema -or
   $record.status -ne 'UCIE_W22_OWNER_MAINTENANCE_QUIESCE_INTENT' -or
   $record.owner_sid_sha256 -ne (ShaText $script:ownerSid) -or
   $record.c40_action_sha256 -ne $baseline -or
   @($record.original_task_states).Count -ne 3 -or
   @($record.original_task_names).Count -ne 3 -or
   $record.original_tasks_exact_old_actions -ne $true) {
    throw 'UCIE_W22_RESUME_JOURNAL_MISMATCH'
}
foreach($i in 0..2) {
    if($record.original_task_names[$i] -ne $names[$i] -or
       $record.original_task_states[$i] -cne @('Ready','Ready','Running')[$i]) {
        throw 'UCIE_W22_UNEXPECTED_ORIGINAL_AVAILABILITY'
    }
}
if(Test-Path -LiteralPath $w21Journal) {
    # The W21 rollback is always delegated; it preserves both DBs and
    # restores OLD three task actions in Disabled status only.
    & $w21 -RollbackLocal -OwnerApproval $w21Rollback
    if($LASTEXITCODE -is [int] -and $LASTEXITCODE -ne 0) {
        throw 'UCIE_W22_W21_ROLLBACK_RETURNED_ERROR'
    }
} elseif((Test-Path -LiteralPath $w19Journal) -or
         (Test-Path -LiteralPath $w20Journal) -or
         (Test-Path -LiteralPath $w13Journal)) {
    throw 'UCIE_W22_PARTIAL_STAGE_WITHOUT_W21_JOURNAL_MANUAL_HOLD'
}
# Partial quiescence may have disabled only one task. Do not reject an
# otherwise exact OLD task merely because maintenance interrupted halfway.
foreach($i in 0,1) {
    $state=[string](CheckOld $i).State
    if($state -notin @('Disabled','Ready','Running')) {
        throw 'UCIE_W22_UNEXPECTED_OLD_WRITER_STATE_HOLD'
    }
}
$localState=[string](CheckOld 2).State
if($localState -notin @('Disabled','Ready','Running')) {
    throw 'UCIE_W22_UNEXPECTED_OLD_LOCAL_STATE_HOLD'
}
if($localState -eq 'Running' -and (PortState) -eq 'ONE_LOOPBACK_LISTENER' -and
   (HealthyOld)) {
    $localRestored='ALREADY_RUNNING_HTTP_HEALTHY'
} else {
    # Never start the old LocalV1 while a foreign or unknown listener holds
    # port 18767. The presence of HTTP schema does not prove task identity.
    if((PortState) -ne 'FREE') {
        throw 'UCIE_W22_PORT_OCCUPIED_NO_BLIND_OLD_RESTART'
    }
    if($localState -eq 'Disabled') {
        Enable-ScheduledTask -TaskPath '\' -TaskName $names[2] -ErrorAction Stop | Out-Null
    }
    Start-ScheduledTask -TaskPath '\' -TaskName $names[2] -ErrorAction Stop
    $healthy=$false
    for($i=0;$i -lt 25;$i++){
        if((PortState) -eq 'ONE_LOOPBACK_LISTENER' -and (HealthyOld) -and
           [string](CheckOld 2).State -eq 'Running') {
            $healthy=$true
            break
        }
        Start-Sleep -Milliseconds 350
    }
    if(-not $healthy) {
        throw 'UCIE_W22_OLD_LOCALV1_RESUME_FAILED_MANUAL_HOLD'
    }
    $localRestored='START_REQUESTED_HTTP_HEALTHY'
}
foreach($i in 0,1) {
    $task=CheckOld $i
    if([string]$task.State -eq 'Disabled') {
        Enable-ScheduledTask -TaskPath '\' -TaskName $names[$i] -ErrorAction Stop | Out-Null
    }
}
foreach($i in 0,1) {
    if([string](CheckOld $i).State -notin @('Ready','Running')) {
        throw 'UCIE_W22_ORIGINAL_WRITER_SCHEDULE_NOT_RESTORED'
    }
}
$restored='ORIGINAL_SCHEDULE_STATES_RESTORED__LOCAL_HTTP_HEALTHY'
if((C40ActionHash) -ne $baseline){
    throw 'UCIE_W22_C40_ACTION_DRIFT_AFTER_RECOVERY'
}
SavePrivate $resumeReceipt ([ordered]@{
    schema=$schema;status='UCIE_W22_ORIGINAL_TASK_SCHEDULES_AND_LOCAL_HTTP_RESTORED'
    restoration=$restored
    old_local_http_healthy=$true
    listener_task_pid_identity_verified=$false
    original_writer_schedules_enabled=2
    c40_action_unchanged=$true
    c40_mcp_round_trip_verified=$false
    original_sqlite_restored_or_overwritten=$false
    new_private_sqlite_copies_preserved=$true
    full_cutover_authorized=$false
})
[pscustomobject]@{
    schema=$schema
    status='UCIE_W22_ORIGINAL_SCHEDULES_RESTORED__HTTP_HEALTHY_PID_AND_C40_HOLD'
    restoration=$restored
    old_local_http_healthy=$true
    listener_task_pid_identity_verified=$false
    original_writer_schedules_enabled=2
    c40_action_unchanged=$true
    old_sqlite_unchanged_by_w22=$true
    c40_mcp_round_trip_verified=$false
    full_cutover_authorized=$false
} | ConvertTo-Json -Compress
