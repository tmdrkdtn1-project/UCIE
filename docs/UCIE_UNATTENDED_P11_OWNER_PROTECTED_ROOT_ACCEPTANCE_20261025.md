# UCIE P11 — owner-created protected host root acceptance and next activation contract

Date: 2026-10-25 KST
Project: UCIE only
Draft PR: https://github.com/tmdrkdtn1-project/UCIE/pull/79
Status: **P10 OWNER-REPORTED ROOT CREATION PASS; LIVE AUTOMATION STILL NO-GO**

## Actual owner-host report

The owner executed pinned \`scripts/ucie_unattended_protected_root_bootstrap_p10.ps1\`
with fresh, previously limited authorization for **one new folder only**,
and supplied \`UCIE_ONE_OWNER_PROTECTED_ROOT_BOOTSTRAP_P10_V1\` JSON.

- Status: \`UCIE_P10_ONE_PROTECTED_DIRECTORY_CREATED_ACL_RECHECK_ONLY\`
- Target class: \`WINDOWS_PROGRAMFILES_UCIE_UNATTENDEDHOST_ONE_ROOT\`
- Parent existed, no reparse ancestor observed, ACL readable, trusted
  well-known owner and canonical DACL; no foreign mutating Allow ACE and no
  unresolved Allow identity; direct SID rule reading was used.
- Run under an elevated Administrator token; no target existed before.
- **target_created_this_invocation=true** and
  **target_exact_admin_and_system_acl_verified=true**.
- The installer checked the newly created directory after creation for
  Administrators owner, a protected DACL with exactly Administrators and
  LocalSystem FullControl Allow ACEs, no inherited ACE.
- Existing UCIE Admin Bridge state, public miner, C40 tunnel, Windows
  scheduled tasks, source database and other-project resources untouched.
- No Git push, GitHub token, owner host signing key, external monotonic
  anti-replay state, worker identity, service registration or rule promotion.

This is **an owner-produced and self-verified Windows result**, not an
independent post-install OS attestation, effective access check, reboot
persistence acceptance or security release. Do not portray it as all those.

## Existing root boundary and service identity

The ProgramFiles root is a **protected administrative host/config trust
root**, not a general writable evidence database. Its current DACL allows
**Administrators and LOCAL SYSTEM only** and has inheritance disabled.
A normal, non-elevated owner account and any future service-specific SID
must **not be assumed** to have write access. Do not relax its parent ACL.

A distinct, one-time service identity and its service-object DACL must be
designed, pinned and approved before installing an executable. In particular:
- Keep UCIE owner-signing PRIVATE key entirely OFF the unattended worker.
- Keep immutable signing trust material and approved code hashes separate
  from mutable execution receipts.
- Provision a separate **writer-scoped child or separate OS-controlled
  operational-data root** only after explicit ACL and ownership review.
  Do not quietly add broad \`Users\`/\`Authenticated Users\` write ACEs.
- Windows service SID/restricted SID and service object change-config,
  start/stop permissions are distinct from filesystem ACLs.
- A writable SQLite journal and a hash chain are NOT independently anchored
  anti-rollback proof. Require a separately protected epoch/revocation
  checkpoint and an adversarial restore/replay test before real automation.

## New P11 evidence acceptance

\`src/ucie_public/unattended_p11_root_acceptance.py\` accepts exactly the
bounded owner-provided P10 schema, rejects any unexpected field, duplicate,
incorrect type, missing ACL PASS, unexpected mutation or foreign project.
It labels success \`UCIE_P10_ONE_DIRECTORY_OWNER_REPORTED_CREATED_ACL_MATCH\`
but **all production/readiness flags remain false**, including independent
host attestation, service writer, signer, anti-rollback, short-lived GitHub
App credential, C40 recovery, Git automation and Rulepack promotion.

\`tests/test_ucie_unattended_p11_root_acceptance.py\` covers actual-shaped
report, failed/forged/tampered flags, duplicate keys and strict NO-GO
semantics. CI is synthetic; it does not read the owner's Windows machine.

## Next implementation bundle (not authorized for installation yet)

1. **Separate ACL recheck and service-writer specification:** pin the
   root's direct SID DACL and source hashes, define one stable service
   identity, service-object ACL and a separate writer-scoped journal
   boundary. Any new ACL or service is a distinct fresh owner approval.
2. **Durable independent anti-rollback state:** bind policy sequence,
   revocation epoch and consumed nonce to an OS-protected checkpoint
   *separate* from SQLite, demonstrate lost-write and snapshot restore
   denial, including host reboots.
3. **First host sandbox activation:** verify actual exact installer,
   protected writer ACL, process identity and service executable hash;
   test one synthetic grant replay/rollback and reject every unauthorized
   operation. No public Git push or live C40 restart yet.
4. **Staged live acceptance:** obtain repo-scoped short-lived credential
   only through authorized provider, publish exactly one Draft PR and
   independently verify commit/CI; separately run bounded owner-approved
   C40 failure/recovery, including post-restart ChatGPT functional probe.
   Do not automatically merge or release rules.

**No permission for any of 1-4 was granted by the earlier ONE FOLDER
creation approval.** Do not re-run P10 \`-Apply\`; stop and report if any
preexisting folder/ACL changes appear without authorization.

## Official references

- https://learn.microsoft.com/en-us/windows/win32/services/service-security-and-access-rights
- https://learn.microsoft.com/en-us/windows/win32/api/winsvc/ns-winsvc-service_sid_info
- https://learn.microsoft.com/en-us/dotnet/api/system.security.accesscontrol.directoryobjectsecurity.getaccessrules

Final gate:
\`P10_OWNER_REPORTED_CREATE_AND_ACL_PASS / P11_SOURCE_ONLY /
SERVICE_WRITER_NOT_INSTALLED / EXTERNAL_ANTIROLLBACK_NOT_VERIFIED /
AUTOMATED_GIT_AND_C40_OFF / RULE_AUTO_PROMOTION_OFF\`.
