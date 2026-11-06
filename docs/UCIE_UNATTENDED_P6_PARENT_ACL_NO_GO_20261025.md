# UCIE P6 — Actual parent ACL NO_GO and targeted read-only inspection

Date: 2026-10-25 KST
Project: UCIE only, PR #79 Draft, production installation NOT authorized

## Latest owner-local observations

Owner supplied two JSON reports from fixed UCIE read-only scripts.

- \`UCIE_WINDOWS_IDENTITY_ACL_READONLY_DIAGNOSTIC_V2\`:
  the existing hourly public miner principal SID resolves and matches the
  current owner Windows user SID. The existing task is Interactive / Limited
  / Ready. The UCIE C40 Supervisor task name is unoccupied.
  Existing \`D:\UCIE\.ucie_bridge_state\` belongs to built-in Administrators,
  has inherited ACL and a broad mutating allow ACE was reported. This is
  direct ACE-pattern detection, NOT an independently measured effective
  access check or evidence of compromise. Preserve the existing bridge
  path/owner/ACL until reviewed separately.
- \`UCIE_OWNER_OPERATIONS_DIRECTORY_BOOTSTRAP_V1\` default/no-Apply:
  \`UCIE_PARENT_OWNER_OR_ACL_UNSAFE_NO_INSTALL\`.
  The parent \`D:\UCIE_DATA\` exists and none of its ancestors was detected as
  a reparse point. The combined owner/ACL guard is false. No new operations
  directory was created and no credentials, Windows task, service, Git
  publishing or Rulepack promotion was changed.
- \`D:\UCIE_DATA\ucie_unattended_state\` does not exist yet. The V2
  \`broad_allow_write_ace_found\` result concerns the *existing bridge
  directory*, not proof about the proposed journal parent.

The combined parent guard conflates distinct conditions:
owner unallowlisted, ACL unreadable, broad/foreign modifying ACE, unresolved
allow ACE. It cannot identify which blocked installation. No \`-Apply\` until
the exact cause is observed and reviewed.

## Single next read-only check

New \`scripts/ucie_unattended_parent_acl_cause_readonly_v1.ps1\`
inspects **only the fixed parent** \`D:\UCIE_DATA\`, and reports:
owner category as booleans (current user/Administrators/SYSTEM/other),
ACL readable, link-free ancestors, explicit broad/foreign modifying ACE,
unresolved allow identity, inheritance, and whether a target is already
present. The owner Windows account name, raw SID, ACL rules, token and
unrelated directories are never reported.

The diagnostic never grants OS installation authority and does not modify
existing files, ACLs, tasks, services, C40, Git or rules. CI syntax-parses
but never executes PowerShell; actual host result requires an owner-run
read-only invocation after SHA pinning.

If owner is not on the allowlist, or a foreign/broad writer can mutate the
parent, **keep this target NO_GO**. Do not change ACLs of the existing
\`D:\UCIE_DATA\` tree as a shortcut. A separate UCIE-only protected parent
under verified owner control could be evaluated in a later, distinct approval,
but no alternative path has been installed or declared safe.

## Acceptance gates remain

1. Read-only parent cause report actually observed on owner Windows host.
2. Independent review of parent ownership/ACL and exact target path.
3. Fresh explicit owner permission for one narrowly scoped directory action.
4. OS-protected signed grant+anti-rollback epoch and revocation before host
   executor can access the new journal.
5. Live, independently verified Git Draft PR and C40 functional recovery;
   no main auto-merge, no auto rule promotion without separate human QA and
   owner release signature.

Result: \`P6_PARENT_ACL_CAUSE_PENDING / HOST_INSTALL_NO_GO /
EXISTING_MINER_UNCHANGED / AUTO_RULE_PROMOTION_OFF\`.
