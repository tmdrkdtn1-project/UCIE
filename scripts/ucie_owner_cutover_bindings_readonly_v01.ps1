# UCIE owner Windows migration safety: read-only known Task/MCP path inventory.
# Does not move folders, start/stop tasks, inspect secret config contents or
# open SQLite. It cannot prove live tunnel health or authorize cutover.
[CmdletBinding()]
param([switch]$ContractOnly)

$ErrorActionPreference = 'Stop'
$schema = 'UCIE_OWNER_CUTOVER_BINDINGS_READONLY_V01'
$oldRoot = 'D:\UCIE'
$newRoot = 'D:\UCIE_PROJECT\UCIE'
$knownTasks = @(
    'UCIE-PublicMiner-Hourly',
    'UCIE-Internal-Minute',
    'UCIE-C40-Recover',
    'UCIE-LocalV1-Web'
)
$base = [ordered]@{
    schema = $schema
    status = 'UCIE_OWNER_CUTOVER_NOT_AUTHORIZED_NO_GO'
    source_root = $oldRoot
    proposed_repo_root = $newRoot
    known_ucie_task_names = $knownTasks
    all_ucie_tasks_enumerated = $false
    scheduled_task_actions_verified_for_new_root = $false
    mcp_live_tunnel_binding_verified = $false
    mcp_client_process_count_verified = $false
    owner_profile_and_acl_migration_verified = $false
    owner_checkout_dirty_files_backed_up = $false
    original_operating_db_backup_verified = $false
    owner_approved_live_migration = $false
    safe_to_move_or_delete = $false
    bridge_or_task_restarted = $false
    owner_files_moved = $false
    owner_files_deleted = $false
    git_clean_reset_gc_or_prune_executed = $false
    operating_database_opened_or_modified = $false
    private_profile_contents_read = $false
    network_requests = 0
}
if ($ContractOnly) {
    $base.status = 'UCIE_READONLY_SCRIPT_CONTRACT_ONLY_NOT_HOST_TESTED'
    $base.contract_only = $true
    $base.task_binding_checks_executed = $false
    $base.exact_paths_checked = @()
    $base.task_bindings = @()
    $base | ConvertTo-Json -Depth 6 -Compress
    return
}

