# UCIE W26: exact patched W19 "Same" comparator on CURRENT owner Task actions.
# No ScheduledTask state change. The old W19 Apply/Disabled-state is NEVER run.
# Default contract-only accesses NO host, files, Tasks, network or SQLite.
[CmdletBinding()]
param([switch]$ContractOnly,[switch]$CheckLocal,[string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W26_PATCHED_W19_REAL_TASK_COMPARATOR_READONLY_V01'
$approval='AUTHORIZE_UCIE_W26_READONLY_PATCHED_W19_HOST_ACTION_COMPARISON'
$root='D:\UCIE_PROJECT\UCIE'
$old='D:\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$self=$root+'\scripts\ucie_owner_w26_real_task_action_check_v01.ps1'
$w19=$root+'\scripts\ucie_owner_w19_data_task_stage_v01.ps1'
$sourceCommit='b5f3d05db9c2dd13e23a066c96a5c73dda5a2920'
$w19Blob='17e1620659c15a570313c4d87fa425227f076839'
$names=@('UCIE-PublicMiner-Hourly','UCIE-Internal-Minute','UCIE-LocalV1-Web')
$specs=@(
    [pscustomobject]@{
        Name=$names[0];Execute='D:\UCIE\.venv\Scripts\python.exe'
        Arguments='"D:\UCIE\scripts\public_miner_cycle.py"';State='Ready'
    },
    [pscustomobject]@{
        Name=$names[1];Execute='D:\UCIE\.venv\Scripts\python.exe'
        Arguments='-B "D:\UCIE\scripts\internal_minute_tick.py"';State='Ready'
    },
    [pscustomobject]@{
        Name=$names[2];Execute='D:\UCIE\.venv\Scripts\pythonw.exe'
        Arguments='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'
        State='Running'
    }
)
if(-not $CheckLocal){$ContractOnly=$true}
if($ContractOnly){
    if($CheckLocal){throw 'UCIE_W26_CONFLICTING_CONTRACT_AND_OWNER_MODES'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W26_CONTRACT_ONLY_NO_HOST_ACCESS'
        host_files_read=$false;owner_tasks_queried=$false
        sqlite_opened=$false;port_probed=$false
        c40_queried_or_modified=$false;task_action_modified=$false
        task_schedules_changed=$false;journal_written=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if(-not [string]::Equals($OwnerApproval,$approval,[StringComparison]::Ordinal)){
    throw 'UCIE_W26_EXPLICIT_READONLY_OWNER_APPROVAL_REQUIRED'
}
if($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive){
    throw 'UCIE_W26_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
$id=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($id)
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    throw 'UCIE_W26_SAME_OWNER_ELEVATED_TOKEN_REQUIRED'
}
function Direct([string]$path,[bool]$directory){
    $item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if([bool]$item.PSIsContainer -ne $directory){
        throw 'UCIE_W26_PATH_TYPE_HOLD'
    }
    while($null -ne $item -and
          $item.FullName.StartsWith('D:\',[StringComparison]::OrdinalIgnoreCase)){
        if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
            throw 'UCIE_W26_REPARSE_PATH_DENIED'
        }
        if($item -is [IO.FileInfo]){$item=$item.Directory}
        else {$item=$item.Parent}
    }
}
foreach($dir in @($old,$root,$archive)){Direct $dir $true}
foreach($file in @($self,$w19)){Direct $file $false}
if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
                        [IO.Path]::GetFullPath($self),
                        [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W26_EXACT_FIRST_PARTY_ENTRYPOINT_REQUIRED'
}
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
if(-not $acl.AreAccessRulesProtected -or
   $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $id.User.Value){
    throw 'UCIE_W26_SAME_OWNER_PRIVATE_ARCHIVE_REQUIRED'
}
# Pin committed W19 comparator bytes by Git blob, and reject owner worktree
# modifications. This protects AST ScriptBlock extraction from unreviewed code.
$prior=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    $remote=(& git -C $root remote get-url origin 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $remote -cne
       'https://github.com/tmdrkdtn1-project/UCIE.git'){
        throw 'UCIE_W26_FIRST_PARTY_REMOTE_HOLD'
    }
    & git -C $root merge-base --is-ancestor $sourceCommit HEAD 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw 'UCIE_W26_SOURCE_ANCESTRY_HOLD'}
    $blob=(& git -C $root rev-parse 'HEAD:scripts/ucie_owner_w19_data_task_stage_v01.ps1' |
           Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $blob -cne $w19Blob){
        throw 'UCIE_W26_W19_PINNED_GIT_BLOB_CHANGED_HOLD'
    }
    $dirty=(& git -C $root status --porcelain --untracked-files=all 2>$null |
            Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $dirty.Length -gt 0){
        throw 'UCIE_W26_WORKTREE_DRIFT_HOLD'
    }
} finally {$env:GIT_OPTIONAL_LOCKS=$prior}
# Parse first-party W19 source, but execute ONLY its pure Same function.
# Never dot-source the entire W19 owner Apply script.
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile(
    $w19,[ref]$tokens,[ref]$errors)
if(@($errors).Count -gt 0){throw 'UCIE_W26_W19_SOURCE_PARSE_HOLD'}
$sameFunctionAsts=@($ast.FindAll({
    param($node)
    ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
     $node.Name -ceq 'Same')
},$true))
if($sameFunctionAsts.Count -ne 1){throw 'UCIE_W26_EXACTLY_ONE_W19_SAME_REQUIRED'}
$pure=$sameFunctionAsts[0].Extent.Text
if(-not $pure.StartsWith(
       'function Same($action,[string]$exe,[string]$expectedArguments,[string]$work) {',
       [StringComparison]::Ordinal) -or
   -not $pure.Contains(
       '[string]::Equals([string]$action.Arguments,$expectedArguments,[StringComparison]::Ordinal)')){
    throw 'UCIE_W26_W19_PURE_COMPARATOR_SIGNATURE_CHANGED'
}
. ([scriptblock]::Create($pure))
Import-Module ScheduledTasks -ErrorAction Stop
$states=@()
foreach($spec in $specs){
    $t=Get-ScheduledTask -TaskPath '\' -TaskName $spec.Name -ErrorAction Stop
    if(@($t.Actions).Count -ne 1){
        throw 'UCIE_W26_TASK_ACTION_COUNT_CHANGED'
    }
    $account=[string]$t.Principal.UserId
    try {
        $sid=if($account -match '^S-1-[0-9-]+$'){$account}else{
            ([Security.Principal.NTAccount]::new($account)).Translate(
                [Security.Principal.SecurityIdentifier]).Value
        }
    } catch {throw 'UCIE_W26_TASK_PRINCIPAL_NOT_RESOLVED'}
    if($sid -ne $id.User.Value){throw 'UCIE_W26_TASK_OWNER_CHANGED_HOLD'}
    $actualState=[string]$t.State
    if($actualState -cne $spec.State -and
       -not ($actualState -ceq 'Running' -and $spec.State -ceq 'Ready')){
        throw 'UCIE_W26_ORIGINAL_RUNNING_TASK_STATES_CHANGED'
    }
    if(-not (Same ($t.Actions[0]) $spec.Execute $spec.Arguments $old)){
        throw 'UCIE_W26_REAL_HOST_W19_COMPARATOR_FALSE_DRIFT_HOLD'
    }
    $states+= [pscustomobject]@{
        task=$spec.Name;task_state=$actualState;action_match='PASS'
        task_owner_match=$true
    }
}
[pscustomobject]@{
    schema=$schema
    status='UCIE_W26_REAL_HOST_W19_PATCHED_SAME_PASS__DISABLED_APPLY_NOT_REPLAYED'
    tasks=$states
    pinned_w19_git_blob_verified=$true
    w19_actual_pure_same_function_executed=$true
    expected_original_actions_match_count=3
    original_writers_paused_for_test=$false
    historical_owner_w21_exception_recovered=$false
    original_owner_failure_root_cause_verified=$false
    operating_sqlite_opened=$false
    task_or_c40_modified=$false
    journal_written=$false
    c40_mcp_round_trip_verified=$false
    full_cutover_authorized=$false
} | ConvertTo-Json -Depth 6 -Compress
