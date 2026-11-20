# UCIE W31: READ ONLY exact owner LocalV1 loopback listener PID identity gate.
# Never claims proof of Task Scheduler launch lineage or C40 MCP roundtrip.
[CmdletBinding()]
param(
    [switch]$ContractOnly,
    [switch]$CheckLocal,
    [string]$OwnerApproval=''
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W31_OLD_LOCAL_LISTENER_PID_IDENTITY_READONLY_V01'
$root='D:\UCIE_PROJECT\UCIE'
$old='D:\UCIE'
$archive='D:\UCIE_PROJECT\ARCHIVE'
$self=$root+'\scripts\ucie_owner_w31_local_listener_pid_readonly_v01.ps1'
$w29Source=$root+'\scripts\ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1'
$w30Ancestor='5a0251f8c8b22efbb7cb3876ef66409486b053dd'
$w29Blob='848cb03f50dc455fc61935a484c3d71e82506c90'
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
    $archive+'\UCIE_W28_OWNER_NEW_TRANSACTION_RESTORED_V01.json',
    $archive+'\UCIE_W29_OWNER_OLDROOT_REHEARSAL_INTENT_V01.json',
    $archive+'\UCIE_W29_OWNER_OLDROOT_RECOVERY_INTENT_V01.json',
    $archive+'\UCIE_W29_OWNER_OLDROOT_RESTORED_V01.json',
    $archive+'\UCIE_W30_OWNER_SECONDARY_RECOVERY_INTENT_V01.json',
    $archive+'\UCIE_W30_OWNER_SECONDARY_RETRY_INTENT_V01.json',
    $archive+'\UCIE_W30_OWNER_SECONDARY_RESTORED_V01.json'
)
if(-not $CheckLocal){
    # Default contract-only mode never touches host data. An orphan
    # approval is not evidence that owner checks were performed.
    if($OwnerApproval){throw 'UCIE_W31_APPROVAL_WITHOUT_CHECK_DENIED'}
    [pscustomobject]@{
        schema=$schema
        status='UCIE_W31_CONTRACT_ONLY_NO_HOST_ACCESS'
        host_process_queried=$false;tcp_listener_queried=$false
        task_scheduler_queried_or_modified=$false
        sqlite_content_opened=$false;private_archive_read_or_modified=$false
        c40_queried_or_modified=$false;journal_written=$false
        owner_task_pid_launch_lineage_verified=$false
        c40_mcp_round_trip_verified=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
    return
}
if($ContractOnly){throw 'UCIE_W31_CONTRACT_AND_OWNER_MODE_CONFLICT'}
if(-not [string]::Equals(
        $OwnerApproval,
        'AUTHORIZE_UCIE_W31_READONLY_OLD_LOCAL_LISTENER_PID_INSPECTION',
        [StringComparison]::Ordinal)){
    throw 'UCIE_W31_EXPLICIT_OWNER_READONLY_APPROVAL_REQUIRED'
}
# W32: user-friendly, owner-approved READ-ONLY UAC handoff. The launcher
# never reads or writes owner private data or starts/stops original tasks.
# Only the elevated child may run the existing W31 read-only source gates.
function NewReadOnlyUacArguments([string]$expectedOwnerSid) {
    if($expectedOwnerSid -cnotmatch '^S-1(?:-[0-9]+){2,15}$'){
        throw 'UCIE_W32_INVALID_OR_UNTRUSTED_OWNER_SID'
    }
    # Literal first-party path and fixed owner approval: never interpolate
    # user-controlled executable paths or arbitrary command strings.
    $command=@'
$ErrorActionPreference='Stop'
$expectedSid='__UCIE_OWNER_SID__'
$actualSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if($actualSid -cne $expectedSid){
    throw 'UCIE_W32_UAC_ACCOUNT_CHANGED__READONLY_HOLD'
}
& 'D:\UCIE_PROJECT\UCIE\scripts\ucie_owner_w31_local_listener_pid_readonly_v01.ps1' -CheckLocal -OwnerApproval 'AUTHORIZE_UCIE_W31_READONLY_OLD_LOCAL_LISTENER_PID_INSPECTION'
'@
    $command=$command.Replace('__UCIE_OWNER_SID__',$expectedOwnerSid)
    $encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    return '-NoProfile -NoExit -EncodedCommand '+$encoded
}
# Extractable for disposable CI: mock Start-Process and assert exact RunAs
# invocation without ever opening a UAC prompt on the test runner.
function InvokeReadOnlyUacHandoff([string]$powershellPath,[string]$callerSid) {
    $arguments=NewReadOnlyUacArguments $callerSid
    try {
        [void](Start-Process -FilePath $powershellPath -ArgumentList $arguments `
            -Verb RunAs -ErrorAction Stop -PassThru)
    } catch {
        throw 'UCIE_W32_OWNER_UAC_CANCELLED_OR_LAUNCH_FAILED__NO_HOST_CHECK'
    }
    return [pscustomobject]@{
        schema=$schema
        status='UCIE_W32_ELEVATED_READONLY_WINDOW_STARTED__RESULT_PENDING'
        host_service_examined_in_parent=$false
        task_scheduler_or_c40_modified=$false
        operating_sqlite_opened=$false
        journal_written=$false
        full_cutover_authorized=$false
    }
}
# W33: Environment.SystemDirectory is obtained from Windows itself.
# The Machine 'SystemRoot' environment variable is not guaranteed to exist;
# process environment variables and PATH must never choose the UAC binary.
function GetTrustedWindowsPowerShellPath {
    $systemDirectory=[Environment]::SystemDirectory
    if([string]::IsNullOrWhiteSpace($systemDirectory) -or
       -not [IO.Path]::IsPathRooted($systemDirectory)){
        throw 'UCIE_W33_OS_SYSTEM_DIRECTORY_UNAVAILABLE'
    }
    $windowsPowerShell=Join-Path -Path $systemDirectory -ChildPath 'WindowsPowerShell\v1.0\powershell.exe'
    if(-not [IO.File]::Exists($windowsPowerShell)){
        throw 'UCIE_W32_SYSTEM_POWERSHELL_NOT_FOUND'
    }
    return $windowsPowerShell
}
if($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive){
    throw 'UCIE_W31_INTERACTIVE_WINDOWS_OWNER_REQUIRED'
}
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$admin=[Security.Principal.WindowsPrincipal]::new($identity)
if(-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    # No trust in the caller's working directory, PATH-resolved powershell,
    # or the ability of a different Windows account to satisfy UAC.
    if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
                            [IO.Path]::GetFullPath($self),
                            [StringComparison]::OrdinalIgnoreCase)){
        throw 'UCIE_W32_CANONICAL_SELF_FOR_UAC_REQUIRED'
    }
    $windowsPowerShell=GetTrustedWindowsPowerShellPath
    InvokeReadOnlyUacHandoff $windowsPowerShell $identity.User.Value |
        ConvertTo-Json -Compress
    return
}
$script:ownerSid=$identity.User.Value

# Pure, separately extractable function for native PowerShell fake-argv tests.
# This compares Windows process executable and the EXACT W29 Task Action
# argument string, preventing a generic HTTP server from spoofing local health.
function AssertExactOriginalCommandLine(
    [string]$processCommandLine,
    [string]$expectedExecutable,
    [string]$expectedArguments
) {
    if([string]::IsNullOrWhiteSpace($processCommandLine) -or
       [string]::IsNullOrWhiteSpace($expectedExecutable) -or
       [string]::IsNullOrWhiteSpace($expectedArguments)){
        throw 'UCIE_W31_MISSING_COMMANDLINE_OR_TASK_ACTION_HOLD'
    }
    $value=$processCommandLine.Trim()
    if($value.StartsWith('"',[StringComparison]::Ordinal)){
        $end=$value.IndexOf('"',1)
        if($end -le 1){throw 'UCIE_W31_COMMANDLINE_EXE_QUOTING_HOLD'}
        $observedExecutable=$value.Substring(1,$end-1)
        $remaining=$value.Substring($end+1)
    } else {
        $separator=$value.IndexOf(' ')
        if($separator -le 0){throw 'UCIE_W31_COMMANDLINE_EXE_MISSING_ARGS_HOLD'}
        $observedExecutable=$value.Substring(0,$separator)
        $remaining=$value.Substring($separator)
    }
    if(-not [string]::Equals($observedExecutable,$expectedExecutable,
                           [StringComparison]::OrdinalIgnoreCase)){
        throw 'UCIE_W31_LISTENER_EXE_COMMANDLINE_MISMATCH_HOLD'
    }
    if($remaining -cnotmatch '^[ ]+' -or
       -not [string]::Equals($remaining.TrimStart(' '),$expectedArguments,
                           [StringComparison]::Ordinal)){
        throw 'UCIE_W31_LISTENER_ARGS_COMMANDLINE_MISMATCH_HOLD'
    }
    return $true
}
# W35: Official CPython Windows venv redirectors start base pythonw.exe
# from pyvenv.cfg, retaining the original virtual-environment argv[0].
# Only read the exact old-venv configuration. No Python execution or write.
function GetVenvRedirectorBasePythonw([string]$venvLauncherPath) {
    if([string]::IsNullOrWhiteSpace($venvLauncherPath) -or
       [IO.Path]::GetFileName($venvLauncherPath) -cne 'pythonw.exe'){
        throw 'UCIE_W35_EXACT_PYTHONW_LAUNCHER_REQUIRED_HOLD'
    }
    $scripts=[IO.Path]::GetDirectoryName($venvLauncherPath)
    if([IO.Path]::GetFileName($scripts) -cne 'Scripts'){
        throw 'UCIE_W35_EXACT_VENV_SCRIPTS_REQUIRED_HOLD'
    }
    $venv=[IO.Path]::GetDirectoryName($scripts)
    $config=Join-Path -Path $venv -ChildPath 'pyvenv.cfg'
    foreach($target in @(
        [pscustomobject]@{Path=$venv;Directory=$true},
        [pscustomobject]@{Path=$scripts;Directory=$true},
        [pscustomobject]@{Path=$venvLauncherPath;Directory=$false},
        [pscustomobject]@{Path=$config;Directory=$false}
    )){
        try {
            $node=Get-Item -LiteralPath $target.Path -Force -ErrorAction Stop
        } catch {throw 'UCIE_W35_VENV_REDIRECTOR_FILE_UNAVAILABLE_HOLD'}
        if([bool]$node.PSIsContainer -ne [bool]$target.Directory -or
           ($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
            throw 'UCIE_W35_VENV_REDIRECTOR_REPARSE_OR_TYPE_HOLD'
        }
    }
    $configFile=Get-Item -LiteralPath $config -Force -ErrorAction Stop
    if($configFile.Length -le 0 -or $configFile.Length -gt 8192){
        throw 'UCIE_W35_VENV_CONFIG_SIZE_HOLD'
    }
    try {
        $lines=[IO.File]::ReadAllLines($config)
    } catch {throw 'UCIE_W35_VENV_CONFIG_READ_HOLD'}
    $homes=[Collections.Generic.List[string]]::new()
    foreach($line in $lines){
        if($line -cmatch '^[ \t]*home[ \t]*=[ \t]*(.*?)[ \t]*$'){
            $homes.Add($Matches[1])
        }
    }
    if($homes.Count -ne 1 -or [string]::IsNullOrWhiteSpace($homes[0])){
        throw 'UCIE_W35_VENV_HOME_NOT_UNIQUE_HOLD'
    }
    $venvHome=$homes[0]
    if(-not [IO.Path]::IsPathRooted($venvHome) -or
       ($env:OS -eq 'Windows_NT' -and $venvHome -cnotmatch '^[A-Za-z]:\\') -or
       $venvHome -match '(^|[\\/])\.\.?([\\/]|$)'){
        throw 'UCIE_W35_VENV_HOME_NOT_CANONICAL_LOCAL_HOLD'
    }
    try {
        $normalizedHome=[IO.Path]::GetFullPath($venvHome)
    } catch {throw 'UCIE_W35_VENV_HOME_NOT_CANONICAL_LOCAL_HOLD'}
    # GetFullPath canonicalizes an already absolute, local, traversal-free
    # Windows home; text equality against its input is not a trust boundary.
    # The actual PID image must still match the OS-normalized base executable.
    if($env:OS -eq 'Windows_NT' -and
       $normalizedHome -cnotmatch '^[A-Za-z]:\\'){
        throw 'UCIE_W35_VENV_HOME_NOT_CANONICAL_LOCAL_HOLD'
    }
    $baseImage=Join-Path -Path $normalizedHome -ChildPath 'pythonw.exe'
    foreach($target in @(
        [pscustomobject]@{Path=$normalizedHome;Directory=$true},
        [pscustomobject]@{Path=$baseImage;Directory=$false}
    )){
        try {
            $node=Get-Item -LiteralPath $target.Path -Force -ErrorAction Stop
        } catch {throw 'UCIE_W35_VENV_BASE_BINARY_UNAVAILABLE_HOLD'}
        if([bool]$node.PSIsContainer -ne [bool]$target.Directory -or
           ($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
            throw 'UCIE_W35_VENV_BASE_BINARY_REPARSE_OR_TYPE_HOLD'
        }
    }
    return $baseImage
}
# Pure host-read-only probe: query EXACTLY ONE TCP port and ONLY its PID,
# not all host processes. Do NOT imply that matching process command line
# proves the Task Scheduler engine was the actual process launcher.
function AssertOwnerLocalListenerPidIdentity {
    $listeners=@(Get-NetTCPConnection -LocalPort 18767 -State Listen -ErrorAction Stop)
    if($listeners.Count -ne 1){
        throw 'UCIE_W31_ONE_LISTENER_REQUIRED_HOLD'
    }
    $listener=$listeners[0]
    if([string]$listener.LocalAddress -cne '127.0.0.1' -or
       [int]$listener.LocalPort -ne 18767){
        throw 'UCIE_W31_EXACT_LOOPBACK_BINDING_REQUIRED_HOLD'
    }
    $listenerProcessId=[int]$listener.OwningProcess
    if($listenerProcessId -le 0){
        throw 'UCIE_W31_LISTENER_PROCESS_ID_MISSING_HOLD'
    }
    $process=@(Get-CimInstance -ClassName Win32_Process -Filter (
        'ProcessId = {0}' -f $listenerProcessId
    ) -ErrorAction Stop)
    if($process.Count -ne 1 -or
       [int]$process[0].ProcessId -ne $listenerProcessId){
        throw 'UCIE_W31_LISTENER_PID_PROCESS_LOOKUP_HOLD'
    }
    $item=$process[0]
    $expected=$specs[2]
    $sid=Invoke-CimMethod -InputObject $item -MethodName GetOwnerSid -ErrorAction Stop
    if($null -eq $sid -or [int]$sid.ReturnValue -ne 0 -or
       [string]$sid.Sid -cne $script:ownerSid){
        throw 'UCIE_W31_LISTENER_PROCESS_OWNER_SID_HOLD'
    }
    [void](AssertExactOriginalCommandLine (
        [string]$item.CommandLine
    ) $expected.Exe $expected.Arguments)
    $directImage=[string]::Equals([string]$item.ExecutablePath,$expected.Exe,
                                 [StringComparison]::OrdinalIgnoreCase)
    $redirectedImage=$false
    if(-not $directImage){
        # Only after the original task argv and same-owner PID have matched.
        $baseImage=GetVenvRedirectorBasePythonw $expected.Exe
        $observedImage=[string]$item.ExecutablePath
        if(-not [IO.Path]::IsPathRooted($observedImage) -or
           ($env:OS -eq 'Windows_NT' -and
            $observedImage -cnotmatch '^[A-Za-z]:\\')){
            throw 'UCIE_W35_LISTENER_IMAGE_PATH_INVALID_HOLD'
        }
        try {
            $observedCanonical=[IO.Path]::GetFullPath($observedImage)
            $baseCanonical=[IO.Path]::GetFullPath($baseImage)
        } catch {throw 'UCIE_W35_LISTENER_IMAGE_PATH_INVALID_HOLD'}
        if(-not [string]::Equals($observedCanonical,$baseCanonical,
                               [StringComparison]::OrdinalIgnoreCase)){
            throw 'UCIE_W35_LISTENER_BASE_PYTHONW_IMAGE_MISMATCH_HOLD'
        }
        $redirectedImage=$true
    }
    # The listener may have exited/rebound while CIM owner and argv were
    # inspected. Requery ONLY the same UCIE port; a changed PID is a HOLD.
    $confirmed=@(Get-NetTCPConnection -LocalPort 18767 -State Listen -ErrorAction Stop)
    if($confirmed.Count -ne 1 -or
       [string]$confirmed[0].LocalAddress -cne '127.0.0.1' -or
       [int]$confirmed[0].LocalPort -ne 18767 -or
       [int]$confirmed[0].OwningProcess -ne $listenerProcessId){
        throw 'UCIE_W31_LISTENER_PID_CHANGED_DURING_READONLY_HOLD'
    }
    return [pscustomobject]@{
        direct_original_task_binary=$directImage
        venv_base_pythonw_redirector_consistent=$redirectedImage
    }
}
# Host source, task and historical provenance checks happen only AFTER
# the explicit -CheckLocal owner approval and UAC checks above.
if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
                        [IO.Path]::GetFullPath($self),
                        [StringComparison]::OrdinalIgnoreCase)){
    throw 'UCIE_W31_CANONICAL_FIRST_PARTY_ENTRYPOINT_REQUIRED'
}
foreach($path in @($old,$root,$archive)){
    $node=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if(-not $node.PSIsContainer -or
       ($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
        throw 'UCIE_W31_DIRECT_OWNER_ROOT_REQUIRED'
    }
}
foreach($path in @($self,$w29Source)){
    $node=Get-Item -LiteralPath $path -Force -ErrorAction Stop
    if($node.PSIsContainer -or
       ($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
        throw 'UCIE_W31_DIRECT_FIRST_PARTY_SCRIPT_REQUIRED'
    }
}
$acl=Get-Acl -LiteralPath $archive -ErrorAction Stop
if(-not $acl.AreAccessRulesProtected -or
   $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $script:ownerSid){
    throw 'UCIE_W31_PROTECTED_ARCHIVE_SAME_OWNER_REQUIRED'
}
$oldLocks=$env:GIT_OPTIONAL_LOCKS
$env:GIT_OPTIONAL_LOCKS='0'
try {
    $remote=(& git -C $root remote get-url origin 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or
       $remote -cne 'https://github.com/tmdrkdtn1-project/UCIE.git'){
        throw 'UCIE_W31_FIRST_PARTY_REMOTE_HOLD'
    }
    & git -C $root merge-base --is-ancestor $w30Ancestor HEAD 2>$null | Out-Null
    if($LASTEXITCODE -ne 0){throw 'UCIE_W31_W30_GIT_ANCESTOR_MISSING_HOLD'}
    $blob=(& git -C $root rev-parse 'HEAD:scripts/ucie_owner_w29_oldroot_rehearsal_restore_v01.ps1' 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $blob -cne $w29Blob){
        throw 'UCIE_W31_W29_GIT_BLOB_DRIFT_HOLD'
    }
    $dirty=(& git -C $root status --porcelain --untracked-files=all 2>$null | Out-String).Trim()
    if($LASTEXITCODE -ne 0 -or $dirty){
        throw 'UCIE_W31_OWNER_NEWROOT_DIRTY_HOLD'
    }
} finally {
    $env:GIT_OPTIONAL_LOCKS=$oldLocks
}
# Never dot-source W29: import only the reviewed pure/READ-ONLY helpers.
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile(
    $w29Source,[ref]$tokens,[ref]$errors)
if(@($errors).Count -ne 0){throw 'UCIE_W31_W29_AST_PARSE_HOLD'}
foreach($functionName in @(
    'ShaText','Direct','Absent','ReadReceipt','OwnerTask','CheckOld',
    'C40Hash','PortState','HealthyOld','AssertRecoveredHistory',
    'AssertNoStagedData'
)) {
    $found=@($ast.FindAll({
        param($node)
        ($node -is [Management.Automation.Language.FunctionDefinitionAst] -and
         $node.Name -ceq $functionName)
    },$true))
    if($found.Count -ne 1){throw 'UCIE_W31_W29_AST_FUNCTION_NOT_UNIQUE_HOLD'}
    . ([scriptblock]::Create($found[0].Extent.Text))
}
# W29 Direct verifies parent path components on D: as well, not only
# the leaf roots and script files checked above.
foreach($path in @($old,$root,$archive)){Direct $path $true}
foreach($path in @($self,$w29Source)){Direct $path $false}
Import-Module ScheduledTasks -ErrorAction Stop
$c40Baseline=C40Hash
AssertRecoveredHistory $c40Baseline
AssertNoStagedData
# W29/W30 one-shot intents MUST be absent in the currently healthy oldroot.
foreach($record in @(
    'UCIE_W29_OWNER_OLDROOT_REHEARSAL_INTENT_V01.json',
    'UCIE_W29_OWNER_OLDROOT_RECOVERY_INTENT_V01.json',
    'UCIE_W29_OWNER_OLDROOT_RESTORED_V01.json',
    'UCIE_W30_OWNER_SECONDARY_RECOVERY_INTENT_V01.json',
    'UCIE_W30_OWNER_SECONDARY_RETRY_INTENT_V01.json',
    'UCIE_W30_OWNER_SECONDARY_RESTORED_V01.json'
)){Absent (Join-Path $archive $record)}
foreach($i in 0..2){
    $task=CheckOld $i
    $state=[string]$task.State
    if($i -lt 2 -and $state -notin @('Ready','Running')){
        throw 'UCIE_W31_ORIGINAL_WRITER_STATE_HOLD'
    }
    if($i -eq 2 -and $state -cne 'Running'){
        throw 'UCIE_W31_ORIGINAL_LOCAL_TASK_NOT_RUNNING'
    }
}
if(-not (HealthyOld)){throw 'UCIE_W31_ORIGINAL_LOCAL_HTTP_HEALTH_HOLD'}
$listenerIdentity=AssertOwnerLocalListenerPidIdentity
if((C40Hash) -cne $c40Baseline){
    throw 'UCIE_W31_C40_ACTION_CHANGED_DURING_READONLY'
}
[pscustomobject]@{
    schema=$schema
    status=$(if($listenerIdentity.venv_base_pythonw_redirector_consistent){
        'UCIE_W35_VENV_BASE_PYTHONW_CLI_OWNER_CONFIG_CONSISTENT__TASK_LAUNCH_LINK_HOLD'
    } else {
        'UCIE_W31_EXACT_LOOPBACK_PID_BINARY_CLI_OWNER_VERIFIED__TASK_LAUNCH_LINK_HOLD'
    })
    original_tasks_owner_action_and_state_verified=$true
    historical_owner_receipts_preserved_and_validated=$true
    old_local_http_healthy=$true
    listener_process_owner_sid_verified=$true
    listener_binary_matches_original_task=[bool]$listenerIdentity.direct_original_task_binary
    listener_venv_base_pythonw_config_consistent=[bool]$listenerIdentity.venv_base_pythonw_redirector_consistent
    listener_command_line_matches_original_task=$true
    listener_is_exactly_one_loopback=$true
    listener_pid_launched_by_task_scheduler_verified=$false
    listener_task_pid_identity_verified=$false
    c40_action_unchanged=$true
    c40_mcp_round_trip_verified=$false
    sqlite_content_opened=$false
    task_scheduler_or_c40_modified=$false
    process_killed_or_started=$false
    journal_written=$false
    full_cutover_authorized=$false
} | ConvertTo-Json -Compress
