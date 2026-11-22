# UCIE P10C — Windows ACL SID-lookup false-blocker repair

Date: 2026-10-25 KST
Scope: UCIE only, Draft PR #79.
Classification: SOURCE FIX / OWNER HOST ROOT NOT INSTALLED / AUTOMATION OFF.

## Actual owner P10 read-only result

The owner fetched a fixed GitHub commit, restored precisely one new UCIE
PowerShell source file and invoked it with no `-Apply`. It reported:

- `UCIE_P10_PARENT_OR_ACL_REVIEW_NO_GO`;
- expected ProgramFiles parent exists and no reparse ancestors were seen;
- ACL readable; owner matches known trusted Windows principal;
- parent DACL canonical; no foreign mutating Allow ACE observed;
- `parent_unresolved_allow_identity=true`;
- target not present; no directory/service/task/C40/Git/rule changes;
- `caller_elevated_administrator=false`, as expected for non-elevated
  inspection.

The read-only output **does not establish** a safe operating root. It only
isolates the remaining *reported* blocker to identity resolution.
The `git fetch` object counts are download/local object maintenance and do
not establish that a new Git remote push was made.

## Root cause in source and correction

The first P10 code walked `Get-Acl.Access` and translated each ACE identity
from account name to `SecurityIdentifier` by `Translate()`, then treated
any mapping exception as an untrusted owner/ACL blocker. Windows may expose
legitimate ACEs whose account display name cannot be resolved. Treating
a failed account-name translation as an unknown writer is an overbroad gate.

The correction explicitly requests SID identities from the .NET
`DirectorySecurity.GetAccessRules($true,$true,[SecurityIdentifier])` API,
both on the parent and on post-create exact DACL verification. No account
names, SID values or raw ACL entries are emitted. Unmapped SIDs remain
present and are **not whitelisted**: their mutating Allow ACEs are classified
as foreign and still force NO-GO. Invalid/missing SID identities or a
failure to parse the ACL still fail closed.

Official technical basis:
https://learn.microsoft.com/en-us/dotnet/api/system.security.accesscontrol.commonobjectsecurity.getaccessrules
https://learn.microsoft.com/en-us/dotnet/api/system.security.principal.ntaccount.translate

## CI regression and owner action

- `tests/test_ucie_p10_sid_acl_scope.ps1`: synthetic in-memory ACL with
  fabricated, unknown SID. ReadAndExecute is not modifying; same SID with
  Write must be rejected. No filesystem or user data touched.
- CI executes this on Windows PowerShell 5.1 and PowerShell 7; Python
  source contract pins direct SID lookup. Existing P10 disposable Windows
  ACL-at-creation fixture is retained.
- Exact source SHA and source-commit pin must be verified from the current
  PR branch when tests complete, **before** updating the owner local file.
  A previously restored untracked owner file may be updated only after
  checking it equals the previous Git blob `1cea01945edaf2083947e40c9fe3fadc58a8b83d`.
- If subsequent default inspection returns
  `UCIE_P10_PARENT_OBSERVED_CANDIDATE_OWNER_APPROVAL_PENDING`, it means
  conservative owner-parent ACE screening passed **only**, and DOES NOT
  authorize `-Apply`, privilege elevation, an unattended service, a
  Git credential, or a C40 restart.
- If unknown modifying ACE, parent DACL, target collision or ancestry
  checks fail, retain NO-GO.

## Boundary and remaining work

Existing `D:\UCIE_DATA` and owner LocalAppData paths remain rejected.
Do not patch or relax their ACLs. No new random parent search.
Actual privileged install is separate, fresh owner authorization and
post-install independent ACL/effective access verification.
Protected runtime signer/epoch/rollback prevention, GitHub App credential,
one Draft PR acceptance and C40 functional post-restart/reboot tests are
still unimplemented as owner-host live operations.
No automatic Rulepack promotion.

Verdict: `P10C_SID_DIRECT_SOURCE_ONLY / HOST_RECHECK_PENDING /
PROTECTED_ROOT_NOT_CREATED / AUTO_C40_OFF / AUTO_GIT_OFF /
AUTO_RULE_PROMOTION_OFF`.
