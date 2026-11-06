# UCIE release unblocking — two separate scopes (2026-11-06)

**Scope: UCIE only.** This handoff is an owner decision record, not a release,
license grant, independent-QA verdict, key creation or deployment record.

## Actual observed preflight

- Pinned technical staging code: commit
  `0e62339f1fba7ce0c892d80fbe5cc725c3f5a7c3`.
- Staging source branch:
  `staging/ucie-public-only-0.1.0-integrity-20261106`.
- PR #197 GitHub CI: four Windows/Ubuntu x Python 3.13/3.15 jobs passed.
  This was a **pull_request** CI. It is not the **push-to-main** run that the
  restricted owner-risk signer demands.
- A GitHub lookup for the exact squash-merged commit's workflow run returned no
  completed main-push run. The owner cannot reuse a prior PR run ID.
- Existing owner worktree `D:\UCIE` has tracked modifications and hundreds of
  untracked files. Never reset, clean, overwrite, pull/rebase or sign from it.
- Repo top-level `LICENSE`, `LICENSE.txt`, `COPYING`, `COPYING.txt`
  absent at observed commit. This is **not** permission to redistribute.
- The 09:00 KST UCIE report automation was paused, not silently reactivated.
  The Windows hourly PUBLIC_ONLY collector is a different, unchanged task.

## Track A — FIRST manual static public rule only

The existing owner-approved `AUTOMATED_QA_OWNER_RISK_ACCEPTED` policy (see
`docs/STAGE4_AUTOMATED_QA_OWNER_APPROVAL.md`, issue #50) applies **only** to
the first fixed `PUBLIC_ONLY_MANUAL_STATIC_SCAN` rule. It explicitly does
**not** claim independent human QA or legal license signoff. It cannot be
borrowed for SkillBooks, arbitrary Rulepacks, auto-fix, unattended scanning or
general UCIE V1 release.

### Owner-safe steps (manual, not executed here)

1. Make an **entirely separate clean checkout** of UCIE `main`, not a reset
   of `D:\UCIE`. Do not copy operating DB, `.build_keys`, unrelated
   projects or sensitive files. Verify it is on `main` and
   `git status --porcelain` is empty.
2. Obtain a **new complete actual GitHub Actions `push` run on main** for the
   exact commit that the clean checkout uses. If the merge API did not produce
   a run, a real owner-authorized `git push` of a new reviewed commit from
   the clean checkout is required (for example an explicitly approved
   empty CI-attestation commit). Then fetch the resulting **real** run ID from
   `https://github.com/tmdrkdtn1-project/UCIE/actions`. Recheck all 4 jobs
   and required per-job security/runtime/signed-consumer steps.
3. Before touching keys, execute the read-only command with the
   exact `main` checkout root and verified run ID:

   ```powershell
   $root = 'D:\UCIE_RELEASE\UCIE'
   $py = 'D:\UCIE\.venv\Scripts\python.exe'
   $env:PYTHONPATH = Join-Path $root 'src'
   & $py -B -m ucie_public.owner_risk_preflight_v01 --ucie-root $root --run-id <ACTUAL_MAIN_PUSH_CI_RUN_ID>
   ```

   Required result: `READY_FOR_EXPLICIT_OWNER_SIGNING_DECISION`, exact
   local HEAD == CI HEAD, four expected CI jobs verified. Do not treat this
   as signature, permission or distribution.
4. Only the owner can review the scope and decide whether to accept missing
   independent human review and legal signoff. Existing code requires **two
   separate exact consent strings**. Do not invent or auto-answer them.
5. If explicitly approved, generate/custody the **production Ed25519 key**
   locally in a protected owner-controlled location. Do not reuse demo or
   review keys, expose the private key in chats/logs/CI, or commit it.
   Use the existing `ucie_public.cli keygen-production`,
   `publish-owner-risk-release`, and
   `verify-owner-risk-release` commands exactly as documented in
   `docs/STAGE4_AUTOMATED_QA_OWNER_APPROVAL.md`, with the real CI run ID
   and the **same clean main** checkout.
6. Validate the resulting signed, serial-bound, 7-day-limited package with
   a separate clean recipient and verified owner public-key fingerprint.
   Test harmless synthetic `-SourceText` only via the approved owner-risk
   PowerShell consumer. Distribute only on a separate explicit owner decision.
   Record package SHA-256, owner key ID/public fingerprint, serial, scope,
   recipient acknowledgement and rollback/minimum-serial handling.

**If anything does not match:** NO_GO. Do not sign and do not silently
switch to the independent-QA package verifier (different channel).

## Track B — general UCIE V1 / reusable SkillBook distribution

Not covered by Track A's exception. The code-rights owner(s) must decide:

- Is this first-party UCIE code intended to be open-licensed (e.g. MIT or
  Apache-2.0, after ownership checks), or licensed only to specified
  recipients under separate terms? A public GitHub repo is not by itself
  an open-source license. No license text or ownership claim is fabricated.
- Which individuals/organizations own the submitted source and have authority
  to grant a license? Do all contributors agree? Which third-party dependency
  license notices and original public-document attribution must be included?
- For each packaged artifact, list the exact contents and source SHA, any
  upstream code excerpts, license and NOTICE obligations, opt-out/right-to-
  delete handling, approved redistribution audience, recipient and version.
- Run independent security/functional review (or an explicitly authorized
  and scope-specific alternative where legally sufficient); archive signed
  findings on exact commit/source/wheel SHA, *not* just 'CI green'.
- Require an owner-signed release decision and package signatures with
  recipient verification and rollback plan. Never use first-rule
  `AUTOMATED_QA_OWNER_RISK_ACCEPTED` as V1-wide approval.

## Blocking evidence gates

| Gate | Restricted first rule | General V1 |
|---|---|---|
| Clean isolated main checkout | PENDING OWNER | PENDING OWNER |
| Exact successful main-push CI and 4 job/step match | PENDING | PENDING |
| Technical staging wheel checksum, contents | PR #197 PASS | PR #197 PASS only |
| Code ownership and licensing decision | Risk accepted only if owner chooses | PENDING owner/legal |
| Independent human QA | Optional by existing specific policy | PENDING or valid scope-specific approval |
| Owner production key and signed approval | PENDING owner | PENDING owner |
| Recipient verification and rollback trial | PENDING | PENDING |
| Hourly collector modification | NOT REQUESTED | NOT REQUESTED |
| UCIE 09:00 report activation | PAUSED | PAUSED |

**Release verdict: NO_GO until the exact chosen track is fully evidenced.**
The historical 2026-11-05 incident is not an active blocking gate unless
the same failure recurs with new exact evidence.
