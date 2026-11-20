# W36: bounded owner read-only TaskScheduler event 129 / venv parent PID correlation.
# A matching event is NOT immutable process-launch lineage proof.
[CmdletBinding()]
param([switch]$ContractOnly,[switch]$InspectLocal,[string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W36_TASK129_PARENT_PID_EVENT_READONLY_V01'
$root='D:\UCIE_PROJECT\UCIE'
$self=$root+'\scripts\ucie_owner_w36_task129_parent_event_readonly_v01.ps1'
$w35=$root+'\scripts\ucie_owner_w31_local_listener_pid_readonly_v01.ps1'
$w35Blob='b6420a1b00336d62907440078947a50ffbc3af51'
$expectedExe='D:\UCIE\.venv\Scripts\pythonw.exe'
$expectedArgs='-B "D:\UCIE\scripts\run_ucie_local_v1_autostart.py" --port 18767'
if(-not $InspectLocal){
    if($OwnerApproval){throw 'UCIE_W36_APPROVAL_WITHOUT_INSPECTION_DENIED'}
    [pscustomobject]@{
        schema=$schema;status='UCIE_W36_CONTRACT_ONLY_NO_HOST_ACCESS'
        process_queried=$false;task_scheduler_queried_or_modified=$false
        event_log_queried_or_modified=$false;sqlite_opened=$false
        c40_queried_or_modified=$false;journal_written=$false
        task_scheduler_to_child_launch_verified=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if($ContractOnly){throw 'UCIE_W36_CONFLICTING_INSPECTION_MODES'}
if(-not [string]::Equals($OwnerApproval,
    'AUTHORIZE_UCIE_W36_READONLY_TASK129_PARENT_EVENT_INSPECTION',
    [StringComparison]::Ordinal)){
    throw 'UCIE_W36_EXPLICIT_OWNER_READONLY_APPROVAL_REQUIRED'
}
# AST-extractable pure verifier for synthetic PowerShell negative tests.
function TestExactTask129ParentEvent(
    [string]$xmlText,[datetime]$eventTime,[datetime]$listenerCreated,
    [int]$parentProcessId,[string]$taskName,[string]$taskExecutable
) {
    if([string]::IsNullOrWhiteSpace($xmlText) -or $xmlText.Length -gt 16384 -or
       $parentProcessId -le 0){return $false}
    $age=($listenerCreated-$eventTime).TotalSeconds
    if($age -lt -2 -or $age -gt 60){return $false}
    try {
        $doc=[Xml.XmlDocument]::new()
        $doc.XmlResolver=$null
        $doc.LoadXml($xmlText)
        $system=$doc.SelectSingleNode("/*[local-name()='Event']/*[local-name()='System']")
        if($null -eq $system){return $false}
        $provider=$system.SelectSingleNode("*[local-name()='Provider']")
        $eventId=$system.SelectSingleNode("*[local-name()='EventID']")
        $channel=$system.SelectSingleNode("*[local-name()='Channel']")
        if($null -eq $provider -or $null -eq $eventId -or $null -eq $channel -or
           $provider.GetAttribute('Name') -cne 'Microsoft-Windows-TaskScheduler' -or
           $eventId.InnerText -cne '129' -or
           $channel.InnerText -cne 'Microsoft-Windows-TaskScheduler/Operational'){
            return $false
        }
        $fields=@{}
        $nodes=@($doc.SelectNodes("/*[local-name()='Event']/*[local-name()='EventData']/*[local-name()='Data']"))
        foreach($node in $nodes){
            $name=[string]$node.GetAttribute('Name')
            if($name -in @('TaskName','Path','ProcessID')){
                if($fields.ContainsKey($name)){return $false}
                $fields[$name]=[string]$node.InnerText
            }
        }
        if($fields.Count -ne 3 -or
           $fields.ProcessID -cnotmatch '^[1-9][0-9]{0,9}$'){
            return $false
        }
        $observedId=[int]::Parse($fields.ProcessID)
        return (
            $fields.TaskName -ceq $taskName -and
            [string]::Equals($fields.Path,$taskExecutable,
                             [StringComparison]::OrdinalIgnoreCase) -and
            $observedId -eq $parentProcessId
        )
    } catch {
        return $false
    }
}
if($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive){
    throw 'UCIE_W36_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
                        [IO.Path]::GetFullPath($self),
                        [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W36_CANONICAL_FIRST_PARTY_SCRIPT_REQUIRED'
}
foreach($file in @($root,$self,$w35)){
    $item=Get-Item -LiteralPath $file -Force -ErrorAction Stop
    if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
       [bool]$item.PSIsContainer -ne [bool]($file -ceq $root)){
        throw 'UCIE_W36_DIRECT_FIRST_PARTY_FILES_REQUIRED'
    }
}
# Source-pinned W35: never import arbitrary local PowerShell contents.
$oldLocks=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    $remote=(& git -C $root remote get-url origin 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or
       $remote -cne 'https://github.com/tmdrkdtn1-project/UCIE.git'){
        throw 'UCIE_W36_FIRST_PARTY_REMOTE_HOLD'
    }
    & git -C $root merge-base --is-ancestor 846fbcb0e69efdb76115d83773f7e4af28193f54 HEAD 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw 'UCIE_W36_W35_MAIN_ANCESTOR_HOLD'}
    $blob=(& git -C $root rev-parse 'HEAD:scripts/ucie_owner_w31_local_listener_pid_readonly_v01.ps1' 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $blob -cne $w35Blob){throw 'UCIE_W36_W35_SOURCE_BLOB_HOLD'}
    $dirty=(& git -C $root status --porcelain --untracked-files=all 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $dirty){throw 'UCIE_W36_DIRTY_NEWROOT_HOLD'}
} finally {$env:GIT_OPTIONAL_LOCKS=$oldLocks}
$tok=$null;$err=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($w35,[ref]$tok,[ref]$err)
if(@($err).Count -ne 0){throw 'UCIE_W36_W35_SOURCE_PARSE_HOLD'}
foreach($name in @('AssertExactOriginalCommandLine','GetVenvRedirectorBasePythonw')){
    $found=@($ast.FindAll({param($node)
        ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
         $node.Name -ceq $name)},$true))
    if($found.Count -ne 1){throw 'UCIE_W36_W35_FUNCTION_NOT_UNIQUE_HOLD'}
    . ([scriptblock]::Create($found[0].Extent.Text))
}
$ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$task=Get-ScheduledTask -TaskPath '\' -TaskName 'UCIE-LocalV1-Web' -ErrorAction Stop
if(@($task.Actions).Count -ne 1 -or [string]$task.State -cne 'Running'){
    throw 'UCIE_W36_EXACT_ORIGINAL_TASK_STATE_HOLD'
}
$action=$task.Actions[0]
if(-not [string]::Equals([string]$action.Execute,$expectedExe,
                       [StringComparison]::OrdinalIgnoreCase) -or
   -not [string]::Equals([string]$action.Arguments,$expectedArgs,
                       [StringComparison]::Ordinal) -or
   -not [string]::Equals([string]$action.WorkingDirectory,'D:\UCIE',
                       [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W36_EXACT_ORIGINAL_TASK_ACTION_HOLD'
}
$taskOwnerRaw=[string]$task.Principal.UserId
try {
    $taskOwnerSid=([Security.Principal.NTAccount]::new($taskOwnerRaw)).Translate(
        [Security.Principal.SecurityIdentifier]).Value
} catch {
    if($taskOwnerRaw -cne $ownerSid){throw 'UCIE_W36_TASK_OWNER_UNRESOLVED_HOLD'}
    $taskOwnerSid=$ownerSid
}
if($taskOwnerSid -cne $ownerSid){throw 'UCIE_W36_TASK_OWNER_CHANGED_HOLD'}
$tcp=@(Get-NetTCPConnection -LocalPort 18767 -State Listen -ErrorAction Stop)
if($tcp.Count -ne 1 -or [string]$tcp[0].LocalAddress -cne '127.0.0.1' -or
   [int]$tcp[0].LocalPort -ne 18767){throw 'UCIE_W36_EXACT_LOOPBACK_LISTENER_HOLD'}
$listenerPid=[int]$tcp[0].OwningProcess
if($listenerPid -le 0){throw 'UCIE_W36_INVALID_LISTENER_PID_HOLD'}
$processes=@(Get-CimInstance -ClassName Win32_Process -Filter (
    'ProcessId = {0}' -f $listenerPid
) -ErrorAction Stop)
if($processes.Count -ne 1 -or [int]$processes[0].ProcessId -ne $listenerPid){
    throw 'UCIE_W36_EXACT_PROCESS_REQUIRED_HOLD'
}
$p=$processes[0]
$owner=Invoke-CimMethod -InputObject $p -MethodName GetOwnerSid -ErrorAction Stop
if($null -eq $owner -or [int]$owner.ReturnValue -ne 0 -or
   [string]$owner.Sid -cne $ownerSid){throw 'UCIE_W36_LISTENER_OWNER_HOLD'}
[void](AssertExactOriginalCommandLine ([string]$p.CommandLine) $expectedExe $expectedArgs)
$base=GetVenvRedirectorBasePythonw $expectedExe
if(-not [string]::Equals([IO.Path]::GetFullPath([string]$p.ExecutablePath),
                       [IO.Path]::GetFullPath([string]$base),
                       [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W36_VENV_BASE_IMAGE_HOLD'
}
$parentProcessId=[int]$p.ParentProcessId
$created=[datetime]$p.CreationDate
if($parentProcessId -le 0 -or $created.Year -lt 2020 -or
   $created -gt (Get-Date).AddMinutes(1)){
    throw 'UCIE_W36_INVALID_LISTENER_CREATION_OR_PARENT_HOLD'
}
# Do not enable event history. No log writes; only ID 129 and a four-minute window.
try {
    $records=@(Get-WinEvent -FilterHashtable @{
        LogName='Microsoft-Windows-TaskScheduler/Operational';Id=129
        StartTime=$created.AddMinutes(-2);EndTime=$created.AddMinutes(2)
    } -MaxEvents 128 -ErrorAction Stop)
} catch {throw 'UCIE_W36_TASK129_LOG_UNAVAILABLE_OR_EMPTY_HOLD'}
$foundCount=0
foreach($rec in $records){
    if([int]$rec.Id -ne 129){throw 'UCIE_W36_UNEXPECTED_EVENT_ID_HOLD'}
    if(TestExactTask129ParentEvent ([string]$rec.ToXml()) ([datetime]$rec.TimeCreated) $created $parentProcessId '\UCIE-LocalV1-Web' $expectedExe){
        $foundCount++
    }
}
if($foundCount -ne 1){throw 'UCIE_W36_NO_UNAMBIGUOUS_TASK129_PARENT_EVENT_HOLD'}
# Re-read only the original listener; do not enumerate processes.
$tcpAgain=@(Get-NetTCPConnection -LocalPort 18767 -State Listen -ErrorAction Stop)
if($tcpAgain.Count -ne 1 -or
   [string]$tcpAgain[0].LocalAddress -cne '127.0.0.1' -or
   [int]$tcpAgain[0].OwningProcess -ne $listenerPid){
    throw 'UCIE_W36_LISTENER_PID_REBIND_HOLD'
}
$procAgain=@(Get-CimInstance -ClassName Win32_Process -Filter (
    'ProcessId = {0}' -f $listenerPid
) -ErrorAction Stop)
if($procAgain.Count -ne 1 -or
   [int]$procAgain[0].ParentProcessId -ne $parentProcessId -or
   [datetime]$procAgain[0].CreationDate -ne $created){
    throw 'UCIE_W36_LISTENER_PROCESS_REBIND_HOLD'
}
[pscustomobject]@{
    schema=$schema
    status='UCIE_W36_TASK129_PARENT_PID_TIME_CORRELATED__LAUNCH_NOT_ATTESTED'
    task_event129_parent_pid_time_correlated=$true
    listener_same_owner_and_original_command_line=$true
    listener_venv_base_pythonw_config_consistent=$true
    parent_process_creation_independently_attested=$false
    listener_pid_launched_by_task_scheduler_verified=$false
    security4688_creation_event_verified=$false
    c40_mcp_round_trip_verified=$false
    event_log_modified=$false;task_scheduler_modified=$false
    sqlite_content_opened=$false;process_killed_or_started=$false
    journal_written=$false;full_cutover_authorized=$false
} | ConvertTo-Json -Compress