# Must run in the actual original owner checkout, never at an arbitrary path.
$sourceRoot = ''
try {
    $sourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..') -ErrorAction Stop).ProviderPath.TrimEnd('\')
} catch {
    $base.status = 'UCIE_ORIGINAL_ROOT_UNAVAILABLE_NO_GO'
    $base | ConvertTo-Json -Depth 6 -Compress
    return
}
if (-not [string]::Equals($sourceRoot, $oldRoot,
        [System.StringComparison]::OrdinalIgnoreCase)) {
    $base.status = 'UCIE_ORIGINAL_ROOT_PATH_MISMATCH_NO_GO'
    $base | ConvertTo-Json -Depth 6 -Compress
    return
}
$rootItem = Get-Item -LiteralPath $sourceRoot -Force -ErrorAction Stop
if (-not $rootItem.PSIsContainer -or
    (($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
    $base.status = 'UCIE_ROOT_INDIRECT_OR_INVALID_NO_GO'
    $base | ConvertTo-Json -Depth 6 -Compress
    return
}

# Inspect ONLY these known UCIE-owned file or folder names. Never list D:\.
$exact = @(
    @{ Name = 'old_repo_git'; Path = 'D:\UCIE\.git' },
    @{ Name = 'old_venv_python'; Path = 'D:\UCIE\.venv\Scripts\python.exe' },
    @{ Name = 'public_miner_db'; Path = 'D:\UCIE\runtime\public_miner.sqlite3' },
    @{ Name = 'ucie_c40_bridge_health'; Path = 'D:\UCIE\.ucie_bridge_state\c40_supervisor_health_v1.json' },
    @{ Name = 'ucie_data_root'; Path = 'D:\UCIE_DATA' },
    @{ Name = 'ucie_preview_root'; Path = 'D:\UCIE_PREVIEW' },
    @{ Name = 'ucie_c40_profile'; Path = 'D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml' },
    @{ Name = 'ucie_c40_tunnel_client'; Path = 'D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe' },
    @{ Name = 'ucie_admin_registration'; Path = 'D:\UCIE_PREVIEW\UCIE_ADMIN\src\ucie_admin\mcp_registration.py' },
    @{ Name = 'proposed_ucie_parent'; Path = 'D:\UCIE_PROJECT' },
    @{ Name = 'proposed_ucie_repo'; Path = 'D:\UCIE_PROJECT\UCIE' }
)
$paths = @()
foreach ($entry in $exact) {
    $state = 'UNKNOWN_OR_INACCESSIBLE_NO_GO'
    $direct = $false
    try {
        $file = Get-Item -LiteralPath $entry.Path -Force -ErrorAction Stop
        $direct = (($file.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -eq 0)
        $state = if ($direct) { 'PRESENT_DIRECT_PATH' } else { 'REPARSE_PATH_NO_GO' }
    } catch [System.Management.Automation.ItemNotFoundException] {
        $state = 'MISSING'
    } catch [System.IO.FileNotFoundException] {
        $state = 'MISSING'
    } catch {
        $state = 'UNKNOWN_OR_INACCESSIBLE_NO_GO'
    }
    $paths += [PSCustomObject]@{
        label = [string]$entry.Name
        status = $state
        direct_non_reparse_path = [bool]$direct
    }
}

# Query four explicitly known UCIE tasks. Do not enumerate every user's tasks.
$bindings = @()
$scheduledTasksAvailable = $true
try {
    Import-Module ScheduledTasks -ErrorAction Stop
} catch {
    $scheduledTasksAvailable = $false
}
foreach ($name in $knownTasks) {
    $state = 'UNKNOWN_OR_UNREADABLE_NO_GO'
    $actions = -1
    $oldExecute = $false
    $oldWorkingDirectory = $false
    $oldArguments = $false
    $dataBinding = $false
    $previewBinding = $false
    if ($scheduledTasksAvailable) {
        try {
            $task = Get-ScheduledTask -TaskPath '\' -TaskName $name -ErrorAction Stop
            if ($null -ne $task) {
                $state = [string]$task.State
                $acts = @($task.Actions)
                $actions = $acts.Count
                if ($acts.Count -eq 1) {
                    $execute = [string]$acts[0].Execute
                    $arguments = [string]$acts[0].Arguments
                    $work = [string]$acts[0].WorkingDirectory
                    $oldExecute = $execute.IndexOf('D:\UCIE\', [System.StringComparison]::OrdinalIgnoreCase) -ge 0
                    $oldWorkingDirectory = [string]::Equals($work.TrimEnd('\'),
                        $oldRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
                        $work.IndexOf('D:\UCIE\', [System.StringComparison]::OrdinalIgnoreCase) -ge 0
                    $oldArguments = $arguments.IndexOf('D:\UCIE\', [System.StringComparison]::OrdinalIgnoreCase) -ge 0
                    $dataBinding = ($execute + ' ' + $arguments + ' ' + $work).IndexOf(
                        'D:\UCIE_DATA\', [System.StringComparison]::OrdinalIgnoreCase) -ge 0
                    $previewBinding = ($execute + ' ' + $arguments + ' ' + $work).IndexOf(
                        'D:\UCIE_PREVIEW\', [System.StringComparison]::OrdinalIgnoreCase) -ge 0
                }
            }
        } catch {
            $state = 'UNKNOWN_OR_UNREADABLE_NO_GO'
        }
    }
    $bindings += [PSCustomObject]@{
        task_name = $name
        observed_state = $state
        action_count = $actions
        action_executable_references_old_root = $oldExecute
        action_workdir_references_old_root = $oldWorkingDirectory
        action_arguments_reference_old_root = $oldArguments
        action_mentions_ucie_data_root = $dataBinding
        action_mentions_ucie_preview_root = $previewBinding
        task_configuration_was_modified = $false
    }
}
$base.contract_only = $false
$base.task_binding_checks_executed = $scheduledTasksAvailable
$base.exact_paths_checked = $paths
$base.task_bindings = $bindings
$base.path_dependencies_read_only = $true
$base.status = 'UCIE_OWNER_TASK_AND_MCP_PATHS_OBSERVED__CUTOVER_BLOCKED_NO_GO'
$base | ConvertTo-Json -Depth 7 -Compress
