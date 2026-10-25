# UCIE P9 — stop parent-path iteration; consolidate unattended host trust bootstrap

Date: 2026-10-25 KST
Owner project: UCIE only
Reference: PR #79 (Draft). Stage is SOURCE-ONLY; no live operating grant.

## Owner-supplied P8 host observation

The *exact* source \`UCIE_OWNER_LOCALAPPDATA_ACE_SCOPE_READONLY_V2\`
reported a Windows owner LocalAppData parent with readable ACL, current
user ownership, inheritance, no reparse ancestors and two foreign Allow ACEs:

- 2 foreign modifying ACEs, 2 potentially inheritable to children.
- **0 inherit-only**; both apply to the parent.
- Both reported **not inherited** from an ancestor.
- Parent \`DELETE\` Allow ACE **true**, parent \`DELETE_CHILD\` Allow ACE **false**.
- Parent \`CREATE_CHILD\` and \`WRITE\` Allow ACE **true**.
- No foreign observed \`WRITE_DAC\` or \`WRITE_OWNER\`, no broad account
  modifying Allow ACE.
- No Windows token-based \`AccessCheck\` was executed; a matching Allow
  ACE is not proof that any particular principal can actually access
  or delete a protected child.
- Target not present; no folder, ACL, scheduler, C40, Git or rule mutation.

The earlier fixed \`D:\UCIE_DATA\` root was already rejected due to
Administrators ownership plus inherited broad/foreign mutating Allow ACEs.
The newer owner LocalAppData root is **also rejected under the present
conservative UCIE security policy**, not declared compromised. The
parent-DELETE vs parent-DELETE_CHILD distinction must remain explicit:
these are different permissions; neither P8 nor CI proves a Windows
effective-rights evaluation. Do not conflate them in security reports.

**Stop selecting a third user-writable directory and requesting one ACL
JSON per candidate.** That process does not establish an independent
anti-rollback/owner trust root. Prior candidate install scripts must
remain disabled (especially D: \`-Apply\`).

## Single P9 architecture for an owner-approved unattended host

Replace arbitrary parent probing with a **one-time UCIE-only privileged
bootstrap** whose *source* can be reviewed in a Draft PR before host
approval. No privilege is conferred by a Python JSON parser or a task
manifest alone.

1. **Identity + scope:** exact UCIE repository, signed release SHA,
   current owner Windows identity and one separately authorized host
   runtime/service identity. Service object ACL must protect
   change-config/start/stop; only approved principal may mutate the worker.
   Do not reuse a general administrator shell or widen the UCIE MCP bridge.
2. **Protected root:** at installation, use an owner-approved designated
   system-controlled UCIE-only storage location with verified parent +
   ancestor rights, reparse/collision checks and an exact ACL created
   **atomically**. Do not treat \`ProgramData\`, an arbitrary profile
   folder, or another disk as safe by name. Trust depends on observed OS
   ACL/effective access at the actual target and owner approval.
   Separate owner read-only audit access from host writer permissions.
3. **Rollback and authorization:** independently anchored monotonic epoch,
   atomic task claim, durable revocation and consumed-state receipts. A
   local SQLite database or hash chain alone must NOT be trusted against
   owner-host snapshot rollback. Validate hostile snapshot/replay tests.
   Never store owner release-signing private keys in the unattended worker.
4. **Restricted Git:** short-lived, UCIE-repo-scoped GitHub App credentials
   obtained through an owner-approved OS credential provider, never
   committed or pasted. Dedicated \`automation/ucie-*\` branch, Draft PR
   only; no force, direct main push, merge or release. Verify real remote
   ref, exact commit SHA, unique PR, bounded retries and real CI afterwards.
5. **C40 recovery:** owner-approved, single-instance Windows supervisor,
   owner lock and binary/profile hash pinning, two ordered live functional
   failures before restart, 20-minute minimum cooldown, max 2/hour, 4/day.
   Require actual process exit before restart, post-launch local MCP
   initialize/tools/list/public search and then an independent ChatGPT
   search/admin acceptance. A single tunnel 300-second absence is a
   signal, NOT independent authority to restart an unknown process.
6. **Learning gate:** public official-only evidence collection and verified
   error-pattern feedback can run automatically once live host gates pass.
   Keep automatic Rulepack promotion OFF without separately defined
   independent QA, approved release authority, signed Rulepack and
   rollback/revocation policy. Do not conflate knowledge ingestion, model
   training or rule deployment.

### Review acceptance and final statuses

- A signed plan, tested bootstrap installer and rollback rehearsal are
  required **before** the first privileged one-time Windows installation.
- Initial installation is a separate *explicit* owner approval specifying
  exact path, authorized identity, service/task name, executable hashes,
  file/registry writes, credential source and rollback.
- One real controlled GitHub Draft PR, genuine CI and C40 fail/recover
  experiment must be seen before claiming unattended operation readiness.
- P9 code classifies the supplied P8 observation only; it never reads the
  owner's Windows device and never authorizes installation.
- Only if those runtime gates and independent owner review succeed may
  an appropriate narrow, revocable standing operational policy be issued.

### Official security references

- https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights
- https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants
- https://learn.microsoft.com/en-us/windows/win32/services/service-security-and-access-rights
- https://learn.microsoft.com/en-us/dotnet/api/system.io.filesystemaclextensions.createdirectory

## Present verdict

\`P9_PARENT_CANDIDATE_SEARCH_CLOSED / D_PARENT_REJECTED /
LOCALAPPDATA_PARENT_REJECTED / PROTECTED_OWNER_HOST_BOOTSTRAP_NOT_INSTALLED /
AUTO_GIT_OFF / AUTO_C40_RECOVERY_OFF / AUTO_RULE_PROMOTION_OFF\`

Owner should not execute another repeated ACL-check script or any
previously offered \`-Apply\`. No existing UCIE Bridge, miner or C40
service/process was modified in this stage.
