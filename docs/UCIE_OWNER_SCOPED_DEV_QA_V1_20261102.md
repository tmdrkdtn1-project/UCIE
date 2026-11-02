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
- The local consent JSON is **not proof of human identity or a secure OS principal**. Only the trusted UCIE owner bridge/OS policy may call `enroll()` and `apply_verified_batch()`, and future integrated tools must preserve the identity/ACL boundary.

## Acceptance accomplished in this branch

`PYTHONPATH=src python -B -m unittest discover -s tests -p test_ucie_owner_scoped_batch_v1.py -v`

This focused offline regression has 37 cases for strict scope, SHA and commit, one-time grant lifetime/budget, exact CI job/source checks with mocked API, collision and symlink defense, exception rollback, and no accidental source execution. **Synthetic tests do not prove owner Windows host acceptance.**

The existing `.github/workflows/stage1-offline-tests.yml` already runs the full offline test suite on Windows/Ubuntu with Python 3.13/3.15 for every PR. Its exact-head CI must be checked separately before merge.

## Current integration gates

1. **GitHub PR/CI**: branch review and exact-head CI; this does not require a Windows user download.
2. **UCIE bridge**: currently reports `Tunnel-client has not been seen for 300 seconds`. Need the existing UCIE-only tunnel reconnected; do not access any unrelated system to fix it.
3. **Scoped bridge wiring**: provide one trusted, bounded `enroll/status/revoke/apply_verified_batch` bridge operation. This module's CLI deliberately exposes only `--status`; there is **no independent local auto-execution endpoint** and no grant has been created.
4. **Live host acceptance**: verify owner Windows path restrictions, protected grant ACLs, atomic backup/recovery handling, batch safety and real GitHub CI API receipts. Do not infer PASS from PR CI.
5. **Unattended host delivery**: separately bind to an already-authorized UCIE-only event/connector; do not silently register a new scheduled task or accept self-asserted owner approval.

**Until gates 2–5 complete: `SCOPED_DEV_QA_CODE_IMPLEMENTED_HOST_NOT_ACTIVATED`.** GitHub PR CI reduces manual verification now; true no-download no-touch host deployment requires connected trusted bridge.

No other project or private source is part of this proposal.
