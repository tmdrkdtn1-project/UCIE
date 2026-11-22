# UCIE unattended operations P2 — trusted host bootstrap and partial-PR recovery

Date: 2026-10-23 KST
Source PR: #79
State: SOURCE-ONLY / LIVE OWNER HOST NOT ACTIVATED / NO AUTOMATIC RULE PROMOTION

## What has actually been implemented

1. Read-only Windows owner host inspector:
   \`scripts/ucie_unattended_host_readonly_preflight.ps1\` measures **UCIE-only**
   root, exact GitHub origin, tracked worktree, Python/worker presence, exact
   hourly task identity, fixed C40 profile/client existence and SHA256,
   and collision at the proposed \`UCIE-C40-Supervisor\` task name.
   Outputs redacted structured JSON. Reads no token and does not start,
   restart, install or terminate any task, service, tunnel or process.
   Windows CI syntax-parses it but **never executes it**.

2. Partial GitHub publication reconciler:
   \`src/ucie_public/unattended_github_reconcile.py\` classifies a crash after
   blob/ref creation, a branch without Draft PR, an existing matching
   Draft PR, changed \`main\`, foreign parent, branch collision or corrupt
   metadata. It never silently reuses consumed approval/nonce, updates
   any ref, recreates the PR, pushes to main, merges or signs a rule.
   The host must obtain independent authenticated GitHub observations;
   caller-supplied dictionaries are not evidence.

3. **Real GitHub API code path, not an installed host service**:
   \`src/ucie_public/unattended_live_publisher.py\` accepts a current
   detached Ed25519 **owner grant**, independent signed exact file manifest,
   and separately signed short-lived **host ticket**. These are all bound
   to one UCIE job/branch/base commit and SHA256 digests. The code:
   - Requires \`armed=True\` (otherwise fails before touching a journal).
   - Rejects using the owner public key as the host trusted key.
   - Rejects invalid host signature, expired >2-minute host ticket, foreign
     repo, unapproved base, altered files and invalid credential shape.
   - Reads remote \`main\` and branch using the fixed transport; accepts only
     absence of a new \`automation/ucie-*\` branch at the exact pinned base.
   - **Atomically consumes** the signed one-shot grant in the UCIE-local
     SQLite journal before any GitHub mutation.
   - Creates bounded blobs/tree/commit/new automation ref and one Draft PR
     via fixed UCIE-only API calls.
   - **Never force-pushes, writes main, auto-merges, installs a service,
     executes arbitrary shell commands, touches unapproved repos or
     promotes Rulepacks.**
   - Returns separate status for injected synthetic transport vs live API
     response. Even a live Draft PR response is CI_PENDING; it does not
     grant production approval.

   A crash after journal consumption is intentionally **NOT silently
   retryable**; an independent GitHub reconciliation and new explicit owner
   approval are required. A future OS worker must turn such uncertain cases
   into a task with status \`AMBIGUOUS_REMOTE_STATE_NO_GO\` and persist
   exact immutable receipts without exposing credentials.

4. Unit tests use ephemeral synthetic Ed25519 keys, fake GitHub transport
   and temporary SQLite database only. A new static contract test ensures
   the host inspector has no mutating PowerShell commands. GitHub Actions
   Windows workflow parses the PowerShell script with the built-in parser.

## Critical limits — do not claim operational readiness

- **No Windows host execution or OS privilege grant was performed.**
  The code does not install or configure a Windows Service/Task.
- The host signing key and public trust anchor have NOT been securely
  provisioned or pinned to the owner's Windows identity. The current
  \`verify_signed_host_ticket\` checks a cryptographic assertion; it does
  **not independently measure** live OS ACL/SID, trusted root or process.
- The external monotonic revocation/checkpoint anchor is NOT installed.
  The SQLite journal alone is vulnerable to restored old snapshots, so
  ***owner host bootstrap and rollback-resistant epoch storage are P0
  blockers for live authorization***.
- No GitHub App or short-lived installation credential is provisioned.
  A GitHub connector writing development files into PR #79 is **not**
  evidence the new local publisher can authenticate by itself.
- Real C40 functional recovery and boot/logoff persistence are NOT
  implemented/attested; policy engine remains source-only.
- No initial standing owner policy was signed. No autonomous Git publishes,
  automated C40 restarts, learning-rule release or QA signatures occurred.

## Next exact owner approval gate

Before executing a host script with mutation or registering services:
- Independently run the **read-only** UCIE inspector in the current owner
  Windows session, verify JSON report against the actual path/task/identity.
- Confirm exact owner-only C40 audience, planned supervision task owner SID,
  startup/logon constraints, existing C40 single instance, exact pinned
  binary/profile and rollback plan.
- Provision host trust anchor, OS-protected key storage and independent
  monotonic/revocation store; verify restored-DB attack rejection.
- Supply repo-scoped short-lived GitHub credential without ever pasting
  a token into ChatGPT or committing it.
- Execute **one signed synthetic-safe single Draft PR acceptance** on the
  exact UCIE repository, then review GitHub CI and protected main checks.
- Separately authorize a controlled C40 failure/recovery acceptance.

**Current source CI must be checked on the exact latest HEAD.**
No source test or dry-run allows replacing these live checks with PASS.
