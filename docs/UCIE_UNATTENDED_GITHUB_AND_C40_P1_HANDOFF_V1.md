# UCIE unattended GitHub and C40 supervisor P1 — source handoff

Date: 2026-10-23 KST
Parent: PR #79, exact branch \`feat/ucie-unattended-ops-foundation-20261023\`
State: **SOURCE ONLY / NO LIVE GIT PUSH / NO LIVE SERVICE RESTART / NO AUTO RULE PROMOTION**

## Delivered here

- \`src/ucie_public/unattended_github.py\` strictly binds **two separate
  owner Ed25519 signatures**: a short-lived V1 exact-operation grant and the
  canonical, immutable GitHub publish manifest. The second signature fixes:
  source branch name, base main commit, repository, task ID, every file SHA256,
  commit message, PR title and grant digest. Any mismatching file is denied.
- \`simulate_github_publish\` exercises the GitHub REST commit flow through
  an **injected fixture transport**, never a host token: compare exact remote
  main, ensure new automation branch absent, create bounded Git blobs/tree/
  commit, create only an \`automation/ucie-*\` ref, open a **Draft PR to main**.
  No direct main push, force-update or merge endpoint is available.
- \`src/ucie_public/unattended_c40_supervisor.py\` uses two recent,
  time-ordered *functional* observations of exactly one C40 process, original
  Library search and admin capabilities. One failure is insufficient to
  trigger recovery. At most two restarts per hour, minimum 20-minute cooldown.
  Missing trusted owner lock, idle miner or external rollback gate blocks
  the recovery. Binding a V1 signed C40 grant remains **PLAN ONLY**.
- Offline ephemeral-key and fixture tests cover signature mismatch, changed
  bytes, malicious filenames, stale branch, branch collision, API sequence,
  two-probe failure, false health, duplicate process, restart storm, owner
  signed plan and denial paths.

## Host activation *not* performed

None of these sources install a Windows supervisor, register or restart a
task/service, contact GitHub, fetch credentials or issue real commits/PRs.
They cannot autonomously execute a program to write new learning logic.
The existing ChatGPT MCP admin bridge remains unchanged.

## Required next implementation/approval gates

1. **UCIE-only owner Windows host verifier:** check current principal SID,
   exact trusted root, binary+profile SHA, no reparse links, owner ACL and
   distinct service identity. Existing C40 remains in place. No task duplication.
2. **Durable authorization:** owner identity and host-signed action receipts,
   short-lived per-task grants OR explicitly owner-signed narrow standing
   recovery/publisher policy; distinct from release-signing permission.
   Atomic claim plus externally anchored monotonic anti-rollback receipt,
   including consumed/in-progress/completed state.
3. **Live GitHub App transport:** owner-local, short-lived and repo-scoped
   credentials loaded from a protected OS store; fixed URL/method allowlist,
   no redirects or arbitrary remote commands, bounded responses, no token
   logging. After atomic claim and actual tests, publish a new isolated
   automation branch and Draft PR, then verify real 4-job CI. Retries must
   reconcile partial branch creation and avoid duplicate PRs; never force push.
4. **C40 restart adapter:** separately owned Windows startup task or service,
   exact C40 executable/profile, health checks including actual local MCP
   initialize, tools/list, benign public search. A cloud-side end-to-end
   ChatGPT tool check remains a separate acceptance. Stop only one proven
   owner C40, ensure it exited, launch one replacement; verify functional
   health, cooldown and rollback. Never restart as a response to one brief
   search timeout or an untrusted externally asserted status.
5. **Independent QA and Rulepack:** source and CI PASS never equate to a
   signed candidate/release approval. The collector and Library review
   pipeline remain PUBLIC_ONLY, auto-rule promotion stays OFF.

The current signed grant format is short-lived and does **not** itself confer
continuous autonomous operating authority. Such authority requires an
additional tightly scoped, revocable, separately approved host policy.

## Acceptance interpretation

- Fixed source regression = evidence of **code contract only**.
- Synthetic GitHub REST sequence = **not** an actual push or PR.
- Synthetic C40 watchdog = **not** a recovered tunnel.
- Real one-shot controlled owner host publisher and supervisor test are
  required before treating this infrastructure as unattended READY.
