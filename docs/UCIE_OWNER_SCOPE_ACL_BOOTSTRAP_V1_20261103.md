# UCIE owner-scoped grant directory ACL bootstrap V1

Only for owner-controlled \`D:\UCIE_HUB\04_MIGRATION\UCIE_OWNER_SCOPED_QA_V1\`.
This is **not** a grant or approval and does not activate any MCP tools.

Current read-only Windows survey (2026-11-03) found the grant directory absent.
The owner-scoped batch/bridge/tools Python source blobs match PR #175 exactly
and focused isolated local Python tests passed 47+21+11 cases. The live server
does NOT yet have the four owner tools attached, and current remote MCP
owner session authentication has NOT been established. Therefore
**MUTATING OWNER MCP AUTHORIZATION = NO_GO** independently of directory ACL.

## Owner directory preflight

The new script \`scripts/ucie_owner_scope_acl_bootstrap_once.ps1\`
defaults to Preview:

\`& 'D:\UCIE\scripts\ucie_owner_scope_acl_bootstrap_once.ps1' -Mode Preview\`

Its guardrails:
- Must run as elevated Windows owner matching the exact existing root
  \`UCIE-C40-Recover\` task owner, Running/Highest/Interactive.
- The migration parent must already exist, not be reparse-linked, and have
  no write-authorized identities beyond the exact owner, Administrators and
  SYSTEM; refuse unresolved write principals.
- If the target scope directory exists, refuse overwrite.
- Preview only prints bounded readiness flags/status and changes nothing.

## One-time ACL creation — local owner only, NOT run by ChatGPT

Only if Preview reports \`ready_to_create=true\`, the local owner may
choose to run in elevated PowerShell:

\`& 'D:\UCIE\scripts\ucie_owner_scope_acl_bootstrap_once.ps1' -Mode Apply -OwnerOnlyConfirmed\`

Enter the exact local phrase \`UCIE_OWNER_SCOPE_ACL_ONLY\` at the prompt.
The script repeats its checks and creates **only** the new scope directory
with an explicit owner/Admin/SYSTEM full-control ACL, inheritance disabled.
It never modifies the parent directory's ACL, creates \`grant.json\`,
changes scheduled tasks, manages processes, runs code from a commit, signs
rules or enables MCP registrations. Post-write ACL must pass exact checks.

A blocked Preview requires investigation; do not weaken the ACL checks to
force creation. This is intentionally a separate local owner action because
the existing UCIE Admin plugin has neither arbitrary PowerShell nor
OS ACL mutation rights. Report \`BLOCKED_PARENT_ACL\` if a broad writer is
found. Do not substitute a static owner environment marker for session auth.

## Next stage after ACL creation

Implement an actual trusted server-owned per-request identity context on
the existing UCIE FastMCP host and demonstrate forged/non-owner rejection.
Then register \`ucie_owner_scope_status/enroll/revoke/apply\` exactly once,
verify a real owner request and a denied non-owner request. Only after that
step, run an isolated disposable-root one-batch CI SHA/rollback acceptance
before granting permission for a bounded real-host batch. No code auto-promotion.

PR #175 remains Draft and C40 recovery supervisor remains unchanged.
