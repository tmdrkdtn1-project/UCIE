# UCIE P10 — one approved Windows protected-root bootstrap, staged only

Date: 2026-10-25 KST
Project: UCIE only
GitHub: https://github.com/tmdrkdtn1-project/UCIE/pull/79 (Draft)
Operational classification: **NOT INSTALLED / NO-GO FOR UNATTENDED ACTIONS**

## Prior verified owner observations

- `D:\UCIE_DATA` rejected as trust-root parent: built-in Administrators
  ownership with inherited foreign/broad mutating Allow ACEs.
- Owner LocalAppData parent also rejected: 2 foreign parent-applicable
  mutating Allow ACEs, `DELETE` on parent but `DELETE_CHILD` not reported.
  Neither report included actual token-based Windows AccessCheck.
- Existing hourly UCIE public miner principal SID matches owner, task
  `Interactive / Limited / Ready`. The owner-approved C40 tunnel currently
  runs as a hidden process; reboot/logoff persistence not attested.
- Existing `D:\UCIE\.ucie_bridge_state` is the current UCIE admin bridge
  state and must NOT be repurposed or modified by this bootstrap.
- No protected host journal, monotonic independent rollback anchor,
  standing owner signer, short-lived GitHub App token or supervisor
  service/task is installed.

## P10 one-directory bootstrap source

`scripts/ucie_unattended_protected_root_bootstrap_p10.ps1` is the **only**
proposed installer for this phase. Its target derives from Windows
`Environment.SpecialFolder.ProgramFiles` plus exactly one
`UCIE_UnattendedHost` leaf. It takes no user-supplied absolute paths.

- **Default, no flags:** inspect the parent ACL and known Windows SID
  categories, 64-bit Windows identity, ancestor reparse flags, canonical
  DACL, foreign effective mutating Allow ACEs, and whether a target already
  exists; output booleans only. No filesystem write, service/task registration
  or token retrieval.
- The well-known permitted parent owners are Administrators, LOCAL SYSTEM,
  and the precise TrustedInstaller SID. Unresolved Allow identities,
  foreign mutating ACEs effective on the *parent*, unexpected parent owner,
  symlink/reparse, invalid paths and an existing target all block installation.
  An explicit `InheritOnly` ACE is *not parent-effective*; creation with a
  protected new DACL excludes inherited ACEs from the child. Parent trust
  is still a preliminary DACL inspection, not OS AccessCheck.
- **Mutation path is inert until `-Apply` AND exact phrase
  `APPROVE_UCIE_PROGRAMFILES_ROOT_ONE_DIRECTORY_ONLY` AND an elevated
  Administrator token** are simultaneously present. Even then, only a
  non-existing single directory can be created, with initial owner
  Administrators and exactly Administrators + SYSTEM FullControl ACEs
  and ACL inheritance disabled, using .NET ACL-at-creation.
- After creation the script reads back the new owner, DACL, canonical owner,
  ACE identities and inherited status. If verification fails, it exits with
  a specific HOLD; does **not** attempt to alter existing parent ACL or
  silently remove a partially created directory. It reports booleans and
  no account name, raw SID, user profile path or credentials.
- Scope stops at this **one directory**: service/worker identity and its
  file permissions are deliberately NOT provisioned yet. Current non-elevated
  miner must not be repointed to the protected path. The service writer
  would be added through a later separate approved service identity+ACL
  plan, never a blanket Users/Everyone ACE.

## Signatures, release and rollback safety

1. Owner verifies the source SHA256 and exact GitHub PR commit and reads the
   inspector-only output. This is not a signed operation release.
2. Explicit owner approval would need to cover **only** creation of
   `<Windows ProgramFiles>\UCIE_UnattendedHost` with exact ACL noted above.
   Source inspection PASS does not allow `-Apply`.
3. If created and exact ACL matches, freeze immutable evidence (target
   class, source digest, run time, owner approval, ACL checks) in UCIE-only
   audit records; never dump raw SIDs or credentials to public GitHub.
4. Follow-on tasks, each separate approval/gate: protected service identity,
   OS-held monotonic anti-rollback/revocation anchor, signed trusted policy,
   short-lived repo-scoped GitHub credential provider, one live Draft PR with
   actual CI, one controlled C40 post-restart MCP probe and reboot/logoff QA.
5. Do not call the new root `PRODUCTION_READY` unless the independently
   anchored anti-rollback and service identity are actually provisioned.
   Rulepack auto-promotion remains OFF pending independent QA and
   separately signed owner release decisions.

## Official Windows technical anchors

- https://learn.microsoft.com/en-us/dotnet/api/system.io.directory.createdirectory?view=netframework-4.8.1
- https://learn.microsoft.com/en-us/dotnet/api/system.io.filesystemaclextensions.createdirectory?view=net-10.0
- https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants
- https://learn.microsoft.com/en-us/windows/win32/services/service-security-and-access-rights

## Current stop conditions

No current ChatGPT UCIE admin MCP arbitrary shell/service install authority.
Any real folder creation requires owner's separate elevated Windows host
session and **fresh explicit scope approval**. Do not call the existing
D: `-Apply` installer and do not use LocalAppData. No other project paths.

**Verdict:** `P10_BOOTSTRAP_SOURCE_STAGED / OLD_PATHS_REJECTED /
PROTECTED_PARENT_NOT_LOCALLY_INSPECTED / OWNER_APPROVAL_NOT_GRANTED /
AUTO_GIT_OFF / AUTO_C40_OFF / AUTO_PROMOTION_OFF`.
