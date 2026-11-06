# UCIE P7 — unsafe existing parent; alternative owner-only journal candidate

Date: 2026-10-25 KST
Project: UCIE only
Source: PR #79 (Draft)
Release: **NO-GO for real Windows host activation**

## Owner's actual Windows read-only report

The user returned `UCIE_OWNER_PARENT_ACL_CAUSE_READONLY_V1`:

- The existing `D:\UCIE_DATA` parent exists, its ancestors had no detected
  reparse points, and the parent ACL was readable.
- Parent owner = built-in Administrators, *not* current owner Windows SID.
- The parent has ACL inheritance enabled. Both **broad** and **foreign**
  mutating Allow ACEs were reported; both were marked inherited.
- No unresolved Allow ACE identities; eight Allow entries were observed.
- Proposed `D:\UCIE_DATA\ucie_unattended_state` did not exist.
- Guard result = `guarded_parent_criteria_met=false`, no directory
  created, no existing ACL changed, no scheduler changes, no Git push or
  C40 restart, and no rule promotion.

**Decision:** No authorized unattended trust root under this exact parent.
An Allow ACE is not an independently measured effective-permissions report,
but inherited modifying ACEs and owner mismatch establish that the
previously defined conservative installation policy rejects this parent.

File-system delete checks can depend on access rights on the parent
directory; protecting a new child DACL alone is insufficient to ignore
unsafe parent rights. Microsoft Windows reference:
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-deletefile

**Do not** change `D:\UCIE_DATA` or existing Admin Bridge state ownership,
inheritance, ACEs, files or existing UCIE scheduled tasks to bypass this
failed gate.

## UCIE-only alternative; not installed

Added `scripts/ucie_unattended_alternative_owner_parent_readonly_v1.ps1`.

It chooses a single exact candidate leaf
`CURRENT_OWNER_LOCALAPPDATA_UCIE_UNATTENDED_STATE`, implemented by
retrieving the Windows known folder LocalApplicationData with .NET and
appending `UCIE_Unattended_State`. It does **not** enumerate LocalAppData,
read user private files, expose the actual profile path, account names,
SIDs or raw ACEs. It reads only the known-folder directory ACL and reparse
flags of parent ancestors, and classifies broad/foreign mutating Allow
ACEs, including DELETE_CHILD.

This is a **conservative preliminary screen only**. Even a clean result
does not independently verify Windows host identity, security of every
ancestor ACL, an immutable rollback epoch, trusted owner/host signer,
revocation policy, GitHub App credential, reboot persistence or functional
C40 recovery. If false or uncertain, remain NO-GO; never force a parent
ACL change or install into an untrusted path. The previous
`ucie_unattended_owner_journal_bootstrap.ps1` is still pinned to the
rejected D: target and **MUST NOT be invoked with `-Apply`**.

## Next steps

1. CI: source-only offline tests + Windows PowerShell syntax parse, exact
   latest PR HEAD before any source-file staging claims.
2. Deploy only the new read-only diagnostic into the UCIE source directory
   through owner-scoped UCIE admin MCP using SHA-leased create and verify.
3. Owner runs the exact SHA-checked read-only diagnostic once and shares
   boolean-only JSON. It creates nothing.
4. If candidate passes the preliminary screen, develop a **separate**
   precisely scoped creation-at-ACL-time bootstrap for that leaf, with
   independently checked ancestor rights and an explicit fresh owner
   approval. Do not repurpose the D: installer.
5. Only later: external monotonic anti-rollback/revocation, protected host
   signer and short-lived GitHub credentials, one live Draft PR acceptance,
   one bounded C40 supervisor/reboot acceptance; automatic rule promotion
   stays OFF pending independent QA and separate release authorization.

Status: `P7_D_PARENT_NO_GO / OWNER_LOCALAPPDATA_CANDIDATE_NOT_INSPECTED /
NO_SERVICE_OR_ACL_MUTATION / AUTO_RULE_PROMOTION_OFF`.
