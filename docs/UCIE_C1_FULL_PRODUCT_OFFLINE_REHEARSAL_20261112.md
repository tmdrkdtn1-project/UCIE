# UCIE V3 B3/C1 — Complete first-party offline PRODUCT rehearsal (2026-11-12 KST)

**Main reference: GitHub issue #199. Project UCIE only. Owner-restricted, no automated customer shipping or skill promotion.**

## Reviewed current state

- User-supplied 2026-11-12 12:30 KST *owner tool receipt*:
  `UCIE_C1_OWNER_OFFLINE_DEPENDENCY_INSTALL_REHEARSAL_V01`,
  `evidence=SAME_OWNER_HOST_DISPOSABLE_VENV_ONLY`,
  `cryptography 50.0.2`, `cffi 2.1.1`, `pycparser 3.12`;
  wheel capture SHA256
  `f7be8672b57a4a879c5651ad22e9cfcb19a77fa7b07d7d97abdca164e94b6fbf`.
  Hash-locked no-index install, pip dependency check and disposable venv cleanup
  were reported PASS; `full_product_installed=false` remains explicit.
- Exact-owner new read-only UCIE-only unittest preflight subsequently reports
  `HASH_LOCKED_DEPENDENCIES_READY_FOR_OWNER_FULL_PRODUCT_CONSENT`.
  This checks local receipt structure and source-bound wheel byte hashes in
  owner test execution, but is **not a publisher signature, legal approval,
  customer acceptance or remote GitHub source-certification of the vendor**.
- PR #246 previously tested only **external dependency** installation. The
  practical next customer product requirement is a FIRST-PARTY UCIE package
  installed *together with* the locked dependencies, then its actual
  **four-pillar CLI and Local V04 UI** exercised in the isolated environment.

## Implemented PR step (no owner Apply yet)

`src/ucie_miner/customer_full_product_offline_rehearsal_v01.py`:

- Default **read-only** UCIE checkout preview; no subprocess, pip, network,
  vendor import, source build, customer file path, TaskScheduler, operating
  database or service change.
- One-time Apply requires exact interactive Windows x64 **standard** Python
  3.15 `D:\UCIE\.venv\Scripts\python.exe`, prior PR245 real PyPI-capture
  integrity receipt, PR246 real same-host dependency rehearsal receipt,
  source-approved UCIE-only fixed product configuration, and a **new**
  distinct typed owner consent.
- The first-party staging uses PR244's **full indexed UCIE Python package
  source** plus PR242's bounded 23-path C0 UI/scripts/docs/config census.
  Each copied source byte has a SHA256-backed manifest and is staged only
  under a disposable `D:\UCIE\downloaded\ucie_c1_full_product_*` directory.
  The operational owner Git worktree is never reset or rebuilt in place.
- A new **stdlib-only PEP 427 temporary wheel recipe** constructs
  `ucie_public_only_demo-0.1.0-py3-none-any.whl` from the copied
  `ucie_miner` and `ucie_public` Python modules (no third-party
  build backend, setuptools/extension hook or network needed). Metadata
  declares the existing `cryptography>=50.0.2,<51` runtime requirement
  and first-party installed CLI entry point. The product wheel is then
  re-read by the existing ZIP/WHEEL/RECORD verifier, and **all UCIE Python
  member bytes must exactly match the staged source**. This is a
  QA-only wheel, **not** a complete redistributable Windows installer:
  the owner Windows launch scripts, static docs and external OS services
  are NOT installed from it.
- Constructs one requirements file with exact SHA256 for the **three
  vendor wheels plus the just-built UCIE wheel**. Creates an entirely
  NEW temporary venv; invokes only that venv's `pip --isolated install
  --no-index --require-hashes --only-binary=:all:` with fixed local
  `--find-links` paths and with resolver enabled (not `--no-deps`).
  Runs `pip check`.
- On the **explicitly approved Apply only**, executes `cryptography`
  native AES-GCM encrypt/decrypt of inert UCIE test bytes, a CFFI declaration,
  and pycparser C declaration. This executes real third-party code, so
  the user must explicitly authorize this step. The pip resolver has no
  online index; this is NOT an OS network sandbox or publisher audit.
- Executes the installed `ucie_miner.customer_staging_v01 --pillar all`
  for the four real first-party engines **on UCIE-owned synthetic inputs**:
  error prevention, capability trials, SkillBook/Library search and
  evidence evolution (record=False). Validates all release and auto-
  promotion flags remain FALSE.
- Executes the installed Local V04 handler against the disposable root,
  self-probing `127.0.0.1` port 0: health, home, Python SkillBook JSON,
  two synthetic engine cases, and denied POST. The existing resident
  `UCIE-LocalV1-Web` on port 18767 is NOT restarted or altered.
- Removes **entire** copied source, wheel, requirements and new venv
  after the procedure. Only a bounded **unsigned first-party QA receipt**
  remains under Git-ignored `downloaded/` after successful technical
  completion. Receipt never states customer GO.

**Important limitations:** This is STILL the **same owner's Windows PC**,
not a second clean recipient host; first-party wheel snapshot is from
the current source tree, not a reproducibly signed/versioned customer
release; no whole-product A→B customer version update/rollback/uninstall
has occurred; native functional smoke is not malware audit; rights/SBOM,
private customer entitlement, C3 signing, C4 recipient and C5 pilot
approval still remain NO-GO.

## Exact owner commands — NO task or web restart

Read-only preview:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_full_product_offline_rehearsal_v01
```

Only after inspecting that result and separately agreeing to execute
third-party code in a **disposable venv**:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_full_product_offline_rehearsal_v01 --apply
```

Required typed phrase:

`RUN_UCIE_C1_FULL_PRODUCT_LOCAL_ONLY_ONCE`

A success receipt is recorded locally at

`D:\UCIE\downloaded\ucie_c1_full_product_rehearsal_receipt_v01.json`

The new path is never automatically uploaded to GitHub, exposed over
Cloudflare or copied to customer storage. A successful receipt means
only **same-owner-host first-party wheel + dependencies + synthetic
four-pillar CLI + localhost UI + native dependency functional smoke**.
No full customer installation or commercial release is certified.

## QA and owner gates

- Test file `tests/test_ucie_c1_full_product_offline_rehearsal_v01.py`
  uses UCIE-owned synthetic ZIP fixtures and a fully MOCKED positive
  pip/native/UI launch workflow. Independent test of the **actual
  stdlib-generated UCIE test wheel and its SHA256 RECORD** is allowed,
  but real external vendor code is never imported or installed in CI
  or UCIE Admin one-file tests.
- Confirm exact-head GitHub Actions Windows/Ubuntu Python 3.13/3.15
  4/4, safe owner source SHA lease & bounded C0/C1/Local V04 regression.
- No forced `git pull`, `reset` or `clean`; existing tracked 17
  owner-local changes preserved. No scheduler/public miner/C40,
  operating SQLite, other project, customer or private repository access.

### Official public packaging format references

- https://packaging.python.org/en/latest/specifications/binary-distribution-format/
- https://packaging.python.org/en/latest/specifications/core-metadata/
- https://pip.pypa.io/en/stable/topics/secure-installs/
- https://docs.python.org/3.15/library/venv.html

**Current full-product commercial decision: `UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO`.**
