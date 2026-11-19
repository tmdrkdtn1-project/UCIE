# UCIE owner-scoped MCP V1 — live bridge readiness and go/no-go gates

Date: 2026-11-03 (KST). Scope: **only UCIE**. Do not inspect any
separate project or enroll production rights as part of a survey.

## Baseline evidence

Existing UCIE bridge \`ucie_admin_capabilities\` is online and read/write
source operations use SHA-256 expected leases with UCIE-only directories.
The Windows C40 transport has passed one controlled real client loss
recovery and one owner sign-out/sign-in reconnect, independently verified.
Those facts DO NOT authenticate a remote request to write development code.

Draft PR #175 includes three inert code modules:

- \`owner_scoped_batch_v1.py\`: 14-day, 12-batch limited grant, exact-commit
  CI and content hashes, max six bounded UTF-8 Python source/test files per
  batch, backups/rollback and a fail-closed crash journal.
- \`owner_scoped_bridge_v1.py\`: \`status/enroll/revoke/apply\` dispatcher. All
  inputs are snapshotted before a **server-owned** authentication callback.
- \`owner_scoped_mcp_tools_v1.py\`: opt-in registration of four names, with
  no server start or registration on import.

Host-focused isolated tests already passed on owner Windows:
\`test_ucie_owner_scoped_batch_v1.py\` 47/47,
\`test_ucie_owner_scoped_bridge_v1.py\` 21/21,
\`test_ucie_owner_scoped_mcp_tools_v1.py\` 11/11. Synthetic tests are not
proof that remote session identity or Windows ACLs are trusted.

## Evidence-only live preflight

\`tests/test_ucie_owner_scoped_host_readiness_readonly_v1.py\` checks:

1. Only known UCIE roots, exact live MCP server
   \`D:\UCIE_DATA\library_app\private_lib\mcp_stdio_server.py\`.
2. Exact Git blob pins of the three owner-scoped Python modules against PR
   #175 before applying any new UCIE source.
3. Static server-registration indicators without dumping any server code or
   sensitive credentials.
4. Presence and read-only ACL summary for
   \`D:\UCIE_HUB\04_MIGRATION\UCIE_OWNER_SCOPED_QA_V1\` using fixed paths.
5. No remote-session identity assertion. **A static UCIE owner approval marker,
   Windows login SID, or successful C40 tunnel is not authentication of the
   current remote MCP caller.**

A passing test means the survey ran. Any uncertain owner authentication,
grant ACL or server registration is **NO_GO** for mutating tools.

## Actual four-operation host activation — required gates

1. Trusted host can identify and authenticate the **current** owner MCP
   request from a non-caller-controlled server session. Evidence must show
   forged request fields/identity cannot impersonate the owner, and that the
   session identity is bound to the checked request through execution.
2. Local principal matches the UCIE owner; grant directory and backups
   belong to owner/admin and are not writable by broad identities.
3. Existing UCIE FastMCP server attaches four new operations exactly once
   with the authenticated callback, never passing a caller-supplied
   \`authenticated_session_action\`, test-mode flag, root, hub or verifier.
4. In disposable isolated **UCIE-only** Windows paths first: deny non-owner,
   deny forged/expired/revoked consent, fail on wrong GitHub CI SHA/matrix,
   reject target drift and duplicates, prove file backups+grant counter rollback,
   and fail closed after a simulated interrupted journal.
5. Observe an actual owner-authenticated status/enroll/revoke/apply MCP call
   with bounded receipt, a single approved source/test batch at most after
   test-passed escalation, and independent post-operation observation.
6. No recreation of the existing C40 tunnel, unattended registration,
   other UCIE scheduler/operating DB changes, rule signing, automatic learning
   promotion or merges based merely on simulated CI.

## Delivery boundary

The current UCIE administrator tool can atomically write approved
source/doc/test files with SHA leases. It cannot restart the MCP service,
execute arbitrary owner PowerShell or expose a server-owned authenticated
session just by taking a user request. **No production four-tool activation
is claimed** until the above host-specific gates truly PASS.

Target outcome for this stage:
\`HOST_READONLY_SURVEY_COMPLETE\` plus explicit blockers if any, then
\`HOST_ACCEPTED_BOUNDED\` only with real authenticated MCP receipts.
Keep PR #175 Draft until the latter is achieved.
