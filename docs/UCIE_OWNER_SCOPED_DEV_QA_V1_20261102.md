# UCIE one-time scoped development QA consent — V1 (draft)

**UCIE only.** This is source code plus isolated acceptance tests, **not** activated owner-host authority. The `UCIE_OWNER_SCOPED_DEV_QA_V1` module is a local bounded code synchronization primitive designed for a trusted, connected UCIE owner bridge. Do not use this as a general filesystem automation or a release approval.

## Owner intent and contract

- Avoid repeated assistant-generated file downloads and manual PowerShell checks for each UCIE development revision.
- GitHub development uses a **draft PR** and the existing Windows/Ubuntu, Python 3.13/3.15 **four-job CI matrix**, then inspect exact head SHA.
- A **single explicit, local opt-in** records permission for **14 days / at most 12 batches**, restricted to **at most six bounded UTF-8 Python files** per batch, only `src/ucie_miner/` or `tests/test_ucie_*` (deny protected operating files, including this policy module).
- The trusted UCIE bridge must independently call `verify_github_ci_and_source_blobs(commit_sha, file_sha256_map)` before each application. The verifier reads only public GitHub metadata for this UCIE repo, requires one exact successful PR workflow run, all four successful matrix jobs and the exact content at the pinned commit. User-supplied claims, a candidate hash or an old CI result do not confer approval.
- Existing files require exact previous SHA-256; missing files require `ABSENT`. Refuse symlinks, unknown source, malformed grant, duplicate/replayed batch, concurrent transaction, stale/signed-off scope and unsupported paths.
- The host code writes backup copies and a fail-closed journal before applying source bytes, restores modified files on Python exception, and uses short atomic replacements. **Power loss/process death can leave a recovery-required journal**; no false claim of transactional crash recovery.
- Host sync is **code-copy only**: never execute downloaded code on the host. No scheduler changes, operational DB writes, model training, rule promotion, signatures, package publishing or external project access.
- An explicit read-only `inspect_scope` reports NOT_ENROLLED/ACTIVE/EXPIRED/EXHAUSTED/REVOKED without modifying the scope. The trusted bridge-only `revoke_scope` requires exact confirmation, serializes under the same batch lock, and permanently refuses further batch application. Both functions remain **unwired** until trusted UCIE owner bridge identity checks are implemented.
- After a successful source write, a final journal-write failure must roll back both changed files **and the grant's used-batch counter**; never report an applied batch with an incomplete journal.
- The local consent JSON is **not proof of human identity or a secure OS principal**. Only the trusted UCIE owner bridge/OS policy may call `enroll()` and `apply_verified_batch()`, and future integrated tools must preserve the identity/ACL boundary.

## Acceptance accomplished in this branch

`PYTHONPATH=src python -B -m unittest discover -s tests -p test_ucie_owner_scoped_batch_v1.py -v`

This focused offline regression has 47 cases for strict scope, SHA and commit, one-time grant lifetime/budget, exact CI job/source checks with mocked API, collision and symlink defense, exception rollback, and no accidental source execution. **Synthetic tests do not prove owner Windows host acceptance.**

The existing `.github/workflows/stage1-offline-tests.yml` already runs the full offline test suite on Windows/Ubuntu with Python 3.13/3.15 for every PR. Its exact-head CI must be checked separately before merge.

## UCIE-only bridge adapter (code delivered; host not activated)

`src/ucie_miner/owner_scoped_bridge_v1.py` defines four allowlisted bridge calls:
`status`, `enroll`, `revoke`, `apply`. The only accepted request fields
are the fixed schema, operation and its exact operation-specific payload.
A trusted UCIE host bridge must supply an independently authenticated
server-owned session authorizer: a caller-provided string, grant or identity
boolean cannot establish owner identity. The adapter fixes all host roots,
rejects remote `test_mode`, root overrides and alternate CI callbacks, and
binds the existing exact-commit GitHub source/CI verifier.

The adapter freezes validated JSON request data before the session check,
preventing a mutable caller object from changing the bundle mid-authorization.
The adapter does not create a network listener or register an MCP tool.
Focused first-party adapter regressions: 21 cases. A green GitHub matrix
does not prove ACL/identity trust or host deployment.

