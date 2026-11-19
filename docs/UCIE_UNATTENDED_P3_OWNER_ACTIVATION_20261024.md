# UCIE P3 — unattended runtime lifecycle and owner activation boundary

Date: 2026-10-24 KST
Project: UCIE only
PR: https://github.com/tmdrkdtn1-project/UCIE/pull/79
Status: SOURCE_ONLY / PR_DRAFT / HOST_INSTALL_NOT_AUTHORIZED / AUTO_RULE_PROMOTION_OFF

## New source

- \`src/ucie_public/unattended_dispatch_ledger.py\`: append-only, ordered
  operation lifecycle receipts using SQLite \`BEGIN IMMEDIATE\`, explicit
  monotonic event numbers and a chained SHA-256 event digest. Git publication
  states: \`CLAIMED -> REMOTE_MUTATION_STARTED -> DRAFT_PR_API_RESPONSE ->
  CI_PENDING -> CI_PASS_REVIEW_REQUIRED / CI_FAILED_HOLD\`. A lost GitHub
  response goes to \`AMBIGUOUS_REMOTE_STATE -> OPERATOR_RECONCILIATION_REQUIRED\`;
  it cannot automatically replay the owner grant or overwrite a branch.
  C40 path: \`CLAIMED -> RECOVERY_STARTED -> C40_POST_PROBE_PASS /
  C40_POST_PROBE_FAILED_HOLD\`. No production release terminal state exists.
  The verifier can detect changed, deleted or reordered rows **when checked
  against a separately preserved authentic external head**. A caller-provided
  head is not an OS trusted checkpoint; a restored DB plus restored head
  could defeat local-only integrity.
- \`src/ucie_public/unattended_c40_recovery_runner.py\`: fixed single-client
  stop -> independently observed exited -> one pinned-client start ->
  functional MCP post-probe, and HOLD with no automatic retry if post-probe
  fails. This is a **synthetic adapter contract**, NOT a Windows process
  controller. It cannot terminate/start a real C40 or register a service.
- \`tests/test_ucie_unattended_dispatch_ledger.py\` and
  \`tests/test_ucie_unattended_c40_recovery_runner.py\` exercise benign
  synthetic data and temporary local SQLite fixtures only.

## Verified present versus missing

**Verified earlier in ChatGPT:** UCIE owner-only MCP administrator capabilities
and read-only Git status called live. Those tools explicitly report
\`arbitrary_shell=false\`, \`automatic_service_restart=false\`,
\`automatic_git_push=false\`. A previously observed hidden C40 process was
not Windows reboot/logoff persistent. The existing hourly public miner
and its scheduled task are separate; do not register duplicates.

**Not independently verified:** actual Windows principal, inherited ACL,
the executable/profile SHA at the current home PC, C40 process owner,
functional FastMCP probe after restart, scheduled task restart behavior,
repo-scoped GitHub installation token, owner host-signing key, independent
anti-rollback epoch, policy revocation or any production QA/release approval.

## One-time operator preparation — no installation yet

The already developed and CI syntax-parsed
\`scripts/ucie_unattended_host_readonly_preflight.ps1\` is the first UCIE-only
check to run on the **owner Windows PC** after making the PR source available
in an isolated clean preview. It does not register tasks, restart services,
alter credentials or push commits. It reports fixed UCIE paths, Git remote,
hourly miner task identity/action, C40 executable/profile hashes, and
possible supervisor task-name collisions. It cannot establish an authorized
standing policy on its own.

**Operator approval scope after that real report:**
1. A single UCIE owner-only Windows supervisor task registration (if no
   conflicting task already exists), under the exact owner principal,
   with bounded reboots/logon semantics and no elevated SYSTEM identity.
2. OS-protected host identity and pinned public trust root, secure GitHub App
   credential reference (no secret in chat), and one owner-signed narrowly
   revocable operation policy. Explicitly NO arbitrary shell.
3. Externally anchored monotonic receipt epoch/rollback prevention distinct
   from the local SQLite journal.
4. Controlled UCIE-only one-Draft-PR test to \`automation/ucie-*\`, with
   real GitHub CI and no direct \`main\` push/merge.
5. Controlled single C40 recovery with real initialize/tools/list/search,
   cooldown, restoration and reboot/logoff persistence observations.

No standing signer/private key must be provided to an autonomous worker.
No external code copied verbatim, no unapproved public repository, no access
to private documents/chats, and no automatic promotion of collected rules.

## Current release gate

Do not mark the UCIE home PC as unattended-ready just because CI or the
offline synthetic supervisor passed. The **next legitimate owner approval**
is for the exact Windows installation plan following the owner-local
read-only report. Until then C40 runtime recovery, actual GitHub auto-push
and autonomous learning remain **NOT_ACTIVATED**.

The new code is source-staged within PR #79; the user-owned operating
\`D:\UCIE\` checkout and existing services were NOT changed by these
GitHub commits.
