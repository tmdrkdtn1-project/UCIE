# UCIE P8 — LocalAppData inherited foreign ACE scope / safer activation decision

Date: 2026-10-25 KST
Owner project: UCIE
Source PR: https://github.com/tmdrkdtn1-project/UCIE/pull/79 (Draft)
Operational state: NO INSTALL / NO AUTO PUSH / NO SERVICE RESTART / NO RULE PROMOTION

## Real source evidence (owner's Windows P7 JSON)

The `UCIE_OWNER_ALTERNATIVE_JOURNAL_PARENT_READONLY_V1` result confirms:

- Windows LocalAppData parent exists; no ancestor reparse points observed; ACL read OK;
- parent owned by the current Windows user; inheritance enabled;
- *no broad account mutating Allow ACE*;
- *one or more foreign account mutating Allow ACEs* were detected;
- no foreign parent `DELETE_CHILD` Allow ACE observed;
- six Allow ACEs; all identities resolved; target `UCIE_Unattended_State` absent;
- no user key read, OS changes, Git push, C40 restart, rules promoted or services installed.

The conservative P7 screen therefore returned `UCIE_LOCALAPPDATA_PARENT_UNTRUSTED_NO_INSTALL`.

**Crucial nuance:** an Allow ACE flagged as mutating does not prove that it
applies to the parent itself. Its inheritance/propagation may make it
*inherit-only*. Also `DELETE_CHILD` and `DELETE`, `WRITE_DAC` and
`WRITE_OWNER` on the parent have materially different security consequences
from the right to create a child. Distinguish those rights, not just
whether an ACE contains any Write bits.

Microsoft official source:
- https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights
- https://learn.microsoft.com/en-us/windows/win32/wmisdk/file-and-directory-access-rights-constants
- https://learn.microsoft.com/en-us/dotnet/api/system.security.accesscontrol.propagationflags
- https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object

Effective access still depends on actual user/group tokens, DENY entries,
privileges and ACE order. Our AST/script-only tests do not implement the OS
AccessCheck algorithm or an external anti-rollback anchor. The observations
are NOT owner-host attestation or a claim that a child folder would be safe.

## New limited source (no OS work yet)

`scripts/ucie_unattended_localappdata_ace_scope_readonly_v2.ps1`
scopes to the same owner LocalAppData parent as P7, reads only parent ACL
metadata (no directory/file enumeration, no account/SID/raw path output).
It counts distinct foreign mutating *Allow ACEs*, separating
`InheritOnly` from parent-effective ACEs and distinguishing
parent DeleteChild, Delete, ChangePermissions/TakeOwnership, CreateDirectories,
and Write rights. The output contains only bounded booleans/counters and
an advisory gate with **NO automatic installation permission**, even if a
benign inherit-only pattern is observed.

The P8 output will let the owner make a single informed decision about:
(a) retaining strict NO-GO for the current parent; or
(b) authorizing a separately designed, secured UCIE-only child DACL created
at the instant the new directory is created with independent ancestor
protection, exact SID binding, and owner-approved one-shot installer.

**No automatic relaxation of the old P7 gate is permitted.**

## Acceptance remains separate

1. Offline Python + Windows PS AST checks for exact HEAD.
2. Stage only the new readonly script to `D:\UCIE\scripts` with UCIE MCP
   exact SHA lease, if CI is green, and verify local presence.
3. Actual owner-run, SHA-pinned P8 readonly JSON observation once.
4. Separate owner approval for exactly one new UCIE operations state directory,
   if ACL trust is independently adequate; do not mutate existing parents.
5. OS-held monotonic ledger/revocation, secure signer and GitHub App tokens.
6. Controlled single Draft PR and C40 post-restart MCP test. No arbitrary
   unattended rule promotion: require independent QA and owner release gates.

P7 report does not authorize mutating operations. Existing UCIE miner and
C40 tunnel are preserved.
