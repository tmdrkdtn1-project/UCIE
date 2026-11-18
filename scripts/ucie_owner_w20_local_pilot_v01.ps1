# UCIE W20: owner-only, LocalV1-only activation pilot + fail-closed rollback.
# W19 three Python task actions MUST ALREADY be safely rebound but Disabled.
# No PublicMiner/Internal activation, no C40 restart/rebind/profile access, no DB rollback.
[CmdletBinding()]
param([switch]$ContractOnly,[switch]$PilotLocal,[switch]$RollbackLocal,
      [string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W20_OWNER_LOCAL_ACTIVATION_PILOT_V01'
$old='D:\UCIE'
$root='D:\UCIE_PROJECT\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$journal=$archive+'\UCIE_W20_LOCAL_PILOT_JOURNAL_V01.json'
$rollbackReceipt=$archive+'\UCIE_W20_LOCAL_PILOT_ROLLBACK_V01.json'
$w19Journal=$archive+'\UCIE_W19_OWNER_DATA_TASK_STAGE_JOURNAL_V01.json'
$w13Journal=$archive+'\UCIE_W13_TASK_REBIND_V01.json'
$marker=$archive+'\.ucie_owner_runtime_opt_in_v01'
$manifest=$archive+'\UCIE_W19_LOCKSTEP_FINAL_DATA_V01\private_handoff_manifest.json'
$drift=$root+'\scripts\ucie_owner_w20_activation_integrity_v01.py'
$python=$root+'\.venv\Scripts\python.exe'
$w19=$root+'\scripts\ucie_owner_w19_data_task_stage_v01.ps1'
$w19Approval='AUTHORIZE_UCIE_W19_RESTORE_OLD_DISABLED_TASK_ACTIONS'
$driftApproval='AUTHORIZE_UCIE_W20_READONLY_WRITER_BARRIER_CHECK'
$pilotApproval='AUTHORIZE_UCIE_W20_OWNER_LOCALV1_PILOT_ONLY'
$rollbackApproval='AUTHORIZE_UCIE_W20_OWNER_LOCALV1_ROLLBACK'
$targetHead='301a13bc6a8228ed0d979dc36913c4da68f35e3a'
$port=18767
$known=@(
    [pscustomobject]@{
        Name='UCIE-PublicMiner-Hourly'
        Executable='D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe'
        Arguments='"D:\UCIE_PROJECT\UCIE\scripts\public_miner_cycle.py" --owner-relocated-runtime'
    },
    [pscustomobject]@{
        Name='UCIE-Internal-Minute'
        Executable='D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe'
        Arguments='-B "D:\UCIE_PROJECT\UCIE\scripts\internal_minute_tick.py" --owner-relocated-runtime'
    },
    [pscustomobject]@{
        Name='UCIE-LocalV1-Web'
        Executable='D:\UCIE_PROJECT\UCIE\.venv\Scripts\pythonw.exe'
        Arguments='-B "D:\UCIE_PROJECT\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767 --owner-relocated-runtime'
    }
)
if (-not $PilotLocal -and -not $RollbackLocal) {$ContractOnly=$true}
if ($ContractOnly) {
    if ($PilotLocal -or $RollbackLocal) {throw 'UCIE_W20_CONTRACT_MUTATION_DENIED'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W20_CONTRACT_ONLY_NO_HOST_ACCESS'
        tasks_queried=$false;task_started=$false;task_enabled=$false
        local_http_probed=$false;sqlite_opened=$false;c40_accessed=$false
        db_restored_or_deleted=$false;live_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if ($PilotLocal.IsPresent -eq $RollbackLocal.IsPresent) {
    throw 'UCIE_W20_EXACT_ONE_OWNER_MODE_REQUIRED'
}
$required=if ($PilotLocal) {$pilotApproval} else {$rollbackApproval}
if (-not [string]::Equals($OwnerApproval,$required,[StringComparison]::Ordinal)) {
    throw 'UCIE_W20_EXPLICIT_OWNER_APPROVAL_REQUIRED'
}
if ($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive) {
    throw 'UCIE_W20_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
function Direct([string]$path,[bool]$dir) {
    $node=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if ([bool]$node.PSIsContainer -ne $dir) {throw 'UCIE_W20_PATH_TYPE_MISMATCH'}
    while ($null -ne $node -and
           $node.FullName.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'UCIE_W20_REPARSE_PATH_DENIED'
        }
        if ($node -is [System.IO.FileInfo]) {$node=$node.Directory}
        else {$node=$node.Parent}
    }
}
function Absent([string]$path) {
    $found=Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    if ($null -ne $found -or [IO.File]::Exists($path) -or
        [IO.Directory]::Exists($path)) {throw 'UCIE_W20_ALREADY_EXISTS_NO_RETRY'}
}
function HashText([string]$text) {
    $hash=[Security.Cryptography.SHA256]::Create()
    try {
        $data=[Text.Encoding]::UTF8.GetBytes($text)
        return [BitConverter]::ToString($hash.ComputeHash($data)).Replace('-','').ToLowerInvariant()
    } finally {$hash.Dispose()}
}
function PrivateJson([string]$path,$value) {
    Absent $path
    $temp=$archive+'\UCIE_W20_'+[guid]::NewGuid().ToString('N')+'.tmp'
    try {
        [IO.File]::WriteAllText($temp,(ConvertTo-Json $value -Compress -Depth 6),
                               [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($temp,$path)
    } finally {
        if (Test-Path -LiteralPath $temp) {
            Remove-Item -LiteralPath $temp -ErrorAction Stop
        }
    }
}
function Task([string]$name) {
    $task=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
    if (@($task.Actions).Count -ne 1) {throw 'UCIE_W20_UNKNOWN_TASK_ACTION_COUNT'}
    $account=[string]$task.Principal.UserId
    try {
        $sid=if ($account -match '^S-1-[0-9-]+$') {$account} else {
            ([Security.Principal.NTAccount]::new($account)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
    } catch {throw 'UCIE_W20_TASK_OWNER_NOT_VERIFIED'}
    if ($sid -ne $script:ownerSid) {throw 'UCIE_W20_TASK_OWNER_MISMATCH'}
    return $task
}
function C40Hash {
    $c=Get-ScheduledTask -TaskPath '\' -TaskName 'UCIE-C40-Recover' -ErrorAction Stop
    if (@($c.Actions).Count -ne 1) {throw 'UCIE_W20_C40_ACTION_COUNT_UNEXPECTED'}
    $a=$c.Actions[0]
    return HashText ((@([string]$a.Execute,[string]$a.Arguments,
                       [string]$a.WorkingDirectory)) -join [char]0)
}
function SameNew($task,$spec) {
    $a=$task.Actions[0]
    return ([string]::Equals([string]$a.Execute,$spec.Executable,
                [StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals([string]$a.Arguments,$spec.Arguments,
                [StringComparison]::Ordinal) -and
            [string]::Equals([string]$a.WorkingDirectory,$root,
                [StringComparison]::OrdinalIgnoreCase))
}
function RequireThreeActions {
    foreach ($spec in $known) {
        $t=Task $spec.Name
        if (-not (SameNew $t $spec)) {throw 'UCIE_W20_NEW_TASK_ACTION_UNEXPECTED'}
    }
}
function RequireTwoDisabled {
    foreach ($idx in 0,1) {
        if ([string](Task $known[$idx].Name).State -ne 'Disabled') {
            throw 'UCIE_W20_OTHER_PYTHON_TASK_ENABLED_NO_GO'
        }
    }
}
function ListenerCount {
    $tcp=[Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties()
    return @($tcp.GetActiveTcpListeners() | Where-Object {$_.Port -eq $port}).Count
}
function LocalHealth {
    $uri='http://127.0.0.1:18767/local/health'
    for ($i=0;$i -lt 20;$i++) {
        try {
            $h=Invoke-RestMethod -Method Get -Uri $uri -TimeoutSec 2 -ErrorAction Stop
            if ($h.schema -eq 'UCIE_OWNER_LOCAL_FOUR_PILLAR_APP_V01' -and
                $h.status -eq 'LOCAL_V1_OWNER_ACCEPTED_LOCAL_GO_NO_ONLINE_RELEASE' -and
                $h.bound_host -eq '127.0.0.1' -and $h.bound_port -eq $port -and
                $h.owner_acceptance_verified -eq $true -and
                $h.online_release_authorized -eq $false -and
                $h.operating_database_writes -eq 0) {return $true}
            throw 'UCIE_W20_LOCAL_HEALTH_FOREIGN_SCHEMA'
        } catch {
            if ($i -eq 19) {return $false}
        }
        Start-Sleep -Milliseconds 250
    }
    return $false
}
function StopDisableLocal {
    $t=Task $known[2].Name
    if (-not (SameNew $t $known[2])) {throw 'UCIE_W20_ROLLBACK_UNKNOWN_LOCAL_TASK'}
    Disable-ScheduledTask -TaskPath '\' -TaskName $known[2].Name -ErrorAction Stop | Out-Null
    # Scheduler may report Disabled while the previously started process
    # remains alive; stopping exact owner LocalV1 is allowed, C40 untouched.
    try {
        Stop-ScheduledTask -TaskPath '\' -TaskName $known[2].Name -ErrorAction Stop
    } catch {
        if ((ListenerCount) -ne 0) {
            throw 'UCIE_W20_LOCAL_TASK_STOP_UNVERIFIED'
        }
    }
    for ($i=0;$i -lt 20;$i++) {
        $t=Task $known[2].Name
        if ([string]$t.State -eq 'Disabled' -and (ListenerCount) -eq 0) {return}
        Start-Sleep -Milliseconds 250
    }
    throw 'UCIE_W20_LOCAL_PILOT_DID_NOT_QUIESCE'
}
$expected=$root+'\scripts\ucie_owner_w20_local_pilot_v01.ps1'
if (-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
        $expected,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_W20_EXACT_NEW_CHECKOUT_SCRIPT_REQUIRED'
}
foreach ($path in @($old,$root,$archive,$root+'\runtime')) {Direct $path $true}
foreach ($path in @($expected,$drift,$python,$w19,$w19Journal,$w13Journal,$manifest,$marker)) {
    Direct $path $false
}
$script:ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
if (-not $acl.AreAccessRulesProtected -or
    $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:ownerSid) {
    throw 'UCIE_W20_PRIVATE_OWNER_ARCHIVE_REQUIRED'
}
$prior=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    & git -C $root merge-base --is-ancestor $targetHead HEAD 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {throw 'UCIE_W20_W19_BASE_NOT_ANCESTOR'}
} finally {$env:GIT_OPTIONAL_LOCKS=$prior}
$original=[IO.File]::ReadAllBytes($marker)
$valid=[Text.Encoding]::ASCII.GetBytes('UCIE_OWNER_RELOCATED_RUNTIME_OPT_IN_V01'+[char]10)
if ($original.Length -ne $valid.Length) {throw 'UCIE_W20_OWNER_MARKER_CHANGED'}
for ($i=0;$i -lt $original.Length;$i++) {
    if ($original[$i] -ne $valid[$i]) {throw 'UCIE_W20_OWNER_MARKER_CHANGED'}
}
$stage=Get-Content -LiteralPath $w19Journal -Raw -Encoding UTF8 | ConvertFrom-Json
$rebinding=Get-Content -LiteralPath $w13Journal -Raw -Encoding UTF8 | ConvertFrom-Json
if ($stage.schema -ne 'UCIE_W19_OWNER_DATA_TASK_STAGE_V01' -or
    $stage.status -ne 'UCIE_W19_OWNER_STAGE_STARTED_NOT_LIVE' -or
    $stage.owner_sid_sha256 -ne (HashText $script:ownerSid) -or
    $stage.old_root -ne $old -or $stage.new_root -ne $root -or
    $stage.task_actions_initial -ne 'THREE_ORIGINAL_DISABLED' -or
    $stage.tasks_enabled -ne 0 -or
    @($stage.task_names).Count -ne 3 -or
    $rebinding.schema -ne 'UCIE_W13_OWNER_TASK_REBIND_V01') {
    throw 'UCIE_W20_PRIVATE_STAGE_JOURNAL_MISMATCH'
}
foreach ($i in 0..2) {
    if ($stage.task_names[$i] -ne $known[$i].Name) {
        throw 'UCIE_W20_STAGE_TASK_NAMES_MISMATCH'
    }
}
Import-Module ScheduledTasks -ErrorAction Stop
$originalC40=C40Hash
if ($originalC40 -ne $stage.c40_action_sha256 -or
    $originalC40 -ne $rebinding.c40_sha256) {
    throw 'UCIE_W20_C40_ORIGINAL_ACTION_DRIFT'
}
RequireThreeActions
RequireTwoDisabled
if ($PilotLocal) {
    Absent $journal
    Absent $rollbackReceipt
    if ([string](Task $known[2].Name).State -ne 'Disabled') {
        throw 'UCIE_W20_LOCAL_TASK_MUST_BE_DISABLED'
    }
    if ((ListenerCount) -ne 0) {throw 'UCIE_W20_LOCAL_LOOPBACK_PORT_IN_USE'}
    # Verify actual old and new SQLite data immediately BEFORE enabling.
    & $python -I -B $drift --verify --owner-approval $driftApproval
    if ($LASTEXITCODE -ne 0) {throw 'UCIE_W20_SQLITE_POST_HANDOFF_DRIFT_HOLD'}
    PrivateJson $journal ([ordered]@{
        schema=$schema;status='UCIE_W20_LOCAL_ONLY_PILOT_STARTED'
        owner_sid_sha256=(HashText $script:ownerSid)
        c40_action_sha256=$originalC40
        source_w19_manifest_sha256=(Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
        other_two_task_actions_held_disabled=$true
        original_sqlite_restored_or_deleted=$false
        live_cutover_authorized=$false
    })
    try {
        Enable-ScheduledTask -TaskPath '\' -TaskName $known[2].Name -ErrorAction Stop | Out-Null
        Start-ScheduledTask -TaskPath '\' -TaskName $known[2].Name -ErrorAction Stop
        if (-not (LocalHealth)) {throw 'UCIE_W20_LOCAL_HEALTH_NOT_VERIFIED'}
        RequireThreeActions
        RequireTwoDisabled
        if ((C40Hash) -ne $originalC40) {throw 'UCIE_W20_C40_ACTION_CHANGED'}
        [pscustomobject]@{
            schema=$schema;status='UCIE_W20_LOCALV1_LOOPBACK_HEALTH_PASS__C40_AND_TWO_TASKS_HOLD'
            localv1_health='HTTP_SCHEMA_PASS';localv1_start_requested=$true
            public_miner_enabled=$false;internal_minute_enabled=$false
            c40_action_unchanged=$true;c40_mcp_round_trip_verified=$false
            old_data_restored_or_deleted=$false;live_cutover_authorized=$false
        } | ConvertTo-Json -Compress
        return
    } catch {
        try {StopDisableLocal} catch {
            throw 'UCIE_W20_LOCAL_PILOT_FAILED_AND_QUIESCENCE_UNVERIFIED'
        }
        throw 'UCIE_W20_LOCAL_PILOT_FAILED_PRESERVE_JOURNAL_RUN_EXPLICIT_ROLLBACK'
    }
}
# Explicit owner rollback of W20 local pilot, even if partially started.
Direct $journal $false
Absent $rollbackReceipt
$record=Get-Content -LiteralPath $journal -Raw -Encoding UTF8 | ConvertFrom-Json
if ($record.schema -ne $schema -or
    $record.status -ne 'UCIE_W20_LOCAL_ONLY_PILOT_STARTED' -or
    $record.owner_sid_sha256 -ne (HashText $script:ownerSid) -or
    $record.c40_action_sha256 -ne $originalC40 -or
    $record.source_w19_manifest_sha256 -ne
        (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()) {
    throw 'UCIE_W20_LOCAL_ROLLBACK_JOURNAL_CHANGED'
}
StopDisableLocal
RequireThreeActions
RequireTwoDisabled
if ((C40Hash) -ne $originalC40) {throw 'UCIE_W20_C40_ACTION_DRIFT'}
# W19 owner-only rollback delegates W13 exact disabled-action restore and
# removes only the exact W12 opt-in marker; it never overwrites a SQLite DB.
& powershell.exe -NoProfile -NonInteractive -File $w19 -Rollback -OwnerApproval $w19Approval
if ($LASTEXITCODE -ne 0) {throw 'UCIE_W20_W19_ROLLBACK_FAILED_REQUIRES_OWNER_REVIEW'}
PrivateJson $rollbackReceipt ([ordered]@{
    schema=$schema;status='UCIE_W20_LOCAL_PILOT_OLD_BINDINGS_RESTORED_DISABLED'
    c40_action_unchanged=((C40Hash) -eq $originalC40)
    new_sqlite_data_preserved=$true;old_sqlite_never_overwritten=$true
    task_schedules_reenabled=$false;live_cutover_authorized=$false
})
[pscustomobject]@{
    schema=$schema;status='UCIE_W20_LOCAL_PILOT_ROLLED_BACK__OLD_TASKS_DISABLED'
    tasks_restored_disabled=3;old_sqlite_data_preserved=$true
    c40_action_unchanged=((C40Hash) -eq $originalC40)
    c40_mcp_round_trip_verified=$false;live_cutover_authorized=$false
} | ConvertTo-Json -Compress