## Current integration gates

1. **GitHub PR/CI**: branch review and exact-head CI; this does not require a Windows user download.
2. **UCIE bridge**: currently reports `Tunnel-client has not been seen for 300 seconds`. Need the existing UCIE-only tunnel reconnected; do not access any unrelated system to fix it.
3. **Scoped bridge wiring**: connect the implemented `enroll`, `inspect_scope`, `revoke_scope`, and `apply_verified_batch` functions through a trusted, authenticated UCIE-only bridge; never expose `test_mode` or arbitrary callback/file-path arguments to remote callers. This module's CLI deliberately exposes only `--status`; there is **no independent local auto-execution endpoint** and no grant has been created.
4. **Live host acceptance**: verify owner Windows path restrictions, protected grant ACLs, atomic backup/recovery handling, batch safety and real GitHub CI API receipts. Do not infer PASS from PR CI.
5. **Unattended host delivery**: separately bind to an already-authorized UCIE-only event/connector; do not silently register a new scheduled task or accept self-asserted owner approval.

**Until gates 2–5 complete: `SCOPED_DEV_QA_CODE_IMPLEMENTED_HOST_NOT_ACTIVATED`.** GitHub PR CI reduces manual verification now; true no-download no-touch host deployment requires connected trusted bridge.

No other project or private source is part of this proposal.


## C40 automatic recovery at owner logon (opt-in)

The new UCIE-only script scripts/ucie_c40_recover.ps1 registers exactly one
Windows task (UCIE-C40-Recover) under the current owner interactive account.
Its supervised PowerShell process checks the existing pinned UCIE C40 client
every 300 seconds. If the existing C40 process is present, it does nothing;
if absent, it starts the SAME approved tunnel-client and profile only.
It never replaces a profile, creates another tunnel ID, changes other scheduled
tasks, or handles other projects. It runs only after owner logon.

After the file is installed into D:\UCIE\scripts and the owner confirms the
existing UCIE ChatGPT MCP admin app is OWNER-ONLY, register it once:

    & 'D:\UCIE\scripts\ucie_c40_recover.ps1' -Mode Status
    & 'D:\UCIE\scripts\ucie_c40_recover.ps1' -Mode Install -OwnerOnlyConfirmed -EnableAdminTools

Enter APPROVE once at the local prompt. It does not prompt again at the next
owner logon. It refuses to overwrite an existing same-name task. Optional
Remove mode requires -OwnerOnlyConfirmed and explicit REMOVE and unregisters
only UCIE-C40-Recover, leaving the live C40 client alone.
The original PR #78 manual launcher is preserved as a fallback.

This is an owner-approved C40 transport recovery task, not automatic Rulepack
approval or a scope-grant enrollment. The recovery task still needs an actual
Windows registration receipt and reboot/logon test. GitHub CI only checks
static scope and PowerShell syntax. This does not promise recovery when a
disconnected control plane keeps the C40 process alive.

## Owner-scoped FastMCP registration (code only)

The new src/ucie_miner/owner_scoped_mcp_tools_v1.py exposes an explicit
register_ucie_owner_scope_tools() function, with four allowlisted functions:
ucie_owner_scope_status, ucie_owner_scope_enroll, ucie_owner_scope_revoke and
ucie_owner_scope_apply. Existing legacy public search and nine administrator
functions are not replaced or modified. Tests use fake FastMCP registration,
and reject absent or false session authorization.

The new module DOES NOT self-register or start a new MCP listener. A trusted
owner-only C40 server startup hook must supply the authenticated session
callback, under a host-controlled principal. No static identity boolean, user
argument or unverified token may grant source-write permission. Existing owner
approvals in the PR #78 launcher do not by themselves prove the required
protected directory D:\UCIE_HUB\04_MIGRATION\UCIE_OWNER_SCOPED_QA_V1 exists
or has sufficient ACL protection. Real one-batch apply and rollback on this
Windows host are still NO_GO pending explicit host wiring and acceptance.
