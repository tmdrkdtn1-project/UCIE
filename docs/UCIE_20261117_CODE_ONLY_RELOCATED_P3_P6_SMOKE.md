# UCIE 2026-11-17 — actual P3/P6 code-only relocation rehearsal

Project: UCIE ONLY. No Windows owner-host relocation, no transfer of UCIE_DATA/UCIE_PREVIEW or operating services.

## Problem and measurable result

The owner wants `D:\UCIE_PROJECT` with one canonical UCIE Git repo and separate UCIE-only data/preview/archive folders. Live `D:\UCIE` has 230 dirty Git entries and a C40/Task/LocalV1 absolute-path dependency; moving it would risk the UCIE tunnel. GitHub CI validates source behavior, but earlier PR #302/#303 only provided read-only inventory/contract checks. This batch runs **actual existing P3/P6 application search logic** from a staged new-parent layout in a separate first-party CI Python process.

## Actual staged structure in disposable CI runner

```text
<GitHub ephemeral runner temp>/UCIE_PROJECT/UCIE/
  src/ucie_miner/*.py
  src/ucie_public/*.py
  scripts/ucie_isolated_library_smoke_v01.py
```

The test copies **only current UCIE first-party Python source files and the one smoke script** into the temporary relocated layout. The source package contains no Git directory or history, `.venv`, `runtime`, SQLite, P11 opt-in, private C40 data, MCP registration/profile, owner dirty docs or tests. The child process runs `python -I -B` and loads ONLY the staged source path; a SHA-256 lease verifies the exact current first-party `library_exact_index.py` bytes against the originating CI checkout. If a `.git`, runtime, venv or bridge state directory is present, the smoke refuses execution. No D-drive scan or process access.

Actual code-only smoke proves deterministic P3 pagination (27/27 synthetic UCIE source-linked entries in 10+10+7 results, no overlap), P6 one-pass in-memory lookup, multiquery indexing, rejection of forged approval and of malformed nonmatching source, invalid offset fail-closed, and incomplete source ledger NO-GO. It patches public GET, SQLite connect and Python write helpers to deny accidental side effects during the smoke. No test accesses an actual owner's operating data.

## Independent CI verification

New `scripts/ucie_isolated_library_smoke_v01.py` executes inside the relocated Git-less code-only stage. New `tests/test_ucie_isolated_layout_stage_v01.py` constructs the ephemeral stage and launches an actual independent Python interpreter rather than mocking the search behavior. It covers real result equality, source SHA tamper refusal, foreign/missing source, wrong parent, injected PYTHONPATH isolation, no pycache or runtime writes, and symlink denial (skipped only where Windows privilege is unavailable).

Require exact source-HEAD Windows and Ubuntu Python3.13/3.15 existing CI 4/4, inspect all 10 new tests and platform skips separately. No new product feature/algorithm performance claim is made: this is proof of **P3/P6 source portability and behavior at a separated code-only path**, NOT a live plugin/tunnel migration.

## Cutover NO-GO remains

- No creation of D:\UCIE_PROJECT on the owner's drive. CI uses its own ephemeral `UCIE_PROJECT/UCIE` directory on the runner, not the owner's Windows D: drive.
- No on-host exact Task Scheduler actions, C40 one-client process/SID, plug-in tunnel binding, UCIE_DATA/UCIE_PREVIEW profile or ACL validation performed.
- No owner dirty-file inventory/backups (20 tracked modified and 210 untracked) or operating SQLite backup acceptance; no source/Git reset or history rewriting.
- No move of live D:\UCIE; no scheduler change/restart, tunnel/client start/stop, network fetch, Rulepack signing, automatic promotion, actual rollback or customer V1 release.
- The active Private Readonly UCIE bridge remains read-only and cannot create or run a new top-level owner workspace; do not bypass that boundary.

## Concrete next action without repeating gate-only development

Use a scoped **owner-only path staging approval** to create the exact empty D:\UCIE_PROJECT path after verifying existing ACL/drive ownership; preserve live roots and Task/C40 bindings. Obtain the read-only owner Windows Task/C40 source profile snapshot from PR #303, and then stage ONLY a hash-pinned code copy — NOT operating data, not another long-lived Git clone — for a local `-I -B` P3/P6 smoke. Only after that works should the first-party hardcoded path compatibility changes and isolated rollback rehearsals be considered. There is no justification for deleting untracked owner work or taking down the tunnel now.

STATUS=UCIE_RELOCATED_CODE_ONLY_FIRST_PARTY_CI_REHEARSAL__OWNER_RUNTIME_PATH_UNCHANGED__C40_LIVE_TUNNEL_UNVERIFIED__CUSTOMER_V1_NO_GO