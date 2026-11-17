# UCIE_PROJECT cutover — exact owner Windows Task/MCP binding safety check (2026-11-17)

PROJECT: UCIE ONLY. Branch-only new script and test; NOT an approved live folder migration or confirmed tunnel uptime.

## Why direct moving D:\UCIE would break things

Actual UCIE-owned source has fixed old-root guards in bootstrap_local.ps1, install_hourly_task.ps1, install_internal_minute_task.ps1, and LocalV1 autostart. C40 scripts refer to D:\UCIE, D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml, D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe, and D:\UCIE_PREVIEW\UCIE_ADMIN paths. The exact presence/health/ownership of those sibling UCIE paths on the owner Windows host is NOT known from GitHub source references. Installing a junction at the old path is NOT a verified workaround; old scripts reject reparse roots.

Current UCIE read-only admin bridge returned UCIE_LOCAL_ADMIN_BRIDGE_READY to tool calls, which means it was reachable at that moment, NOT that every tunnel client, Task Scheduler job, or app was independently healthy. The Git working tree still has **230 nonclean entries (20 tracked modified, 210 untracked)**. Treat unknown source scripts, receipts, .git history, active DBs, venv, locks and opt-ins as protected.

## New owner-local read-only snapshot

Script: scripts/ucie_owner_cutover_bindings_readonly_v01.ps1

The script is intentionally pinned to the current exact direct root D:\UCIE. It queries only four explicitly known UCIE scheduled-task names:
- UCIE-PublicMiner-Hourly
- UCIE-Internal-Minute
- UCIE-C40-Recover
- UCIE-LocalV1-Web

It reads their states and whether one action refers to the OLD UCIE root in the executable/args/working directory. It NEVER prints executables, task arguments, usernames, SIDs, credentials, public tokens or profile contents. It checks exact known UCIE-only path **existence/reparse flags**, not file contents, for .git, venv python, operating miner DB, C40 health receipt, DATA/PREVIEW roots, C40 YAML/client/admin registration, and intended new parent/repo path. It does not enumerate D:\, other user tasks, system processes or other projects. Missing/inaccessible paths are not assumed safe.

The script is ALWAYS fail-closed: all_ucie_tasks_enumerated=false; mcp_live_tunnel_binding_verified=false; mcp_client_process_count_verified=false; owner_approved_live_migration=false; safe_to_move_or_delete=false, even when every known file exists. A profile on disk is not proof that the tunnel is running or the plugin is bound to it.

After a separately approved exact-file installation inside the ORIGINAL UCIE checkout (never by git pull over 230 dirty entries), the owner may obtain the NON-MUTATING Windows snapshot by running:

    powershell.exe -NoProfile -NonInteractive -File D:\UCIE\scripts\ucie_owner_cutover_bindings_readonly_v01.ps1

This instruction is for an explicit future owner-controlled step only. **We have NOT installed or executed this script on owner D:\UCIE**. For CI only, the contract-only command does not inspect actual owner Tasks:

    powershell.exe -NoProfile -NonInteractive -File scripts\ucie_owner_cutover_bindings_readonly_v01.ps1 -ContractOnly

No data collection is necessary from unrelated folders. The emitted JSON report should be reviewed in the UCIE workroom; do NOT include secrets or unfiltered private task arguments.

## Migration critical path and hard NO-GO

1. Inventory known scheduled task actions, existing C40 tunnel/UCIE plugins and UCIE-local app, active clients/locks and owner ACLs (not all are accessible through present bridge).
2. Back up and classify **each** of 230 dirty entries; verify database snapshot/checksum and recovery receipts separately. Never delete unknown files or call git clean/reset/gc/prune.
3. Stage empty D:\UCIE_PROJECT only after owner destination ACL/path existence validation. Prepare UCIE-only isolated QA and hash-pinned backup. Keep all live old paths in service.
4. Patch all absolute references in the isolated first-party copy and run independent Windows Python3.15, fixed-path Task/C40 MCP/tunnel, security/negative and rollback tests. No auto-restart, no symlink/junction bypass.
5. Only with owner-approved outage plan and exact rollback image, stop specifically identified UCIE services and apply a single coordinated relocation; verify Task Scheduler actions, C40 one-client process, MCP plugin round-trip, LocalV1, DB and Python env; reverse on mismatch.
6. Only after successful owner acceptance, consider selective quarantine of verified Python caches and review-based retention cleanup. No proven host runtime speedup or reclaimed disk space in this iteration.

## CI acceptance boundaries

GitHub CI Windows Python3.13/3.15 runs the script with -ContractOnly and uses PowerShell parser without touching host live tasks. Ubuntu Python3.13/3.15 validates static no-mutation constraints; Windows-only dynamic cases are explicitly skipped on Ubuntu, NOT misreported as PASS. Real owner host binding snapshot, current tunnel health, desktop experience, or safe relocation are NOT certified by CI.

STATUS=UCIE_OWNER_CUTOVER_BINDING_PREVIEW_ONLY__TASK_MCP_PATH_MIGRATION_NO_GO__OWNER_DIRTY_FILES_UNCHANGED__PUBLIC_P11_HOLD__CUSTOMER_V1_NO_GO
