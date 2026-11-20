# UCIE W39. Exact, server-side-scoped read-only observation of the existing
# C40 client process. This cannot attest the ChatGPT MCP connector route.
[CmdletBinding()]
param([switch]$ContractOnly,[switch]$InspectLocal,[string]$OwnerApproval='')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$schema='UCIE_W39_C40_CLIENT_IMAGE_OWNER_READONLY_V01'
$root='D:\UCIE_PROJECT\UCIE'
$self=$root+'\scripts\ucie_owner_w39_c40_client_readonly_v01.ps1'
$exe='D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
$profile='D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml'
$taskName='UCIE-C40-Recover'
$approved='AUTHORIZE_UCIE_W39_READONLY_EXACT_C40_CLIENT_METADATA'
function WriteW39Receipt([string]$status,[bool]$hostQueried) {
    [pscustomobject]@{
        schema=$schema
        status=$status
        c40_client_metadata_queried=$hostQueried
        c40_client_image_owner_and_stability_observed=($status -ceq 'UCIE_W39_ONE_EXACT_C40_CLIENT_IMAGE_OWNER_STABLE__MCP_ROUTE_HOLD')
        c40_task_launch_origin_verified=$false
        c40_profile_contents_read=$false
        c40_endpoint_or_authenticated_session_verified=$false
        c40_mcp_round_trip_verified=$false
        connector_route_binding_verified=$false
        operating_sqlite_opened=$false
        task_or_tunnel_modified=$false
        process_killed_or_started=$false
        journal_written=$false
        full_cutover_authorized=$false
    } | ConvertTo-Json -Compress
}
if(-not $InspectLocal){
    if($OwnerApproval){throw 'UCIE_W39_APPROVAL_WITHOUT_INSPECT_HOLD'}
    WriteW39Receipt 'UCIE_W39_CONTRACT_ONLY_NO_HOST_ACCESS' $false
    return
}
if($ContractOnly){throw 'UCIE_W39_CONFLICTING_MODES_HOLD'}
if($OwnerApproval -cne $approved){
    throw 'UCIE_W39_EXPLICIT_OWNER_APPROVAL_REQUIRED_HOLD'
}
# Pure helper; WQL escapes backslashes and queries ONLY the one known UCIE
# executable path, with optional conjunctive PID for the rebinding check.
function NewW39ExactClientWql([string]$requestedExe,[int]$processId=0) {
    $fixed='D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe'
    if(-not [string]::Equals($requestedExe,$fixed,
        [StringComparison]::OrdinalIgnoreCase) -or $processId -lt 0){
        throw 'UCIE_W39_UNKNOWN_CLIENT_PATH_OR_PID_HOLD'
    }
    $escaped=$fixed.Replace('\','\\')
    $query="SELECT ProcessId, ExecutablePath, CreationDate, ParentProcessId FROM Win32_Process WHERE ExecutablePath = '$escaped'"
    if($processId -gt 0){$query+=' AND ProcessId = '+$processId}
    return $query
}
# A source-isolated verifier, also used with fake first-party CIM records.
function AssertW39OneExactClient([object[]]$rows,[string]$expectedExe) {
    if($rows.Count -ne 1 -or $null -eq $rows[0]){
        throw 'UCIE_W39_EXACT_CLIENT_COUNT_NOT_ONE_HOLD'
    }
    $p=$rows[0]
    if([int]$p.ProcessId -le 0 -or
       [string]::IsNullOrWhiteSpace([string]$p.ExecutablePath) -or
       -not [string]::Equals(
           [IO.Path]::GetFullPath([string]$p.ExecutablePath),
           [IO.Path]::GetFullPath($expectedExe),
           [StringComparison]::OrdinalIgnoreCase)){
        throw 'UCIE_W39_CLIENT_EXE_IDENTITY_MISMATCH_HOLD'
    }
    if([datetime]$p.CreationDate -gt (Get-Date).AddMinutes(1) -or
       [datetime]$p.CreationDate -lt [datetime]'2020-01-01'){
        throw 'UCIE_W39_CLIENT_CREATION_DATE_HOLD'
    }
    return $p
}
# All queries beyond this point are OWNER-NATIVE and READ ONLY. Never
# inspect any tunnel profile text, task action arguments, environment,
# process command line, network addresses, secrets, or unrelated project.
$queried=$false
try {
    if($env:OS -ne 'Windows_NT' -or -not [Environment]::UserInteractive){
        throw 'UCIE_W39_INTERACTIVE_WINDOWS_OWNER_REQUIRED_HOLD'
    }
    if(-not [string]::Equals([IO.Path]::GetFullPath($PSCommandPath),
        [IO.Path]::GetFullPath($self),[StringComparison]::OrdinalIgnoreCase)){
        throw 'UCIE_W39_CANONICAL_FIRST_PARTY_SCRIPT_HOLD'
    }
    foreach($entry in @(
        [pscustomobject]@{Path=$root;Directory=$true},
        [pscustomobject]@{Path=$self;Directory=$false},
        [pscustomobject]@{Path='D:\UCIE_DATA';Directory=$true},
        [pscustomobject]@{Path='D:\UCIE_DATA\tools';Directory=$true},
        [pscustomobject]@{Path='D:\UCIE_DATA\tools\tunnel-client-v0.0.16';Directory=$true},
        [pscustomobject]@{Path=$exe;Directory=$false},
        [pscustomobject]@{Path='D:\UCIE_DATA\mcp_tunnel_profiles';Directory=$true},
        [pscustomobject]@{Path=$profile;Directory=$false}
    )){
        $item=Get-Item -LiteralPath $entry.Path -Force -ErrorAction Stop
        if([bool]$item.PSIsContainer -ne [bool]$entry.Directory -or
           ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){
            throw 'UCIE_W39_FIXED_PATH_TYPE_OR_REPARSE_HOLD'
        }
    }
    $prior=$env:GIT_OPTIONAL_LOCKS
    $env:GIT_OPTIONAL_LOCKS='0'
    try {
        $remote=(& git -C $root remote get-url origin 2>$null | Out-String).Trim()
        if($LASTEXITCODE -ne 0 -or
           $remote -cne 'https://github.com/tmdrkdtn1-project/UCIE.git'){
            throw 'UCIE_W39_FIRST_PARTY_ORIGIN_HOLD'
        }
        $branch=(& git -C $root symbolic-ref --short HEAD 2>$null | Out-String).Trim()
        if($LASTEXITCODE -ne 0 -or $branch -cne 'main'){
            throw 'UCIE_W39_EXPECTED_MAIN_HOLD'
        }
        & git -C $root merge-base --is-ancestor 0ab6c549bc493988abcee66ee17548c365313d9a HEAD 2>$null | Out-Null
        if($LASTEXITCODE -ne 0){throw 'UCIE_W39_W38_BASE_ANCESTOR_HOLD'}
        $dirty=(& git -C $root status --porcelain --untracked-files=all 2>$null | Out-String).Trim()
        if($LASTEXITCODE -ne 0 -or $dirty){throw 'UCIE_W39_NEWROOT_DIRTY_HOLD'}
    } finally {
        $env:GIT_OPTIONAL_LOCKS=$prior
    }
    $queried=$true
    $task=Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction Stop
    if(@($task.Actions).Count -ne 1 -or [string]$task.State -cne 'Running'){
        throw 'UCIE_W39_C40_TASK_NOT_RUNNING_OR_ACTION_COUNT_HOLD'
    }
    $ownerSid=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $rawPrincipal=[string]$task.Principal.UserId
    if($rawPrincipal -match '^S-1-[0-9-]+$'){
        $taskSid=$rawPrincipal
    } else {
        $taskSid=([Security.Principal.NTAccount]::new($rawPrincipal)).Translate(
            [Security.Principal.SecurityIdentifier]).Value
    }
    if($taskSid -cne $ownerSid){throw 'UCIE_W39_C40_TASK_OWNER_HOLD'}
    # WQL WHERE is exact and server-side; no enumeration of other processes.
    $query=NewW39ExactClientWql $exe
    $records=@(Get-CimInstance -Query $query -ErrorAction Stop)
    $client=AssertW39OneExactClient $records $exe
    $sid=Invoke-CimMethod -InputObject $client -MethodName GetOwnerSid -ErrorAction Stop
    if($null -eq $sid -or [int]$sid.ReturnValue -ne 0 -or
       [string]$sid.Sid -cne $ownerSid){
        throw 'UCIE_W39_C40_CLIENT_OWNER_HOLD'
    }
    $samePid=[int]$client.ProcessId
    $sameCreated=[datetime]$client.CreationDate
    $again=@(Get-CimInstance -Query (
        NewW39ExactClientWql $exe $samePid
    ) -ErrorAction Stop)
    $second=AssertW39OneExactClient $again $exe
    if([int]$second.ProcessId -ne $samePid -or
       [datetime]$second.CreationDate -ne $sameCreated){
        throw 'UCIE_W39_C40_CLIENT_PID_OR_CREATION_CHANGED_HOLD'
    }
    $sidAgain=Invoke-CimMethod -InputObject $second -MethodName GetOwnerSid -ErrorAction Stop
    if($null -eq $sidAgain -or [int]$sidAgain.ReturnValue -ne 0 -or
       [string]$sidAgain.Sid -cne $ownerSid){
        throw 'UCIE_W39_C40_CLIENT_OWNER_CHANGED_HOLD'
    }
    $taskAgain=Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction Stop
    if(@($taskAgain.Actions).Count -ne 1 -or
       [string]$taskAgain.State -cne 'Running' -or
       [string]$taskAgain.Principal.UserId -cne $rawPrincipal){
        throw 'UCIE_W39_C40_TASK_STATE_CHANGED_HOLD'
    }
    WriteW39Receipt 'UCIE_W39_ONE_EXACT_C40_CLIENT_IMAGE_OWNER_STABLE__MCP_ROUTE_HOLD' $true
} catch {
    $code=[string]$_.Exception.Message
    if($code -cnotmatch '^UCIE_W39_[A-Z0-9_]{5,90}_HOLD$'){
        $code='UCIE_W39_NATIVE_READONLY_QUERY_UNCLASSIFIED_HOLD'
    }
    WriteW39Receipt $code $queried
}
