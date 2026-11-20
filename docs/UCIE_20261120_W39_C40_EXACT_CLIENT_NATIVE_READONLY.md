# UCIE W39 — one exact C40 client process image/owner, read only

Date: 2026-11-20. Project scope: **UCIE ONLY**. This source-only
milestone does not touch, restart, install, reconfigure or access the
C40 tunnel through any network connection. Owner-host W39 is NOT RUN.

## Why W39 exists

W35 real owner Windows observation accepted the ORIGINAL LocalV1 one-loopback
listener, same owner, exact task argv and Windows Python 3.15 virtualenv
redirector configuration. W37 real owner TaskScheduler/Operational ID 129
query was \`UCIE_W37_TASK129_NO_MATCH_HOLD\` with the channel enabled. That
historical log must not be broadened or re-created. W38 connected
\`ucie_admin_capabilities({})\` produced \`UCIE_LOCAL_ADMIN_BRIDGE_READY\`,
but returned NO independently trusted C40 connector/session/transport
binding. W38 source-only false-PASS regression merged in
\`0ab6c549bc493988abcee66ee17548c365313d9a\`.

The first-party UCIE repository has a known old C40 Task
\`UCIE-C40-Recover\`, a dedicated client binary expected at
\`D:\UCIE_DATA\tools\tunnel-client-v0.0.16\tunnel-client.exe\`, and a
dedicated UCIE profile path
\`D:\UCIE_DATA\mcp_tunnel_profiles\ucie-private-c40.yaml\`.
These are **source claims**, not present-day host observations. Source:
\`docs/UCIE_20261117_OWNER_TASK_MCP_CUTOVER_READONLY_PRECHECK.md\`
and \`scripts/ucie_owner_cutover_bindings_readonly_v01.ps1\`.
No private profile contents, credentials or connector logs are collected.

## W39 first-party owner-native read-only inspection

\`scripts/ucie_owner_w39_c40_client_readonly_v01.ps1\`:
- Defaults to a no-host \`UCIE_W39_CONTRACT_ONLY_NO_HOST_ACCESS\` JSON.
  Inspect mode requires interactive original Windows account, canonical,
  non-reparse first-party newroot, clean pinned-ancestor Git source,
  explicit owner-approval string and expected task/file metadata. It
  never elevates automatically, starts another process or changes a service.
- Checks **one exact UCIE-C40-Recover Scheduled Task** Running and single
  action, with the same current Windows owner SID. It does not read Task
  Action args, credentials or task secrets; prior owner W35 historical
  C40 task-action integrity remains a separate observation.
- Checks only that the exact UCIE C40 client EXE and YAML profile path
  EXIST as direct non-reparse files. It does not open the profile.
- Uses a WQL query whose predicate is the **exact expected executable
  path** (escaped Windows backslashes), retrieving only ProcessId,
  ExecutablePath, CreationDate and ParentProcessId, NOT CommandLine.
  Requires exactly one matching process and the original task owner SID;
  then re-queries the same **path AND PID**, checking process creation time
  and owner SID for a simple rebind race. No enumeration of unrelated
  task names, service commands or other projects.
- Never prints PIDs, raw SID, client argv, profile text, external
  endpoint, tunnel tokens, raw WMI errors or other process details.
  Invalid or inaccessible state returns a sanitized HOLD JSON.

Even the best owner-native status here is only
\`UCIE_W39_ONE_EXACT_C40_CLIENT_IMAGE_OWNER_STABLE__MCP_ROUTE_HOLD\`.
This establishes an exact executable image/owner and stable PID *at the
sampling time*, **not** the tunnel client binding to the C40 task or
profile, not the actual tunnel endpoint, session authentication,
transport identity, or the *same* ChatGPT-to-C40 MCP request/response.
That identity remains independently blocked by issue
[#334](https://github.com/tmdrkdtn1-project/UCIE/issues/334).
Every output explicitly says \`c40_mcp_round_trip_verified=false\`,
\`connector_route_binding_verified=false\`, and
\`full_cutover_authorized=false\`.

## Official narrow Windows API grounding

- Microsoft Get-CimInstance \`-Query\`: filtered WQL read and strict
  backslash quoting.
  https://learn.microsoft.com/en-us/powershell/module/cimcmdlets/get-ciminstance
- Microsoft about_WQL: a Windows path backslash in a WQL value must be
  escaped with a second backslash.
  https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_wql
- Microsoft Win32_Process: ExecutablePath and CreationDate are read-only;
  GetOwnerSid retrieves owner SID.
  https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-process

## Test and acceptance boundary

\`tests/test_ucie_w39_c40_client_readonly_v01.py\` uses AST-extracted
pure first-party PowerShell helpers with synthetic Windows paths and fake
process records, plus source checks prohibiting broad process enumeration,
profile contents access and any scheduler/tunnel or SQLite mutation.
Require exact-head Windows/Ubuntu Python 3.13/3.15 CI 4/4 before
merging. Native owner W39 must be separately observed, with explicit
approval, after an exact merged SHA is synchronized and reviewed.

The original D:\UCIE writers, LocalV1, C40 tunnel, private archives,
SQLite, Task Scheduler, plugin registrations and external services
remain unchanged; W21 maintenance, W29/W30 recovery, C40 authentication
and full cutover remain HOLD. No automatic reconnection, log activation,
data migration or customer release.
