# UCIE P10 1-minute INTERNAL dispatcher (existing hourly miner unaffected).
# Default preview only; -Install explicitly creates a new UCIE-only queue/task.
[CmdletBinding()]
param([switch]$Install)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath.TrimEnd('\')
if (-not [string]::Equals($root, 'D:\UCIE', [StringComparison]::OrdinalIgnoreCase)) { throw 'UCIE_P10_EXPECTED_EXACT_ROOT' }
if ((Get-Item -LiteralPath $root).Attributes -band [System.IO.FileAttributes]::ReparsePoint) { throw 'UCIE_P10_ROOT_IS_SYMLINK' }
if (-not (Test-Path -LiteralPath (Join-Path $root '.git') -PathType Container)) { throw 'UCIE_P10_CHECKOUT_MISSING' }
$py = Join-Path $root '.venv\Scripts\python.exe'
$module = Join-Path $root 'src\ucie_miner\runtime_pipeline.py'
$entry = Join-Path $root 'scripts\internal_minute_tick.py'
if (-not (Test-Path -LiteralPath $py -PathType Leaf) -or -not (Test-Path -LiteralPath $module -PathType Leaf) -or -not (Test-Path -LiteralPath $entry -PathType Leaf)) { throw 'UCIE_P10_RUNTIME_FILES_MISSING' }
$version = (& $py --version 2>&1 | Out-String).Trim()
if (-not $version.StartsWith('Python 3.15')) { throw 'UCIE_P10_REQUIRES_PYTHON_315' }
$taskName = 'UCIE-Internal-Minute'
$existing = Get-ScheduledTask -TaskPath '\' -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -ne $existing) { throw 'UCIE_P10_EXISTING_TASK_REFUSE_OVERWRITE' }
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Output 'P10_TASK=UCIE-Internal-Minute'
Write-Output 'FREQUENCY=PT1M'
Write-Output 'MODE=NONBLOCKING_CLAIM_AND_SPAWN'
Write-Output 'WORKER_LIMIT=3'
Write-Output 'OTHER_SCHEDULED_TASKS_MODIFIED=FALSE'
Write-Output 'PUBLIC_API_GETS_IN_P10_RUNTIME=0'
Write-Output 'RULE_AUTO_PROMOTION=FALSE'
if (-not $Install) {
    Write-Output 'PREVIEW_ONLY_NO_QUEUE_OR_TASK_CREATION'
    return
}
# Explicit install only: initialize isolated UCIE queue, do not run any public miner.
$env:PYTHONPATH = Join-Path $root 'src'
$init = & $py -B -m ucie_miner.runtime_pipeline --ucie-root $root --initialize
if ($LASTEXITCODE -ne 0) { throw 'UCIE_P10_QUEUE_INITIALIZE_FAILED_NO_TASK_CREATED' }
Write-Output $init
$action = New-ScheduledTaskAction -Execute $py -Argument ('-B "' + $entry + '"') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskPath '\' -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'UCIE P10 independent read-only minute dispatcher; hourly public miner unchanged' -ErrorAction Stop | Out-Null
Write-Output 'TASK_REGISTERED=TRUE'
Get-ScheduledTask -TaskPath '\' -TaskName $taskName | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskPath '\' -TaskName $taskName | Select-Object LastRunTime, NextRunTime, LastTaskResult
