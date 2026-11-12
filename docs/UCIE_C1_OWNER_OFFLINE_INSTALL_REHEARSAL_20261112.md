# UCIE C1 — hash-locked, owner-consented OFFLINE wheel install rehearsal (2026-11-12 KST)

**Only UCIE / approved roadmap #199. Technical C1 preview; NOT a customer installer, software release or completed C4 recipient acceptance.**

## Actual starting evidence

- GitHub main after PR #245 is `0aa0edc0e40bb6725209c8f5ffdba2b599f292a1`.
- Owner Windows direct UCIE-only read-only test on 2026-11-12: `UCIE_C1_WHEELHOUSE_READONLY_OWNER_STATE=WAITING_FOR_OWNER_WHEEL_ACQUISITION`. Thus the three approved wheel binaries / local captured PyPI hash receipt have **not yet been observed** in the fixed quarantine.
- PR #245 already built a separate, explicitly owner-approved downloader. It must run first. The new tool in this change does **not** automatically download, call any URL, install source distributions or alter the acquisition code.

## Two distinct operator authorizations

### A. Acquire official PyPI wheel files — download-only (PR #245)

Owner checks default offline preview, then applies only after explicit confirmation:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_owner_wheelhouse_acquire_v01
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_owner_wheelhouse_acquire_v01 --apply
```

Typed one-time confirmation required:
`ACQUIRE_UCIE_C1_WIN315_WHEELS_ONCE`

Actual download is constrained to exact `D:\UCIE`, standard Windows x64 CPython 3.15 in the owner venv and fixed PyPI-only binary candidates:

- `cryptography==50.0.2`
- `cffi==2.1.1`
- `pycparser==3.12`

Accepted files are quarantined exclusively under Git-ignored
`D:\UCIE\downloaded\ucie_c1_offline_wheelhouse_preview\`, with a
separate unsigned hash receipt. This step **does not install or run** them.

Then run a no-network byte integrity recheck:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_owner_wheelhouse_acquire_v01 --verify
```

### B. Separate, consented same-host OFFLINE install rehearsal (this PR)

Default preview is read-only, with no subprocess or network:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_offline_install_rehearsal_v01
```

Only after verified A and separate owner consent:

```powershell
& 'D:\UCIE\.venv\Scripts\python.exe' -B -m ucie_miner.customer_offline_install_rehearsal_v01 --apply
```

Typed phrase:
`RUN_UCIE_C1_DISPOSABLE_OFFLINE_INSTALL_ONCE`

This is a **second, explicit authorization** because unlike download-only,
pip installation may process third-party wheel contents. This source file
must NEVER run `--apply` in GitHub CI or through the restricted UCIE bridge.

## How the C1 install rehearsal is bounded

- Enforces exact owner `D:\UCIE`, owner `.venv\Scripts\python.exe`,
  interactive standard CPython 3.15 x64; refuses CI and any pre-existing
  completed rehearsal receipt. Preserves original owner venv and service.
- Before anything executes, re-verifies captured wheel receipt and hashes
  using PR #245's first-party inspector. Official PyPI hash verification
  occurred at download time; **the saved receipt is unsigned** and is not
  independent publisher provenance or complete supply-chain approval.
- Creates a **new disposable** virtual environment inside a fresh
  UCIE-only `downloaded/ucie_c1_offline_install_*` temporary folder.
  Uses Python standard `venv --copies --without-scm-ignore-files`
  without `--upgrade-deps`, then bundled pip (no network index).
- Generates requirements with every pinned direct/transitive package
  version and its exact captured `--hash=sha256:` value. Calls the new
  venv's pip with `--isolated install --no-index --find-links`,
  `--require-hashes --only-binary=:all: --no-cache-dir --no-input`.
  No `--no-deps`: the resolver must reject missing transitive deps.
- Runs the new venv's `pip check` and reads installed package **metadata**
  under isolated Python. It does **not** import `cryptography` native
  extension code or certify Windows ABI/native feature behavior.
- Temporary venv, requirements and any downloaded/cache scratch files
  are removed after the command. A bounded, first-party JSON test receipt
  is created at
  `downloaded/ucie_c1_isolated_install_rehearsal_receipt_v01.json`
  on complete technical success only; existing receipts are never overwritten.
- Package install can in principle execute distribution behavior. It is
  not an OS-level network sandbox; the pip index is disabled but no claim
  that hostile third-party code cannot contact the network is made.
  Therefore package trust, rights and signatures remain independent gates.

## What these results will and will not prove

If an owner does run Apply and it succeeds, the **only** new result is
the initial same-owner-host **disposable dependency environment** installed
with hash-locked offline wheels and its metadata dependency check succeeded.
This does not prove:

- all first-party UCIE features or static/dynamic resources run in the
  new venv (the previous preview used first-party code only);
- native `cryptography` functional ABI, the external vendor's rights,
  security or publisher identity;
- real package signatures, SPDX/NOTICE and complete SBOM signoff;
- a portable, independently provisioned **second Windows recipient**;
- clean recipient full-product A→B update, rollback and uninstall;
- designated-customer contract, private license/signature or C5 final GO.

All of the above remain `UCIE_FULL_PRODUCT_DESIGNATED_CUSTOMER_NO_GO`.
The UCIE PublicMiner, C40, Cloudflare, scheduler, operating DB, other
projects, existing Local V1 listener and paused 09:00 report are untouched.

## Official procedure references (public technical docs only)

- pip hash checking: https://pip.pypa.io/en/stable/topics/secure-installs/
- pip install offline flags: https://pip.pypa.io/en/stable/cli/pip_install/
- Python venv behavior: https://docs.python.org/3.15/library/venv.html

Test plan: `tests/test_ucie_c1_offline_install_rehearsal_v01.py` has
read-only exact owner presence reporting and **synthetic/mock-only**
installation command tests; it does not execute real wheel files.
Require CI Windows/Ubuntu × Python3.13/3.15 4/4, then owner Windows
C0/C1 regression tests, before merging this code.
