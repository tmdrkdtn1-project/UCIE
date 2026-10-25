# UCIE P5 — real Windows V2 SID/ACL result and one-folder owner bootstrap

Date: 2026-10-25 KST
Workroom: UCIE only
PR: https://github.com/tmdrkdtn1-project/UCIE/pull/79
State: OWNER V2 FACTS REVIEWED / HOST INSTALL NOT AUTHORIZED / AUTO PROMOTION OFF

## Actual, owner-provided V2 diagnostic facts

Output schema: \`UCIE_WINDOWS_IDENTITY_ACL_READONLY_DIAGNOSTIC_V2\`.
It is a **local owner-reported observation**, not cryptographically signed
host attestation. Do not reproduce or disclose raw Windows SID, user names,
credential values, private key material or unrelated host records.

- UCIE root exists with no observed reparse ancestor.
- \`UCIE-PublicMiner-Hourly\`: exists, principal SID resolved and is **equal**
  to the current owner Windows SID. \`Interactive / Limited / Ready\`.
  Therefore the earlier name-string mismatch was a **false mismatch**.
  **Keep the existing miner principal, task and launch action unchanged.**
- Reserved \`UCIE-C40-Supervisor\` task name is unoccupied.
- Existing \`D:\UCIE\.ucie_bridge_state\`: directory exists, ACL was read,
  its owner is the built-in Administrators group, not the current user SID;
  inherited ACL is enabled. The originally reported
  `broad_allow_write_ace_found=true` is **NOT reliable evidence of write
  permission**: the first V2 script incorrectly ORed `FullControl` into
  the test mask, inadvertently matching read-only rights. A later source
  patch changes the mask to Write/Delete/DeleteSubdirectoriesAndFiles/
  ChangePermissions/TakeOwnership only. Owner must rerun that exact
  SHA-pinned corrected read-only V2 script before declaring any broad-write
  ACL finding. The Administrators owner + inherited ACL remains a security
  **REVIEW item**, not proof of compromise.
  The directory is existing UCIE admin backup/audit state. DO NOT reuse as
  an unattended operation authorization journal; do not change its owner
  or ACL automatically because that could break the existing admin bridge.
- Proposed independent \`D:\UCIE_DATA\ucie_unattended_state\`: does **not**
  exist. No host trust key, independent anti-rollback anchor or privileged
  unattended operation has yet been installed.
- Existing services/tasks, Git, rule promotion and ACLs were not changed by
  the read-only V2 diagnostic.

## New first-party source

- \`src/ucie_public/unattended_identity_reconciliation.py\` evaluates the
  bounded V2 report and distinguishes a correctly matching miner SID from
  the separate existing bridge ACL risk and the absent operations journal.
  It NEVER returns an install permission or live operational PASS.
- \`scripts/ucie_unattended_owner_journal_bootstrap.ps1\`:
  - Default mode is **inspect/no write**.
  - Exactly one proposed target: \`D:\UCIE_DATA\ucie_unattended_state\`.
    Source code and operation journal are separate, so no unexpected Git
    changes or accidental source checkout writes.
  - \`-Apply -Approval APPROVE_UCIE_NEW_OPERATIONS_DIRECTORY_ONLY\` can
    create this **single directory ONLY after a fresh, explicit owner
    approval**. Do not run Apply until the owner approves this exact action.
  - Fails closed if target already exists; parent is absent/linked, its
    owner not the current user/SYSTEM/Administrators, or any writable ACE
    belongs to an unknown, foreign or broad account. Parent ACL may require
    owner review rather than automatic alteration.
  - Creates a **new** directory with explicit owner SID + SYSTEM Full
    Control DACL, inheritance disabled, by using .NET's atomic
    security-at-creation method. Uses the .NET Framework overload on Windows
    PowerShell 5.1 and FileSystemAclExtensions on PowerShell 7+. If the
    API or ACL verification fails, the script errors without pretending PASS.
    No pre-existing directory ACL is modified.
  - Outputs non-identifying booleans, never raw SID/ACL/secret data.
  - Does NOT create a host signer, Git credential, Windows scheduled task,
    launch C40, set an external trust anchor, publish PRs or promote rules.
- Synthetic unit tests and Windows AST syntax checks ensure the limited
  source contract; no actual Windows creation takes place in GitHub Actions.

Official .NET design references (for security-at-creation):
- https://learn.microsoft.com/en-us/dotnet/api/system.io.directory.createdirectory
- https://learn.microsoft.com/en-us/dotnet/api/system.io.filesystemaclextensions.createdirectory

## Exact requested future approval (NOT YET GRANTED)

\`UCIE_APPROVE_ONE_NEW_OWNER_ONLY_OPERATIONS_DIRECTORY\`

Only create \`D:\UCIE_DATA\ucie_unattended_state\` with owner current SID +
LOCAL SYSTEM full permissions, ACL inheritance disabled, under existing
safe parent. No change to \`D:\UCIE\.ucie_bridge_state\`, existing hourly
task, supervisor tasks/services, C40 profile, GitHub credentials, source
database, packages, rule promotion or other projects. If parent ACL unsafe,
report \`NO_GO\`, do not alter parent. After actual Windows command execution,
require exact structured result and independent ACL verification before
considering separate OS anti-rollback/signing/token bootstrap.

**Source CI PASS != owner Windows host install PASS.** PR remains Draft.

## Correction to original V2 ACL test (2026-10-25)

The old diagnostic combined `Write | Modify | FullControl` and then used
`mask -band ACE_rights`. `FullControl` includes read bits, so the old
`broad_allow_write_ace_found=true` may be a **false positive**. The new
V2 and V1 read-only diagnostic and the P5 bootstrap parent safety test use
the narrower actual mutation mask `Write | Delete |
DeleteSubdirectoriesAndFiles | ChangePermissions | TakeOwnership`.
Do not treat any reported broad-write state from the old executable hash as
verified. Actual host ACL changes remain **NOT AUTHORIZED**.
