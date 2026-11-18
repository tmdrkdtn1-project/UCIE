# UCIE W13: owner-only reversible Task Scheduler action rebind.
# Never stops/starts jobs, changes C40, moves directories or reads databases.
[CmdletBinding()]
param([switch]$ContractOnly,[switch]$Apply,[switch]$Rollback,
      [string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W13_OWNER_TASK_REBIND_V01'
$old='D:\UCIE'
$new='D:\UCIE_PROJECT\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$journal=Join-Path $archive 'UCIE_W13_TASK_REBIND_V01.json'
$marker=Join-Path $archive '.ucie_owner_runtime_opt_in_v01'
$approval='AUTHORIZE_UCIE_W13_THREE_TASK_MAINTENANCE_REBIND'
$baseCommit='b8301014f9f8e5b2a7d40424684a98a05fcd040e'
$c40='UCIE-C40-Recover'
$specs=@(
    [pscustomobject]@{
        Name='UCIE-PublicMiner-Hourly'
        OldExec='D:\UCIE\.venv\Scripts\python.exe'
        OldArgs='"D:\UCIE\scripts\public_miner_cycle.py"'
        NewExec='D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe'
        NewArgs='"D:\UCIE_PROJECT\UCIE\scripts\public_miner_cycle.py" --owner-relocated-runtime'
        File='public_miner_cycle.py'
    },
    [pscustomobject]@{
        Name='UCIE-Internal-Minute'
        OldExec='D:\UCIE\.venv\Scripts\python.exe'
        OldArgs='-B "D:\UCIE\scripts\internal_minute_tick.py"'
        NewExec='D:\UCIE_PROJECT\UCIE\.venv\Scripts\python.exe'
        NewArgs='-B "D:\UCIE_PROJECT\UCIE\scripts\internal_minute_tick.py" --owner-relocated-runtime'
        File='internal_minute_tick.py'
    },
    [pscustomobject]@{
        Name='UCIE-LocalV1-Web'
        OldExec='D:\UCIE\.venv\Scripts\pythonw.exe'
        OldArgs='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'
        NewExec='D:\UCIE_PROJECT\UCIE\.venv\Scripts\pythonw.exe'
        NewArgs='-B "D:\UCIE_PROJECT\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767 --owner-relocated-runtime'
        File='run_ucie_local_v1_autostart.py'
    }
)
if (-not $Apply -and -not $Rollback) { $ContractOnly=$true }
if ($ContractOnly) {
    if ($Apply -or $Rollback) { throw 'UCIE_W13_CONTRACT_MUTATION_DENIED' }
    [pscustomobject]@{
        schema=$schema;status='UCIE_W13_CONTRACT_ONLY'
        planned_python_task_count=3;c40_action_modified=$false
        tasks_queried=$false;task_actions_changed=$false
        services_restarted=$false;operating_database_modified=$false
        live_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if ($Apply.IsPresent -eq $Rollback.IsPresent) {
    throw 'UCIE_W13_EXPLICIT_APPLY_OR_ROLLBACK_REQUIRED'
}
if (-not [string]::Equals($OwnerApproval,$approval,[StringComparison]::Ordinal)) {
    throw 'UCIE_W13_EXPLICIT_OWNER_APPROVAL_REQUIRED'
}
function Assert-Direct([string]$path,[bool]$directory) {
    $item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if ($item.PSIsContainer -ne $directory -or
        (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw 'UCIE_W13_REPARSE_OR_WRONG_PATH_TYPE'
    }
    $node=$item
    while ($null -ne $node -and $node.FullName.StartsWith('D:\UCIE_PROJECT',
                   [StringComparison]::OrdinalIgnoreCase)) {
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'UCIE_W13_REPARSE_ANCESTOR'
        }
        $node=$node.Parent
    }
}
function Get-OneTask([string]$name) {
    $task=Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
    $actions=@($task.Actions)
    if ($actions.Count -ne 1) { throw 'UCIE_W13_TASK_ACTION_COUNT_NOT_ONE' }
    return [pscustomobject]@{Task=$task;Action=$actions[0]}
}
function SameAction($action,[string]$exe,[string]$args,[string]$work) {
    return ([string]::Equals([string]$action.Execute,$exe,[StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals([string]$action.Arguments,$args,[StringComparison]::Ordinal) -and
            [string]::Equals([string]$action.WorkingDirectory,$work,[StringComparison]::OrdinalIgnoreCase))
}
function RequireOwnerAndPause($item) {
    if ([string]$item.Task.State -ne 'Disabled') {
        throw 'UCIE_W13_PYTHON_TASK_NOT_ALREADY_DISABLED'
    }
    try {
        $raw=[string]$item.Task.Principal.UserId
        $sid=if ($raw -match '^S-1-[0-9-]+$') {
            ([Security.Principal.SecurityIdentifier]::new($raw)).Value
        } else {
            ([Security.Principal.NTAccount]::new($raw)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
        if ($sid -ne $script:ownerSid) { throw 'OWNER_MISMATCH' }
    } catch { throw 'UCIE_W13_TASK_OWNER_UNVERIFIED' }
}
function CheckAction($spec,[bool]$isNew) {
    $p=Get-OneTask $spec.Name
    RequireOwnerAndPause $p
    $valid=if ($isNew) {
        SameAction $p.Action $spec.NewExec $spec.NewArgs $new
    } else {
        SameAction $p.Action $spec.OldExec $spec.OldArgs $old
    }
    if (-not $valid) { throw 'UCIE_W13_UNEXPECTED_TASK_ACTION' }
}
function MakeAction($spec,[bool]$isNew) {
    if ($isNew) {
        return New-ScheduledTaskAction -Execute $spec.NewExec -Argument $spec.NewArgs -WorkingDirectory $new
    }
    return New-ScheduledTaskAction -Execute $spec.OldExec -Argument $spec.OldArgs -WorkingDirectory $old
}
function HashText([string]$value) {
    $h=[Security.Cryptography.SHA256]::Create()
    try {
        $bytes=[Text.Encoding]::UTF8.GetBytes($value)
        return [BitConverter]::ToString($h.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()
    } finally { $h.Dispose() }
}
function C40ActionHash {
    $c=Get-OneTask $c40
    # Hash-only, never display C40 action arguments/profile contents.
    return HashText ((@([string]$c.Action.Execute,
                       [string]$c.Action.Arguments,
                       [string]$c.Action.WorkingDirectory)) -join [char]0)
}
function RequirePrivateArchive {
    Assert-Direct $archive $true
    $acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
    $who=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $owner=$acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
    if (-not $acl.AreAccessRulesProtected -or $owner -ne $who) {
        throw 'UCIE_W13_PRIVATE_ARCHIVE_ACL_REQUIRED'
    }
}
function RequireTarget {
    Assert-Direct $old $true
    Assert-Direct 'D:\UCIE_PROJECT' $true
    Assert-Direct $new $true
    foreach ($p in @('.git','runtime')) {
        Assert-Direct (Join-Path $new $p) $true
    }
    # W14's offline venv does not migrate ANY live state. A data-bearing new
    # runtime and private W14 setup receipt are mandatory before rebinding.
    Assert-Direct (Join-Path $new 'runtime\public_miner.sqlite3') $false
    $envReceipt=Join-Path $archive 'UCIE_W14_OFFLINE_RUNTIME_RECEIPT_V01.json'
    Assert-Direct $envReceipt $false
    $prepared=Get-Content -LiteralPath $envReceipt -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($prepared.schema -ne 'UCIE_W14_OFFLINE_RUNTIME_V01' -or
        $prepared.status -ne 'UCIE_W14_ISOLATED_OFFLINE_PYTHON_RUNTIME_PREPARED' -or
        $prepared.offline_dependency_import_ok -ne $true -or
        $prepared.operating_root_modified -ne $false -or
        $prepared.runtime_database_migrated -ne $false) {
        throw 'UCIE_W13_W14_ENVIRONMENT_RECEIPT_INVALID'
    }
    foreach ($p in @('.venv\Scripts\python.exe','.venv\Scripts\pythonw.exe',
                     'scripts\ucie_owner_root_gate_v01.py',
                     'docs\UCIE_LOCAL_V1_OWNER_ACCEPTANCE_20261108.md')) {
        Assert-Direct (Join-Path $new $p) $false
    }
    foreach ($spec in $specs) {
        Assert-Direct (Join-Path $new ('scripts\' + $spec.File)) $false
    }
    Assert-Direct $marker $false
    $expected=[Text.Encoding]::ASCII.GetBytes(
        'UCIE_OWNER_RELOCATED_RUNTIME_OPT_IN_V01' + [char]10)
    $actual=[IO.File]::ReadAllBytes($marker)
    if ($actual.Length -ne $expected.Length) { throw 'UCIE_W13_OWNER_MARKER_INVALID' }
    for ($i=0;$i -lt $expected.Length;$i++) {
        if ($actual[$i] -ne $expected[$i]) { throw 'UCIE_W13_OWNER_MARKER_INVALID' }
    }
    $prior=$env:GIT_OPTIONAL_LOCKS
    $env:GIT_OPTIONAL_LOCKS='0'
    try {
        & git -C $new merge-base --is-ancestor $baseCommit HEAD 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'UCIE_W13_ROOT_GATE_COMMIT_MISSING' }
    } finally { $env:GIT_OPTIONAL_LOCKS=$prior }
    $version=(& (Join-Path $new '.venv\Scripts\python.exe') -V 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $version.StartsWith('Python 3.15')) {
        throw 'UCIE_W13_PYTHON_315_MISSING'
    }
}
if (-not [Environment]::UserInteractive) { throw 'UCIE_W13_INTERACTIVE_OWNER_ONLY' }
$scriptPath=[IO.Path]::GetFullPath($PSCommandPath)
$expectedScript=Join-Path $new 'scripts\ucie_owner_task_rebind_v01.ps1'
if (-not [string]::Equals($scriptPath,$expectedScript,
        [StringComparison]::OrdinalIgnoreCase)) {
    throw 'UCIE_W13_EXACT_NEW_CHECKOUT_SCRIPT_REQUIRED'
}
Assert-Direct $scriptPath $false
RequirePrivateArchive
Import-Module ScheduledTasks -ErrorAction Stop
$script:ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$c40Before=C40ActionHash

if ($Apply) {
    RequireTarget
    if (Test-Path -LiteralPath $journal) { throw 'UCIE_W13_JOURNAL_EXISTS_NO_REAPPLY' }
    foreach ($spec in $specs) { CheckAction $spec $false }
    # Durable private rollback contract written before any task changes.
    $receipt=[ordered]@{
        schema=$schema
        old_root=$old
        new_root=$new
        owner_sid_sha256=(HashText $script:ownerSid)
        c40_sha256=$c40Before
        names=@($specs | ForEach-Object { $_.Name })
        actions=@($specs | ForEach-Object {
            [ordered]@{
                old_execute=$_.OldExec;old_arguments=$_.OldArgs
                new_execute=$_.NewExec;new_arguments=$_.NewArgs
            }
        })
        tasks_started=$false;c40_modified=$false
    }
    $tmp=Join-Path $archive ('UCIE_W13_' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.File]::WriteAllText($tmp,(ConvertTo-Json $receipt -Depth 6 -Compress),
                               [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($tmp,$journal)
    } finally {
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -ErrorAction Stop }
    }
    $touched=@()
    try {
        foreach ($spec in $specs) {
            $touched+= $spec
            Set-ScheduledTask -TaskPath '\' -TaskName $spec.Name -Action (MakeAction $spec $true) -ErrorAction Stop | Out-Null
            CheckAction $spec $true
        }
        if ((C40ActionHash) -ne $c40Before) { throw 'UCIE_W13_C40_ACTION_CHANGED' }
    } catch {
        $allRestored=$true
        for ($i=$touched.Count-1;$i -ge 0;$i--) {
            try {
                Set-ScheduledTask -TaskPath '\' -TaskName $touched[$i].Name -Action (MakeAction $touched[$i] $false) -ErrorAction Stop | Out-Null
                CheckAction $touched[$i] $false
            } catch { $allRestored=$false }
        }
        if (-not $allRestored) { throw 'UCIE_W13_PARTIAL_FAILURE_MANUAL_ROLLBACK_REQUIRED' }
        throw 'UCIE_W13_APPLY_FAILED_ORIGINAL_ACTIONS_RESTORED'
    }
    [pscustomobject]@{
        schema=$schema;status='UCIE_W13_THREE_TASK_ACTIONS_REBOUND_DISABLED_NOT_STARTED'
        python_tasks_rebound=3;c40_action_unchanged=$true
        tasks_started=0;tasks_enabled=0;original_source_modified=$false
        operating_sqlite_modified=$false;live_cutover_authorized=$false
        private_rollback_journal_preserved=$true
    } | ConvertTo-Json -Compress
    return
}
# Rollback: restores exact original action on each already-disabled Task.
# Accepts interrupted partial rebinds but refuses unknown/newly edited actions.
Assert-Direct $journal $false
$data=Get-Content -LiteralPath $journal -Encoding UTF8 -Raw | ConvertFrom-Json
if ($data.schema -ne $schema -or $data.old_root -ne $old -or
    $data.new_root -ne $new -or @($data.names).Count -ne 3 -or
    $data.owner_sid_sha256 -ne (HashText $script:ownerSid) -or
    $data.c40_sha256 -ne $c40Before) {
    throw 'UCIE_W13_ROLLBACK_JOURNAL_MISMATCH'
}
for ($i=0;$i -lt $specs.Count;$i++) {
    $s=$specs[$i];$a=$data.actions[$i]
    if ($data.names[$i] -ne $s.Name -or
        $a.old_execute -ne $s.OldExec -or
        $a.old_arguments -cne $s.OldArgs -or
        $a.new_execute -ne $s.NewExec -or
        $a.new_arguments -cne $s.NewArgs) {
        throw 'UCIE_W13_ROLLBACK_ACTION_CONTRACT_MISMATCH'
    }
    $t=Get-OneTask $s.Name
    RequireOwnerAndPause $t
    if (-not (SameAction $t.Action $s.OldExec $s.OldArgs $old) -and
        -not (SameAction $t.Action $s.NewExec $s.NewArgs $new)) {
        throw 'UCIE_W13_ROLLBACK_UNKNOWN_ACTION_NO_GO'
    }
}
for ($i=$specs.Count-1;$i -ge 0;$i--) {
    $spec=$specs[$i]
    $item=Get-OneTask $spec.Name
    if (-not (SameAction $item.Action $spec.OldExec $spec.OldArgs $old)) {
        Set-ScheduledTask -TaskPath '\' -TaskName $spec.Name -Action (MakeAction $spec $false) -ErrorAction Stop | Out-Null
    }
    CheckAction $spec $false
}
if ((C40ActionHash) -ne $c40Before) { throw 'UCIE_W13_C40_ACTION_DRIFT' }
[pscustomobject]@{
    schema=$schema;status='UCIE_W13_THREE_TASK_ACTIONS_ROLLED_BACK_DISABLED'
    python_tasks_restored=3;c40_action_unchanged=$true
    tasks_started=0;tasks_enabled=0;private_rollback_journal_preserved=$true
    original_source_modified=$false;operating_sqlite_modified=$false
    live_cutover_authorized=$false
} | ConvertTo-Json -Compress
