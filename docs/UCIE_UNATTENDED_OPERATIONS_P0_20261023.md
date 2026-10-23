# UCIE unattended operations P0 — owner grant and fail-closed preflight

**Date:** 2026-10-23 KST
**Project:** UCIE only
**Branch:** feat/ucie-unattended-ops-foundation-20261023
**State:** source-only, offline validation pending; **NOT INSTALLED**
**Deployment:** NO_GO
**Owner / QA release:** NOT APPROVED
**Auto rule promotion:** OFF

## Why this precedes autonomous learning

Home-PC-free UCIE development requires durable work intake, restricted Git
publishing, a Windows-independent-of-MCP restart owner and safe approval
replay protection. Existing UCIE hourly miner, PR #77 public Library and
PR #78 owner-scoped C40 admin tunnel remain separate and unchanged.

There is **no** generic ChatGPT arbitrary shell / Git / OS escalation.
No access to unrelated projects, private conversations, files, or external
unapproved repositories is introduced.

## Delivered here: offline first-party control-plane primitives

\`src/ucie_public/unattended_ops.py\` has:

- Strict bounded, canonical JSON detached Ed25519 owner grant verifier.
- One exact \`project_id=UCIE\`, \`audience=UCIE_OWNER_ONLY\`, a fixed
  \`task_id\`, random nonce, monotonic sequence, 40-hex revision, <=15min
  validity, no duplicate/unknown fields and caller-provided trust anchor.
- Only three **named** operations:
  - \`GIT_BRANCH_PUBLISH\` -> \`tmdrkdtn1-project/UCIE\`
  - \`C40_RECOVERY\` -> \`UCIE_C40_TUNNEL\`
  - \`RULE_SHADOW_REVIEW\` -> \`UCIE_PUBLIC_RULE_SHADOW\`
- Read-only, strongly restrictive Git preflight. Rejects foreign repos, main
  branch push, changed protected config, symlinks, dirty preimages, missing
  local tests, missing secret scan or unverified owner credentials.
- Read-only C40 preflight. Requires independently observed failed functional
  MCP probe, exact owner binary/profile, absent old process, single-owner
  lock, zero active miner jobs, recovery cooldown, attempts <2.
- Rule shadow review can be planned but cannot sign or promote rules.
- Every result says **NO EXECUTION**. No git commands, subprocess, API calls,
  Windows tasks, service actions, key generation, DB writes or release action.

Tests use **ephemeral synthetic signing keys**, never production owner keys;
they exercise replay, forged signatures, foreign paths, source and branch
overrides, protected files, duplicate JSON and false health observations.

## P0 blockers before a remote command can be executed

1. **Owner-signed operator grant bootstrap.** Provision owner public trust key
   at the exact UCIE-only host. Keep the production private key owner-held
   (not in chat, repo, shared MCP server or unattended worker). Remote owner
   approval may deliver a short-lived signed request without opening PC.
2. **OS-protected durable journal.** Store last consumed owner sequence and
   nonce, with atomic claim under interprocess lock **before** execution.
   Filesystem safety and anti-rollback storage must be independently tested.
   Passing a \`last_consumed_sequence\` integer into this module is **not**
   durable replay protection. A caller may not treat a returned preflight as
   execution authorization.
3. **Bounded OS adapter** for exact Git or C40 actions. Owner-approved,
   background Windows process only, least-privilege identities, no generic
   shell, no scanning other project paths. Recheck every grant and OS fact
   *inside the owner adapter* immediately before and after action.
4. **Git branch publisher** with separate UCIE detached worktree, verified
   repository origin, exact base revision, signed owner grant, branch name
   \`automation/ucie-*\`, no force-push/no direct main push, protected config
   and secrets deny list, tests, OS atomic claim, explicit PR creation and
   actual CI status receipt. Scoped GitHub credentials held in Windows
   Credential Manager or equivalent trusted OS store, never in receipts.
5. **UCIE-only C40 Windows supervisor**, independently owned from its target
   tunnel client; exact verified binary/profile; no duplicate C40 clients;
   real \`initialize + tools/list + harmless search\` functionality probe;
   bounded recovery attempts/cooldown, stable stop-start ownership and
   roll back after failed post-probe. No generic process termination.
   Owner-controlled one-time service/task installation, reboot/logoff
   persistence and independent runtime acceptance are required. The currently
   observed background C40 launch alone has **no reboot persistence**.
6. **Learning and rule safety.** Keep existing Stage10/12/16 and PR77
   classification/QA history. Knowledge accumulation and candidate review
   may become unattended. Rulepack release requires separate signed owner
   decision, genuine independent QA, precise version/rollback evidence; the
   unattended worker does not possess release signing keys and cannot
   automatically approve external snippets.

## Suggested host acceptance, only after the owner's next approval

- One owner-scoped test-signed UCIE job; incorrect foreign/root/branch/task
  denied before an operation or credential access.
- One synthetic-safe UCIE source change => verified local tests => isolated
  automation branch => GitHub PR => exact four-job CI receipts, **no main push**.
- A controlled UCIE-only test of missing MCP functionality => one bounded
  recovery => actual post-recovery tool invocation. Verify no overlapping C40.
- Independently verify behavior after Windows logoff/reboot, without owner
  keeping a console window open. Do not claim PASS on scheduled-task presence.
- Restore an audit journal from known backup and confirm stale serial/nonce
  rejection; do not fake persistent approval/replay integrity.

## Test command for source inspection (not a host acceptance)

\`\`\`powershell
$env:PYTHONPATH='D:\UCIE\src'
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p test_ucie_unattended_ops.py -v
\`\`\`

## Current separation of facts

**Existing:** C40 owner-only admin read paths responded live; repo status clean;
hourly UCIE public-miner task observed; background windowless C40 one-shot
owner launch observed; PR77 provenance and one isolated CPython 3.15.1
public-case test observed.

**New:** source-only constrained owner-operation authorization and pure dry-run
preflights in this PR.

**Not done:** persistent owner grant provisioning, OS-held anti-replay, Git
automatic commit/push/PR runner, service supervisor installation, auto reboot
startup, automated learning closure, independent reviewer sign-off, signed
Rulepack promotion. No new owner secret, host service, tunnel, worker, task,
GitHub workflow or operating DB was changed.

**Acceptance gate:** Source CI matrix 4/4 required; source CI never means
a service was installed. Merge/host activation subject to explicit owner
approval and no access-boundary widening.
