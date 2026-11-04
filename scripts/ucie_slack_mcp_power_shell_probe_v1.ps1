# UCIE ONLY. Read-only owner PowerShell diagnostics; never restart C40.
# Use -Mode FreshImport to evaluate the pinned staging registration in a
# separate inert Python process. Does not launch the MCP server or Slack API.
[CmdletBinding()]
param([ValidateSet('Status','FreshImport')][string]$Mode='Status')
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$taskName='UCIE-C40-Recover'
$registration='D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin\mcp_registration.py'
$reader='D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin\slack_history_readonly_mcp_v1.py'
$python='D:\UCIE_DATA\.venv_mcp\Scripts\python.exe'
$probe='D:\UCIE\scripts\ucie_slack_mcp_fresh_import_probe_v1.py'
$regSha='f75a9780bbf745b547af8a6d7ca830269aa3ebffb25cef690724d0ffe4184962'
$readerSha='92e273f93495bd2e0c0c6b4da70e70cc1c0406a81c1ce70b7ac169edce7f08ac'

foreach($path in @($registration,$reader,$python,$probe)) {
    $item=Get-Item -LiteralPath $path -ErrorAction Stop
    if (-not $item -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw 'UCIE_MCP_DIAG_REQUIRED_PATH_ABSENT_OR_LINKED'
    }
}
$regOk=((Get-FileHash -LiteralPath $registration -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $regSha)
$readerOk=((Get-FileHash -LiteralPath $reader -Algorithm SHA256).Hash.ToLowerInvariant() -ceq $readerSha)
$tasks=@(Get-ScheduledTask -TaskName $taskName -ErrorAction Stop |
    Where-Object {$_.TaskPath -eq [string][char]92})
if($tasks.Count -ne 1){throw 'UCIE_C40_OWNER_TASK_NOT_UNIQUE'}
$task=$tasks[0]
$taskOk=([string]$task.State -eq 'Running' -and
         [string]$task.Principal.RunLevel -eq 'Highest' -and
         [string]$task.Principal.LogonType -eq 'Interactive')
$result=[ordered]@{
  schema='UCIE_C40_MCP_READONLY_POWER_SHELL_DIAGNOSTIC_V1'
  status='UCIE_C40_MCP_SOURCE_AND_TASK_INSPECTED_READONLY'
  mode=$Mode
  registration_sha256_matches=$regOk
  new_reader_sha256_matches=$readerOk
  task_running_highest_interactive=$taskOk
  task_state=[string]$task.State
  owner_registration_file_changed=$false
  service_or_client_restarted=$false
  other_tasks_modified=$false
  operating_database_modified=$false
  slack_credentials_or_messages_read=$false
}
if($Mode -eq 'FreshImport'){
    if(-not $regOk -or -not $readerOk -or -not $taskOk){
        $result.status='UCIE_C40_MCP_DIAG_FAIL_CLOSED_PRECONDITION'
        $result | ConvertTo-Json -Compress -Depth 3
        return
    }
    # The Python probe uses mocked bridge functions; no network/secret accesses.
    # Capture one bounded JSON receipt only, never process command line/env.
    $response=@(& $python -B $probe 2>$null)
    $exit=[int]$LASTEXITCODE
    if($exit -ne 0 -or $response.Count -ne 1){
        $result.status='UCIE_FRESH_REGISTRATION_PROBE_FAILED'
        $result.fresh_interpreter_exit=$exit
    }
    else {
        try {
            $row=ConvertFrom-Json -InputObject ([string]$response[0]) -ErrorAction Stop
            if([string]$row.schema -eq 'UCIE_MCP_FRESH_REGISTRATION_IMPORT_V1' -and
               [string]$row.status -eq 'UCIE_FRESH_PROCESS_TEN_TOOLS_PASS' -and
               $row.new_slack_tool_registered_in_fresh_python -eq $true){
                $result.status='UCIE_FRESH_PROCESS_TEN_TOOLS_PASS'
                $result.fresh_admin_tools=9
                $result.fresh_extra_slack_tools=1
            }
            else {
                $result.status='UCIE_FRESH_REGISTRATION_PROBE_BLOCKED'
                $result.fresh_block_code=[string]$row.block_code
            }
        }
        catch {$result.status='UCIE_FRESH_PROBE_RESPONSE_INVALID'}
    }
}
$result | ConvertTo-Json -Compress -Depth 3
